"""End-to-end mining pipeline: search → enrich → scan → score → cluster → ideas.

The GitHub client is injected so the whole pipeline is testable with a mock
transport and never requires network access or a token in tests. Source errors
(rate limits, network failures) are collected, not raised, so a partial run still
produces a useful report and a real, documented blocker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from reporadar.analysis.clustering import cluster_repos
from reporadar.analysis.ideas import generate_ideas
from reporadar.analysis.readme import summarize_readme
from reporadar.analysis.scoring import ScoringConfig, load_scoring_config, score_repos
from reporadar.cache import SearchCache
from reporadar.config import load_profile
from reporadar.local.scanner import scan_local_projects
from reporadar.models import RepoCandidate
from reporadar.reports.report import MineReport
from reporadar.sources.github import GitHubClient, RateLimitError


@dataclass
class _SearchResult:
    repos: list[RepoCandidate]
    errors: list[str]
    cache_hits: int
    cache_misses: int


def _search_all(
    client: GitHubClient,
    queries: list[str],
    limit: int,
    cache: SearchCache | None,
    day: str,
) -> _SearchResult:
    """Search every query, using the cache when present, de-duplicating repos."""

    seen: dict[str, RepoCandidate] = {}
    errors: list[str] = []
    hits = 0
    misses = 0
    for query in queries:
        cached = cache.get(query, limit, day) if cache else None
        if cached is not None:
            hits += 1
            repos = [RepoCandidate(**item) for item in cached]
        else:
            misses += 1
            try:
                repos = client.search_repos(query, limit=limit)
            except RateLimitError as exc:
                errors.append(f"[{query}] rate limited: {exc}")
                continue
            except httpx.HTTPError as exc:
                errors.append(f"[{query}] network/HTTP error: {exc}")
                continue
            if cache is not None:
                cache.put(query, limit, day, [r.model_dump(mode="json") for r in repos])
        for repo in repos:
            seen.setdefault(repo.full_name, repo)
    return _SearchResult(list(seen.values()), errors, hits, misses)


def run_mine(
    *,
    profile_name: str,
    limit: int,
    locals_root: Path,
    client: GitHubClient,
    now: datetime,
    scoring_config: ScoringConfig | None = None,
    profiles_path: Path | None = None,
    enrich_readmes: bool = True,
    cache: SearchCache | None = None,
) -> MineReport:
    config = scoring_config or load_scoring_config()
    profile = load_profile(profile_name, profiles_path)

    # 1. Search GitHub across all profile queries (cache-aware, keyed by day).
    search = _search_all(client, profile.queries, limit, cache, now.date().isoformat())
    repos, errors = search.repos, search.errors

    # Keep the most-starred repos up to the overall limit for a deterministic set.
    repos.sort(key=lambda r: (r.stars, r.full_name), reverse=True)
    repos = repos[:limit]

    # 2. Enrich READMEs (best effort). A rate limit on one repo must not abort
    #    the rest: once limited, remaining repos are logged and skipped (no
    #    further API hammering) so every repo is accounted for and the run stays
    #    internally comparable rather than enriching an arbitrary prefix.
    if enrich_readmes:
        rate_limited = False
        for repo in repos:
            if rate_limited:
                errors.append(f"readme skipped (rate limited earlier): {repo.full_name}")
                continue
            try:
                text = client.fetch_readme(repo.full_name)
            except RateLimitError as exc:
                rate_limited = True
                errors.append(f"readme rate limit hit at {repo.full_name}: {exc}")
                continue
            if text:
                repo.readme_text = text
                summary = summarize_readme(text)
                if summary.summary:
                    repo.readme_summary = summary.summary

    # 3. Scan local portfolio.
    locals_ = scan_local_projects(locals_root)

    # 4. Score, cluster, and generate ideas.
    scored = score_repos(repos, locals_, config=config, now=now)
    clusters = cluster_repos(repos)
    by_name = {s.repo.full_name: s for s in scored}
    ideas = generate_ideas(clusters, by_name)

    return MineReport(
        generated_at=now,
        profile=profile_name,
        repos_scanned=len(repos),
        scored=scored,
        clusters=clusters,
        ideas=ideas,
        errors=errors,
        cache_hits=search.cache_hits,
        cache_misses=search.cache_misses,
    )
