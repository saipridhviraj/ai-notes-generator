# Project Current Status
> Last updated by: CEO — Meeting 010 (2026-05-24_0208)

---

## Overall Verdict
| Field | Value |
|-------|-------|
| Status | ✅ GO (local / teaching) |
| Active Milestone | Mermaid-only notes on Qwen 9B + fresh Gen AI regenerate |
| Overall Completion | ~99% |
| Last Meeting | [Meeting 010 — 2026-05-24_0208](meetings/2026-05-24_0208/) |
| Next Action | Regenerate Introduction to Generative AI; Ollama E2E sign-off |

---

## Codebase Structure (new)
| Resource | Purpose |
|----------|---------|
| [docs/CODEBASE.md](../docs/CODEBASE.md) | Module map, diagram modes, where to add code |
| [tests/README.md](../tests/README.md) | unit / integration / e2e layout |
| `utils/mermaid/` | Mermaid validate + repair (default) |
| `utils/diagram/` | JSON/SVG pipeline (opt-in) |

---

## Hard Blockers
**None.**

---

## Live Testing Status
| Field | Value |
|-------|-------|
| Tests | **339 passing**, ~80.5% coverage |
| Vitest | **4 passing** |
| Mermaid flow tests | **9** in `tests/unit/test_mermaid_flow_default.py` |
| Open runtime bugs | **0** |

---

## v1.1 Backlog
| Task | Owner | Status |
|------|-------|--------|
| Manual browser E2E | QA / Tutor | 🔄 |
| Production Ollama E2E sign-off | QA | 🔄 |
| Split helpers.py validators | Backend | ⬜ v1.2 |
| Restore full prompts (Groq Dev tier) | Backend | 🟡 Deferred |

---

## Team Log Files
| File | Purpose |
|------|---------|
| [runtime_bugs.md](runtime_bugs.md) | QA → Backend live bugs (0 open) |
| [production_backlog.md](production_backlog.md) | Dev workarounds for production restore |
| [../docs/known-limitations.md](../docs/known-limitations.md) | Accepted risks register |
| [../docs/CODEBASE.md](../docs/CODEBASE.md) | Codebase structure |
| [meetings/](meetings/) | Sprint history |
