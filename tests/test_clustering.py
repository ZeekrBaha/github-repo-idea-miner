from datetime import UTC, datetime

from reporadar.analysis.clustering import cluster_repos
from reporadar.models import RepoCandidate


def _repo(name: str, desc: str) -> RepoCandidate:
    return RepoCandidate(
        full_name=f"org/{name}",
        url=f"https://github.com/org/{name}",
        description=desc,
        stars=10,
        forks=1,
        language="Python",
        topics=[],
        pushed_at=datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        readme_summary=desc,
        source_query="q",
    )


def test_groups_repos_by_theme():
    repos = [
        _repo("qa1", "Playwright autonomous QA testing agent"),
        _repo("qa2", "Self-healing browser agent for QA"),
        _repo("eval1", "LLM eval harness and judge calibration"),
    ]
    clusters = {c.id: c for c in cluster_repos(repos)}
    assert "agentic-qa" in clusters
    assert set(clusters["agentic-qa"].repos) == {"org/qa1", "org/qa2"}
    assert "llm-eval" in clusters


def test_unmatched_repo_goes_to_other():
    clusters = {c.id: c for c in cluster_repos([_repo("misc", "A weather forecast CLI")])}
    assert "other" in clusters
    assert clusters["other"].repos == ["org/misc"]


def test_empty_input_returns_no_clusters():
    assert cluster_repos([]) == []


def test_clusters_have_keywords_and_names():
    clusters = cluster_repos([_repo("qa", "Playwright QA agent")])
    assert clusters[0].name
    assert clusters[0].keywords


def test_repo_can_belong_to_multiple_themes():
    repos = [_repo("both", "LLM eval dashboard with Playwright QA agent")]
    cluster_ids = {c.id for c in cluster_repos(repos)}
    assert {"agentic-qa", "llm-eval"} <= cluster_ids


def test_clusters_are_deterministic():
    repos = [_repo("a", "LLM eval"), _repo("b", "QA agent Playwright")]
    first = [(c.id, tuple(c.repos)) for c in cluster_repos(repos)]
    second = [(c.id, tuple(c.repos)) for c in cluster_repos(repos)]
    assert first == second
