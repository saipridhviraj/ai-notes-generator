# Sprint Agenda — Meeting 006 (2026-05-23_1419)

## Sprint Work Queue

| # | Source | Item | Owner | Phase | Execute? |
|---|--------|------|-------|-------|----------|
| 1 | runtime_bugs.md (new) | BUG-RT-012 — stub notes in `generated_notes/python_decorators/` (conftest placeholder text) | Backend | 1 | ✅ |
| 2 | post-Meeting-005 | Pipeline speed optimizations (research brief, Tavily policy, annotate tutor, gap patch-only) — verify shipped | Backend | 1 | ✅ verify |
| 3 | post-Meeting-005 | Side-by-side notes preview UI + `/result` markdown fields | Frontend | 3 | ✅ verify |
| 4 | current_status.md | Update status doc (181 tests, Meeting 006 scope) | Docs | 3 | ✅ |
| 5 | current_status.md → v1.1 | Browser E2E both tabs + 3-day course smoke | QA | 2 | ✅ checklist |
| 6 | production_backlog.md | Restore full prompts on Groq Dev tier | Backend | 1 | 🟡 Deferred — Ollama + production profile in use |
| 7 | Frontend build | `ImportMeta.env` + unused React imports — `npm run build` fails | Frontend | 3 | ✅ |
| 8 | `.env` alignment | `MAX_EVAL_RETRIES=1` to match optimized default | Backend | 1 | ✅ |

## Priority order
1. BUG-RT-012 (stub notes root cause)
2. Verify pipeline optimizations + notes preview
3. Frontend TS build green
4. QA full pytest + E2E checklist
5. Docs/status update
