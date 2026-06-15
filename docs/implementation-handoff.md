# RepoRadar — Implementation Handoff (Phase 1)

**Repo:** `github-repo-idea-miner` (product name: **RepoRadar**)
**Absolute repo path:** `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner`
**Status:** Phase 1 complete + code-review fixes (B1–B14, H3) + enhancements.
`make check` green — 115 tests, ~97% coverage.
**Date:** 2026-06-15

---

## 1. What this is

A local-first CLI (`reporadar`) that mines GitHub for AI / LLM / QA / dev-tool
repositories, compares them against Baha's local project portfolio at
`/Users/baha/Desktop/llm-ai-projects`, scores opportunities deterministically,
clusters them into themes, and emits ranked, differentiated build ideas as
Markdown + JSON reports plus Kanban task **drafts** (never auto-created).

Deterministic by design: **no LLM API keys required.** Every recommendation
cites fetched GitHub repos; links are never invented.

---

## 2. Architecture

```text
CLI (reporadar.cli, Typer)
 │   profiles · scan-local · mine · kanban-drafts · explain
 ▼
Pipeline (reporadar.pipeline.run_mine)         GitHub client injected → testable
 │
 ├─ config.load_profile        configs/profiles.yaml  → SearchProfile
 ├─ sources.github.GitHubClient REST search + README  (graceful rate-limit handling)
 ├─ analysis.readme            deterministic title/summary/headings/keywords
 ├─ local.scanner + local.tags scan portfolio → LocalProject[] + inferred tags
 ├─ analysis.dedupe            candidate vs locals → none/adjacent/similar/duplicate
 ├─ analysis.scoring           7 weighted criteria − duplication penalty (configs/scoring.yaml)
 ├─ analysis.clustering        tag buckets → IdeaCluster[]
 └─ analysis.ideas             clusters → IdeaRecommendation[] (blueprints)
 ▼
reports.report.MineReport  →  reports.markdown / reports.json_report / reports.kanban
                              (Jinja2 templates in reporadar/templates/)
```

Key design choices:

- **Dependency injection for network.** `GitHubClient` takes an `httpx.Client`,
  so the entire pipeline runs in tests against `httpx.MockTransport` — no
  network, no token. The CLI builds the real client via an overridable
  `build_github_client()` factory (monkeypatched in `tests/test_cli_mine.py`).
- **Errors collected, not raised.** `search_many` and README enrichment record
  rate-limit / network failures into `MineReport.errors` and keep going, so a
  partial run still produces a useful report and a documented blocker.
- **Determinism everywhere.** Scoring, dedupe, clustering, and idea blueprints
  are pure functions of inputs; `now` is injected so freshness logic is testable.

---

## 3. Feature flow (the `mine` command)

1. Load the named search profile (e.g. `baha-ai-qa`, 10 queries).
2. `GitHubClient.search_many` runs every query, de-duplicates repos by
   `full_name`, collects per-query errors.
3. Keep the top-`limit` repos by stars (deterministic set).
4. Best-effort README enrichment per repo; stop cleanly on rate limit.
5. Scan the local portfolio into a `LocalProject[]` inventory.
6. Score each repo (7 criteria, weighted, minus duplication penalty).
7. Cluster repos into themes by inferred tags.
8. Generate one idea per recognized cluster, each citing its source repos.
9. Write Markdown + JSON; print a Rich summary.

---

## 4. Scoring model

Seven 1–10 criteria, explicit weights in `configs/scoring.yaml`:

```text
overall = 0.20*portfolio_fit + 0.20*market_pain + 0.15*novelty
        + 0.15*buildability + 0.10*demo + 0.10*differentiation + 0.10*proof
        − duplication_penalty        # none 0 · adjacent 1 · similar 2 · duplicate 4
```

- `portfolio_fit` rises with the count of target theme tags.
- `market_pain` derives from stars, reduced when the repo is stale
  (`pushed_at` older than `stale_after_days`, default 365).
- `novelty` / `differentiation` derive from the duplication verdict.
- `proof` rises when README text mentions tests/CI/coverage/eval/benchmark.

Duplication requires a **shared theme tag** (not just text overlap), which
prevents unrelated local projects from being flagged. Verdict sharpens with
length-balanced fuzzy similarity (`rapidfuzz.token_sort_ratio`).

---

## 5. Tool stack

| Concern            | Choice                                   |
|--------------------|------------------------------------------|
| Packaging / venv   | `uv`, Python 3.12, hatchling build       |
| CLI                | Typer + Rich                             |
| Data models        | Pydantic v2                              |
| HTTP               | httpx (injectable client / MockTransport)|
| Fuzzy matching     | rapidfuzz                                |
| Templating         | Jinja2 (`reporadar/templates/`)          |
| Config             | PyYAML (`configs/*.yaml`)                |
| Tests              | pytest + pytest-cov                      |
| Lint / format      | ruff                                     |
| Types              | mypy (strict; tests relaxed)             |
| CI                 | GitHub Actions (`.github/workflows/ci.yml`) |

22 source modules, 13 test modules, 115 tests.

---

## 6. Validation — commands and real results

```bash
make check
```

Result (real, this run):

```text
uv run ruff check .            → All checks passed!
uv run mypy                    → Success: no issues found
uv run pytest --cov=src ...    → 115 passed; Total coverage: 96.72% (gate: 90%)
uv run ruff format --check .   → all files already formatted
```

Per-test-file coverage was 90–100% across all `src/reporadar` modules.

Live smoke test (real GitHub, unauthenticated, no token):

```bash
uv run reporadar mine --profile baha-ai-qa --limit 12 --out reports/latest.md
# Repos analyzed: 12 · Ideas recommended: 4 · no rate-limit errors
```

Network was available; no rate-limit fallback was triggered this run. If GitHub
rate-limits a future run, the affected queries are recorded in the report's
`errors` list and surfaced in the CLI summary — the run still completes.

---

## 7. Generated report artifacts (exact absolute paths)

- `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/reports/latest.md`
- `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/reports/latest.json`
- `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/reports/local-inventory.json`
- `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/reports/kanban-drafts.md`

---

## 8. Tests (what is covered)

| File                          | Covers                                        |
|-------------------------------|-----------------------------------------------|
| `test_models.py`              | Pydantic validation, score ranges, dup penalty |
| `test_config.py`              | Profile loading, unknown profile, custom path  |
| `test_readme_analysis.py`     | Title/summary/headings/keyword extraction      |
| `test_local_scanner.py`       | Scanner + tag inference, noise-dir skipping     |
| `test_github_source.py`       | Search mapping, rate limit, README, dedupe      |
| `test_dedupe.py`              | Verdicts, shared-tag requirement, flood regression |
| `test_scoring.py`            | Determinism, penalty, relevance, staleness      |
| `test_clustering.py`          | Theme grouping, multi-theme, "other" bucket     |
| `test_ideas.py`               | Idea generation, source citing, dup-note cap    |
| `test_markdown_report.py`     | Markdown/JSON/Kanban rendering                  |
| `test_cli.py`                 | profiles, scan-local, kanban-drafts, explain    |
| `test_cli_mine.py`            | End-to-end pipeline + `mine` command (mocked GH)|

---

## 9. Code-review fixes applied (B1–B14)

P0: B1 word-boundary tag matching · B2 monotonic differentiation score ·
B3 README rate-limit logs-and-continues (no `break`) · B4 weight-sum validator.
P1: B5 idea text now derives from the actual top repos (why/angle/MVP) ·
B6 buildability uses README/test/CI/install signals · B7 portfolio-fit floor
lowered to 1 · B8 idea score is top-weighted (0.7·best + 0.3·mean) ·
B9 graduated staleness decay (−1/−2/−3) · B10 proof requires ≥2 hints.
P2: B11 empty `storage/` package deleted · B12 pagination implemented ·
B13 User-Agent no longer advertises a fabricated repo URL · B14 JSON artifact
schema round-trip test added.

Repo-engineering review follow-up (`docs/reviews/2026-06-15-2209-…md`): that
review ran on a pre-fix snapshot, so C1/C2/H1/H2/H4/M1–M6/L1/L2 were already
resolved by B1–B14. Net-new items fixed: **H3** hardcoded personal path in
`cli.py` → `Path.home() / "Desktop/llm-ai-projects"` (portable default);
README gained a competitor-differentiation table (§5) and a repo map (§11);
`pip-audit` added as a CI step (`uvx pip-audit` → "No known vulnerabilities").

## Enhancements applied (post-review)

- **Blueprints externalized** to `configs/blueprints.yaml` (`load_blueprints()`),
  so ideas are tuned without touching code. `generate_ideas` accepts an optional
  `blueprints` override.
- **Per-day SQLite search cache** (`reporadar/cache.py`, `SearchCache`), wired
  through `run_mine(cache=...)` and the `mine --cache/--no-cache` flag. Keyed by
  `(day, limit, query)`. Verified locally: cache hit ≈3× faster than miss.
  Stored at `~/.reporadar/cache.db` (stable per-user, not CWD). `prune(keep_days=7)`
  runs on each mine to bound growth; CLI reports `N from cache, M live`.
- **`mine --dry-run`** lists the queries a profile would run with zero network
  calls and writes nothing.
- **`.gitignore`** added (caches, venv, `cache.db`).

## Known limitations / remaining work

Phase 1 deliberately stops short of:

- **README enrichment depth** — first meaningful paragraph only; no section-aware
  summarization.
- **Clustering is tag-bucketed**, not embedding-based; broad themes can over-match.
  Consider TF-IDF / embeddings if theme precision becomes a problem.
- **Idea blueprints are still theme-templated** — now seeded with real repo
  signals, but the scaffold (validation plan, tech stack) is per-theme.

Phase 2 (documented in the plan, not built): Next.js dashboard, Hacker
News/Reddit/X ingestion, optional LLM-assisted cluster synthesis with
deterministic fallback, and a `create-kanban` command that creates Hermes Kanban
cards **after explicit user approval** (drafts only today).

---

## 10. Quick reference

```bash
uv sync
uv run reporadar profiles
uv run reporadar mine --profile baha-ai-qa --limit 12 --out reports/latest.md
uv run reporadar scan-local --root /Users/baha/Desktop/llm-ai-projects --out reports/local-inventory.json
uv run reporadar kanban-drafts reports/latest.json --top 3 --out reports/kanban-drafts.md
make check
```

**Repo path:** `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner`
**This handoff:** `/Users/baha/Desktop/llm-ai-projects/github-repo-idea-miner/docs/implementation-handoff.md`
