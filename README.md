# RepoRadar — GitHub Repo Idea Miner

> Mine GitHub for promising AI / LLM / QA / dev-tool repos, compare them against
> your existing local projects, and get ranked, differentiated, build-ready
> project ideas — with source links, MVP scope, validation plan, and Kanban
> task drafts.

RepoRadar turns the recurring question *"what should I vibe-code next?"* into a
repeatable, local-first CLI pipeline. It is deterministic by default: **no LLM
API keys required.**

```text
GitHub search → enrich READMEs → scan local portfolio → score → cluster → ideas
                                                                       ↓
                                                      Markdown + JSON + Kanban drafts
```

## Why it exists

A list of trending repos is not useful on its own. RepoRadar explains, for each
opportunity:

- what people are building and why it is interesting,
- whether you already built something similar (local duplication check),
- a differentiated build angle,
- an MVP scope and a validation plan,
- and a Kanban task draft you can review (never auto-created).

## How it compares

| Tool | What it does | What RepoRadar adds |
|------|--------------|---------------------|
| GitHub Trending / search | Lists popular repos | Scores for *your* niche, dedupes vs your portfolio, emits build ideas |
| Langfuse / Arize / Opik | LLM observability & eval *runtime* | Not runtime — a *discovery* layer that finds what to build next |
| Awesome-lists | Curated static links | Live mining + ranking + differentiation angle + MVP scope |
| "Ask an LLM for ideas" | Free-form, ungrounded | Every idea cites fetched GitHub repos; links never invented |

RepoRadar is a **portfolio-gap radar**, not an eval/observability tool. It
answers "what should I build next, given what already exists and what I've
already built?" — deterministically, no API keys.

## Install

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
```

## Quickstart

List the built-in search profiles:

```bash
uv run reporadar profiles
```

Run the full mining workflow (works unauthenticated; set `GITHUB_TOKEN` to lift
rate limits):

```bash
uv run reporadar mine --profile baha-ai-qa --limit 12 --out reports/latest.md
```

Real output from a live run:

```text
Profile: baha-ai-qa
Repos analyzed: 12
Ideas recommended: 4
Top themes: Coding-Agent Orchestration, Agentic QA & Browser Testing, LLM Eval &
Observability, RAG Systems & Eval
Markdown report: reports/latest.md
JSON report: reports/latest.json
```

Scan only the local portfolio into an inventory:

```bash
uv run reporadar scan-local --root /Users/baha/Desktop/llm-ai-projects --out reports/local-inventory.json
# Scanned 71 local projects -> reports/local-inventory.json
```

Generate Kanban task drafts from a JSON report (drafts only — not created):

```bash
uv run reporadar kanban-drafts reports/latest.json --top 3 --out reports/kanban-drafts.md
```

Explain a single idea:

```bash
uv run reporadar explain reports/latest.json --idea "Self-Healing Browser QA Agent"
```

Preview a profile's queries without hitting the network, and control caching:

```bash
uv run reporadar mine --profile baha-ai-qa --dry-run     # list queries, fetch nothing
uv run reporadar mine --profile baha-ai-qa --no-cache    # bypass the per-day cache
```

Results are cached per day in `cache.db` (gitignored), so a repeated same-day
mine serves from cache instead of re-hitting the API (≈3× faster locally).

## Sample report excerpt

Real excerpt from `reports/latest.md`:

```markdown
### 1. Self-Healing Browser QA Agent

Score: 6.50/10

Source repos:
- https://github.com/qawolf/cli

Why it is interesting:
Browser tests break on selector drift; agentic QA repos show demand for resilient
flows. Example: qawolf/cli (3427★).

Local duplication check:
Similar local projects: IBG, agent-fleet-orchestrator, agentic-qa, ai-app-auditor,
ai-engineering-from-scratch, ai-voice-dictation, budgetzero-web, flightdeck-live-map,
and 9 more (closest verdict: adjacent). Build only if differentiated.

Differentiated build angle:
An agent that re-derives broken selectors from the DOM and proposes a verified
patch + screenshot diff.
```

Every recommendation cites **fetched** GitHub repos — links are never invented.

## How the local duplication check works

`scan-local` reads every immediate subdirectory of your projects root, extracts
each README title/summary and git remote, and infers coarse theme tags
(`llm-eval`, `agentic-qa`, `coding-agents`, …). When mining, each candidate repo
is compared against that inventory. A duplication verdict is assigned —
`none` / `adjacent` / `similar` / `duplicate` — and that verdict applies a
penalty in the scorer so ideas you have already built rank lower.

A theme overlap (shared tag) is **required** for a match, so unrelated projects
are not flagged just because their text happens to overlap.

## Scoring

Each opportunity is scored 1–10 on seven criteria, combined with explicit
weights (see `configs/scoring.yaml`):

```text
overall = 0.20*portfolio_fit + 0.20*market_pain + 0.15*novelty
        + 0.15*buildability + 0.10*demo + 0.10*differentiation + 0.10*proof
        - duplication_penalty
```

Freshness lowers `market_pain` for stale repos, so identical-but-stale repos
rank below active ones.

## Adding a search profile

Profiles live in `configs/profiles.yaml`. Add a named entry:

```yaml
profiles:
  my_profile:
    description: What this profile targets.
    queries:
      - "your GitHub search query stars:>20 pushed:>2026-01-01"
```

Then run `uv run reporadar mine --profile my_profile`.

## Repo map

```text
src/reporadar/
  cli.py                 Typer CLI: profiles · scan-local · mine · kanban-drafts · explain
  pipeline.py            Orchestrates one mining run (search → enrich → score → cluster → ideas)
  config.py              Loads search profiles from configs/profiles.yaml
  models.py              Pydantic models (RepoCandidate, LocalProject, IdeaRecommendation, …)
  sources/github.py      GitHub REST client (injectable httpx, pagination, rate-limit handling)
  local/scanner.py       Scans the local project portfolio into an inventory
  local/tags.py          Word-boundary theme-tag inference
  analysis/readme.py     Deterministic README title/summary/keyword extraction
  analysis/dedupe.py     Candidate-vs-local duplication verdict (shared-tag gated)
  analysis/scoring.py    Weighted 7-criteria scoring + duplication penalty
  analysis/clustering.py Tag-bucket theme clustering
  analysis/ideas.py      Cluster → IdeaRecommendation (blueprints from config + real repo signals)
  cache.py               Per-day SQLite cache of GitHub search results
  reports/markdown.py    Jinja2 Markdown report
  reports/json_report.py JSON report (machine-readable companion)
  reports/kanban.py      Kanban task drafts (drafts only — never auto-created)
  templates/             Jinja2 templates (report.md.j2, kanban_task.md.j2)
configs/                 profiles.yaml · scoring.yaml · blueprints.yaml (idea scaffolds)
tests/                   13 files, one per source module, 115 tests
docs/                    implementation-handoff.md, reviews/
```

## Limitations

- Clustering is tag-bucketed (keyword), not embedding-based.
- Idea blueprints are theme-templated (`configs/blueprints.yaml`), seeded with
  real repo signals at generation time.
- Cache is per-day and same-machine; no shared/remote cache.
- See `docs/implementation-handoff.md` §9 for the full list and Phase 2 plan.

## Development

```bash
make check   # ruff + mypy + pytest (coverage >= 90%) + format check
```

Current status: **115 tests passing, ~97% coverage.**

## Scope

Phase 1 (this repo): GitHub mining, local dedupe, deterministic scoring,
clustering, idea generation, Markdown/JSON reports, Kanban drafts. Phase 2 ideas
(web dashboard, HN/Reddit/X ingestion, LLM-assisted synthesis, direct Kanban
creation) are documented in `docs/implementation-handoff.md` but not built.
