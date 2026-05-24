"""Post-completion chat: user message → gap patch → save notes."""

from __future__ import annotations

import time
from pathlib import Path

from prompts.gap_bridger_prompts import get_chat_patch_prompt
from services.file_service import save_markdown, NOTES_DIR
from utils.gap_patch import apply_gap_patch
from utils.helpers import slugify

CHAT_ALLOWED_STATUSES = frozenset({"completed", "max_retries_reached"})


def validate_chat_request(state: dict) -> str | None:
    status = state.get("status", "")
    if status not in CHAT_ALLOWED_STATUSES:
        return f"Chat is only available after generation finishes (status={status})"
    if not (state.get("student_notes") or "").strip():
        return "No student notes to edit — generate notes first."
    if not (state.get("tutor_notes") or "").strip():
        return "No tutor notes to edit — generate notes first."
    return None


def save_session_notes(state: dict) -> list[str]:
    """Write current student/tutor markdown to disk; return absolute paths."""
    plan = state["planner_output"]
    if state.get("output_dir"):
        output_dir = Path(state["output_dir"])
    else:
        output_dir = NOTES_DIR / slugify(plan.topic)

    student_path = save_markdown(
        state["student_notes"],
        state["student_filename"],
        output_dir,
    )
    tutor_path = save_markdown(
        state["tutor_notes"],
        state["tutor_filename"],
        output_dir,
    )
    return [str(student_path), str(tutor_path)]


def handle_session_chat(state: dict, message: str) -> dict:
    """
    Apply user chat request via gap bridger and persist updated notes.
    Returns fields to merge into session state.
    """
    err = validate_chat_request(state)
    if err:
        raise ValueError(err)

    text = (message or "").strip()
    if len(text) < 3:
        raise ValueError("Message must be at least 3 characters.")

    errors = list(state.get("errors", []))
    patch = apply_gap_patch(
        student_notes=state["student_notes"] or "",
        tutor_notes=state["tutor_notes"] or "",
        research_data=state.get("research_data") or "",
        missing_topics=[f"User edit request: {text}"],
        diagram_issues=[],
        alignment_issues=[],
        session_id=state.get("session_id"),
        errors=errors,
        stream_node="gap_bridger",
        prompt_builder=get_chat_patch_prompt,
    )

    if "student_notes" not in patch and "tutor_notes" not in patch:
        if patch.get("errors"):
            raise RuntimeError(patch["errors"][-1])
        raise RuntimeError("No changes were applied.")

    updated = dict(state)
    if patch.get("student_notes") is not None:
        updated["student_notes"] = patch["student_notes"]
    if patch.get("tutor_notes") is not None:
        updated["tutor_notes"] = patch["tutor_notes"]
    updated["errors"] = patch.get("errors", errors)

    output_files = save_session_notes(updated)
    updated["output_files"] = output_files

    history = list(updated.get("chat_history") or [])
    now = time.time()
    history.append({"role": "user", "content": text, "ts": now})
    history.append(
        {
            "role": "assistant",
            "content": "Notes updated and saved from your request.",
            "ts": now,
        }
    )
    updated["chat_history"] = history[-40:]

    return {
        "student_notes": updated["student_notes"],
        "tutor_notes": updated["tutor_notes"],
        "output_files": output_files,
        "errors": updated["errors"],
        "chat_history": updated["chat_history"],
        "status": updated.get("status", "completed"),
    }
