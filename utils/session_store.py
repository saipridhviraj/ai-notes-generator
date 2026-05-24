"""SQLite-backed HTTP session store — survives server restarts (tasks stay in-memory)."""
import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional

from graph.state import EvaluationResult, KeywordPlan

_MODEL_TYPES = {
    "KeywordPlan": KeywordPlan,
    "EvaluationResult": EvaluationResult,
}

_db_path: str | None = None
_conn: sqlite3.Connection | None = None

# In-memory only: asyncio tasks cannot be persisted
session_store: Dict[str, Dict[str, Any]] = {}


def _db_path_resolved() -> str:
    global _db_path
    if _db_path is None:
        _db_path = os.getenv("SESSION_DB_PATH", "data/sessions.db")
    return _db_path


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = _db_path_resolved()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                current_node TEXT,
                start_time REAL NOT NULL
            )
            """
        )
        _conn.commit()
    return _conn


def _prepare_for_json(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return {"__model__": obj.__class__.__name__, "data": obj.model_dump()}
    if isinstance(obj, dict):
        return {k: _prepare_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prepare_for_json(v) for v in obj]
    return obj


def _restore_from_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        if set(obj.keys()) == {"__model__", "data"} and obj["__model__"] in _MODEL_TYPES:
            return _MODEL_TYPES[obj["__model__"]](**obj["data"])
        return {k: _restore_from_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_restore_from_json(v) for v in obj]
    return obj


def _persist(session_id: str, data: dict) -> None:
    state = data.get("state", {})
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO sessions (session_id, state_json, current_node, start_time)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            state_json = excluded.state_json,
            current_node = excluded.current_node,
            start_time = excluded.start_time
        """,
        (
            session_id,
            json.dumps(_prepare_for_json(state)),
            data.get("current_node"),
            data.get("start_time", time.time()),
        ),
    )
    conn.commit()


def _load_from_db(session_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT state_json, current_node, start_time FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    state_json, current_node, start_time = row
    return {
        "state": _restore_from_json(json.loads(state_json)),
        "current_node": current_node,
        "start_time": start_time,
        "task": None,
    }


def get_session(session_id: str) -> Optional[dict]:
    if session_id in session_store:
        return session_store[session_id]
    loaded = _load_from_db(session_id)
    if loaded:
        session_store[session_id] = loaded
    return loaded


def set_session(session_id: str, data: dict) -> None:
    session_store[session_id] = data
    _persist(session_id, data)
    try:
        from utils.status_events import publish_status_update

        publish_status_update(session_id)
    except Exception:
        pass


def list_sessions(limit: int = 50) -> list[dict]:
    """Summaries for session history UI (newest first)."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT session_id, state_json, start_time
        FROM sessions
        ORDER BY start_time DESC
        LIMIT ?
        """,
        (max(1, min(limit, 200)),),
    ).fetchall()

    summaries: list[dict] = []
    for session_id, state_json, start_time in rows:
        try:
            state = _restore_from_json(json.loads(state_json))
        except (json.JSONDecodeError, TypeError):
            continue
        plan = state.get("planner_output")
        topic = getattr(plan, "topic", None) if plan else None
        if not topic:
            topic = state.get("user_input") or "Untitled lesson"
        summaries.append(
            {
                "session_id": session_id,
                "topic": str(topic)[:200],
                "status": state.get("status", "unknown"),
                "start_time": start_time,
                "has_notes": bool((state.get("student_notes") or "").strip()),
                "output_files": state.get("output_files") or [],
                "chat_count": len(state.get("chat_history") or []),
                "student_filename": state.get("student_filename"),
                "tutor_filename": state.get("tutor_filename"),
            }
        )
    return summaries


def delete_session(session_id: str) -> bool:
    """Remove session from memory and SQLite. Cancels in-flight task if present."""
    session = get_session(session_id)
    if session:
        task = session.get("task")
        if task and not task.done():
            task.cancel()
        session_store.pop(session_id, None)

    conn = _get_conn()
    cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()

    try:
        from utils.stream_bus import clear_session

        clear_session(session_id)
    except Exception:
        pass

    return cur.rowcount > 0


def delete_all_sessions() -> int:
    """Delete every session. Cancels in-flight tasks."""
    conn = _get_conn()
    rows = conn.execute("SELECT session_id FROM sessions").fetchall()
    ids = {sid for (sid,) in rows} | set(session_store.keys())

    for session_id in ids:
        session = session_store.get(session_id)
        if not session:
            session = _load_from_db(session_id)
        if session:
            task = session.get("task")
            if task and not task.done():
                task.cancel()
        try:
            from utils.stream_bus import clear_session

            clear_session(session_id)
        except Exception:
            pass

    session_store.clear()
    cur = conn.execute("DELETE FROM sessions")
    conn.commit()
    return cur.rowcount


def clear_session_chat(session_id: str) -> bool:
    """Clear edit-chat history for a session (notes on disk are unchanged)."""
    session = get_session(session_id)
    if not session:
        return False

    task = session.get("task")
    if task is not None and not task.done():
        raise ValueError("Session is still running.")

    session["state"]["chat_history"] = []
    set_session(session_id, session)
    return True


def create_session(session_id: str, initial_state: dict, **meta) -> None:
    session_store[session_id] = {
        "state": initial_state,
        "task": None,
        "current_node": "planner",
        "start_time": time.time(),
        **meta,
    }
    _persist(session_id, session_store[session_id])
    try:
        from utils.status_events import publish_status_update

        publish_status_update(session_id)
    except Exception:
        pass
