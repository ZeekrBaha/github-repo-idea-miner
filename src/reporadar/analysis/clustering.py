"""Lightweight theme clustering by inferred tags.

No ML — each repo's theme tags map it into one or more named opportunity
buckets. Repos matching no theme fall into an "other" bucket so nothing is
silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

from reporadar.analysis.dedupe import repo_tags
from reporadar.models import IdeaCluster, RepoCandidate


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    tags: frozenset[str]
    keywords: tuple[str, ...]


# Ordered for deterministic cluster output.
THEMES: tuple[Theme, ...] = (
    Theme(
        "coding-agents",
        "Coding-Agent Orchestration",
        frozenset({"coding-agents"}),
        ("claude code", "worktree", "multi-agent", "orchestration"),
    ),
    Theme(
        "agentic-qa",
        "Agentic QA & Browser Testing",
        frozenset({"agentic-qa"}),
        ("playwright", "browser agent", "self-healing", "qa"),
    ),
    Theme(
        "llm-eval",
        "LLM Eval & Observability",
        frozenset({"llm-eval", "llm-observability"}),
        ("eval harness", "llm judge", "observability", "metrics"),
    ),
    Theme(
        "prompt",
        "Prompt Regression & Engineering",
        frozenset({"prompt"}),
        ("prompt regression", "prompt lab"),
    ),
    Theme("rag", "RAG Systems & Eval", frozenset({"rag"}), ("retrieval augmented", "rag")),
    Theme(
        "repo-audit",
        "Repo Audit & Agent Readiness",
        frozenset({"repo-audit"}),
        ("agent readiness", "code audit", "governance"),
    ),
    Theme(
        "dataset",
        "Synthetic Dataset Generation",
        frozenset({"dataset"}),
        ("synthetic dataset", "data generation"),
    ),
    Theme(
        "portfolio-tooling",
        "Portfolio & SaaS Tooling",
        frozenset({"portfolio-tooling"}),
        ("boilerplate", "dashboard template"),
    ),
)


def cluster_repos(repos: list[RepoCandidate]) -> list[IdeaCluster]:
    """Group repos into theme clusters; unmatched repos go to an 'other' bucket."""

    if not repos:
        return []

    buckets: dict[str, list[str]] = {theme.id: [] for theme in THEMES}
    other: list[str] = []

    for repo in repos:
        tags = set(repo_tags(repo))
        matched = False
        for theme in THEMES:
            if tags & theme.tags:
                buckets[theme.id].append(repo.full_name)
                matched = True
        if not matched:
            other.append(repo.full_name)

    clusters: list[IdeaCluster] = []
    for theme in THEMES:
        members = buckets[theme.id]
        if members:
            clusters.append(
                IdeaCluster(
                    id=theme.id,
                    name=theme.name,
                    summary=f"{len(members)} repo(s) in the {theme.name} theme.",
                    repos=members,
                    keywords=list(theme.keywords),
                )
            )
    if other:
        clusters.append(
            IdeaCluster(
                id="other",
                name="Other / Uncategorized",
                summary=f"{len(other)} repo(s) without a recognized theme.",
                repos=other,
                keywords=[],
            )
        )
    return clusters
