# Runtime Bugs — QA → Backend
> **Purpose:** Bugs found during live/manual runs (not unit tests). QA logs them here; Backend fixes and marks resolved.
> **Workflow:** Error during run → QA adds row → Backend picks up via `/backend` or `/sprint` → Code Reviewer + QA verify → mark ✅
> **Last updated:** 2026-05-23 (Meeting 003)

---

## How To Use This File

| Role | Action |
|------|--------|
| **QA / Tester (you or `/qa`)** | When something fails in the browser or terminal during a real run, add a row below with steps to reproduce |
| **Backend (`/backend`)** | Pick open ⬜ bugs, fix, update status to 🔄 then ✅ |
| **CEO (`/ceo`)** | Pulls open runtime bugs into Assigned Work table in next meeting report |

**Bug ID format:** `BUG-RT-###` (RT = runtime)

---

## Open Runtime Bugs

| ID | Summary | Steps to Reproduce | File / Area | Priority | Status | Owner | Notes |
|----|---------|-------------------|-------------|----------|--------|-------|-------|
| *(none)* | | | | | | | |

---

## Resolved Runtime Bugs

| ID | Summary | Fix | Resolved By | Date |
|----|---------|-----|-------------|------|
| BUG-RT-001 | Graph failed at planner: `object is not iterable` | Skip `__interrupt__` events in `api/routes.py` | Backend | 2026-05-23 |
| BUG-RT-002 | Browser Network Error on `/generate` | Added CORS middleware in `main.py` | Backend | 2026-05-23 |
| BUG-RT-003 | Tutor approve/resume broken on LangGraph 1.x | `Command(resume=...)` + updated `consult_tutor_node.py` | Backend | 2026-05-23 |
| BUG-RT-004 | Evaluator used decommissioned model | Swapped to `llama-3.3-70b-versatile` | Backend | 2026-05-23 |
| BUG-RT-005 | Groq TPM rate limits on free tier | Trimmed prompts; see `production_backlog.md` | Backend | 2026-05-23 |
| BUG-RT-006 | Double-click Approve → 400 | Hide tutor panel after respond | Frontend | 2026-05-23 |
| BUG-RT-007 | Gap bridger invalid/truncated JSON | Append-at-end fallback in `_resolve_insertions()` | Backend | 2026-05-23 |
| BUG-RT-008 | Session lost after server reload | Clear 404 message on all session endpoints | Backend | 2026-05-23 |
| BUG-RT-009 | Mermaid min-4 vs dev prompts | `MIN_MERMAID_DIAGRAMS` env (default 2) | Backend | 2026-05-23 |
| BUG-RT-010 | Frontend generic tutor error | Parse axios `detail` in StatusPanel | Frontend | 2026-05-23 |
| BUG-RT-011 | Groq 429 not retried | Retry-with-backoff in `groq_client.py` | Backend | 2026-05-23 |
| BUG-RT-012 | Stub notes in generated_notes (conftest placeholder text) | MIN_NOTE_CHARS warning in `final_response_node`; re-run generation | Backend | 2026-05-23 |

---

## QA Test Session Log (2026-05-23 — Live E2E)

**Environment:** Local dev, Groq free tier, uvicorn + Vite frontend  

| Time | Action | Result | Bug Filed |
|------|--------|--------|-----------|
| ~04:03 | `/generate` from UI | Network Error | BUG-RT-002 |
| ~04:33 | Generate | object is not iterable | BUG-RT-001 |
| ~04:39 | Approve tutor | 400 on 2nd click | BUG-RT-006 |
| ~04:51 | Full run | gap_bridger JSON fail; 429 | BUG-RT-007, BUG-RT-011 |
| ~05:00+ | Python Decorators | Notes generated ✅ | — |

**Meeting 003:** All filed bugs resolved. Re-test E2E recommended.
