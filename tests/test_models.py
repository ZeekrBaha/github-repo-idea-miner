from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from reporadar.models import (
    DuplicationLevel,
    IdeaCluster,
    IdeaRecommendation,
    LocalProject,
    RepoCandidate,
    RepoScores,
)


def _repo(**over: object) -> RepoCandidate:
    base: dict[str, object] = dict(
        full_name="acme/agent-qa",
        url="https://github.com/acme/agent-qa",
        description="AI QA agent",
        stars=120,
        forks=8,
        language="Python",
        topics=["ai", "qa"],
        pushed_at=datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        source_query="AI QA agent",
    )
    base.update(over)
    return RepoCandidate(**base)  # type: ignore[arg-type]


def test_repo_candidate_parses_valid():
    repo = _repo()
    assert repo.full_name == "acme/agent-qa"
    assert repo.topics == ["ai", "qa"]
    assert repo.readme_text is None


def test_repo_candidate_rejects_negative_stars():
    with pytest.raises(ValidationError):
        _repo(stars=-1)


def test_local_project_minimal():
    proj = LocalProject(name="promptlab", path="/tmp/promptlab", inferred_tags=["llm", "eval"])
    assert proj.repo_url is None
    assert "eval" in proj.inferred_tags


def test_repo_scores_reject_out_of_range():
    with pytest.raises(ValidationError):
        RepoScores(
            portfolio_fit=11,
            market_pain=5,
            novelty=5,
            buildability=5,
            demo=5,
            differentiation=5,
            proof=5,
        )


def test_repo_scores_valid_range():
    scores = RepoScores(
        portfolio_fit=9,
        market_pain=8,
        novelty=7,
        buildability=8,
        demo=6,
        differentiation=7,
        proof=6,
    )
    assert scores.portfolio_fit == 9


def test_duplication_level_ordering():
    assert DuplicationLevel.duplicate.penalty == 4
    assert DuplicationLevel.none.penalty == 0
    assert DuplicationLevel.adjacent.penalty == 1
    assert DuplicationLevel.similar.penalty == 2


def test_idea_cluster_parses():
    cluster = IdeaCluster(
        id="agentic_qa",
        name="Agentic QA",
        summary="Browser QA agents",
        repos=["acme/agent-qa"],
        keywords=["qa", "agent"],
    )
    assert cluster.id == "agentic_qa"


def test_idea_recommendation_requires_source_repos():
    with pytest.raises(ValidationError):
        IdeaRecommendation(
            title="Flight Recorder",
            score=9.0,
            source_repos=[],
            why_interesting="x",
            local_duplication="none",
            differentiated_angle="x",
            mvp_scope=["a"],
            validation_plan=["b"],
            tech_stack=["python"],
            kanban_task_title="t",
            kanban_task_body="b",
        )
