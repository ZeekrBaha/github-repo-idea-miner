"""JSON report serialization.

The JSON report is the machine-readable companion to the Markdown report and the
input to ``reporadar kanban-drafts``. Every repo entry carries its scores, the
overall value, and the duplication verdict so downstream tools never recompute.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reporadar.reports.report import MineReport


def report_to_dict(report: MineReport) -> dict[str, Any]:
    repos: list[dict[str, Any]] = []
    for scored in report.scored:
        entry = scored.repo.model_dump(mode="json")
        entry["scores"] = scored.scores.model_dump()
        entry["overall"] = scored.overall
        entry["duplication"] = {
            "level": scored.duplication.level.value,
            "matched_projects": scored.duplication.matched_projects,
            "rationale": scored.duplication.rationale,
        }
        repos.append(entry)

    return {
        "generated_at": report.generated_at.isoformat(),
        "profile": report.profile,
        "repos_scanned": report.repos_scanned,
        "top_themes": report.top_themes(),
        "errors": report.errors,
        "repos": repos,
        "clusters": [c.model_dump() for c in report.clusters],
        "ideas": [i.model_dump() for i in report.ideas],
    }


def write_json(report: MineReport, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report_to_dict(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
