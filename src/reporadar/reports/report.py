"""In-memory container bundling everything one mining run produced."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from reporadar.analysis.scoring import OpportunityScore
from reporadar.models import IdeaCluster, IdeaRecommendation


@dataclass
class MineReport:
    generated_at: datetime
    profile: str
    repos_scanned: int
    scored: list[OpportunityScore]
    clusters: list[IdeaCluster]
    ideas: list[IdeaRecommendation]
    errors: list[str] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0

    def top_themes(self, limit: int = 5) -> list[str]:
        return [c.name for c in self.clusters[:limit]]
