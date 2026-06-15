"""Markdown report rendering via Jinja2."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reporadar.reports.report import MineReport

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_markdown(report: MineReport) -> str:
    template = _env().get_template("report.md.j2")
    return template.render(
        generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        profile=report.profile,
        repos_scanned=report.repos_scanned,
        top_themes=report.top_themes(),
        ideas=report.ideas,
        errors=report.errors,
    )


def write_markdown(report: MineReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")
    return path
