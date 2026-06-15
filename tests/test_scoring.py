from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from reporadar.analysis.scoring import (
    ScoringConfig,
    _differentiation,
    load_scoring_config,
    score_repos,
)
from reporadar.models import DuplicationLevel, LocalProject, RepoCandidate

NOW = datetime(2026, 6, 15, tzinfo=UTC)


def _repo(name: str, desc: str, stars: int = 100, pushed: datetime | None = None) -> RepoCandidate:
    return RepoCandidate(
        full_name=f"org/{name}",
        url=f"https://github.com/org/{name}",
        description=desc,
        stars=stars,
        forks=stars // 10,
        language="Python",
        topics=[],
        pushed_at=pushed or datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        readme_summary=desc,
        source_query="q",
    )


def test_load_scoring_config_weights_sum_to_one():
    config = load_scoring_config()
    assert abs(sum(config.weights.values()) - 1.0) < 1e-9


def test_scores_are_deterministic():
    repo = _repo("agent-qa", "AI QA agent with Playwright self healing browser testing")
    a = score_repos([repo], [], config=load_scoring_config(), now=NOW)
    b = score_repos([repo], [], config=load_scoring_config(), now=NOW)
    assert a[0].overall == b[0].overall
    assert a[0].scores.model_dump() == b[0].scores.model_dump()


def test_results_sorted_descending():
    repos = [
        _repo("plain", "A generic todo list app", stars=10),
        _repo("qa-agent", "LLM eval harness and Playwright QA agent dashboard", stars=500),
    ]
    results = score_repos(repos, [], config=load_scoring_config(), now=NOW)
    assert results[0].overall >= results[1].overall
    assert results[0].repo.full_name == "org/qa-agent"


def test_ai_qa_relevance_ranks_higher():
    relevant = _repo("a", "LLM eval harness Playwright QA agent observability")
    generic = _repo("b", "A simple weather forecast CLI")
    results = {
        r.repo.full_name: r.overall
        for r in score_repos([relevant, generic], [], config=load_scoring_config(), now=NOW)
    }
    assert results["org/a"] > results["org/b"]


def test_duplication_penalty_lowers_score():
    repo = _repo("promptlab", "LLM prompt regression eval harness")
    locals_ = [
        LocalProject(
            name="promptlab",
            path="/x",
            readme_title="PromptLab",
            readme_summary="LLM prompt regression eval harness",
            inferred_tags=["llm-eval", "prompt"],
        )
    ]
    with_dup = score_repos([repo], locals_, config=load_scoring_config(), now=NOW)[0]
    without_dup = score_repos([repo], [], config=load_scoring_config(), now=NOW)[0]
    assert with_dup.duplication.level == DuplicationLevel.duplicate
    assert with_dup.overall < without_dup.overall


def test_stale_repo_ranks_lower_than_fresh():
    fresh = _repo("fresh", "LLM eval harness QA agent", pushed=NOW)
    stale = _repo("stale", "LLM eval harness QA agent", pushed=NOW - timedelta(days=900))
    results = {
        r.repo.full_name: r.overall
        for r in score_repos([fresh, stale], [], config=load_scoring_config(), now=NOW)
    }
    assert results["org/fresh"] > results["org/stale"]


def test_scores_within_range():
    repo = _repo("x", "AI QA agent eval dashboard tests ci coverage", stars=2000)
    result = score_repos([repo], [], config=load_scoring_config(), now=NOW)[0]
    for value in result.scores.model_dump().values():
        assert 1 <= value <= 10
    assert isinstance(result.overall, float)


def test_differentiation_monotonic_decreasing_with_duplication():
    # B2: more duplication must never raise the differentiation score.
    assert (
        _differentiation(DuplicationLevel.none)
        > _differentiation(DuplicationLevel.adjacent)
        > _differentiation(DuplicationLevel.similar)
        > _differentiation(DuplicationLevel.duplicate)
    )


def test_scoring_config_rejects_weights_not_summing_to_one():
    # B4: misconfigured weights must fail loudly, not drift silently.
    with pytest.raises(ValidationError):
        ScoringConfig(
            weights={"portfolio_fit": 0.5, "market_pain": 0.2},
            duplication_penalty={"none": 0, "adjacent": 1, "similar": 2, "duplicate": 4},
            stale_after_days=365,
        )


def test_buildability_rewards_readme_signals():
    # B6: a repo with tests/CI/install signals must out-score a bare repo.
    bare = _repo("bare", "A small tool", stars=10)
    rich = _repo("rich", "A small tool", stars=10)
    rich.readme_text = (
        "# Tool\n\n## Installation\nInstall via pip.\n\n## Tests\n"
        "Run pytest. CI passing. coverage 95%.\n\n## Usage\nreporadar --help\n"
    )
    config = load_scoring_config()
    b_bare = score_repos([bare], [], config=config, now=NOW)[0].scores.buildability
    b_rich = score_repos([rich], [], config=config, now=NOW)[0].scores.buildability
    assert b_rich > b_bare


def test_portfolio_fit_floor_low_for_unrelated():
    # B7: repos outside the niche must not float at 4/10.
    generic = _repo("weather", "A weather forecast CLI", stars=50)
    fit = score_repos([generic], [], config=load_scoring_config(), now=NOW)[0].scores.portfolio_fit
    assert fit <= 2


def test_staleness_penalty_is_graduated():
    # B9: older repos lose progressively more market_pain, not a flat cliff.
    config = load_scoring_config()

    def market_pain(days: int) -> int:
        repo = _repo("r", "LLM eval harness QA agent", stars=300, pushed=NOW - timedelta(days=days))
        return score_repos([repo], [], config=config, now=NOW)[0].scores.market_pain

    fresh, mid = market_pain(10), market_pain(400)
    old, ancient = market_pain(800), market_pain(1200)
    assert fresh > mid > old > ancient


def test_proof_requires_two_hints():
    # B10: a single stray "test" mention must not earn the proof bonus.
    config = load_scoring_config()
    one = _repo("a", "this is a test of the idea", stars=10)
    two = _repo("b", "pytest coverage and CI passing", stars=10)
    p_one = score_repos([one], [], config=config, now=NOW)[0].scores.proof
    p_two = score_repos([two], [], config=config, now=NOW)[0].scores.proof
    assert p_two > p_one


def test_config_can_be_constructed_directly():
    config = ScoringConfig(
        weights={
            "portfolio_fit": 0.2,
            "market_pain": 0.2,
            "novelty": 0.15,
            "buildability": 0.15,
            "demo": 0.1,
            "differentiation": 0.1,
            "proof": 0.1,
        },
        duplication_penalty={"none": 0, "adjacent": 1, "similar": 2, "duplicate": 4},
        stale_after_days=365,
    )
    assert config.stale_after_days == 365
