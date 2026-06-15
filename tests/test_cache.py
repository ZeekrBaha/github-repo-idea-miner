from pathlib import Path

from reporadar.cache import SearchCache

ITEMS = [{"full_name": "org/a"}, {"full_name": "org/b"}]


def test_miss_returns_none(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    assert cache.get("q", 30, "2026-06-15") is None


def test_put_then_get_roundtrips(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-15", ITEMS)
    assert cache.get("q", 30, "2026-06-15") == ITEMS


def test_different_day_misses(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-15", ITEMS)
    assert cache.get("q", 30, "2026-06-16") is None


def test_different_limit_misses(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-15", ITEMS)
    assert cache.get("q", 50, "2026-06-15") is None


def test_put_is_idempotent_upsert(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-15", ITEMS)
    cache.put("q", 30, "2026-06-15", [{"full_name": "org/c"}])
    assert cache.get("q", 30, "2026-06-15") == [{"full_name": "org/c"}]


def test_persists_across_instances(tmp_path: Path):
    db = tmp_path / "c.db"
    SearchCache(db).put("q", 30, "2026-06-15", ITEMS)
    assert SearchCache(db).get("q", 30, "2026-06-15") == ITEMS


def test_prune_removes_entries_older_than_keep_days(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-01", ITEMS)  # old
    cache.put("q", 30, "2026-06-15", ITEMS)  # today
    removed = cache.prune(today="2026-06-15", keep_days=7)
    assert removed == 1
    assert cache.get("q", 30, "2026-06-01") is None
    assert cache.get("q", 30, "2026-06-15") == ITEMS


def test_prune_keeps_entries_within_window(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.db")
    cache.put("q", 30, "2026-06-10", ITEMS)  # 5 days old
    removed = cache.prune(today="2026-06-15", keep_days=7)
    assert removed == 0
    assert cache.get("q", 30, "2026-06-10") == ITEMS
