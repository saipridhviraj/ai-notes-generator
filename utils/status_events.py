"""Build session status payloads and push them over SSE."""

from __future__ import annotations

import time
from typing import Any

from api.models import NodeArtifactItem, StatusResponse, ChatMessageItem
from utils.node_artifacts import build_node_artifacts
from utils.node_labels import get_node_label
from utils.node_personas import get_persona
from utils.node_lifecycle import resolve_active_node
from utils.pipeline_progress import get_pipeline_progress
from utils.session_store import get_session

TERMINAL_STATUSES = frozenset(
    {
        "completed",
        "failed",
        "max_retries_reached",
        "rejected",
        "cancelled",
    }
)

# UI stops live updates but SSE stays open through plan review.
SSE_IDLE_STATUSES = TERMINAL_STATUSES | frozenset({"awaiting_tutor"})


def build_status_payload(session_id: str) -> dict[str, Any] | None:
    """Same shape as GET /status — suitable for JSON + SSE."""
    session = get_session(session_id)
    if not session:
        return None

    state = session["state"]
    elapsed = round(time.time() - session.get("start_time", time.time()), 1)
    current_node = session.get("current_node")
    session_status = state.get("status", "running")
    display_node = resolve_active_node(current_node, session_status, state)
    node_phase = session.get("node_phase")
    status_detail = session.get("status_detail")
    progress = get_pipeline_progress(
        current_node,
        session_status,
        state.get("retry_count", 0),
        state=state,
        node_phase=node_phase,
    )
    awaiting_human = session_status == "awaiting_tutor"
    persona = get_persona(display_node or current_node, awaiting_human=awaiting_human)
    artifacts_raw = build_node_artifacts(state, progress["pipeline_steps"])
    eval_result = state.get("evaluation_result")
    eval_passed = eval_result.passed if eval_result else None
    diagram_issues = len(eval_result.diagram_issues or []) if eval_result else 0
    chat_raw = state.get("chat_history") or []
    chat_history = [ChatMessageItem(**item) for item in chat_raw if isinstance(item, dict)]
    alive = _session_task_alive(session)
    return StatusResponse(
        session_id=session_id,
        status=session_status,
        current_node=display_node or current_node,
        node_label=get_node_label(display_node or current_node, awaiting_human=awaiting_human),
        active_persona=persona["name"] if persona else None,
        active_persona_icon=persona["icon"] if persona else None,
        active_persona_blurb=persona["blurb"] if persona else None,
        node_phase=node_phase,
        status_detail=status_detail,
        elapsed_seconds=elapsed,
        progress_percent=progress["progress_percent"],
        progress_step=progress["progress_step"],
        progress_total=progress["progress_total"],
        pipeline_steps=progress["pipeline_steps"],
        node_artifacts=[NodeArtifactItem(**a) for a in artifacts_raw],
        retry_count=state.get("retry_count", 0),
        tutor_question=state.get("tutor_question"),
        output_files=state.get("output_files", []),
        errors=state.get("errors", []),
        evaluation_passed=eval_passed,
        diagram_issue_count=diagram_issues,
        chat_history=chat_history,
        job_alive=alive if session_status == "running" else None,
        interrupted=session_status == "running" and not alive,
    ).model_dump()


def _session_task_alive(session: dict) -> bool:
    from utils.job_health import session_task_alive

    return session_task_alive(session)


def publish_status_update(session_id: str) -> None:
    """Push current status to SSE subscribers (no-op if session missing)."""
    payload = build_status_payload(session_id)
    if payload is None:
        return
    from utils.stream_bus import publish_status

    publish_status(session_id, payload)
