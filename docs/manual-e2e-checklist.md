# Manual E2E Checklist

Run before production sign-off or after major UI/backend changes.
Requires: Ollama running, `uvicorn main:app --reload`, `npm run dev` in `frontend/`.

---

## Single lesson

- [ ] **New lesson** — sidebar topic → Start generation → pipeline runs
- [ ] **Plan review** — approve tutor plan (if prompted)
- [ ] **Live progress** — flowchart + live tokens update during student notes
- [ ] **Split view** — Show step outputs → click Research / Student in rail
- [ ] **Completion** — notes preview renders; Mermaid diagrams render (no syntax error SVG)
- [ ] **Quality review** — eval pass/fail shown; regenerate buttons work
- [ ] **Chat edit** — send edit → gap bridger → preview refreshes
- [ ] **Download** — student + tutor from preview and sidebar
- [ ] **Reload** — refresh browser → last session restores
- [ ] **History** — previous session in sidebar → reopen → notes still load

## Interrupted job recovery

- [ ] Start generation → restart uvicorn mid-run → amber **interrupted** banner appears
- [ ] **Restart generation** completes or **Cancel** clears job

## Full course

- [ ] **+ Plan** — syllabus form (days, hours, checkpoint) → plan created
- [ ] **Approve plan** → day 1 generation starts
- [ ] **Day progress** — active day panel shows pipeline
- [ ] **Checkpoint** — after N days, checkpoint review appears → approve continues
- [ ] **Pause / Resume** — Pause generation → Resume generation works
- [ ] **Per-day preview** — select day → notes + quality review + chat
- [ ] **Sidebar downloads** — latest day, per-day picker, all days
- [ ] **Reload** — Full course tab restores last course

## Auth (production)

- [ ] Set `APP_API_KEY` + `VITE_API_KEY` → UI works
- [ ] Remove key from frontend → list/status calls return 401

---

## Automated API coverage (Sprint 009)

Run: `pytest tests/e2e/test_api_checklist.py -q --no-cov`

| Checklist area | Covered by API test |
|----------------|---------------------|
| Auth — key required | `TestAuthChecklist` (4 tests) |
| New lesson → list → status | `test_generate_list_status_result_flow` |
| Interrupted flag | `test_interrupted_session_shows_flag` |
| Restart interrupted | `test_restart_interrupted_session` |
| Course plan → list → approve → cancel → resume | `test_course_plan_list_status_controls` |
| Chat without notes → 400 | `test_session_chat_rejects_without_notes` |

**Not covered by API tests (browser required):** live progress UI, split view, Mermaid render, download buttons, reload persistence, checkpoint UX, pause/resume buttons in UI.

---

**Sign-off**

| Tester | Date | Result | Notes |
|--------|------|--------|-------|
| QA (API automated) | 2026-05-23 | ✅ Pass | 9/9 `test_api_checklist.py` |
| QA (Ollama live) | 2026-05-23 | ❌ Fail | Timed out 1200s on `student_notes` — retry with `OLLAMA_E2E_TIMEOUT=3600` |
| Tutor (browser) | | ⬜ Pass / ⬜ Fail | Run sections above in browser |
