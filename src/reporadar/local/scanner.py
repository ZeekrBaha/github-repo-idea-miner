"""Scan a directory of local projects into a portfolio inventory.

For each immediate subdirectory we read the README (title + summary), the git
remote (if present), and infer theme tags. This inventory is what the dedupe
checker compares GitHub candidates against.
"""

from __future__ import annotations

import re
from pathlib import Path

from reporadar.analysis.readme import summarize_readme
from reporadar.local.tags import infer_tags
from reporadar.models import LocalProject

# Directory names that are never projects.
_NOISE_DIRS = frozenset(
    {"node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".git", "_legacy"}
)
_README_NAMES = ("README.md", "README.rst", "README.txt", "readme.md", "Readme.md")
_GIT_URL = re.compile(r"url\s*=\s*(\S+)")


def _read_readme(project_dir: Path) -> str:
    for candidate in _README_NAMES:
        readme = project_dir / candidate
        if readme.is_file():
            try:
                return readme.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
    return ""


def _read_git_remote(project_dir: Path) -> str | None:
    config = project_dir / ".git" / "config"
    if not config.is_file():
        return None
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _GIT_URL.search(text)
    return match.group(1).strip() if match else None


def scan_local_projects(root: Path) -> list[LocalProject]:
    """Return one :class:`LocalProject` per real subdirectory under ``root``.

    Missing roots yield an empty list (callers handle this gracefully). Hidden
    and noise directories are skipped.
    """

    root = Path(root)
    if not root.is_dir():
        return []

    projects: list[LocalProject] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name in _NOISE_DIRS:
            continue

        readme_text = _read_readme(entry)
        summary = summarize_readme(readme_text)
        projects.append(
            LocalProject(
                name=entry.name,
                path=str(entry),
                repo_url=_read_git_remote(entry),
                readme_title=summary.title,
                readme_summary=summary.summary,
                inferred_tags=infer_tags(entry.name, readme_text),
            )
        )
    return projects
