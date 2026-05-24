# Phase 4 — LangGraph Node Implementations

**Goal:** Implement all 8 nodes in `graph/nodes/`. Each node is a Python function with signature `(state: GraphState) -> GraphState` (or a dict of partial state updates). Nodes import from `services/` and `prompts/` — no LLM logic lives directly in nodes.

---

## Task 4.1 — Planner Node (`graph/nodes/planner_node.py`)

**Model:** `llama-3.1-8b-instant` (size=`"small"`)
**Reads:** `state["user_input"]`, `state["session_id"]`
**Writes:** `state["planner_output"]`, `state["planner_verified"]`, `state["awaiting_tutor"]`, `state["tutor_question"]`, `state["status"]`

### Logic

1. Import `groq_client` from `services.groq_client`.
2. Import `get_planner_system_prompt`, `get_planner_user_prompt`, `get_tutor_verification_question` from `prompts.planner_prompts`.
3. Call `groq_client.complete_json(prompt=get_planner_user_prompt(state["user_input"]), size="small", system=get_planner_system_prompt(), temperature=0.1)`.
4. Parse the returned dict into a `KeywordPlan` Pydantic model.
5. Build `tutor_question` using `get_tutor_verification_question(plan.dict(), state["session_id"])`.
6. Return state updates:
   ```python
   {
       "planner_output": plan,
       "planner_verified": False,
       "awaiting_tutor": True,
       "tutor_question": tutor_question,
       "status": "awaiting_tutor",
   }
   ```

### Error handling

- Wrap in `try/except Exception as e`.
- On failure: append `f"PlannerNode failed: {e}"` to `state["errors"]`, set `status = "failed"`.

---

## Task 4.2 — ConsultTutor Node (`graph/nodes/consult_tutor_node.py`)

**No LLM — pure logic (Human-in-the-loop)**
**Reads:** `state["awaiting_tutor"]`, `state["tutor_response"]`, `state["planner_output"]`
**Writes:** `state["planner_verified"]`, `state["planner_feedback"]`, `state["awaiting_tutor"]`, `state["status"]`

### Logic

1. If `state["tutor_response"]` is `None` or empty string:
   - Graph is still waiting for the tutor.
   - Return state unchanged (the routing function will loop back to this node).

2. If `state["tutor_response"]` is populated:
   - Parse the response (it is a string — may contain feedback text or be simply `"approved"`).
   - Set `planner_verified = True`, `awaiting_tutor = False`, `status = "running"`.
   - Store the raw feedback text in `planner_feedback`.
   - If feedback contains keyword additions (e.g. "also add metaclasses"), update `planner_output.keywords` (simple string search — append the mentioned word if not already in list).
   - Clear `tutor_response` back to `None` (reset so it cannot trigger twice).

### Timeout (auto-approve after 5 minutes)

- Store `start_time` in the session store (via `utils.helpers.session_store`) keyed by `session_id`.
- On each entry to this node, check elapsed time.
- If elapsed > 300 seconds (5 minutes): auto-approve — set `planner_verified = True`, `awaiting_tutor = False`, `status = "running"`, append `"ConsultTutor: auto-approved after timeout"` to `state["errors"]`.

### Interrupt mechanism

This node uses LangGraph's `interrupt()`:
```python
from langgraph.types import interrupt

# Inside the node, when awaiting:
if not state["tutor_response"]:
    interrupt("Waiting for tutor response")
```

The graph resumes when `POST /tutor/respond/{session_id}` writes to the session store and the graph is resumed via the LangGraph checkpoint.

---

## Task 4.3 — Research Node (`graph/nodes/research_node.py`)

**Models:** `llama-3.1-8b-instant` (decide) + `llama-3.3-70b-versatile` (synthesize)
**Reads:** `state["planner_output"]`, `state["planner_feedback"]`
**Writes:** `state["research_data"]`, `state["used_web_search"]`

### Logic

**Step 1 — Decide (small model, temperature=0.1, max_tokens=64):**
- Call `groq_client.complete(prompt=get_research_decision_prompt(planner_output.dict()), size="small", temperature=0.1, max_tokens=64)`.
- Strip and lowercase the response.
- Decision = `True` if response starts with `"yes"`, `False` otherwise.

**Step 2a — Web search (only if decision is True):**
- Import `tavily_client` from `services.tavily_client`.
- Call `tavily_client.search_keywords(planner_output.keywords)`.
- Store formatted results in `web_results`.
- Set `used_web_search = True`.

**Step 2b — Synthesize (large model, temperature=0.3, max_tokens=8192):**
- Call `groq_client.complete(prompt=get_research_synthesis_user_prompt(...), size="large", system=get_research_synthesis_system_prompt(domain), temperature=0.3, max_tokens=8192)`.
- Store result in `research_data`.

**Return:**
```python
{
    "research_data": synthesized_text,
    "used_web_search": decision,
}
```

### Error handling

- If Tavily fails (returns empty list), log to `errors`, continue without web results.
- If synthesis fails, re-raise and let the outer try/except set `status = "failed"`.

---

## Task 4.4 — Student Notes Creator (`graph/nodes/student_notes_creator.py`)

**Model:** `llama-3.3-70b-versatile` (size=`"large"`)
**Reads:** `state["research_data"]`, `state["planner_output"]`
**Writes:** `state["student_notes"]`, `state["student_filename"]`

### Module-level example loading

```python
from services.file_service import load_example, slugify

STUDENT_EXAMPLE = load_example("day1_student_notes.md")
```

This runs once at import time. If the file is missing, the app will fail loudly on startup — that is intentional.

### Logic

1. Import prompts: `get_student_notes_system_prompt`, `get_student_notes_user_prompt`.
2. Build system prompt by passing `STUDENT_EXAMPLE` into `get_student_notes_system_prompt`.
3. Call `groq_client.complete(prompt=get_student_notes_user_prompt(planner_output, research_data), size="large", system=system_prompt, temperature=0.7, max_tokens=8192)`.
4. Generate filename: `slugify(planner_output.topic) + "_student.md"`.
5. Return:
   ```python
   {
       "student_notes": notes_markdown,
       "student_filename": filename,
   }
   ```

### Error handling

- Wrap in `try/except`. On failure append to `errors` and set `status = "failed"`.

---

## Task 4.5 — Tutor Notes Creator (`graph/nodes/tutor_notes_creator.py`)

**Model:** `llama-3.3-70b-versatile` (size=`"large"`)
**Reads:** `state["student_notes"]`, `state["planner_output"]`
**Writes:** `state["tutor_notes"]`, `state["tutor_filename"]`

### Module-level example loading

```python
TUTOR_EXAMPLE = load_example("day1_tutor_notes.md")
```

### Logic

1. Import prompts: `get_tutor_notes_system_prompt`, `get_tutor_notes_user_prompt`.
2. Build system prompt by passing `TUTOR_EXAMPLE` into `get_tutor_notes_system_prompt`.
3. Call `groq_client.complete(prompt=get_tutor_notes_user_prompt(planner_output, student_notes), size="large", system=system_prompt, temperature=0.7, max_tokens=8192)`.
4. Generate filename: `slugify(planner_output.topic) + "_tutor.md"`.
5. Return:
   ```python
   {
       "tutor_notes": notes_markdown,
       "tutor_filename": filename,
   }
   ```

---

## Task 4.6 — Evaluator Node (`graph/nodes/evaluator_node.py`)

**Model:** `deepseek-r1-distill-llama-70b` (size=`"reasoning"`)
**Reads:** `state["student_notes"]`, `state["tutor_notes"]`, `state["planner_output"]`, `state["retry_count"]`
**Writes:** `state["evaluation_result"]`, `state["retry_count"]`, `state["status"]`

### Logic

1. Import `get_evaluator_system_prompt`, `get_evaluator_user_prompt` from `prompts.evaluator_prompts`.
2. Call `groq_client.complete_json(prompt=get_evaluator_user_prompt(...), size="reasoning", system=get_evaluator_system_prompt(), temperature=0.1)`.
3. Parse response into `EvaluationResult` Pydantic model.
4. Increment `retry_count` by 1.
5. Check max retries:
   ```python
   max_retries = int(os.getenv("MAX_EVAL_RETRIES", "3"))
   if not result.passed and retry_count >= max_retries:
       errors.append(f"Max retries ({max_retries}) reached. Saving best attempt.")
       status = "max_retries_reached"
   ```
6. Return:
   ```python
   {
       "evaluation_result": result,
       "retry_count": new_retry_count,
       "status": updated_status,
       "errors": updated_errors,
   }
   ```

### Error handling

- If JSON parsing fails (model hallucinated non-JSON), create a fallback `EvaluationResult` with `passed=False`, `student_notes_score=0`, `tutor_notes_score=0`, `missing_topics=["evaluation_failed"]`.

---

## Task 4.7 — Gap Bridger Node (`graph/nodes/gap_bridger_node.py`)

**Model:** `llama-3.3-70b-versatile` (size=`"large"`)
**Reads:** `state["evaluation_result"]`, `state["student_notes"]`, `state["tutor_notes"]`, `state["research_data"]`
**Writes:** Updated `state["student_notes"]`, updated `state["tutor_notes"]`

**Key constraint:** Routes straight back to `evaluator` — never to `student_notes_creator` or `tutor_notes_creator`. This is surgical patching, not full regeneration.

### Logic — 3 Steps

**Step 1 — Generate gap content (large model):**
- Build prompt using the gap content generation prompt (from Phase 3 spec).
- Pass `missing_topics` and `diagram_issues` from `evaluation_result`.
- Call `groq_client.complete(...)` → `gap_content` (markdown string).

**Step 2 — Identify insertion points (large model):**
- Build prompt using the insertion point identification prompt.
- Pass `student_notes` and `gap_content`.
- Call `groq_client.complete_json(...)` → list of `{"insert_after": str, "content": str}`.

**Step 3 — Merge (pure Python, no LLM):**
```python
def merge_sections(existing_notes: str, insertions: list[dict]) -> str:
    for item in insertions:
        anchor = item["insert_after"]
        new_section = item["content"]
        if anchor in existing_notes:
            existing_notes = existing_notes.replace(
                anchor,
                anchor + "\n\n---\n\n" + new_section,
                1   # replace only the first occurrence
            )
    return existing_notes
```

- Apply `merge_sections` to `student_notes`.
- For `tutor_notes`: generate annotated versions of the new sections (small extra LLM call with the tutor annotation prompt), then apply `merge_sections`.

**Return:**
```python
{
    "student_notes": updated_student_notes,
    "tutor_notes": updated_tutor_notes,
}
```

---

## Task 4.8 — Final Response Node (`graph/nodes/final_response_node.py`)

**Model:** `llama-3.1-8b-instant` (size=`"small"`)
**Reads:** `state["student_notes"]`, `state["tutor_notes"]`, `state["student_filename"]`, `state["tutor_filename"]`, `state["session_id"]`, `state["planner_output"]`, `state["evaluation_result"]`
**Writes:** `state["output_files"]`, `state["final_summary"]`, `state["status"]`

### Logic

1. Import `save_markdown` from `services.file_service`.
2. Save both files:
   ```python
   student_path = save_markdown(student_notes, student_filename)
   tutor_path   = save_markdown(tutor_notes, tutor_filename)
   ```
3. Build `final_summary` (small model call, `max_tokens=256`, `temperature=0.1`):
   ```
   Summarize in one sentence what was generated:
   Topic   : {topic}
   Student : {student_filename}
   Tutor   : {tutor_filename}
   Keywords: {keywords}
   Retries : {retry_count}
   Web used: {used_web_search}
   ```
4. Return:
   ```python
   {
       "output_files": [str(student_path), str(tutor_path)],
       "final_summary": summary,
       "status": "completed",
   }
   ```

### Error handling

- If saving either file fails, append error to `errors` and set `status = "failed"`.

---

## `graph/nodes/__init__.py` Exports

```python
from graph.nodes.planner_node import planner_node
from graph.nodes.consult_tutor_node import consult_tutor_node
from graph.nodes.research_node import research_node
from graph.nodes.student_notes_creator import student_notes_creator
from graph.nodes.tutor_notes_creator import tutor_notes_creator
from graph.nodes.evaluator_node import evaluator_node
from graph.nodes.gap_bridger_node import gap_bridger_node
from graph.nodes.final_response_node import final_response_node

__all__ = [
    "planner_node", "consult_tutor_node", "research_node",
    "student_notes_creator", "tutor_notes_creator",
    "evaluator_node", "gap_bridger_node", "final_response_node",
]
```

**Acceptance criteria for all nodes:**
- Each node accepts `GraphState` and returns a dict of partial state updates.
- No node raises an unhandled exception — all errors are caught and appended to `state["errors"]`.
- All nodes are importable from `graph.nodes`.
