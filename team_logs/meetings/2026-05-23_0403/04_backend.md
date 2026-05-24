# Senior Backend Dev — Meeting 002
**Date:** 2026-05-23 | **Verdict:** ✅ ALL P0 BUGS RESOLVED

## Bugs Fixed

### BUG-1 ✅ Output path uses cwd → `generated_notes/<slug>/`
- `services/file_service.py`: Added `NOTES_DIR = PROJECT_ROOT / "generated_notes"` as module constant. Default `output_dir` now points to `NOTES_DIR`.
- `graph/nodes/final_response_node.py`: Imports `NOTES_DIR` + `slugify`. Computes `output_dir = NOTES_DIR / slugify(plan.topic)` before saving.
- `main.py`: lifespan calls `NOTES_DIR.mkdir(parents=True, exist_ok=True)` on startup.

### BUG-2 ✅ Tutor rejection silently continued pipeline
- `graph/nodes/consult_tutor_node.py`: Added rejection check — if `feedback.startswith("rejected:")` returns `{planner_verified: False, status: "rejected"}`.
- `graph/graph_builder.py`: Added `"rejected": END` to the conditional edges map in `route_after_tutor`.
- `route_after_tutor`: Checks `state.get("status") == "rejected"` before the `awaiting_tutor` check.
- `api/routes.py`: Fixed rejection text from `"rejected: {feedback}"` to include fallback `"no reason given"`.

### BUG-3 ✅ `response_to` field dead code
- `api/routes.py`: Now stores `request.response_to` into `session["state"]["response_to"]` so it flows through the graph and surfaces in `/status`.

### BUG-4 ✅ Mermaid validators never called
- `graph/nodes/evaluator_node.py`: Added `from utils.helpers import validate_all_mermaid_in_notes`. Calls it on `student_notes`, formats issues as `mermaid_context`, appends to evaluator LLM prompt.

### BUG-5 ✅ Gap bridger prompts inline
- Created `prompts/gap_bridger_prompts.py` with: `get_gap_content_prompt()`, `get_insertion_point_prompt()`, `get_annotation_prompt()`.
- `graph/nodes/gap_bridger_node.py`: Removed all inline f-strings, replaced with imports from new prompt module.

## Files Changed
| File | Change |
|------|--------|
| `services/file_service.py` | + `PROJECT_ROOT`, `NOTES_DIR` constants |
| `graph/nodes/final_response_node.py` | + `NOTES_DIR` import, slug-based output_dir |
| `main.py` | + `NOTES_DIR.mkdir()` in lifespan |
| `graph/nodes/consult_tutor_node.py` | + rejection detection, `re` import moved to top |
| `graph/graph_builder.py` | + `"rejected": END` edge, rejection check in router |
| `api/routes.py` | + `response_to` stored in session state |
| `graph/nodes/evaluator_node.py` | + `validate_all_mermaid_in_notes` call |
| `prompts/gap_bridger_prompts.py` | NEW — extracted prompt functions |
| `graph/nodes/gap_bridger_node.py` | + prompt module imports, removed inline f-strings |

## Cross-Team Flags
- QA: Add test `test_tutor_rejection_halts_graph` — key BUG-2 regression test
- QA: Add test `test_output_path_is_generated_notes` — key BUG-1 regression test
- DevOps: Mount `/app/generated_notes` as Docker volume (ADR-2)
- Architect: All ADRs implemented as specified
