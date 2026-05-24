# /backend — Senior Backend Developer

**Activates:** Senior Backend Developer agent

## Agent Activation Prompt

You are now the **Senior Backend Developer** for `ai-notes-generator`. Start fixing bugs immediately, in priority order.

## P0 Bugs — Fix These First

**1. Output path bug** (`services/file_service.py`)
- Current: `Path.cwd() / f"{slug}_student.md"`
- Fix: `Path(__file__).parent.parent / "generated_notes" / slug / f"{slug}_student.md"`
- Create `generated_notes/` on startup if missing

**2. Tutor rejection not blocking pipeline** (`graph/nodes/consult_tutor_node.py`)
- When `approved: False`, node still sets `planner_verified = True` — pipeline continues
- Fix: set `planner_verified = False`, add replan/error route in graph builder

**3. `error_clarification` field unused** (`api/routes.py`)
- `TutorRespondRequest` has the field but the route ignores it
- Fix: pass it as context when resuming the interrupt

## P1 Fixes

**4. Wire Mermaid validators** (`graph/nodes/evaluator_node.py`)
- `helpers.validate_all_mermaid_in_notes()` exists but is never called
- Fix: call it before scoring, append syntax errors to eval result

**5. Move gap bridger prompts** (`graph/nodes/gap_bridger_node.py` → `prompts/gap_bridger_prompts.py`)

## P2 Cleanup
- Remove duplicate `slugify` from `file_service.py`
- Remove duplicate `strip_json_fences` from `helpers.py`

## Output format
```
SENIOR BACKEND DEV REPORT
Bugs Fixed: X
Bugs Remaining: Y

FIXED
- [file:line] [description]

REMAINING
- [bug] [reason]

HANDED TO QA
- [changed files]
```

## Full briefing
→ `.cursor/rules/04-senior-backend-dev.mdc`
