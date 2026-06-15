import json
from pathlib import Path

from typer.testing import CliRunner

from reporadar.cli import DEFAULT_CACHE_PATH, DEFAULT_LOCAL_ROOT, app

runner = CliRunner()

_IDEA = {
    "title": "Self-Healing Browser QA Agent",
    "score": 8.5,
    "source_repos": ["org/qa1"],
    "why_interesting": "Demand for resilient browser flows.",
    "local_duplication": "No close local match — clear to build.",
    "differentiated_angle": "Re-derive broken selectors from the DOM.",
    "mvp_scope": ["Detect broken selector", "Propose patch"],
    "validation_plan": ["Break a selector", "Confirm recovery"],
    "tech_stack": ["python", "playwright"],
    "kanban_task_title": "Build: Self-Healing Browser QA Agent",
    "kanban_task_body": (
        "**Angle:** x\n\n- https://github.com/org/qa1\n\nAcceptance criteria\n- [ ] y"
    ),
}


def _write_report(path: Path) -> None:
    path.write_text(json.dumps({"ideas": [_IDEA]}), encoding="utf-8")


def test_default_local_root_is_not_a_hardcoded_personal_path():
    # H3: default must resolve relative to the running user's home, not a
    # baked-in absolute path that points nowhere on another machine.
    assert DEFAULT_LOCAL_ROOT == Path.home() / "Desktop" / "llm-ai-projects"
    assert DEFAULT_LOCAL_ROOT.is_relative_to(Path.home())


def test_default_cache_path_under_home():
    # Cache must live in a stable per-user location, not the current directory.
    assert DEFAULT_CACHE_PATH == Path.home() / ".reporadar" / "cache.db"


def test_profiles_lists_baha_ai_qa():
    result = runner.invoke(app, ["profiles"])
    assert result.exit_code == 0
    assert "baha-ai-qa" in result.stdout


def test_scan_local_writes_inventory(tmp_path: Path):
    proj = tmp_path / "promptlab"
    proj.mkdir()
    (proj / "README.md").write_text("# PromptLab\n\nLLM eval harness.\n", encoding="utf-8")
    out = tmp_path / "inv.json"

    result = runner.invoke(app, ["scan-local", "--root", str(tmp_path), "--out", str(out)])
    assert result.exit_code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["name"] == "promptlab"


def test_kanban_drafts_renders(tmp_path: Path):
    report = tmp_path / "r.json"
    _write_report(report)
    out = tmp_path / "k.md"

    result = runner.invoke(app, ["kanban-drafts", str(report), "--top", "1", "--out", str(out)])
    assert result.exit_code == 0
    assert "Self-Healing Browser QA Agent" in result.stdout
    assert out.exists()


def test_explain_found(tmp_path: Path):
    report = tmp_path / "r.json"
    _write_report(report)

    result = runner.invoke(app, ["explain", str(report), "--idea", "Self-Healing Browser QA Agent"])
    assert result.exit_code == 0
    assert "Angle:" in result.stdout


def test_explain_not_found(tmp_path: Path):
    report = tmp_path / "r.json"
    _write_report(report)

    result = runner.invoke(app, ["explain", str(report), "--idea", "Nonexistent"])
    assert result.exit_code == 1
