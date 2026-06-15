# Repo Engineering Review — Re-check (post-fixes + cache enhancement)

**Reviewed:** 2026-06-15 22:29 CDT  
**Prior review:** `docs/reviews/2026-06-15-2219-repo-engineering-review.md`

---

## About

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner` — Python 3.12 CLI (RepoRadar) that mines GitHub for AI/LLM/QA repos, scores/dedupes against local portfolio, clusters by theme, emits ranked build ideas as Markdown + JSON + Kanban drafts. Enhancement this round: SQLite per-day search cache (`cache.py`).

---

## Verdict

**Ship-ready.** One stale line in README (`repo map` says `100 tests`, actual is 110). Fix that line and this is portfolio-ready. All prior critical/high bugs remain fixed. Cache enhancement is well-designed and correctly integrated.

---

## Changes Since Prior Review — Confirmed

### New: `src/reporadar/cache.py`

SQLite-backed per-day result cache, `SearchCache` class.
- Key: `"{day}|{limit}|{query}"` — deterministic, day-scoped
- `get` → returns `list[dict] | None` (cache miss = `None`)
- `put` → upsert (`ON CONFLICT DO UPDATE`) so repeated writes are safe
- Schema created on init, parent dirs created automatically
- `_connect()` pattern — connection per operation, correct for a CLI tool

### Pipeline refactored: `_search_all` extracted (`pipeline.py:28-56`)

Cache injected as `SearchCache | None`. Cache hit → deserialize; miss → live fetch → write to cache. Rate-limit handling improved: `rate_limited` flag + `continue` pattern ensures all repos get accounted for even after a limit hit. Prior `break` bug is gone.

### CLI wired: `--cache/--no-cache` flag (`cli.py:83-84`)

```
mine --cache      # default: cache.db in CWD
mine --no-cache   # bypass, always live
```

`cache.db` gitignored in `.gitignore`. ✅

### Tests: `tests/test_cache.py` (6 tests)

| Test | What it covers |
|------|----------------|
| `test_miss_returns_none` | Cold cache → `None` |
| `test_put_then_get_roundtrips` | Round-trip fidelity |
| `test_different_day_misses` | Day boundary isolation |
| `test_different_limit_misses` | Limit boundary isolation |
| `test_put_is_idempotent_upsert` | Upsert overwrites correctly |
| `test_persists_across_instances` | SQLite persists across process restarts |

All 6 use `tmp_path` — no shared state between tests. ✅

---

## What Was Done Well (cache-specific)

- Cache is optional (`None` default in `run_mine`) — existing callers/tests unaffected.
- Day-keyed means a re-run on the same day costs zero API quota.
- Upsert semantics mean a repeated `put` is safe (idempotent).
- `cache.db` gitignored before any usage — no accidental commit risk.
- Connection-per-operation is correct for a CLI tool (no long-running server, no connection pool needed).
- `test_persists_across_instances` explicitly verifies the SQLite file survives across `SearchCache` instances. Correct TDD for storage code.

---

## Remaining Issues

### One still-open (stale README line)

**README repo map test count** (`README.md:196`)
```
tests/   12 files, one per source module, 100 tests
```
Actual: **110 tests** (confirmed: `110 tests collected`). Development section on line 214 correctly says "110 tests passing." Just the repo map line is stale.

**Fix:** change `100 tests` → `110 tests` on line 196.

### Medium — Cache path is CWD-relative

`cli.py:105` — `SearchCache(Path("cache.db"))` creates `cache.db` in whatever directory `reporadar mine` is invoked from. Running from different directories produces multiple orphan cache files.
- **Fix:** `Path.home() / ".reporadar" / "cache.db"` or `XDG_CACHE_HOME`.

### Medium — No cache eviction / TTL

Day-keyed entries accumulate indefinitely. A year of daily runs → 365 × queries rows. No `DELETE WHERE day < cutoff` anywhere.
- **Fix (low urgency for CLI):** add a `prune(keep_days=7)` method on `SearchCache`; call it from the CLI after a successful mine.

### Low — No cache-hit signal in CLI output

User can't tell whether a run used cached data or live data. On a cache hit, they may think they're getting fresh GitHub results.
- **Fix:** count cache hits in `_search_all`, surface in `mine` output: `"(N queries from cache, M live)"`.

### Low — `pipeline.py:46-51` uncovered

```python
repos = client.search_repos(query, limit=limit)
# lines 46-51: RateLimitError + HTTPError branches inside _search_all
```
These branches exist but are not exercised in `test_cli_mine.py` when a cache is present. The old `search_many` tests covered the equivalent paths; `_search_all` refactor left them uncovered.
- **Fix:** add tests that pass a `SearchCache` miss and then raise `RateLimitError` / `HTTPError` from the mock transport.

---

## All Prior Critical/High Fixes — Still Holding

| ID | Fix | Status |
|----|-----|--------|
| C1 | Word-boundary tag matching | ✅ `re.search(r'\b...\b')` at `tags.py:74` |
| C2 | Differentiation score corrected | ✅ `none→9, adjacent→7` at `scoring.py:100` |
| H1 | `break` → `continue` on rate-limit | ✅ Fully redesigned as `rate_limited` flag in `pipeline.py:86-96` |
| H2 | Weight validator | ✅ `@model_validator` at `scoring.py:36` |
| H3 | Hardcoded path | ✅ `Path.home()` at `cli.py:32` |
| H4 | Empty storage package | ✅ Deleted; replaced by real `cache.py` |
| M3 | Portfolio fit floor | ✅ `_clamp(1 + 3 * ...)` at `scoring.py:68` |
| L1 | User-Agent URL | ✅ `"reporadar/0.1"` at `github.py:20` |

---

## Lint / Type / CI

| Check | Result |
|-------|--------|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run mypy src/` | ✅ No issues in 22 source files (was 21 — `cache.py` added, clean) |
| `uv run pytest -q` | ✅ 110 passed |
| Coverage | ✅ 96% (gate: 90%) |
| CI (`ci.yml`) | ✅ No changes needed — cache uses stdlib `sqlite3`, no new deps |

---

## Security

No regressions. Cache writes JSON-serialized `RepoCandidate` dicts to a local SQLite file. No user-controlled input reaches SQL query parameters — key is built from `query`/`limit`/`day` args, all internal. Parameterized query used (`?` placeholder). No injection risk.

---

## Verification

```
uv run pytest --collect-only  → 110 tests collected
uv run pytest -q              → 110 passed
uv run ruff check .           → All checks passed!
uv run mypy src/              → No issues in 22 source files
uv run pytest --cov-fail-under=90 → 96% ✅
```

---

## Saved Observations

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/docs/reviews/2026-06-15-2229-repo-engineering-review.md`
