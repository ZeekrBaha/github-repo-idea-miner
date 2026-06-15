"""SQLite-backed cache for GitHub search results.

Keyed by ``(day, limit, query)`` so repeated mines on the same day reuse fetched
results instead of re-hitting the API. The day is passed in by the caller (the
pipeline derives it from the injected ``now``) to keep behavior deterministic and
testable.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS search_cache "
    "(key TEXT PRIMARY KEY, day TEXT NOT NULL, payload TEXT NOT NULL)"
)


class SearchCache:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    @staticmethod
    def _key(query: str, limit: int, day: str) -> str:
        return f"{day}|{limit}|{query}"

    def get(self, query: str, limit: int, day: str) -> list[dict[str, Any]] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM search_cache WHERE key = ?",
                (self._key(query, limit, day),),
            ).fetchone()
        if row is None:
            return None
        result: list[dict[str, Any]] = json.loads(row[0])
        return result

    def put(self, query: str, limit: int, day: str, items: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO search_cache (key, day, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, day = excluded.day",
                (self._key(query, limit, day), day, json.dumps(items)),
            )

    def prune(self, today: str, keep_days: int) -> int:
        """Delete cached entries older than ``keep_days`` before ``today``.

        Returns the number of rows removed. Keeps the cache bounded over time.
        """

        cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM search_cache WHERE day < ?", (cutoff,))
            return cursor.rowcount
