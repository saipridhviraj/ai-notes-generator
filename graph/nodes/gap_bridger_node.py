import logging

from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import use_diagram_pipeline
from utils.gap_patch import apply_gap_patch
from utils.mermaid_enforce import ensure_mermaid_diagrams
from utils.mermaid_sanitize import sanitize_markdown_mermaid
from utils.student_notes_clean import clean_student_notes
from utils.diagram_placeholders import convert_mermaid_blocks_to_placeholders
from utils.diagram_paths import diagrams_dir_for_state
from utils.diagram_pipeline import render_diagrams_in_notes, strip_mermaid_from_notes

logger = logging.getLogger(__name__)


def gap_bridger_node(state: GraphState) -> dict:
    eval_result = state["evaluation_result"]
    errors = list(state.get("errors", []))

    missing_topics = eval_result.missing_topics
    diagram_issues = eval_result.diagram_issues
    alignment_issues = eval_result.alignment_issues or []

    patch = apply_gap_patch(
        student_notes=state["student_notes"] or "",
        tutor_notes=state["tutor_notes"] or "",
        research_data=state.get("research_data", ""),
        missing_topics=missing_topics,
        diagram_issues=diagram_issues,
        alignment_issues=alignment_issues,
        session_id=state.get("session_id"),
        errors=errors,
        stream_node="gap_bridger",
    )

    if not patch.get("student_notes") and not patch.get("tutor_notes"):
        if patch.get("errors") and patch["errors"] != errors:
            return {"errors": patch["errors"]}
        return {}

    result = {
        "student_notes": patch.get("student_notes", state["student_notes"]),
        "tutor_notes": patch.get("tutor_notes", state["tutor_notes"]),
        "retry_count": state.get("retry_count", 0) + 1,
        "errors": patch.get("errors", errors),
    }

    if use_diagram_pipeline() and result.get("student_notes"):
        result["student_notes"] = convert_mermaid_blocks_to_placeholders(
            clean_student_notes(result["student_notes"])
        )

    if diagram_issues and result.get("student_notes"):
        if use_diagram_pipeline():
            result["student_notes"] = render_diagrams_in_notes(
                clean_student_notes(strip_mermaid_from_notes(result["student_notes"])),
                state["planner_output"].model_dump(),
                groq_client,
                diagrams_dir=diagrams_dir_for_state(state),
                session_id=state.get("session_id"),
                stream_node="gap_bridger",
                errors=result["errors"],
                repair_only=True,
            )
        else:
            result["student_notes"] = ensure_mermaid_diagrams(
                result["student_notes"],
                state["planner_output"].model_dump(),
                groq_client,
                session_id=state.get("session_id"),
                errors=result["errors"],
            )
            result["student_notes"] = sanitize_markdown_mermaid(
                clean_student_notes(result["student_notes"])
            )
    logger.info("[gap_bridger_node] patch applied")
    return result
