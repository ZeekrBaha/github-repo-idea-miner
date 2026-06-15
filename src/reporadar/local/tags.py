"""Deterministic theme-tag inference from a repo name + README text.

Tags are coarse buckets used by the deduplication checker and clustering. The
mapping is intentionally explicit and easy to audit — substring triggers on a
normalized text blob, no ML.
"""

from __future__ import annotations

import re

# tag -> trigger substrings (matched against "<name words> <readme>" lowercased).
TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "llm-eval": (
        "deepeval",
        "promptfoo",
        "llm eval",
        "llm evaluation",
        "eval harness",
        "evaluation framework",
        "llm judge",
        "judge calibration",
        "regression eval",
    ),
    "rag": ("rag", "retrieval augmented", "retrieval-augmented"),
    "agentic-qa": (
        "playwright",
        "selenium",
        "agentic qa",
        "qa agent",
        "browser agent",
        "autonomous qa",
        "self healing",
        "self-healing",
    ),
    "coding-agents": (
        "claude code",
        "codex",
        "worktree",
        "coding agent",
        "multi agent",
        "multi-agent",
        "agent orchestration",
        "agent fleet",
    ),
    "llm-observability": ("observability", "langfuse", "llm tracing", "llm monitoring"),
    "prompt": ("prompt regression", "prompt lab", "prompt engineering", "promptlab"),
    "dataset": ("synthetic dataset", "dataset generation", "data generation"),
    "repo-audit": ("repo audit", "code audit", "agent readiness", "codebase governance"),
    "portfolio-tooling": ("boilerplate", "dashboard template", "portfolio os"),
}


def infer_tags(name: str, readme_text: str) -> list[str]:
    """Return sorted, de-duplicated theme tags for a project.

    ``name`` separators (``-``/``_``) are treated as spaces so multi-word
    triggers match repo names too.
    """

    name_words = name.replace("-", " ").replace("_", " ").lower()
    blob = f"{name_words} {readme_text.lower()}"
    tags = {
        tag
        for tag, triggers in TAG_KEYWORDS.items()
        if any(_matches(trigger, blob) for trigger in triggers)
    }
    return sorted(tags)


def _matches(trigger: str, blob: str) -> bool:
    """Word-boundary match so ``rag`` does not fire inside ``storage``/``drag``."""

    return re.search(rf"\b{re.escape(trigger)}\b", blob) is not None
