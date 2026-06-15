from pathlib import Path

from reporadar.local.scanner import scan_local_projects
from reporadar.local.tags import infer_tags


def test_infer_tags_from_name():
    tags = infer_tags("eval-hotel-bot-eval-deepeval", "")
    assert "llm-eval" in tags


def test_infer_tags_from_readme():
    tags = infer_tags("mystery", "A Playwright browser agent for autonomous QA testing.")
    assert "agentic-qa" in tags


def test_infer_tags_dedupes_and_sorts():
    tags = infer_tags("agentic-qa", "agentic qa agent")
    assert tags == sorted(set(tags))


def test_infer_tags_empty_when_no_match():
    assert infer_tags("random-thing", "nothing relevant here") == []


def test_infer_tags_no_substring_false_positive():
    # "rag" must not match inside storage / drag / brag / fragile (B1).
    tags = infer_tags("storage-service", "drag and drop, bragging about fragile code")
    assert "rag" not in tags


def test_infer_tags_word_boundary_still_matches_real_token():
    assert "rag" in infer_tags("rag-tool", "retrieval augmented generation")


def _make_repo(root: Path, name: str, readme: str) -> Path:
    repo = root / name
    repo.mkdir()
    (repo / "README.md").write_text(readme, encoding="utf-8")
    return repo


def test_scan_returns_projects_with_titles(tmp_path: Path):
    _make_repo(tmp_path, "promptlab", "# PromptLab\n\nLLM prompt regression eval harness.\n")
    projects = scan_local_projects(tmp_path)
    assert len(projects) == 1
    proj = projects[0]
    assert proj.name == "promptlab"
    assert proj.readme_title == "PromptLab"
    assert "regression" in (proj.readme_summary or "").lower()


def test_scan_infers_tags(tmp_path: Path):
    _make_repo(tmp_path, "evalforge", "# EvalForge\n\nSynthetic dataset generation for LLM eval.\n")
    projects = scan_local_projects(tmp_path)
    assert "llm-eval" in projects[0].inferred_tags


def test_scan_ignores_hidden_and_noise_dirs(tmp_path: Path):
    _make_repo(tmp_path, "real", "# Real\n\nhello\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "file.txt").write_text("loose file", encoding="utf-8")
    projects = scan_local_projects(tmp_path)
    names = {p.name for p in projects}
    assert names == {"real"}


def test_scan_reads_git_remote(tmp_path: Path):
    repo = _make_repo(tmp_path, "withremote", "# WithRemote\n\nx\n")
    git_dir = repo / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        '[remote "origin"]\n\turl = https://github.com/baha/withremote.git\n',
        encoding="utf-8",
    )
    projects = scan_local_projects(tmp_path)
    assert projects[0].repo_url == "https://github.com/baha/withremote.git"


def test_scan_handles_missing_readme(tmp_path: Path):
    (tmp_path / "noreadme").mkdir()
    projects = scan_local_projects(tmp_path)
    assert projects[0].readme_title is None


def test_scan_nonexistent_root_returns_empty(tmp_path: Path):
    assert scan_local_projects(tmp_path / "nope") == []
