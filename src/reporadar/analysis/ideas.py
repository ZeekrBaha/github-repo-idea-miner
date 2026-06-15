"""Turn theme clusters into actionable, differentiated build ideas.

Each non-"other" cluster becomes one :class:`IdeaRecommendation`. Source repos
always come from fetched candidates (never invented). The per-theme scaffold
(angle, MVP scope, validation plan, tech stack) lives in
``configs/blueprints.yaml``; the miner seeds it with real repo signals (names,
stars, descriptions) at generation time. Score and duplication notes are derived
from the scored repos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from reporadar.analysis.scoring import OpportunityScore
from reporadar.models import IdeaCluster, IdeaRecommendation, RepoCandidate

_MAX_SOURCE_REPOS = 4
_MAX_DUP_PROJECTS = 8

DEFAULT_BLUEPRINTS_PATH = Path(__file__).resolve().parents[3] / "configs" / "blueprints.yaml"


@dataclass(frozen=True)
class IdeaBlueprint:
    title: str
    why: str
    angle: str
    mvp_scope: tuple[str, ...]
    validation_plan: tuple[str, ...]
    tech_stack: tuple[str, ...]


def load_blueprints(path: Path | None = None) -> dict[str, IdeaBlueprint]:
    """Load per-cluster idea blueprints from YAML (keys match clustering ids)."""

    raw = yaml.safe_load((path or DEFAULT_BLUEPRINTS_PATH).read_text(encoding="utf-8")) or {}
    section = raw.get("blueprints")
    if not isinstance(section, dict) or not section:
        raise ValueError("No 'blueprints' mapping found in blueprints config")
    return {
        cluster_id: IdeaBlueprint(
            title=body["title"],
            why=body["why"],
            angle=body["angle"],
            mvp_scope=tuple(body["mvp_scope"]),
            validation_plan=tuple(body["validation_plan"]),
            tech_stack=tuple(body["tech_stack"]),
        )
        for cluster_id, body in section.items()
    }


# Loaded once at import from the bundled config.
BLUEPRINTS: dict[str, IdeaBlueprint] = load_blueprints()


def _local_duplication_note(members: list[OpportunityScore]) -> str:
    matched: set[str] = set()
    worst = "none"
    rank = {"none": 0, "adjacent": 1, "similar": 2, "duplicate": 3}
    for score in members:
        matched.update(score.duplication.matched_projects)
        if rank[score.duplication.level.value] > rank[worst]:
            worst = score.duplication.level.value
    if not matched:
        return "No close local match — clear to build."
    ordered = sorted(matched)
    shown = ordered[:_MAX_DUP_PROJECTS]
    names = ", ".join(shown)
    if len(ordered) > _MAX_DUP_PROJECTS:
        names += f", and {len(ordered) - _MAX_DUP_PROJECTS} more"
    return (
        f"Similar local projects: {names} (closest verdict: {worst}). Build only if differentiated."
    )


def generate_ideas(
    clusters: list[IdeaCluster],
    scored_by_name: dict[str, OpportunityScore],
    blueprints: dict[str, IdeaBlueprint] | None = None,
) -> list[IdeaRecommendation]:
    """Build one recommendation per recognized cluster, sorted by score desc."""

    catalog = blueprints if blueprints is not None else BLUEPRINTS
    ideas: list[IdeaRecommendation] = []
    for cluster in clusters:
        blueprint = catalog.get(cluster.id)
        if blueprint is None:  # skips the "other" bucket
            continue

        members = [scored_by_name[name] for name in cluster.repos if name in scored_by_name]
        if not members:
            continue
        members.sort(key=lambda s: s.overall, reverse=True)

        top_members = members[:_MAX_SOURCE_REPOS]
        source_repos = [m.repo.full_name for m in top_members]
        idea_score = _idea_score(members)
        dup_note = _local_duplication_note(members)

        why = _why_interesting(blueprint, top_members)
        angle = _differentiated_angle(blueprint, top_members)
        mvp_scope = _mvp_scope(blueprint, members[0].repo)
        kanban_body = _kanban_body(blueprint, source_repos, dup_note, mvp_scope)

        ideas.append(
            IdeaRecommendation(
                title=blueprint.title,
                score=idea_score,
                source_repos=source_repos,
                why_interesting=why,
                local_duplication=dup_note,
                differentiated_angle=angle,
                mvp_scope=mvp_scope,
                validation_plan=list(blueprint.validation_plan),
                tech_stack=list(blueprint.tech_stack),
                kanban_task_title=f"Build: {blueprint.title}",
                kanban_task_body=kanban_body,
            )
        )

    ideas.sort(key=lambda i: i.score, reverse=True)
    return ideas


def _idea_score(members: list[OpportunityScore]) -> float:
    # Top-weighted so a single strong repo is not drowned by weak cluster
    # members: 70% best member + 30% cluster mean.
    overalls = [m.overall for m in members]
    top = overalls[0]
    mean = sum(overalls) / len(overalls)
    return round(0.7 * top + 0.3 * mean, 2)


def _repo_signal(member: OpportunityScore) -> str:
    repo = member.repo
    detail = (repo.description or "").strip()
    return f"{repo.full_name} ({repo.stars}★){f' — {detail}' if detail else ''}"


def _why_interesting(blueprint: IdeaBlueprint, top_members: list[OpportunityScore]) -> str:
    seen = "; ".join(_repo_signal(m) for m in top_members)
    return f"{blueprint.why} Seen in: {seen}."


def _differentiated_angle(blueprint: IdeaBlueprint, top_members: list[OpportunityScore]) -> str:
    names = ", ".join(m.repo.full_name for m in top_members)
    return f"{blueprint.angle} Go beyond {names} rather than re-cloning them."


def _mvp_scope(blueprint: IdeaBlueprint, top_repo: RepoCandidate) -> list[str]:
    lead = f"Study {top_repo.full_name} ({top_repo.stars}★) and extract its core flow"
    return [lead, *blueprint.mvp_scope]


def _kanban_body(
    blueprint: IdeaBlueprint, source_repos: list[str], dup_note: str, mvp_scope: list[str]
) -> str:
    sources = "\n".join(f"- https://github.com/{name}" for name in source_repos)
    scope = "\n".join(f"- [ ] {item}" for item in mvp_scope)
    acceptance = "\n".join(f"- [ ] {item}" for item in blueprint.validation_plan)
    return (
        f"**Angle:** {blueprint.angle}\n\n"
        f"**Source repos:**\n{sources}\n\n"
        f"**Local duplication:** {dup_note}\n\n"
        f"**MVP scope:**\n{scope}\n\n"
        f"**Acceptance criteria:**\n{acceptance}\n\n"
        f"**Tech stack:** {', '.join(blueprint.tech_stack)}"
    )
