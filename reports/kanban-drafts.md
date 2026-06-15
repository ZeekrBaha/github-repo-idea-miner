# Kanban Task Drafts

> Drafts only — not auto-created.

## Build: Self-Healing Browser QA Agent

_Recommendation score: 6.50/10_

**Angle:** An agent that re-derives broken selectors from the DOM and proposes a verified patch + screenshot diff.

**Source repos:**
- https://github.com/qawolf/cli

**Local duplication:** Similar local projects: IBG, agent-fleet-orchestrator, agentic-qa, ai-app-auditor, ai-engineering-from-scratch, ai-voice-dictation, budgetzero-web, flightdeck-live-map, and 9 more (closest verdict: adjacent). Build only if differentiated.

**MVP scope:**
- [ ] Run a Playwright flow and detect a broken selector
- [ ] Re-locate the element and propose a patch
- [ ] Emit before/after screenshots as evidence

**Acceptance criteria:**
- [ ] Break a selector deliberately and confirm auto-recovery
- [ ] Verify screenshot diff is attached to the report

**Tech stack:** python, playwright, typer

---

## Build: LLM Eval Drift Dashboard

_Recommendation score: 6.24/10_

**Angle:** A dashboard that diffs eval runs over time and flags statistically meaningful regressions.

**Source repos:**
- https://github.com/langfuse/langfuse
- https://github.com/future-agi/future-agi
- https://github.com/raga-ai-hub/RagaAI-Catalyst
- https://github.com/comet-ml/opik

**Local duplication:** Similar local projects: IBG, Ozon-SwiftUI-iOS-Russian-Ecommerce-Market-App, Telethon Telegram Analysis Bot, agent-fleet-orchestrator, agentic-qa, ai-engineering-from-scratch, ai-news-bot-spec, budgetzero-web, and 30 more (closest verdict: similar). Build only if differentiated.

**MVP scope:**
- [ ] Ingest eval run JSON (promptfoo/deepeval shape)
- [ ] Compute per-metric deltas between runs
- [ ] Flag regressions beyond a threshold

**Acceptance criteria:**
- [ ] Feed two eval runs and confirm regression flags
- [ ] Confirm no false positive on identical runs

**Tech stack:** python, pydantic, rich

---

## Build: RAG Retrieval Auditor

_Recommendation score: 5.70/10_

**Angle:** Score retrieval recall/precision per query and surface the worst-performing chunks.

**Source repos:**
- https://github.com/raga-ai-hub/RagaAI-Catalyst
- https://github.com/comet-ml/opik

**Local duplication:** Similar local projects: IBG, Ozon-SwiftUI-iOS-Russian-Ecommerce-Market-App, Telethon Telegram Analysis Bot, agent-fleet-orchestrator, agentic-qa, ai-engineering-from-scratch, ai-news-bot-spec, budgetzero-web, and 30 more (closest verdict: similar). Build only if differentiated.

**MVP scope:**
- [ ] Run a labeled query set against a retriever
- [ ] Compute recall@k and precision@k
- [ ] Report worst queries with missing chunks

**Acceptance criteria:**
- [ ] Run against a known gold set
- [ ] Confirm metrics match hand calculation

**Tech stack:** python, pydantic, rich
