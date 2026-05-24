"""Generate JSON diagrams + SVG from student-notes placeholders."""

from __future__ import annotations

import logging

from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import use_diagram_pipeline
from utils.diagram_paths import diagrams_dir_for_state
from utils.diagram_placeholders import convert_mermaid_blocks_to_placeholders
from utils.diagram_pipeline import render_diagrams_in_notes, strip_mermaid_from_notes
from utils.node_lifecycle import set_status_detail
from utils.student_notes_clean import clean_student_notes

logger = logging.getLogger(__name__)


def diagram_generator_node(state: GraphState) -> dict:
    if not use_diagram_pipeline():
        return {}

    notes = state.get("student_notes") or ""
    errors = list(state.get("errors", []))
    session_id = state.get("session_id")
    plan = state["planner_output"]

    set_status_detail(session_id, "Generating diagram JSON and SVG…")
    logger.info("[diagram_generator_node] rendering diagrams from placeholders")

    try:
        notes = convert_mermaid_blocks_to_placeholders(clean_student_notes(notes))
        notes = strip_mermaid_from_notes(notes)
        notes = render_diagrams_in_notes(
            notes,
            plan.model_dump(),
            groq_client,
            diagrams_dir=diagrams_dir_for_state(state),
            session_id=session_id,
            stream_node="diagram_generator",
            errors=errors,
        )
        return {"student_notes": notes, "errors": errors}
    except Exception as exc:
        logger.error("[diagram_generator_node] failed: %s", exc, exc_info=True)
        errors.append(f"DiagramGenerator failed: {exc}")
        return {"errors": errors, "status": "failed"}
