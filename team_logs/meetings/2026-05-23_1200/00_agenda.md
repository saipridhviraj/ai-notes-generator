# Meeting 005 — Agenda
**Date:** 2026-05-23 | **Time:** 12:00 | **Type:** Dual-Flow End-to-End Sprint

## Sprint Goal
Wire **Single lesson** and **Full course** flows completely from UI → API → LangGraph, with live day-level progress inside the course tab.

## Sprint Work Queue

| # | Source | Item | Owner | Phase | Execute this sprint? |
|---|--------|------|-------|-------|---------------------|
| 1 | runtime_bugs.md | *(none open)* | — | — | — |
| 2 | User request | Enrich `GET /course/{id}/status` (plan_days, current_session_id, active day) | Backend | 1 | ✅ |
| 3 | User request | Track `current_generating_day` / `current_session_id` in course_runner | Backend | 1 | ✅ |
| 4 | User request | Persistent dual tabs (Single lesson \| Full course) with independent job state | Frontend | 3 | ✅ |
| 5 | User request | Rich CourseStatusPanel: plan checklist, course progress, day personas + token stream | Frontend | 3 | ✅ |
| 6 | User request | Tests for enriched course status response | QA | 2 | ✅ |
| 7 | current_status.md | Restore full prompts (Groq Dev tier) | Backend | 1 | 🟡 Deferred — Dev tier unavailable |
| 8 | production_backlog.md | Items 1–8 (prompt/token restore) | Backend | 1 | 🟡 Deferred — Groq Dev tier unavailable |

## Production Backlog
**Deferred** — Groq Dev tier still unavailable.
