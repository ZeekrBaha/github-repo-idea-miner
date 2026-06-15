"""RepoRadar CLI (``reporadar``).

Commands:
  profiles        List available search profiles.
  scan-local      Scan local projects into a JSON inventory.
  mine            Run the full mining pipeline -> Markdown + JSON reports.
  kanban-drafts   Render Kanban task drafts from a JSON report (never created).
  explain         Print details for one idea from a JSON report.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from reporadar.cache import SearchCache
from reporadar.config import ProfileNotFoundError, load_profile, load_profiles
from reporadar.local.scanner import scan_local_projects
from reporadar.models import IdeaRecommendation
from reporadar.pipeline import run_mine
from reporadar.reports.json_report import write_json
from reporadar.reports.kanban import render_kanban_drafts, write_kanban
from reporadar.reports.markdown import write_markdown
from reporadar.sources.github import GitHubClient

# Derive from the running user's home so the default is portable across machines
# instead of a baked-in personal absolute path.
DEFAULT_LOCAL_ROOT = Path.home() / "Desktop" / "llm-ai-projects"
# Stable per-user cache location, not the current working directory.
DEFAULT_CACHE_PATH = Path.home() / ".reporadar" / "cache.db"

app = typer.Typer(
    add_completion=False,
    help="RepoRadar — mine GitHub for differentiated AI/LLM/QA project ideas.",
)
console = Console()


def build_github_client() -> GitHubClient:
    """Factory for the GitHub client (overridable in tests)."""

    return GitHubClient()


@app.command()
def profiles() -> None:
    """List available search profiles."""

    table = Table(title="Search Profiles")
    table.add_column("Name", style="bold cyan")
    table.add_column("Queries", justify="right")
    table.add_column("Description")
    for name, profile in sorted(load_profiles().items()):
        table.add_row(name, str(len(profile.queries)), profile.description)
    console.print(table)


@app.command("scan-local")
def scan_local(
    root: Path = typer.Option(DEFAULT_LOCAL_ROOT, "--root", help="Local projects root."),
    out: Path = typer.Option(
        Path("reports/local-inventory.json"), "--out", help="Output JSON path."
    ),
) -> None:
    """Scan local projects and write a JSON inventory."""

    projects = scan_local_projects(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [p.model_dump() for p in projects]
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"Scanned [bold]{len(projects)}[/bold] local projects -> {out}")


@app.command()
def mine(
    profile: str = typer.Option("baha-ai-qa", "--profile", help="Search profile name."),
    limit: int = typer.Option(30, "--limit", help="Max repos to analyze."),
    out: Path = typer.Option(Path("reports/latest.md"), "--out", help="Markdown output path."),
    root: Path = typer.Option(DEFAULT_LOCAL_ROOT, "--root", help="Local projects root."),
    use_cache: bool = typer.Option(
        True, "--cache/--no-cache", help="Cache GitHub results in cache.db (per day)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print the queries that would run; fetch nothing, write nothing."
    ),
) -> None:
    """Run the full mining workflow and write Markdown + JSON reports."""

    if dry_run:
        try:
            search_profile = load_profile(profile)
        except ProfileNotFoundError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
        console.print(f"[bold]Dry run[/bold] — profile '{search_profile.name}', no network calls.")
        console.print(f"Local root: {root}")
        console.print(f"Queries that would run (limit {limit} each):")
        for query in search_profile.queries:
            console.print(f"  - {query}")
        return

    cache = SearchCache(DEFAULT_CACHE_PATH) if use_cache else None
    if cache is not None:
        cache.prune(today=datetime.now(UTC).date().isoformat(), keep_days=7)
    try:
        report = run_mine(
            profile_name=profile,
            limit=limit,
            locals_root=root,
            client=build_github_client(),
            now=datetime.now(UTC),
            cache=cache,
        )
    except ProfileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    md_path = write_markdown(report, out)
    json_path = write_json(report, out.with_suffix(".json"))

    console.print(f"Profile: [bold]{report.profile}[/bold]")
    console.print(f"Repos analyzed: [bold]{report.repos_scanned}[/bold]")
    console.print(f"Ideas recommended: [bold]{len(report.ideas)}[/bold]")
    if cache is not None:
        console.print(
            f"Cache: [bold]{report.cache_hits}[/bold] from cache, "
            f"[bold]{report.cache_misses}[/bold] live"
        )
    if report.top_themes():
        console.print("Top themes: " + ", ".join(report.top_themes()))
    if report.errors:
        console.print(f"[yellow]Source notes ({len(report.errors)}):[/yellow]")
        for err in report.errors:
            console.print(f"  - {err}")
    console.print(f"Markdown report: {md_path}")
    console.print(f"JSON report: {json_path}")


def _load_ideas(json_report: Path) -> list[IdeaRecommendation]:
    data = json.loads(json_report.read_text(encoding="utf-8"))
    return [IdeaRecommendation(**raw) for raw in data.get("ideas", [])]


@app.command("kanban-drafts")
def kanban_drafts(
    json_report: Path = typer.Argument(..., help="Path to a JSON report."),
    top: int = typer.Option(5, "--top", help="Number of ideas to draft."),
    out: Path = typer.Option(
        Path("reports/kanban-drafts.md"), "--out", help="Output Markdown path."
    ),
) -> None:
    """Generate Kanban task drafts (drafts only — never auto-created)."""

    ideas = _load_ideas(json_report)
    write_kanban(ideas, out, top=top)
    console.print(render_kanban_drafts(ideas, top=top))
    console.print(f"\n[dim]Drafts written to {out} (not auto-created).[/dim]")


@app.command()
def explain(
    json_report: Path = typer.Argument(..., help="Path to a JSON report."),
    idea: str = typer.Option(..., "--idea", help="Idea title to explain."),
) -> None:
    """Print full details for one idea from a JSON report."""

    for rec in _load_ideas(json_report):
        if rec.title.lower() == idea.lower():
            console.print(f"[bold]{rec.title}[/bold]  ({rec.score:.2f}/10)")
            console.print(f"Why: {rec.why_interesting}")
            console.print(f"Duplication: {rec.local_duplication}")
            console.print(f"Angle: {rec.differentiated_angle}")
            console.print("MVP scope:")
            for item in rec.mvp_scope:
                console.print(f"  - {item}")
            console.print("Source repos: " + ", ".join(rec.source_repos))
            return
    console.print(f"[red]Idea not found: {idea}[/red]")
    raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
