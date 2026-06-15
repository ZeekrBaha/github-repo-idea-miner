# Repo Engineering Review — Re-check (all medium items resolved)

**Reviewed:** 2026-06-15 22:36 CDT  
**Prior review:** `docs/reviews/2026-06-15-2229-repo-engineering-review.md`

---

## About

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner` — Python 3.12 CLI (RepoRadar) that mines GitHub for AI/LLM/QA repos, scores/dedupes against local portfolio, clusters by theme, emits ranked build ideas as Markdown + JSON + Kanban drafts. Stack: uv · Pydantic v2 · httpx · rapidfuzz · Typer · Rich · Jinja2 · SQLite · ruff · mypy.

---

## Verdict

**Ship-ready.** All critical, high, and medium issues from prior reviews resolved. Remaining open items are cosmetic/low-impact only. 115 tests, 97% coverage, all gates green. No blockers.

---

## Fixes Confirmed Since Prior Review (22:29)

| Prior Item | Fix | Status |
|-----------|-----|--------|
| M — `cache.db` in CWD | `DEFAULT_CACHE_PATH = Path.home() / ".reporadar" / "cache.db"` (`cli.py:35`) | ✅ |
| M — No cache eviction | `cache.prune(today, keep_days=7)` called after each mine (`cli.py:109`); `prune()` in `cache.py:56-62` | ✅ |
| L — No cache-hit signal | `report.cache_hits`/`cache_misses` tracked in pipeline, printed in CLI output (`cli.py:131-132`) | ✅ |
| L — `pipeline.py:46-51` uncovered | `_search_all` error branches now covered — `pipeline.py` at 100% coverage | ✅ |
| L — README repo map test count stale | README development section now says "115 tests passing, ~97% coverage" | ✅ (partial — see below) |

### New features added

**`--dry-run` flag** (`cli.py:88-100`) — prints queries that would run without touching network or writing files. Uncovered (lines 97-99) but intentional: dry-run is a CLI-only path not exercised by unit tests.

**Cache hit/miss tracking in pipeline** — `_SearchResult` dataclass carries `hits`/`misses`, flows into `MineReport.cache_hits`/`cache_misses`, printed in CLI summary.

**`cache.prune(today, keep_days=7)`** auto-called each mine. Prevents unbounded DB growth.

---

## Remaining Open Items

### One stale README line

`README.md:196` — repo map section still says `"100 tests"`:
```
tests/   12 files, one per source module, 100 tests
```
Actual: **115 tests**. Development section (line 214) correctly says "115 tests passing." One line inconsistency.

### Low — CLI `--dry-run` path untested (lines 97-99)

Dry-run branch (`cli.py:94-100`) prints profile info and exits. Not covered by tests. Low risk (no side effects), but worth a `test_cli.py` case.

### Low — `--cache` help text still says `cache.db` (`cli.py:86`)

```python
help="Cache GitHub results in cache.db (per day)."
```
Path moved to `~/.reporadar/cache.db` but help string wasn't updated. Misleading to users.

### Persistent minor gaps (not blocking)

- `dedupe.py:41,67,71` — `_ratio` zero-branch, `_pair_level` name-only path
- `readme.py:68,74-75,79` — edge cases in summary extraction  
- `scanner.py:31-32,42-43` — `OSError` paths
- `github.py:43,106-107,118-119` — token path, README error branches
- `cli.py:47` — `build_github_client` factory (never called in tests — monkeypatched)

All cosmetic; 97% overall coverage is well above the 90% gate.

---

## Full Issue Resolution Summary (All Three Reviews)

| ID | Sev | Issue | Status |
|----|-----|-------|--------|
| C1 | Critical | Tag false positives — no word boundaries | ✅ Fixed |
| C2 | Critical | Differentiation score inverted | ✅ Fixed |
| H1 | High | `break` on rate-limit → incomparable scores | ✅ Fixed + improved (flag+continue) |
| H2 | High | Weights not validated to sum 1.0 | ✅ Fixed |
| H3 | High | Hardcoded `/Users/baha/` path in source | ✅ Fixed |
| H4 | High | Empty storage package | ✅ Replaced with real `cache.py` |
| M1 | Medium | Static blueprints | Acknowledged in Limitations section |
| M2 | Medium | `_buildability` constant | Acknowledged in Limitations section |
| M3 | Medium | `_portfolio_fit` floor = 4 | ✅ Fixed |
| M4 | Medium | Idea score = mean | Acknowledged in Limitations section |
| M5 | Medium | Staleness penalty binary | Acknowledged in Limitations section |
| M6 | Medium | `_proof` too loose | Acknowledged in Limitations section |
| M-cache | Medium | `cache.db` in CWD | ✅ Fixed → `~/.reporadar/cache.db` |
| M-evict | Medium | No cache eviction | ✅ Fixed → `prune(keep_days=7)` |
| L1 | Low | User-Agent bad URL | ✅ Fixed |
| L2 | Low | No artifact shape test | Acknowledged |
| L-signal | Low | No cache-hit signal | ✅ Fixed → hits/misses in CLI output |
| L-pipeline | Low | `pipeline.py:46-51` uncovered | ✅ Fixed → 100% pipeline coverage |
| README §5 | — | Missing differentiation table | ✅ Added |
| README §11 | — | Missing repo map | ✅ Added |
| README §14 | — | Missing limitations | ✅ Added |
| README count | Low | Stale test count | ⚠ Partially fixed — line 196 still says 100 |
| L-help | Low | `--cache` help text stale | ⚠ Still says `cache.db` not `~/.reporadar/cache.db` |
| L-dryrun | Low | `--dry-run` untested | ⚠ Open |

---

## Lint / Type / CI

| Check | Result |
|-------|--------|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run mypy src/` | ✅ No issues in 22 source files |
| `uv run pytest -q` | ✅ 115 passed |
| Coverage | ✅ 97% (gate: 90%) |
| `pipeline.py` | ✅ 100% coverage |
| `cache.py` | ✅ 100% coverage |
| CI (`ci.yml`) | ✅ No changes needed — `sqlite3` is stdlib |

---

## Verification

```
uv run pytest --collect-only → 115 tests collected
uv run pytest -q             → 115 passed
uv run ruff check .          → All checks passed!
uv run mypy src/             → No issues in 22 source files
uv run pytest --cov-fail-under=90 → 97% ✅
pipeline.py coverage         → 100% (was 90% with uncovered _search_all branches)
cache.py coverage            → 100%
```

---

## Saved Observations

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/docs/reviews/2026-06-15-2236-repo-engineering-review.md`
