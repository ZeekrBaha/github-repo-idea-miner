# Repo Engineering Review — Re-check (post-fixes)

**Reviewed:** 2026-06-15 22:19 CDT  
**Prior review:** `docs/reviews/2026-06-15-2209-repo-engineering-review.md`

---

## About

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner` — Python 3.12 CLI (RepoRadar) that mines GitHub for AI/LLM/QA repos, scores and deduplicates them against a local portfolio, clusters by theme, and emits ranked build ideas as Markdown + JSON + Kanban drafts. Stack: uv · Pydantic v2 · httpx · rapidfuzz · Typer · Rich · Jinja2 · ruff · mypy.

---

## Verdict

**Near ship-ready.** All critical and high bugs from the prior review are fixed. One stale claim remains in the README ("100 tests" — actual is 101). Everything else is clean. Fix that one line, and this is portfolio-ready.

---

## Fixes Confirmed vs Prior Review

| Prior ID | Sev | Issue | Status |
|----------|-----|-------|--------|
| C1 | Critical | Tag substring false positives (`"rag"` matched `"storage"`) | ✅ Fixed — `re.search(r'\b...\b', ...)` in `tags.py:74` |
| C2 | Critical | Differentiation score inverted (`adjacent` > `none`) | ✅ Fixed — `none→9, adjacent→7, similar→4/5, duplicate→2/3` in `scoring.py:100-114` |
| H1 | High | `break` on README rate-limit made scores incomparable | ✅ Fixed — `continue` at `pipeline.py:54,60` |
| H2 | High | Weights not validated to sum to 1.0 | ✅ Fixed — `@model_validator` at `scoring.py:36-40` |
| H3 | High | Hardcoded `/Users/baha/...` path in source | ✅ Fixed — `Path.home() / "Desktop" / "llm-ai-projects"` at `cli.py:32` |
| H4 | High | Empty `storage/` package dead weight | ✅ Fixed — package deleted |
| M3 | Medium | `_portfolio_fit` floor=4 for zero-match repos | ✅ Fixed — `_clamp(1 + 3 * len(...))` at `scoring.py:68` |
| L1 | Low | User-Agent linked non-existent repo URL | ✅ Fixed — `_USER_AGENT = "reporadar/0.1"` at `github.py:20` |
| README | — | Missing §5 differentiation table | ✅ Added — "How it compares" section with Langfuse/Arize/etc table |
| README | — | Missing §11 repo map | ✅ Added — "Repo map" section |
| README | — | Missing §14 limitations | ✅ Added — "Limitations" section |

---

## Remaining Issues

### One still-open item

**README test count stale** (`README.md:185,202`)
- Repo map says: `"12 files, one per source module, 100 tests"`
- Development section says: `"100 tests passing, ~97% coverage"`
- Actual collected count: **101 tests**

The count moved from 86 → 101 (new tests added for the fixes). README wasn't updated to match.

**Fix:** Change both occurrences of `100 tests` → `101 tests`.

### Still-acknowledged medium items (non-blocking)

These were M-severity in prior review, not blocking for portfolio use but worth future work:

- **M1 Static blueprints** (`ideas.py:31`) — idea text still mostly templated, not derived from mined repo content. Noted in "Limitations" section now, which is the right call.
- **M2 `_buildability` constant** (`scoring.py`) — still only +1 for Python. Low discriminating power.
- **M4 Idea score = mean** (`ideas.py:201`) — strong outliers still diluted by weak cluster members.
- **M5 Staleness binary** (`scoring.py:79`) — -3 points for any repo >365 days with no graduation.
- **M6 `_proof` too loose** (`scoring.py:118`) — single word "test" still triggers +3.
- **L2 No artifact shape test** — still no test validating `reports/latest.json` round-trips through `IdeaRecommendation`.

---

## What Was Done Well (unchanged from prior review, all still hold)

- DI via `httpx.Client` injection — zero live network in tests
- Error collection into `MineReport.errors` — partial runs always produce output
- Pure functions throughout, `now` injected at CLI layer only
- Dedupe shared-tag gate — prevents false positives from unrelated text overlap
- `token_sort_ratio` — correct algorithm, avoids subset inflation
- Weights configurable in `configs/scoring.yaml`
- CI exactly matches `make check` — no drift
- 101 tests, 97% coverage, mypy strict clean, ruff clean

---

## Lint / Type / CI

| Check | Result |
|-------|--------|
| `uv run ruff check .` | ✅ All checks passed |
| `uv run mypy src/` | ✅ No issues in 21 source files |
| `uv run pytest -q` | ✅ 101 passed |
| `uv run pytest --cov-fail-under=90` | ✅ 97% coverage |
| CI (`ci.yml`) | ✅ Matches `make check`, no drift |
| `pip-audit` | ❌ Not installed — dependency CVE scan still blocked |

---

## README

Now comprehensive. All three missing sections added:
- ✅ §5 "How it compares" — differentiation table vs Langfuse/Arize/awesome-lists/LLMs
- ✅ §11 "Repo map" — per-file descriptions
- ✅ §14 "Limitations" — explicit list linking to handoff §9

**One remaining fix:** `"100 tests"` appears twice — should be `"101 tests"`.

No UI/screenshots needed — this is a CLI tool, not a dashboard.

---

## Security

No changes to security posture. Same as prior review:
- No hardcoded secrets
- No SQL/exec/injection risks
- `GITHUB_TOKEN` read from env var, never logged
- `pip-audit` still not available for dependency CVE scan

---

## Verification

Commands run on 2026-06-15 22:19 CDT:

```
uv run pytest --collect-only → 101 tests collected
uv run pytest -q             → 101 passed
uv run ruff check .          → All checks passed!
uv run mypy src/             → No issues in 21 source files
```

Confirmed fixed via source read:
- `tags.py:74` — `re.search(rf"\b{re.escape(trigger)}\b", blob)`
- `scoring.py:36-40` — `@model_validator` on `ScoringConfig`
- `scoring.py:68` — `_clamp(1 + 3 * len(tags & _TARGET_TAGS))`
- `scoring.py:100-114` — `none→9, adjacent→7`
- `pipeline.py:54,60` — `continue` (not `break`)
- `cli.py:32` — `Path.home() / "Desktop" / "llm-ai-projects"`
- `github.py:20` — `_USER_AGENT = "reporadar/0.1"`
- `storage/` — deleted

---

## Saved Observations

`/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/docs/reviews/2026-06-15-2219-repo-engineering-review.md`
