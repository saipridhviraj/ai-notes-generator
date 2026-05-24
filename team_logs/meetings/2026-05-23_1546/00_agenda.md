# Sprint 007 Agenda — Node Output Sidebar + Split View

**Date:** 2026-05-23_1546  
**Trigger:** User `/sprint` — implement per-node output rail (research brief, student notes, etc.)

## Sprint Work Queue

| # | Source | Item | Owner | Phase | Execute |
|---|--------|------|-------|-------|---------|
| 1 | User request | Per-node output sidebar + split-pane UI | Backend + Frontend | 1–3 | ✅ |
| 2 | current_status.md | Manual browser E2E | QA | 2 | 🟡 Document checklist |
| 3 | production_backlog.md | E2E Ollama production profile | QA | 2 | 🟡 User-run |
| 4 | runtime_bugs.md | *(none open)* | — | — | — |

## Success criteria
- `/status` returns `node_artifacts` metadata per pipeline step
- `GET /artifacts/{session_id}/{node_id}` returns full node output
- UI: left rail clickable; split view shows frozen output + live progress continues
- Tests pass; coverage ≥ 80%
