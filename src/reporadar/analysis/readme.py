"""Deterministic README extraction and summarization.

No LLM required. We pull the title, first meaningful paragraph, section
headings, and salient keywords using simple, predictable text rules so the
output is stable across runs and testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Lines we never treat as the summary paragraph (badges, raw image/links, HTML).
_NOISE_LINE = re.compile(r"^\s*(\[!\[|!\[|<|\[.*\]:\s|=+\s*$|-+\s*$)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*#*\s*$")
_WORD = re.compile(r"[a-z][a-z0-9+-]{2,}")

# Common English/markdown stopwords excluded from keyword extraction.
_STOPWORDS = frozenset(
    """
    the and for with this that from your you are can has have will into out
    not but all any its our their them they been being more most other some
    such only own same than too very just also use used using via etc
    """.split()
)


@dataclass
class ReadmeSummary:
    title: str | None = None
    summary: str | None = None
    headings: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


def extract_title(text: str) -> str | None:
    """Return the first markdown ``#`` heading, else the first non-empty line."""

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = _HEADING.match(stripped)
        if heading:
            return heading.group(2).strip()
        # First non-empty, non-noise line acts as the title fallback.
        if not _NOISE_LINE.match(stripped):
            return stripped
    return None


def extract_summary(text: str, max_chars: int = 280) -> str | None:
    """Return the first meaningful paragraph, skipping the title and badges."""

    lines = text.splitlines()
    saw_title = False
    buffer: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                break
            continue
        if _HEADING.match(stripped):
            saw_title = True
            if buffer:
                break
            continue
        if _NOISE_LINE.match(stripped):
            continue
        if not saw_title and not buffer and extract_title(text) == stripped:
            # This non-heading line is the title fallback; skip it.
            saw_title = True
            continue
        buffer.append(stripped)

    if not buffer:
        return None
    paragraph = " ".join(buffer)
    if len(paragraph) > max_chars:
        return paragraph[:max_chars].rstrip() + "…"
    return paragraph


def extract_headings(text: str) -> list[str]:
    """Return section headings (level 2+), excluding the top-level title."""

    headings: list[str] = []
    for line in text.splitlines():
        match = _HEADING.match(line.strip())
        if match and len(match.group(1)) >= 2:
            headings.append(match.group(2).strip())
    return headings


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    """Return the most frequent salient lowercase words, most-common first."""

    counts: dict[str, int] = {}
    for word in _WORD.findall(text.lower()):
        if word in _STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [word for word, _ in ranked[:limit]]


def summarize_readme(text: str, max_chars: int = 280) -> ReadmeSummary:
    """Bundle title, summary, headings, and keywords for a README body."""

    if not text.strip():
        return ReadmeSummary()
    return ReadmeSummary(
        title=extract_title(text),
        summary=extract_summary(text, max_chars=max_chars),
        headings=extract_headings(text),
        keywords=extract_keywords(text),
    )
