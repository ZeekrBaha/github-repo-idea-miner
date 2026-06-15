"""Deterministic, weighted opportunity scoring.

Every criterion (1–10) is derived from observable repo signals with explicit,
auditable rules — no randomness, no LLM. The overall score is the weighted sum
minus a duplication penalty. Freshness lowers ``market_pain`` so stale repos
rank below otherwise-identical fresh ones.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from reporadar.analysis.dedupe import DuplicationResult, check_duplication, repo_tags
from reporadar.models import DuplicationLevel, LocalProject, RepoCandidate, RepoScores

DEFAULT_SCORING_PATH = Path(__file__).resolve().parents[3] / "configs" / "scoring.yaml"

# Tags that signal a fit with Baha's AI-QA / LLM-eval / agent positioning.
_TARGET_TAGS = frozenset(
    {"llm-eval", "agentic-qa", "coding-agents", "llm-observability", "prompt", "repo-audit"}
)
_DEMO_HINTS = ("dashboard", "ui", "visual", "report", "screenshot", "web app")
_PROOF_HINTS = ("test", "ci", "coverage", "benchmark", "metric", "eval", "pytest")


class ScoringConfig(BaseModel):
    weights: dict[str, float]
    duplication_penalty: dict[str, int]
    stale_after_days: int = Field(gt=0)

    @model_validator(mode="after")
    def _weights_sum_to_one(self) -> ScoringConfig:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.4f}")
        return self


@dataclass
class OpportunityScore:
    repo: RepoCandidate
    scores: RepoScores
    overall: float
    duplication: DuplicationResult


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    raw = yaml.safe_load((path or DEFAULT_SCORING_PATH).read_text(encoding="utf-8"))
    return ScoringConfig(**raw)


def _clamp(value: int) -> int:
    return max(1, min(10, value))


def _repo_text(repo: RepoCandidate) -> str:
    parts = [repo.description, repo.readme_summary, " ".join(repo.topics)]
    return " ".join(p for p in parts if p).lower()


def _portfolio_fit(tags: set[str]) -> int:
    # Floor of 1 so repos outside the niche (zero target tags) score low, not 4.
    return _clamp(1 + 3 * len(tags & _TARGET_TAGS))


def _market_pain(repo: RepoCandidate, now: datetime, stale_after_days: int) -> int:
    stars = repo.stars
    base = next(
        score
        for threshold, score in (
            (1000, 10),
            (500, 9),
            (200, 8),
            (100, 7),
            (50, 6),
            (20, 5),
            (0, 4),
        )
        if stars >= threshold
    )
    # Graduated staleness decay: a long-stable library is penalized less than an
    # abandoned prototype. Thresholds are multiples of stale_after_days.
    age_days = (now - repo.pushed_at).days
    if age_days > stale_after_days * 3:
        base -= 3
    elif age_days > stale_after_days * 2:
        base -= 2
    elif age_days > stale_after_days:
        base -= 1
    return _clamp(base)


def _novelty(level: DuplicationLevel) -> int:
    return {
        DuplicationLevel.none: 9,
        DuplicationLevel.adjacent: 7,
        DuplicationLevel.similar: 4,
        DuplicationLevel.duplicate: 2,
    }[level]


def _differentiation(level: DuplicationLevel) -> int:
    # Monotonic: the more a candidate overlaps existing local work, the less
    # room there is to build a meaningfully differentiated version.
    return {
        DuplicationLevel.none: 9,
        DuplicationLevel.adjacent: 7,
        DuplicationLevel.similar: 5,
        DuplicationLevel.duplicate: 3,
    }[level]


def _buildability(repo: RepoCandidate) -> int:
    # Start lower and reward concrete signals that the repo is easy to learn
    # from and re-implement: known language, a README, test/CI evidence, and a
    # documented install/usage path.
    text = (repo.readme_text or repo.readme_summary or repo.description or "").lower()
    base = 5
    if (repo.language or "").lower() == "python":
        base += 1
    if repo.readme_text:
        base += 1
    if any(hint in text for hint in ("test", "ci", "pytest", "coverage")):
        base += 1
    if any(hint in text for hint in ("install", "usage", "getting started", "quickstart", "cli")):
        base += 1
    return _clamp(base)


def _demo(repo: RepoCandidate, text: str) -> int:
    base = 5
    if any(hint in text for hint in _DEMO_HINTS):
        base += 2
    if repo.topics:
        base += 1
    return _clamp(base)


def _proof(repo: RepoCandidate, text: str) -> int:
    # Require at least two distinct proof hints so a single stray "test" mention
    # does not earn the bonus.
    base = 4
    hit_count = sum(1 for hint in _PROOF_HINTS if hint in text)
    if hit_count >= 2:
        base += 3
    if repo.stars >= 100:
        base += 1
    return _clamp(base)


def score_repo(
    repo: RepoCandidate,
    locals_: list[LocalProject],
    config: ScoringConfig,
    now: datetime,
) -> OpportunityScore:
    dup = check_duplication(repo, locals_)
    tags = set(repo_tags(repo))
    text = _repo_text(repo)

    scores = RepoScores(
        portfolio_fit=_portfolio_fit(tags),
        market_pain=_market_pain(repo, now, config.stale_after_days),
        novelty=_novelty(dup.level),
        buildability=_buildability(repo),
        demo=_demo(repo, text),
        differentiation=_differentiation(dup.level),
        proof=_proof(repo, text),
    )

    weighted = sum(config.weights[name] * value for name, value in scores.model_dump().items())
    penalty = config.duplication_penalty.get(dup.level.value, 0)
    overall = round(weighted - penalty, 3)
    return OpportunityScore(repo=repo, scores=scores, overall=overall, duplication=dup)


def score_repos(
    repos: list[RepoCandidate],
    locals_: list[LocalProject],
    config: ScoringConfig,
    now: datetime,
) -> list[OpportunityScore]:
    """Score every repo and return them sorted by overall score, highest first."""

    scored = [score_repo(repo, locals_, config, now) for repo in repos]
    scored.sort(key=lambda s: (s.overall, s.repo.stars, s.repo.full_name), reverse=True)
    return scored
