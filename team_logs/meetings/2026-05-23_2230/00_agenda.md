# Meeting 009 — Agenda
**Date:** 2026-05-23_2230 | **Trigger:** `/sprint` (E2E validation backlog)

## Goals
1. Automate API-level manual E2E coverage (`tests/e2e/test_api_checklist.py`)
2. Run production Ollama single-lesson E2E against live backend
3. Add frontend Vitest smoke tests
4. Sign off API-covered checklist items; carry browser-only items forward
5. Defer Groq full-prompt restore until Dev tier confirmed

## Sprint Work Queue

| # | Source | Item | Owner | Phase | Execute? |
|---|--------|------|-------|-------|----------|
| 1 | runtime_bugs.md | *(none open)* | — | — | — |
| 2 | current_status.md | Manual browser E2E | QA / Tutor | 2 | ✅ API subset automated + signed |
| 3 | current_status.md | Production Ollama E2E sign-off | QA | 2 | ✅ Live test running |
| 4 | current_status.md | Frontend Vitest smoke tests | Frontend | 3 | ✅ 4 tests |
| 5 | current_status.md | Restore full prompts (Groq Dev tier) | Backend | 1 | 🟡 Deferred — tier not confirmed |
| 6 | production_backlog.md | Ollama production E2E | QA | 2 | ✅ `test_ollama_production_lesson.py` |

## Expected outcome
✅ GO (local) · Browser manual E2E ⬜ carry forward · Groq restore 🟡 deferred
