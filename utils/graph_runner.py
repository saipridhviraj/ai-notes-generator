"""Shared LangGraph stream consumer for generate / tutor-resume / node-resume."""

from __future__ import annotations

import asyncio

from utils.helpers import get_session, set_session


async def consume_graph_stream(session_id: str, stream) -> None:
    """Apply graph.astream updates to the HTTP session store."""
    try:
        async for event in stream:
            session = get_session(session_id)
            if session and session["state"].get("status") == "cancelled":
                break

            node_name = list(event.keys())[0]
            if node_name.startswith("__"):
                if node_name == "__interrupt__":
                    session = get_session(session_id)
                    if session:
                        session["state"]["status"] = "awaiting_tutor"
                        set_session(session_id, session)
                continue

            node_output = event[node_name]
            session = get_session(session_id)
            if session and isinstance(node_output, dict):
                session["state"].update(node_output)
                from utils.node_lifecycle import advance_after_node_complete

                advance_after_node_complete(session_id, node_name, session["state"])
                set_session(session_id, session)
    except asyncio.CancelledError:
        session = get_session(session_id)
        if session:
            session["state"]["status"] = "cancelled"
            set_session(session_id, session)
        raise
    except Exception as e:
        session = get_session(session_id)
        if session:
            session["state"]["status"] = "failed"
            session["state"]["errors"].append(f"Graph execution error: {e}")
            set_session(session_id, session)
