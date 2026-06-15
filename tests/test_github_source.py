import httpx
import pytest

from reporadar.sources.github import GitHubClient, RateLimitError

SEARCH_PAYLOAD = {
    "total_count": 2,
    "items": [
        {
            "full_name": "acme/agent-qa",
            "html_url": "https://github.com/acme/agent-qa",
            "description": "AI QA agent",
            "stargazers_count": 120,
            "forks_count": 8,
            "language": "Python",
            "topics": ["ai", "qa"],
            "pushed_at": "2026-05-01T00:00:00Z",
            "created_at": "2025-01-01T00:00:00Z",
        },
        {
            "full_name": "beta/llm-eval",
            "html_url": "https://github.com/beta/llm-eval",
            "description": None,
            "stargazers_count": 50,
            "forks_count": 2,
            "language": None,
            "topics": [],
            "pushed_at": "2026-04-01T00:00:00Z",
            "created_at": "2024-06-01T00:00:00Z",
        },
    ],
}


def _client(handler: httpx.MockTransport) -> GitHubClient:
    return GitHubClient(client=httpx.Client(transport=handler, base_url="https://api.github.com"))


def test_search_repos_maps_candidates():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/repositories"
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    client = _client(httpx.MockTransport(handler))
    repos = client.search_repos("AI QA agent", limit=10)
    assert [r.full_name for r in repos] == ["acme/agent-qa", "beta/llm-eval"]
    assert repos[0].stars == 120
    assert repos[0].source_query == "AI QA agent"
    assert repos[1].description is None


def test_search_repos_respects_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    client = _client(httpx.MockTransport(handler))
    repos = client.search_repos("anything", limit=1)
    assert len(repos) == 1


def test_search_repos_empty_results():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": 0, "items": []})

    client = _client(httpx.MockTransport(handler))
    assert client.search_repos("nothing", limit=10) == []


def test_rate_limit_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0"},
            json={"message": "API rate limit exceeded"},
        )

    client = _client(httpx.MockTransport(handler))
    with pytest.raises(RateLimitError):
        client.search_repos("x", limit=10)


def test_search_many_skips_failing_queries():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                403,
                headers={"X-RateLimit-Remaining": "0"},
                json={"message": "rate limited"},
            )
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    client = _client(httpx.MockTransport(handler))
    repos, errors = client.search_many(["q1", "q2"], limit_per_query=10)
    # First query rate-limited (recorded as error), second succeeds.
    assert any("q1" in e for e in errors)
    assert {r.full_name for r in repos} == {"acme/agent-qa", "beta/llm-eval"}


def test_search_many_dedupes_repos():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    client = _client(httpx.MockTransport(handler))
    repos, errors = client.search_many(["q1", "q2"], limit_per_query=10)
    assert errors == []
    # Same repos returned for both queries -> de-duplicated by full_name.
    assert len(repos) == 2


def test_search_repos_paginates_beyond_one_page():
    # B12: limits over a single page must fetch additional pages.
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        per_page = int(request.url.params.get("per_page", "100"))
        if page == 1:
            items = [_item(i) for i in range(per_page)]  # full page -> more exist
        elif page == 2:
            items = [_item(100 + i) for i in range(50)]  # partial page -> last
        else:
            items = []
        return httpx.Response(200, json={"items": items})

    client = _client(httpx.MockTransport(handler))
    repos = client.search_repos("q", limit=150)
    assert len(repos) == 150
    assert repos[0].full_name == "org/repo-0"
    assert repos[-1].full_name == "org/repo-149"


def _item(i: int) -> dict[str, object]:
    return {
        "full_name": f"org/repo-{i}",
        "html_url": f"https://github.com/org/repo-{i}",
        "description": None,
        "stargazers_count": 10,
        "forks_count": 0,
        "language": "Python",
        "topics": [],
        "pushed_at": "2026-05-01T00:00:00Z",
        "created_at": "2025-01-01T00:00:00Z",
    }


def test_user_agent_has_no_fabricated_repo_url():
    # B13: do not advertise a GitHub URL that may not exist.
    client = GitHubClient()
    headers = client._headers("application/vnd.github+json")
    assert "github.com/baha" not in headers["User-Agent"]


def test_fetch_readme_returns_text():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/acme/agent-qa/readme"
        return httpx.Response(200, text="# Agent QA\n\nDoes things.")

    client = _client(httpx.MockTransport(handler))
    assert client.fetch_readme("acme/agent-qa") == "# Agent QA\n\nDoes things."


def test_fetch_readme_missing_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = _client(httpx.MockTransport(handler))
    assert client.fetch_readme("acme/none") is None
