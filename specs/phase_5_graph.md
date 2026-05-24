# Phase 5 — LangGraph Graph Assembly

**Goal:** Wire all 8 nodes into a `StateGraph`, define routing functions, compile the graph with `MemorySaver` checkpointing, and export a singleton `graph` instance.

---

## Task 5.1 — Graph Builder (`graph/graph_builder.py`)

### Imports required

```python
import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import GraphState
from graph.nodes import (
    planner_node, consult_tutor_node, research_node,
    student_notes_creator, tutor_notes_creator,
    evaluator_node, gap_bridger_node, final_response_node,
)
```

### `build_graph() -> CompiledGraph`

#### Step 1 — Create builder

```python
builder = StateGraph(GraphState)
```

#### Step 2 — Register all nodes

```python
builder.add_node("planner",        planner_node)
builder.add_node("consult_tutor",  consult_tutor_node)
builder.add_node("research",       research_node)
builder.add_node("student_notes",  student_notes_creator)
builder.add_node("tutor_notes",    tutor_notes_creator)
builder.add_node("evaluator",      evaluator_node)
builder.add_node("gap_bridger",    gap_bridger_node)
builder.add_node("final_response", final_response_node)
```

#### Step 3 — Set entry point

```python
builder.set_entry_point("planner")
```

#### Step 4 — Wire edges

```
planner ──────────────────────────────────────► consult_tutor
consult_tutor ─ (conditional: route_after_tutor) ─► research | consult_tutor
research ─────────────────────────────────────► student_notes
student_notes ────────────────────────────────► tutor_notes
tutor_notes ──────────────────────────────────► evaluator
evaluator ─ (conditional: route_after_evaluation) ─► final_response | gap_bridger
gap_bridger ──────────────────────────────────► evaluator
final_response ────────────────────────────────► END
```

Code:

```python
builder.add_edge("planner", "consult_tutor")

builder.add_conditional_edges(
    "consult_tutor",
    route_after_tutor,
    {
        "research":      "research",
        "consult_tutor": "consult_tutor",   # still waiting — loop
    }
)

builder.add_edge("research",       "student_notes")
builder.add_edge("student_notes",  "tutor_notes")
builder.add_edge("tutor_notes",    "evaluator")

builder.add_conditional_edges(
    "evaluator",
    route_after_evaluation,
    {
        "final_response":           "final_response",
        "gap_bridger":              "gap_bridger",
        "final_response_max_retries": "final_response",   # graceful give-up
    }
)

builder.add_edge("gap_bridger",    "evaluator")
builder.add_edge("final_response", END)
```

#### Step 5 — Compile with checkpointing

```python
return builder.compile(checkpointer=MemorySaver())
```

`MemorySaver` stores graph state in memory keyed by `thread_id` (= `session_id`).

---

## Task 5.2 — Routing Functions (`graph/graph_builder.py`)

Define these two functions in the same file, above `build_graph`.

### `route_after_tutor(state: GraphState) -> str`

```python
def route_after_tutor(state: GraphState) -> str:
    if state.get("awaiting_tutor", True):
        return "consult_tutor"
    return "research"
```

### `route_after_evaluation(state: GraphState) -> str`

```python
def route_after_evaluation(state: GraphState) -> str:
    result = state.get("evaluation_result")
    max_retries = int(os.getenv("MAX_EVAL_RETRIES", "3"))

    if result is None:
        # Evaluation failed to produce a result — give up gracefully
        return "final_response_max_retries"

    if result.passed:
        return "final_response"

    if state.get("retry_count", 0) >= max_retries:
        return "final_response_max_retries"

    return "gap_bridger"
```

---

## Task 5.3 — Graph Singleton (`graph/__init__.py`)

```python
from graph.graph_builder import build_graph

# Compiled once at startup; shared across all requests via thread_id
graph = build_graph()

__all__ = ["graph"]
```

Nodes and routes import the compiled graph:

```python
from graph import graph
```

---

## Task 5.4 — Session Configuration Helper

LangGraph uses a `config` dict with `"configurable": {"thread_id": session_id}` to route checkpoints.

Define a helper in `utils/helpers.py` (spec in Phase 7):

```python
def get_graph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}
```

**Usage in routes:**
```python
await graph.ainvoke(initial_state, config=get_graph_config(session_id))
```

---

## Graph Flow Diagram

```
START
  │
  ▼
[planner] ──────────────────────────────────────────────────────────►
  │                                                                    │
  ▼                                                                    │
[consult_tutor] ◄─────────────────────────────── (awaiting_tutor=True)
  │
  │ (awaiting_tutor=False)
  ▼
[research]
  │
  ▼
[student_notes]
  │
  ▼
[tutor_notes]
  │
  ▼
[evaluator] ──── (passed=True)  ─────────────────────────────────────►
  │                                                                    │
  │ (passed=False, retry < max)                                        │
  ▼                                                                    │
[gap_bridger] ──────────────────────────────────────────────────────► │
  │                                                                    │
  │ (back to evaluator)                                                │
  ▼                                                                    │
[evaluator] ──── (retry >= max) ──────────────────────────────────────┤
                                                                       │
                                                                       ▼
                                                              [final_response]
                                                                       │
                                                                       ▼
                                                                     END
```

**Acceptance criteria:**
- `from graph import graph` works.
- `graph.get_graph().nodes` contains all 8 node names.
- Routing functions return valid edge keys.
- `build_graph()` compiles without errors after all nodes are implemented.
