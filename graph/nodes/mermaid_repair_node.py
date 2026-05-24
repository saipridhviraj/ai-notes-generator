"""Re-run diagram JSON/SVG generation on existing student notes."""

from __future__ import annotations

import logging

from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import use_diagram_pipeline
from utils.diagram_paths import diagrams_dir_for_state
from utils.diagram_placeholders import convert_mermaid_blocks_to_placeholders
from utils.diagram_pipeline import render_diagrams_in_notes, strip_mermaid_from_notes
from utils.mermaid_enforce import ensure_mermaid_diagrams
from utils.mermaid_sanitize import sanitize_markdown_mermaid
from utils.node_lifecycle import set_status_detail

logger = logging.getLogger(__name__)


def mermaid_repair_node(state: GraphState) -> dict:
    plan = state["planner_output"]
    notes = state.get("student_notes") or ""
    errors = list(state.get("errors", []))
    session_id = state.get("session_id")

    if use_diagram_pipeline():
        set_status_detail(session_id, "Repairing diagrams (JSON + SVG)…")
        logger.info("[mermaid_repair_node] repairing JSON diagrams on existing student notes")
        try:
            repaired = render_diagrams_in_notes(
                strip_mermaid_from_notes(convert_mermaid_blocks_to_placeholders(notes)),
                plan.model_dump(),
                groq_client,
                diagrams_dir=diagrams_dir_for_state(state),
                session_id=session_id,
                stream_node="mermaid_repair",
                errors=errors,
                repair_only=True,
            )
            return {"student_notes": repaired, "errors": errors}
        except Exception as exc:
            errors.append(f"MermaidRepair (diagram pipeline): {exc}")
            return {"errors": errors}

    set_status_detail(session_id, "Repairing Mermaid diagrams…")
    logger.info("[mermaid_repair_node] repairing diagrams on existing student notes")

    repaired = ensure_mermaid_diagrams(
        notes,
        plan.model_dump(),
        groq_client,
        session_id=session_id,
        errors=errors,
    )
    repaired = sanitize_markdown_mermaid(repaired)

    return {
        "student_notes": repaired,
        "errors": errors,
    }
