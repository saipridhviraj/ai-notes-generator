# Known Limitations

> Accepted risks and conscious trade-offs for v1.x. CEO marks 🟡 items here before shipping.
> Last updated: Sprint 008 (2026-05-23)

---

## Runtime & recovery

| # | Limitation | Impact | Status | Plan |
|---|-----------|--------|--------|------|
| L1 | Async tasks are in-memory | Server restart kills live graph/batch tasks | 🟡 Mitigated | UI shows **interrupted** banner; `POST /restart/{session}` and `POST /course/{id}/resume-batch` recover |
| L2 | LangGraph checkpoint resume | Restart may replay from checkpoint or fall back to full state | 🟡 Accepted | Depends on Ollama + checkpoint DB health |
| L3 | Course batch not auto-resumed on startup | `generating` courses stay interrupted until user clicks Continue | 🟡 Accepted | Logged at startup via `reconcile_stale_jobs_on_startup()` |

---

## Security & deployment

| # | Limitation | Impact | Status | Plan |
|---|-----------|--------|--------|------|
| L4 | `APP_API_KEY` optional in dev | All endpoints open when key unset | ✅ By design | **Must set** `APP_API_KEY` + `VITE_API_KEY` in production |
| L5 | Session/course IDs are UUIDs | Guessable if leaked; notes readable via `/result/{id}` with key | 🟡 Accepted v1 | Add signed URLs or auth middleware in v2 |
| L6 | Prompt injection | Only length limits on user input | 🟡 Accepted | Role-keyword filtering deferred |

---

## Quality & LLM

| # | Limitation | Impact | Status | Plan |
|---|-----------|--------|--------|------|
| L7 | Dev vs production prompts | Groq free tier uses trimmed dev profile | 🟡 Deferred | Use `USE_OLLAMA=true` + production profile locally |
| L8 | Light eval mode | Structural QA only; not deep content review | ✅ By design | Gap bridger + chat edits for manual fixes |
| L9 | Mermaid diagram quality | Up to 2 repair passes; some diagrams may still fail in UI | 🟡 Accepted | Sanitize on render + prompt retries |

---

## Frontend & testing

| # | Limitation | Impact | Status | Plan |
|---|-----------|--------|--------|------|
| L10 | No automated browser E2E | UI regressions caught manually only | ⬜ Open | See `docs/manual-e2e-checklist.md` |
| L11 | No frontend unit tests | React components untested in CI | ⬜ Open | Vitest smoke tests in future sprint |
| L12 | Course sidebar bulk download | Sequential file saves, not a zip | 🟡 Accepted | Zip endpoint optional v2 |

---

## Infrastructure

| # | Limitation | Impact | Status | Plan |
|---|-----------|--------|--------|------|
| L13 | SQLite for sessions/courses | Single-node; not horizontally scaled | 🟡 Accepted v1 | Postgres if multi-instance |
| L14 | CORS allowlist | Must set `CORS_ORIGINS` for non-localhost frontends | ✅ Documented | See README Configuration |
