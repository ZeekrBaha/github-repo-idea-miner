from datetime import UTC, datetime

from reporadar.analysis.clustering import cluster_repos
from reporadar.analysis.ideas import generate_ideas
from reporadar.analysis.scoring import load_scoring_config, score_repos
from reporadar.models import IdeaRecommendation, LocalProject, RepoCandidate

NOW = datetime(2026, 6, 15, tzinfo=UTC)


def _repo(name: str, desc: str, stars: int = 100) -> RepoCandidate:
    return RepoCandidate(
        full_name=f"org/{name}",
        url=f"https://github.com/org/{name}",
        description=desc,
        stars=stars,
        forks=1,
        language="Python",
        topics=[],
        pushed_at=datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        readme_summary=desc,
        source_query="q",
    )


def _pipeline(repos, locals_):
    config = load_scoring_config()
    scored = score_repos(repos, locals_, config=config, now=NOW)
    by_name = {s.repo.full_name: s for s in scored}
    clusters = cluster_repos(repos)
    return generate_ideas(clusters, by_name)


def test_generates_ideas_from_clusters():
    repos = [
        _repo("qa1", "Playwright autonomous QA testing agent dashboard", stars=300),
        _repo("eval1", "LLM eval harness judge calibration metrics ci", stars=400),
    ]
    ideas = _pipeline(repos, [])
    assert ideas
    assert all(isinstance(i, IdeaRecommendation) for i in ideas)


def test_every_idea_cites_source_repos():
    repos = [_repo("qa1", "Playwright QA agent", stars=200)]
    for idea in _pipeline(repos, []):
        assert idea.source_repos
        assert all(r.startswith("org/") for r in idea.source_repos)


def test_ideas_sorted_by_score_desc():
    repos = [
        _repo("low", "A weather CLI", stars=5),
        _repo("high", "LLM eval harness QA agent dashboard ci tests", stars=900),
    ]
    ideas = _pipeline(repos, [])
    scores = [i.score for i in ideas]
    assert scores == sorted(scores, reverse=True)


def test_local_duplication_noted():
    repos = [_repo("promptlab", "LLM prompt regression eval harness")]
    locals_ = [
        LocalProject(
            name="promptlab",
            path="/x",
            readme_title="PromptLab",
            readme_summary="LLM prompt regression eval harness",
            inferred_tags=["llm-eval", "prompt"],
        )
    ]
    ideas = _pipeline(repos, locals_)
    assert any("promptlab" in i.local_duplication for i in ideas)


def test_local_duplication_note_caps_long_lists():
    repos = [_repo("eval-tool", "LLM eval harness judge calibration", stars=300)]
    locals_ = [
        LocalProject(
            name=f"eval-proj-{i}",
            path=f"/x/{i}",
            readme_title=f"Eval {i}",
            readme_summary="LLM eval harness",
            inferred_tags=["llm-eval"],
        )
        for i in range(15)
    ]
    ideas = _pipeline(repos, locals_)
    note = ideas[0].local_duplication
    assert "more" in note  # list is truncated rather than dumping all 15


def test_idea_text_reflects_source_repo_descriptions():
    # B5: idea text must derive from the actual repos found, not be fully static.
    repos1 = [_repo("alpha", "Playwright flow recorder for QA agents", stars=200)]
    repos2 = [_repo("beta", "Selenium grid self-healing QA agent", stars=200)]
    idea1 = _pipeline(repos1, [])[0]
    idea2 = _pipeline(repos2, [])[0]
    assert idea1.why_interesting != idea2.why_interesting
    assert "recorder" in idea1.why_interesting.lower()
    assert any("org/alpha" in item for item in idea1.mvp_scope)


def test_idea_score_favors_top_member_over_mean():
    # B8: one strong repo in a cluster must not be drowned by weak members.
    strong = _repo("strong", "Playwright QA agent dashboard ci tests coverage", stars=3000)
    weak = [_repo(f"weak{i}", "Playwright qa", stars=1) for i in range(4)]
    repos = [strong, *weak]
    config = load_scoring_config()
    scored = score_repos(repos, [], config=config, now=NOW)
    overalls = [s.overall for s in scored]
    mean = sum(overalls) / len(overalls)
    idea = generate_ideas(cluster_repos(repos), {s.repo.full_name: s for s in scored})[0]
    assert idea.score > mean


def test_blueprints_load_from_yaml_config():
    from reporadar.analysis.ideas import DEFAULT_BLUEPRINTS_PATH, load_blueprints

    assert DEFAULT_BLUEPRINTS_PATH.exists()
    blueprints = load_blueprints()
    assert "agentic-qa" in blueprints
    bp = blueprints["agentic-qa"]
    assert bp.title == "Self-Healing Browser QA Agent"
    assert bp.mvp_scope  # non-empty tuple
    assert bp.tech_stack


def test_other_cluster_does_not_produce_idea():
    repos = [_repo("misc", "A generic weather CLI app")]
    ideas = _pipeline(repos, [])
    # "other" bucket is not turned into a recommendation.
    assert all("Uncategorized" not in i.title for i in ideas)


def test_idea_has_actionable_fields():
    repos = [_repo("qa1", "Playwright QA agent dashboard", stars=200)]
    idea = _pipeline(repos, [])[0]
    assert idea.mvp_scope
    assert idea.validation_plan
    assert idea.tech_stack
    assert idea.kanban_task_title
    assert idea.kanban_task_body
