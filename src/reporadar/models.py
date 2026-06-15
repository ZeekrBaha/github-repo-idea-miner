"""Core Pydantic data models for RepoRadar.

Keep these models thin and validation-focused. Scoring weights and business
logic live in the analysis package, not here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DuplicationLevel(StrEnum):
    """How close a candidate idea is to an existing local project.

    The string value is used directly in reports; ``penalty`` feeds the scorer.
    """

    none = "none"
    adjacent = "adjacent"
    similar = "similar"
    duplicate = "duplicate"

    @property
    def penalty(self) -> int:
        return {
            DuplicationLevel.none: 0,
            DuplicationLevel.adjacent: 1,
            DuplicationLevel.similar: 2,
            DuplicationLevel.duplicate: 4,
        }[self]


class RepoCandidate(BaseModel):
    """A public GitHub repository fetched from a search query."""

    full_name: str
    url: str
    description: str | None = None
    stars: int = Field(ge=0)
    forks: int = Field(ge=0)
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    pushed_at: datetime
    created_at: datetime
    readme_text: str | None = None
    readme_summary: str | None = None
    source_query: str


class LocalProject(BaseModel):
    """A repository discovered in Baha's local projects directory."""

    name: str
    path: str
    repo_url: str | None = None
    readme_title: str | None = None
    readme_summary: str | None = None
    inferred_tags: list[str] = Field(default_factory=list)


class RepoScores(BaseModel):
    """The seven 1–10 criterion scores for a single opportunity."""

    portfolio_fit: int = Field(ge=1, le=10)
    market_pain: int = Field(ge=1, le=10)
    novelty: int = Field(ge=1, le=10)
    buildability: int = Field(ge=1, le=10)
    demo: int = Field(ge=1, le=10)
    differentiation: int = Field(ge=1, le=10)
    proof: int = Field(ge=1, le=10)


class IdeaCluster(BaseModel):
    """A theme bucket grouping several candidate repos."""

    id: str
    name: str
    summary: str
    repos: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class IdeaRecommendation(BaseModel):
    """A ranked, actionable build idea derived from a cluster."""

    title: str
    score: float
    source_repos: list[str] = Field(min_length=1)
    why_interesting: str
    local_duplication: str
    differentiated_angle: str
    mvp_scope: list[str]
    validation_plan: list[str]
    tech_stack: list[str]
    kanban_task_title: str
    kanban_task_body: str
