import logging
import os
from pathlib import Path
from graph.state import GraphState
from services.file_service import save_markdown, NOTES_DIR
from services.note_ready_publisher import publish_note_ready
from utils.helpers import slugify
from services.prompt_config import use_diagram_pipeline
from utils.mermaid_sanitize import normalize_markdown_mermaid
from utils.diagram_placeholders import convert_mermaid_blocks_to_placeholders
from utils.student_notes_clean import clean_student_notes

logger = logging.getLogger(__name__)

MIN_NOTE_CHARS = int(os.getenv("MIN_NOTE_CHARS", "500"))


def _check_note_length(label: str, content: str | None, errors: list) -> None:
    length = len(content or "")
    if length < MIN_NOTE_CHARS:
        msg = (
            f"FinalResponseNode: {label} suspiciously short ({length} chars, "
            f"min {MIN_NOTE_CHARS}) — generation may have failed or timed out"
        )
        logger.warning("[final_response_node] %s", msg)
        errors.append(msg)


def final_response_node(state: GraphState) -> dict:
    student_notes = state["student_notes"]
    tutor_notes = state["tutor_notes"]
    student_filename = state["student_filename"]
    tutor_filename = state["tutor_filename"]
    plan = state["planner_output"]
    errors = list(state.get("errors", []))

    student_notes = clean_student_notes(student_notes or "")
    if use_diagram_pipeline():
        student_notes = convert_mermaid_blocks_to_placeholders(student_notes)
    else:
        student_notes = normalize_markdown_mermaid(student_notes)
    tutor_notes = tutor_notes or ""

    _check_note_length("student notes", student_notes, errors)
    _check_note_length("tutor notes", tutor_notes, errors)

    if state.get("output_dir"):
        output_dir = Path(state["output_dir"])
    else:
        output_dir = NOTES_DIR / slugify(plan.topic)

    try:
        student_path = save_markdown(student_notes, student_filename, output_dir)
        tutor_path = save_markdown(tutor_notes, tutor_filename, output_dir)
    except Exception as e:
        logger.error("[final_response_node] file save failed | error=%s", e, exc_info=True)
        errors.append(f"FinalResponseNode: file save failed — {e}")
        return {"errors": errors, "status": "failed"}

    try:
        publish_note_ready(state, student_path, tutor_path, output_dir)
    except Exception as e:
        logger.warning("[final_response_node] note.ready publish failed | error=%s", e)

    use_llm_summary = os.getenv("FINAL_SUMMARY_LLM", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if use_llm_summary:
        try:
            from services.groq_client import groq_client

            summary_prompt = (
                f"Summarize in one sentence what was generated:\n"
                f"Topic: {plan.topic}\n"
                f"Student file: {student_filename}\n"
                f"Tutor file: {tutor_filename}"
            )
            summary = groq_client.complete(
                prompt=summary_prompt,
                size="small",
                temperature=0.1,
                max_tokens=128,
                session_id=state.get("session_id"),
                stream_node="final_response",
            )
        except Exception as e:
            summary = (
                f"Generated {student_filename} and {tutor_filename} for topic: {plan.topic}"
            )
            errors.append(f"FinalResponseNode: summary generation failed — {e}")
    else:
        summary = (
            f"Generated {student_filename} and {tutor_filename} for topic: {plan.topic}"
        )

    return {
        "output_files": [str(student_path), str(tutor_path)],
        "final_summary": summary,
        "status": "completed",
        "errors": errors,
    }
