import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from typer.testing import CliRunner

import reporadar.cli as cli
from reporadar.pipeline import run_mine
from reporadar.sources.github import GitHubClient

runner = CliRunner()
NOW = datetime(2026, 6, 15, tzinfo=UTC)

SEARCH_PAYLOAD = {
    "items": [
        {
            "full_name": "acme/agent-qa",
            "html_url": "https://github.com/acme/agent-qa",
            "description": "Playwright autonomous QA testing agent dashboard",
            "stargazers_count": 300,
            "forks_count": 20,
            "language": "Python",
            "topics": ["qa", "ai"],
            "pushed_at": "2026-05-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
        },
        {
            "full_name": "beta/llm-eval",
            "html_url": "https://github.com/beta/llm-eval",
            "description": "LLM eval harness judge calibration metrics ci tests",
            "stargazers_count": 450,
            "forks_count": 30,
            "language": "Python",
            "topics": ["eval"],
            "pushed_at": "2026-04-01T00:00:00Z",
            "created_at": "2024-06-01T00:00:00Z",
        },
    ]
}


def _mock_client() -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/repositories":
            return httpx.Response(200, json=SEARCH_PAYLOAD)
        if request.url.path.endswith("/readme"):
            return httpx.Response(200, text="# Repo\n\nDoes useful agentic QA things.")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    return GitHubClient(client=httpx.Client(transport=transport, base_url="https://api.github.com"))


def _rate_limited_readme_client() -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/repositories":
            return httpx.Response(200, json=SEARCH_PAYLOAD)
        # Every README fetch is rate-limited.
        return httpx.Response(
            403, headers={"X-RateLimit-Remaining": "0"}, json={"message": "rate limited"}
        )

    transport = httpx.MockTransport(handler)
    return GitHubClient(client=httpx.Client(transport=transport, base_url="https://api.github.com"))


def test_readme_rate_limit_does_not_stop_the_enrichment_loop(tmp_path: Path):
    # B3: a rate limit on one README must not abort enrichment for the rest;
    # every affected repo is logged so the run stays comparable and complete.
    report = run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=_rate_limited_readme_client(),
        now=NOW,
    )
    assert report.repos_scanned == 2
    readme_notes = [e for e in report.errors if "readme" in e.lower()]
    assert len(readme_notes) >= 2  # both repos accounted for, not just the first


def test_cache_avoids_refetching_on_second_run(tmp_path: Path):
    from reporadar.cache import SearchCache

    calls = {"search": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/repositories":
            calls["search"] += 1
            return httpx.Response(200, json=SEARCH_PAYLOAD)
        return httpx.Response(200, text="# Repo\n\nagentic QA things.")

    transport = httpx.MockTransport(handler)
    client = GitHubClient(
        client=httpx.Client(transport=transport, base_url="https://api.github.com")
    )
    cache = SearchCache(tmp_path / "cache.db")

    run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=client,
        now=NOW,
        cache=cache,
    )
    after_first = calls["search"]
    assert after_first > 0

    run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=client,
        now=NOW,
        cache=cache,
    )
    assert calls["search"] == after_first  # second run served entirely from cache


def test_cache_hit_miss_counts_reported(tmp_path: Path):
    from reporadar.cache import SearchCache

    cache = SearchCache(tmp_path / "cache.db")
    first = run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=_mock_client(),
        now=NOW,
        cache=cache,
    )
    assert first.cache_misses > 0
    assert first.cache_hits == 0

    second = run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=_mock_client(),
        now=NOW,
        cache=cache,
    )
    assert second.cache_hits > 0
    assert second.cache_misses == 0


def test_search_errors_recorded_with_cache_present(tmp_path: Path):
    from reporadar.cache import SearchCache
    from reporadar.sources.github import RateLimitError

    class _ErroringClient:
        def search_repos(self, query: str, limit: int):
            if "QA" in query:
                raise RateLimitError("rate limited")
            raise httpx.ConnectError("boom")

        def fetch_readme(self, full_name: str):
            return None

    report = run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,
        client=_ErroringClient(),  # type: ignore[arg-type]
        now=NOW,
        cache=SearchCache(tmp_path / "cache.db"),
    )
    assert report.repos_scanned == 0
    assert any("rate limited" in e for e in report.errors)
    assert any("network/HTTP error" in e for e in report.errors)


def test_run_mine_end_to_end(tmp_path: Path):
    report = run_mine(
        profile_name="baha-ai-qa",
        limit=10,
        locals_root=tmp_path,  # empty -> no local dedupe
        client=_mock_client(),
        now=NOW,
    )
    assert report.repos_scanned == 2
    assert report.ideas
    assert all(idea.source_repos for idea in report.ideas)


def test_mine_command_writes_reports(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "build_github_client", _mock_client)
    out = tmp_path / "out.md"

    result = runner.invoke(
        cli.app,
        [
            "mine",
            "--profile",
            "baha-ai-qa",
            "--limit",
            "10",
            "--root",
            str(tmp_path),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    json_out = out.with_suffix(".json")
    assert json_out.exists()
    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["profile"] == "baha-ai-qa"
    assert len(data["repos"]) == 2


def test_mine_dry_run_lists_queries_without_fetching(tmp_path: Path, monkeypatch):
    def _boom() -> GitHubClient:
        raise AssertionError("dry-run must not build a GitHub client")

    monkeypatch.setattr(cli, "build_github_client", _boom)
    out = tmp_path / "out.md"

    result = runner.invoke(
        cli.app,
        [
            "mine",
            "--profile",
            "baha-ai-qa",
            "--dry-run",
            "--root",
            str(tmp_path),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "dry run" in result.stdout.lower()
    assert "pushed:" in result.stdout  # a real query line is shown
    assert not out.exists()  # nothing written


def test_mine_unknown_profile_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "build_github_client", _mock_client)
    result = runner.invoke(cli.app, ["mine", "--profile", "nope", "--root", str(tmp_path)])
    assert result.exit_code == 2
