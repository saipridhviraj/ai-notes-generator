"""Pipeline node lifecycle — immediate UI updates between steps."""

from __future__ import annotations

from utils.helpers import get_session, set_session
from utils.node_labels import get_node_label
from utils.pipeline_progress import next_pipeline_node, pipeline_node_has_output
from utils.stream_bus import publish_activity, start_node


def mark_node_started(session_id: str | None, node_id: str) -> None:
    """Update session before heavy work; emit token-stream start."""
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        return
    session["current_node"] = node_id
    session["node_phase"] = "starting"
    session["status_detail"] = _starting_detail(node_id)
    set_session(session_id, session)
    start_node(session_id, node_id)


def mark_node_streaming(session_id: str | None, node_id: str) -> None:
    """First LLM token arrived — clear starting placeholder."""
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        return
    if session.get("current_node") != node_id:
        return
    if session.get("node_phase") == "streaming":
        return
    session["node_phase"] = "streaming"
    session["status_detail"] = None
    set_session(session_id, session)


def set_status_detail(session_id: str | None, detail: str | None) -> None:
    """Lightweight status line for pre-LLM work (no full graph state change)."""
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        return
    session["status_detail"] = detail
    set_session(session_id, session)
    if detail:
        publish_activity(session_id, detail)


def advance_after_node_complete(
    session_id: str | None,
    completed_node: str,
    graph_state: dict,
) -> None:
    """
    When a node finishes, mark next step active immediately so the UI does not
    lag on the completed node while LangGraph hands off.
    """
    if not session_id:
        return
    session = get_session(session_id)
    if not session:
        return

    merged = {**session.get("state", {}), **graph_state}
    if merged.get("status") != "running":
        return

    next_id = next_pipeline_node(completed_node, merged)
    if not next_id:
        session["node_phase"] = None
        session["status_detail"] = None
        set_session(session_id, session)
        return

    session["current_node"] = next_id
    session["node_phase"] = "starting"
    session["status_detail"] = _starting_detail(next_id)
    set_session(session_id, session)


def resolve_active_node(current_node: str | None, status: str, state: dict) -> str | None:
    """Pick the step that should appear active (handles completed-node handoff)."""
    if status == "awaiting_tutor":
        return "consult_tutor"
    if status != "running" or not current_node:
        return current_node

    if pipeline_node_has_output(current_node, state):
        nxt = next_pipeline_node(current_node, state)
        return nxt or current_node
    return current_node


def _starting_detail(node_id: str) -> str:
    label = get_node_label(node_id)
    return f"Starting {label}…"
