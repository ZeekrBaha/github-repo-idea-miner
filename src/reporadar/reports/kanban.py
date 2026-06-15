"""Kanban task-draft rendering.

This produces *drafts only* — RepoRadar never auto-creates Kanban cards. The
output is meant to be reviewed and pasted (or wired into a creation command
later, after explicit approval).
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reporadar.models import IdeaRecommendation

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_kanban_drafts(ideas: list[IdeaRecommendation], top: int = 5) -> str:
    if not ideas:
        return "# Kanban Task Drafts\n\n_No ideas available to draft._\n"

    template = _env().get_template("kanban_task.md.j2")
    blocks = [template.render(idea=idea) for idea in ideas[: max(0, top)]]
    header = "# Kanban Task Drafts\n\n> Drafts only — not auto-created.\n\n"
    return header + "\n---\n\n".join(blocks)


def write_kanban(ideas: list[IdeaRecommendation], path: Path, top: int = 5) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_kanban_drafts(ideas, top=top), encoding="utf-8")
    return path
