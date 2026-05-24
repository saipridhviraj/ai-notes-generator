# Meeting 004 — Agenda
**Date:** 2026-05-23 | **Time:** 05:30 | **Type:** v1.1 Backlog Sprint

## Checks from Meeting 003
- [ ] Re-run E2E: generate → approve → completed
- [ ] Groq Dev tier availability check for production_backlog restore

## Sprint Goal
Ship v1.1 backlog items: persistent LangGraph checkpoints, API rate limiting, CI coverage 80%.

## Sprint Work Queue

| # | Source | Item | Owner | Phase | Execute this sprint? |
|---|--------|------|-------|-------|---------------------|
| 1 | runtime_bugs.md | *(none open)* | — | — | — |
| 2 | current_status.md | MemorySaver → SqliteSaver | Backend | 1 | ✅ |
| 3 | current_status.md | Rate limiting (slowapi) | Backend | 1 | ✅ |
| 4 | current_status.md | CI coverage 60% → 80% | DevOps | 3 | ✅ |
| 5 | current_status.md | Restore full prompts (Groq Dev tier) | Backend | 1 | 🟡 Deferred — Dev tier unavailable |
| 6 | production_backlog.md | Items 1–8 (prompt/token restore) | Backend | 1 | 🟡 Deferred — Groq Dev tier unavailable |
| 7 | production_backlog.md | Item 9 (rate-limit retry) | Backend | — | ✅ Already shipped |

## Production Backlog
**Deferred** — Groq Dev tier still unavailable. No prompt/token restore this sprint.
