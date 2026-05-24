"""Pipeline progress for tutor-facing UI — maps graph nodes to weighted steps."""
from __future__ import annotations

import os

from services.prompt_config import use_diagram_pipeline
from utils.node_personas import persona_for_step

_MERMAID_PIPELINE_STEPS: list[tuple[str, int]] = [
    ("planner", 8),
    ("consult_tutor", 15),
    ("research", 22),
    ("student_notes", 48),
    ("tutor_notes", 68),
    ("evaluator", 78),
    ("gap_bridger", 88),
    ("final_response", 96),
]

_JSON_PIPELINE_STEPS: list[tuple[str, int]] = [
    ("planner", 8),
    ("consult_tutor", 15),
    ("research", 22),
    ("student_notes", 42),
    ("diagram_generator", 48),
    ("tutor_notes", 68),
    ("evaluator", 78),
    ("gap_bridger", 88),
    ("final_response", 96),
]


def get_pipeline_steps() -> list[tuple[str, int]]:
    """Active pipeline steps — 8 for Mermaid mode, 9 when JSON/SVG pipeline is enabled."""
    if use_diagram_pipeline():
        return list(_JSON_PIPELINE_STEPS)
    return list(_MERMAID_PIPELINE_STEPS)


# Back-compat for imports that read the list at call time
PIPELINE_STEPS = _JSON_PIPELINE_STEPS


def _node_sequence() -> list[str]:
    return [node for node, _ in get_pipeline_steps()]


def _node_index() -> dict[str, int]:
    return {node: i for i, (node, _) in enumerate(get_pipeline_steps())}


def pipeline_node_has_output(node_id: str, state: dict) -> bool:
    """True when a pipeline step has produced inspectable output."""
    if node_id == "planner":
        return state.get("planner_output") is not None
    if node_id == "consult_tutor":
        return bool(state.get("planner_verified")) and state.get("status") != "awaiting_tutor"
    if node_id == "research":
        return bool(state.get("research_data"))
    if node_id == "student_notes":
        return bool(state.get("student_notes"))
    if node_id == "diagram_generator":
        notes = state.get("student_notes") or ""
        return "```diagram-json" in notes
    if node_id == "tutor_notes":
        return bool(state.get("tutor_notes"))
    if node_id == "evaluator":
        return state.get("evaluation_result") is not None
    if node_id == "gap_bridger":
        return bool(state.get("retry_count", 0) > 0 and state.get("evaluation_result"))
    if node_id == "final_response":
        return bool(state.get("final_summary") or state.get("output_files"))
    return False


def next_pipeline_node(completed_node: str, state: dict) -> str | None:
    """Next graph node after *completed_node* (conditional edges for evaluator)."""
    if completed_node == "evaluator":
        result = state.get("evaluation_result")
        max_retries = int(os.getenv("MAX_EVAL_RETRIES", "1"))
        retry_count = state.get("retry_count", 0)
        if result is None:
            return "final_response"
        if result.passed or retry_count >= max_retries:
            return "final_response"
        return "gap_bridger"

    sequence = _node_sequence()
    try:
        idx = sequence.index(completed_node)
    except ValueError:
        return None
    if idx + 1 >= len(sequence):
        return None
    return sequence[idx + 1]


def _resolve_active_index(
    current_node: str | None,
    status: str,
    state: dict,
) -> int:
    steps = get_pipeline_steps()
    node_index = _node_index()
    if status == "completed":
        return len(steps)
    if status == "awaiting_tutor":
        return node_index.get("consult_tutor", 1)

    active_node = current_node
    if status == "running" and current_node and pipeline_node_has_output(current_node, state):
        nxt = next_pipeline_node(current_node, state)
        if nxt and nxt in node_index:
            active_node = nxt

    if active_node and active_node in node_index:
        return node_index[active_node]
    return 0


def _step_states(
    current_node: str | None,
    status: str,
    retry_count: int = 0,
    state: dict | None = None,
) -> list[dict]:
    """Build checklist items — done steps use real outputs, not index lag."""
    state = state or {}
    active_idx = _resolve_active_index(current_node, status, state)
    pipeline_steps = get_pipeline_steps()

    items: list[dict] = []
    for i, (node_id, _) in enumerate(pipeline_steps):
        if status == "completed":
            if node_id == "gap_bridger" and retry_count == 0:
                step_state = "skipped"
            else:
                step_state = "done"
        elif pipeline_node_has_output(node_id, state) and i != active_idx:
            step_state = "done"
        elif i < active_idx and pipeline_node_has_output(node_id, state):
            step_state = "done"
        elif i < active_idx:
            step_state = "done"
        elif i == active_idx:
            step_state = "active"
        else:
            step_state = "pending"

        row = persona_for_step(node_id)
        if node_id == "consult_tutor" and status == "awaiting_tutor" and step_state == "active":
            row = {
                "persona": "Your review",
                "persona_icon": "🤚",
                "label": "Tutor review",
            }

        items.append(
            {
                "id": node_id,
                "label": row["label"],
                "persona": row["persona"],
                "persona_icon": row["persona_icon"],
                "state": step_state,
            }
        )
    return items


def get_pipeline_progress(
    current_node: str | None,
    status: str,
    retry_count: int = 0,
    state: dict | None = None,
    node_phase: str | None = None,
) -> dict:
    """Return progress fields for StatusResponse."""
    state = state or {}
    pipeline_steps = get_pipeline_steps()
    active_idx = _resolve_active_index(current_node, status, state)
    steps = _step_states(current_node, status, retry_count, state)
    total = len(pipeline_steps)

    if status == "completed":
        return {
            "progress_percent": 100.0,
            "progress_step": total,
            "progress_total": total,
            "pipeline_steps": steps,
        }

    if status in ("failed", "rejected", "cancelled", "max_retries_reached"):
        weight = pipeline_steps[active_idx][1] if active_idx < total else 0
        return {
            "progress_percent": float(weight),
            "progress_step": min(active_idx + 1, total),
            "progress_total": total,
            "pipeline_steps": steps,
        }

    if status == "awaiting_tutor":
        return {
            "progress_percent": float(pipeline_steps[1][1]),
            "progress_step": 2,
            "progress_total": total,
            "pipeline_steps": steps,
        }

    if active_idx < total:
        base = pipeline_steps[active_idx - 1][1] if active_idx > 0 else 0
        target = pipeline_steps[active_idx][1]
        fraction = 0.12 if node_phase == "starting" else 0.35
        mid = base + (target - base) * fraction
        return {
            "progress_percent": float(mid),
            "progress_step": active_idx + 1,
            "progress_total": total,
            "pipeline_steps": steps,
        }

    return {
        "progress_percent": 2.0,
        "progress_step": 1,
        "progress_total": total,
        "pipeline_steps": steps,
    }
