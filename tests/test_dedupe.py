from datetime import UTC, datetime

from reporadar.analysis.dedupe import check_duplication, repo_tags
from reporadar.models import DuplicationLevel, LocalProject, RepoCandidate


def _repo(name: str, desc: str, summary: str = "") -> RepoCandidate:
    return RepoCandidate(
        full_name=f"someorg/{name}",
        url=f"https://github.com/someorg/{name}",
        description=desc,
        stars=10,
        forks=1,
        language="Python",
        topics=[],
        pushed_at=datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        readme_summary=summary,
        source_query="q",
    )


LOCALS = [
    LocalProject(
        name="promptlab",
        path="/x/promptlab",
        readme_title="PromptLab",
        readme_summary="LLM prompt regression eval harness.",
        inferred_tags=["llm-eval", "prompt"],
    ),
    LocalProject(
        name="agentic-qa",
        path="/x/agentic-qa",
        readme_title="Agentic QA",
        readme_summary="Self-healing Playwright browser QA agent.",
        inferred_tags=["agentic-qa"],
    ),
]


def test_repo_tags_uses_name_and_text():
    repo = _repo("eval-thing", "LLM eval harness", "prompt regression eval")
    assert "llm-eval" in repo_tags(repo)


def test_clear_duplicate_detected():
    repo = _repo(
        "promptlab", "LLM prompt regression eval harness", "prompt regression eval harness"
    )
    result = check_duplication(repo, LOCALS)
    assert result.level == DuplicationLevel.duplicate
    assert "promptlab" in result.matched_projects


def test_unrelated_repo_is_none():
    repo = _repo("weather-cli", "A command line weather forecast tool", "shows the weather")
    result = check_duplication(repo, LOCALS)
    assert result.level == DuplicationLevel.none
    assert result.matched_projects == []


def test_shared_theme_is_at_least_adjacent():
    repo = _repo("browser-bot", "Playwright autonomous QA testing agent", "browser agent testing")
    result = check_duplication(repo, LOCALS)
    assert result.level in (
        DuplicationLevel.adjacent,
        DuplicationLevel.similar,
        DuplicationLevel.duplicate,
    )
    assert "agentic-qa" in result.matched_projects


def test_no_shared_theme_not_matched_despite_text_overlap():
    # An unrelated iOS app shares no theme tag; rich candidate text must not
    # spuriously flag it via length-asymmetric token matching.
    repo = _repo(
        "rag-tool",
        "RAG retrieval augmented generation evaluation framework for LLM apps",
        "rag retrieval eval app framework",
    )
    ios = LocalProject(
        name="magic-coffee-ios",
        path="/x",
        readme_title="Magic Coffee",
        readme_summary="A SwiftUI iOS coffee ordering app",
        inferred_tags=[],
    )
    result = check_duplication(repo, [ios])
    assert "magic-coffee-ios" not in result.matched_projects
    assert result.level == DuplicationLevel.none


def test_token_subset_local_without_shared_tag_not_matched():
    # Regression: a short local summary whose tokens are a subset of a long
    # candidate README must NOT be flagged when no theme tag is shared.
    repo = _repo(
        "agent-orchestra",
        "Agent orchestration dashboard for coding agents with worktree isolation",
        "agent orchestration dashboard live map flight deck for coding agents worktree",
    )
    unrelated = LocalProject(
        name="flightdeck-live-map",
        path="/x",
        readme_title="FlightDeck",
        readme_summary="live map flight deck",
        inferred_tags=[],
    )
    result = check_duplication(repo, [unrelated])
    assert "flightdeck-live-map" not in result.matched_projects


def test_empty_locals_returns_none():
    repo = _repo("promptlab", "prompt eval", "prompt eval")
    result = check_duplication(repo, [])
    assert result.level == DuplicationLevel.none


def test_result_is_deterministic():
    repo = _repo("promptlab", "LLM prompt regression eval harness", "prompt regression eval")
    first = check_duplication(repo, LOCALS)
    second = check_duplication(repo, LOCALS)
    assert first.level == second.level
    assert first.matched_projects == second.matched_projects
