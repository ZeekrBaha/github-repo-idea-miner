"""GitHub source client (REST API) with graceful rate-limit handling.

Network access is injected via an :class:`httpx.Client`, so tests drive it with
``httpx.MockTransport`` and never hit the network. A ``GITHUB_TOKEN`` env var is
used automatically when present to lift the unauthenticated rate limit, but it
is never required.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from reporadar.models import RepoCandidate

API_BASE = "https://api.github.com"
_USER_AGENT = "reporadar/0.1"


class RateLimitError(RuntimeError):
    """Raised when GitHub reports the rate limit is exhausted."""


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        if client is not None:
            self._client = client
        else:
            self._client = httpx.Client(base_url=API_BASE, timeout=timeout)

    def _headers(self, accept: str) -> dict[str, str]:
        headers = {"Accept": accept, "User-Agent": _USER_AGENT}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @staticmethod
    def _is_rate_limited(response: httpx.Response) -> bool:
        if response.status_code not in (403, 429):
            return False
        return bool(response.headers.get("X-RateLimit-Remaining") == "0")

    def search_repos(self, query: str, limit: int = 30) -> list[RepoCandidate]:
        """Run one GitHub repository search and map results to candidates.

        Raises :class:`RateLimitError` when GitHub reports the limit is hit.
        """

        per_page = max(1, min(limit, 100))
        collected: list[dict[str, Any]] = []
        page = 1
        while len(collected) < limit:
            response = self._client.get(
                "/search/repositories",
                params={
                    "q": query,
                    "per_page": per_page,
                    "page": page,
                    "sort": "stars",
                    "order": "desc",
                },
                headers=self._headers("application/vnd.github+json"),
            )
            if self._is_rate_limited(response):
                raise RateLimitError(f"GitHub rate limit exhausted for query: {query!r}")
            response.raise_for_status()

            items = response.json().get("items", [])
            if not items:
                break
            collected.extend(items)
            # A short page means we've reached the end of the results.
            if len(items) < per_page:
                break
            page += 1

        return [self._to_candidate(item, query) for item in collected[:limit]]

    def search_many(
        self, queries: list[str], limit_per_query: int = 30
    ) -> tuple[list[RepoCandidate], list[str]]:
        """Run several queries, de-duplicating repos and collecting error notes.

        Failures (rate limits, HTTP/network errors) for one query never abort
        the others — they are recorded in the returned ``errors`` list so the
        caller can surface a real blocker without crashing the pipeline.
        """

        seen: dict[str, RepoCandidate] = {}
        errors: list[str] = []
        for query in queries:
            try:
                for repo in self.search_repos(query, limit=limit_per_query):
                    seen.setdefault(repo.full_name, repo)
            except RateLimitError as exc:
                errors.append(f"[{query}] rate limited: {exc}")
            except httpx.HTTPError as exc:
                errors.append(f"[{query}] network/HTTP error: {exc}")
        return list(seen.values()), errors

    def fetch_readme(self, full_name: str) -> str | None:
        """Fetch raw README text for ``owner/repo``; ``None`` if unavailable."""

        try:
            response = self._client.get(
                f"/repos/{full_name}/readme",
                headers=self._headers("application/vnd.github.raw"),
            )
        except httpx.HTTPError:
            return None
        if self._is_rate_limited(response):
            raise RateLimitError(f"GitHub rate limit exhausted fetching README: {full_name}")
        if response.status_code != 200:
            return None
        return response.text

    @staticmethod
    def _to_candidate(item: dict[str, Any], query: str) -> RepoCandidate:
        topics = item.get("topics") or []
        return RepoCandidate(
            full_name=str(item["full_name"]),
            url=str(item["html_url"]),
            description=item.get("description") or None,
            stars=int(item.get("stargazers_count", 0) or 0),
            forks=int(item.get("forks_count", 0) or 0),
            language=item.get("language") or None,
            topics=[str(topic) for topic in topics],
            pushed_at=_parse_dt(str(item["pushed_at"])),
            created_at=_parse_dt(str(item["created_at"])),
            source_query=query,
        )


def _parse_dt(value: str) -> datetime:
    # GitHub returns ISO-8601 with a trailing Z; normalize to +00:00 offset.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
