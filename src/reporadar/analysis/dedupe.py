"""Duplication checker: compare a GitHub candidate against local projects.

Signals are deterministic and explainable:
  * shared theme tags (from :mod:`reporadar.local.tags`)
  * fuzzy name similarity
  * fuzzy README/description text similarity

These combine into one of four verdicts (none / adjacent / similar / duplicate)
whose penalties feed the scorer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz

from reporadar.local.tags import infer_tags
from reporadar.models import DuplicationLevel, LocalProject, RepoCandidate


@dataclass
class DuplicationResult:
    level: DuplicationLevel
    matched_projects: list[str] = field(default_factory=list)
    rationale: str = ""


def repo_tags(repo: RepoCandidate) -> list[str]:
    """Infer theme tags for a candidate from its name, description, and summary."""

    short_name = repo.full_name.split("/")[-1]
    text = " ".join(
        part for part in (repo.description, repo.readme_summary, " ".join(repo.topics)) if part
    )
    return infer_tags(short_name, text)


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    # token_sort_ratio is length-balanced: unlike token_set_ratio it does not
    # score ~100 just because a short string's tokens are a subset of a long one,
    # which previously flagged unrelated projects with rich candidate READMEs.
    return fuzz.token_sort_ratio(a.lower(), b.lower()) / 100.0


def _pair_level(
    repo: RepoCandidate, candidate_tags: set[str], local: LocalProject
) -> DuplicationLevel:
    shared = candidate_tags & set(local.inferred_tags)
    short_name = repo.full_name.split("/")[-1]
    repo_text = " ".join(part for part in (repo.description, repo.readme_summary) if part)
    local_text = " ".join(part for part in (local.readme_title, local.readme_summary) if part)

    name_sim = _ratio(short_name, local.name)
    text_sim = _ratio(repo_text, local_text)
    best_text = max(name_sim, text_sim)

    # Thematic overlap (a shared theme tag) is required for adjacent/similar/
    # duplicate. Text similarity only sharpens the verdict within a shared theme.
    if shared:
        if len(shared) >= 2 and best_text >= 0.6:
            return DuplicationLevel.duplicate
        if best_text >= 0.45:
            return DuplicationLevel.similar
        return DuplicationLevel.adjacent

    # No shared theme: only a near-identical name counts as a real clone.
    if name_sim >= 0.85:
        return DuplicationLevel.similar
    return DuplicationLevel.none


_RANK = {
    DuplicationLevel.none: 0,
    DuplicationLevel.adjacent: 1,
    DuplicationLevel.similar: 2,
    DuplicationLevel.duplicate: 3,
}


def check_duplication(repo: RepoCandidate, locals_: list[LocalProject]) -> DuplicationResult:
    """Return the strongest duplication verdict across all local projects."""

    candidate_tags = set(repo_tags(repo))
    best = DuplicationLevel.none
    matched: list[str] = []

    for local in locals_:
        level = _pair_level(repo, candidate_tags, local)
        if level is not DuplicationLevel.none:
            matched.append(local.name)
        if _RANK[level] > _RANK[best]:
            best = level

    matched = sorted(set(matched))
    if best is DuplicationLevel.none:
        rationale = "No meaningful overlap with local projects."
    else:
        rationale = f"Overlaps local projects: {', '.join(matched)} (verdict: {best.value})."
    return DuplicationResult(level=best, matched_projects=matched, rationale=rationale)
