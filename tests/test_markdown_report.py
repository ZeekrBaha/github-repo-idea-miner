import json
from datetime import UTC, datetime
from pathlib import Path

from reporadar.analysis.clustering import cluster_repos
from reporadar.analysis.ideas import generate_ideas
from reporadar.analysis.scoring import load_scoring_config, score_repos
from reporadar.models import IdeaCluster, IdeaRecommendation, RepoCandidate
from reporadar.reports.json_report import report_to_dict, write_json
from reporadar.reports.kanban import render_kanban_drafts
from reporadar.reports.markdown import render_markdown, write_markdown
from reporadar.reports.report import MineReport

NOW = datetime(2026, 6, 15, 15, 0, tzinfo=UTC)


def _repo(name: str, desc: str, stars: int = 200) -> RepoCandidate:
    return RepoCandidate(
        full_name=f"org/{name}",
        url=f"https://github.com/org/{name}",
        description=desc,
        stars=stars,
        forks=stars // 10,
        language="Python",
        topics=["ai"],
        pushed_at=datetime(2026, 5, 1, tzinfo=UTC),
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        readme_summary=desc,
        source_query="q",
    )


def _report() -> MineReport:
    repos = [
        _repo("qa1", "Playwright autonomous QA testing agent dashboard", stars=300),
        _repo("eval1", "LLM eval harness judge calibration metrics ci tests", stars=500),
    ]
    config = load_scoring_config()
    scored = score_repos(repos, [], config=config, now=NOW)
    by_name = {s.repo.full_name: s for s in scored}
    clusters = cluster_repos(repos)
    ideas = generate_ideas(clusters, by_name)
    return MineReport(
        generated_at=NOW,
        profile="baha-ai-qa",
        repos_scanned=len(repos),
        scored=scored,
        clusters=clusters,
        ideas=ideas,
    )


def test_markdown_has_executive_summary_and_ideas():
    md = render_markdown(_report())
    assert "# GitHub Repo Idea Miner Report" in md
    assert "Executive Summary" in md
    assert "baha-ai-qa" in md
    assert "Top Recommendations" in md


def test_markdown_includes_source_links():
    md = render_markdown(_report())
    assert "https://github.com/org/qa1" in md


def test_markdown_includes_duplication_note():
    md = render_markdown(_report())
    assert "duplication" in md.lower()


def test_write_markdown_creates_file(tmp_path: Path):
    out = tmp_path / "r.md"
    write_markdown(_report(), out)
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("# GitHub Repo Idea Miner Report")


def test_json_report_shape():
    data = report_to_dict(_report())
    assert data["profile"] == "baha-ai-qa"
    assert data["generated_at"].startswith("2026-06-15")
    assert isinstance(data["repos"], list)
    assert isinstance(data["clusters"], list)
    assert isinstance(data["ideas"], list)
    assert data["repos"][0]["overall"] is not None


def test_json_artifact_matches_pydantic_schema():
    # B14: the serialized report must round-trip back into the domain models,
    # so a model change can never silently break the artifact shape.
    data = report_to_dict(_report())
    for repo in data["repos"]:
        RepoCandidate(**{k: v for k, v in repo.items() if k in RepoCandidate.model_fields})
    for cluster in data["clusters"]:
        IdeaCluster(**cluster)
    for idea in data["ideas"]:
        IdeaRecommendation(**idea)


def test_write_json_roundtrips(tmp_path: Path):
    out = tmp_path / "r.json"
    write_json(_report(), out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["profile"] == "baha-ai-qa"
    assert loaded["ideas"][0]["source_repos"]


def test_kanban_drafts_render_top_n():
    report = _report()
    md = render_kanban_drafts(report.ideas, top=1)
    assert md.count("## ") == 1
    assert "Acceptance criteria" in md
    assert "https://github.com/" in md


def test_kanban_drafts_empty_ideas():
    md = render_kanban_drafts([], top=5)
    assert "No ideas" in md
