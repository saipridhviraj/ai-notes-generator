# System Architect — Meeting 002
**Date:** 2026-05-23 | **Verdict:** ✅ APPROVED (with ADRs)

## ADRs Produced

### ADR-1: Tutor Rejection Route — ACCEPTED
**Decision:** When tutor rejects, `consult_tutor_node` returns `planner_verified=False, status="rejected"`. Graph router adds "rejected" → END branch. Session status becomes "rejected" — client sees it on `/status`.
**Rationale:** Spec is silent on rejection behavior; END is the safest default for v1. Replan loop can be added in v2.
**Consequence:** Backend must add "rejected" key to `route_after_tutor` and add it to the conditional edges map.

### ADR-2: Output Path — ACCEPTED
**Decision:** Add `NOTES_DIR = Path(__file__).resolve().parent.parent / "generated_notes"` to `file_service.py`. `final_response_node` imports `NOTES_DIR` and passes `NOTES_DIR / slug` as `output_dir`. `main.py` lifespan creates the dir on startup.
**Consequence:** DevOps must mount `/app/generated_notes` as a volume.

### ADR-3: response_to Field — ACCEPTED
**Decision:** Pass `response_to` from the API route into the session state. `consult_tutor_node` reads it to distinguish plan verification from error clarification. For v1, both paths behave the same — the field is stored and returned in status so the client can use it.

### ADR-4: Mermaid Validation — ACCEPTED
**Decision:** `evaluator_node` imports `validate_all_mermaid_in_notes` from `utils.helpers` and calls it on `student_notes` before LLM scoring. Errors are appended to the evaluator prompt context.

## Approved Patterns (do not change)
- Node isolation: each node reads from `GraphState`, returns partial dict only
- Prompt modules: all prompt strings in `prompts/`, nodes only call them
- Services are singletons: initialized once at import

## Cross-Team Impacts
- ADR-1 → Backend: add "rejected" route; QA: add rejection test
- ADR-2 → DevOps: mount `/app/generated_notes` as volume; QA: assert path
