"""SQLite persistence for multi-day course runs."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any

from graph.course_models import CoursePlan

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None
_course_store: dict[str, dict[str, Any]] = {}


def _db_path() -> str:
    return os.getenv("COURSE_DB_PATH", "data/courses.db")


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = _db_path()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        _conn.commit()
    return _conn


def _serialize_plan(plan: CoursePlan | None) -> dict | None:
    return plan.model_dump() if plan else None


def _deserialize_plan(data: dict | None) -> CoursePlan | None:
    if not data:
        return None
    return CoursePlan(**data)


def _persist(course_id: str, data: dict) -> None:
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO courses (course_id, data_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(course_id) DO UPDATE SET
            data_json = excluded.data_json,
            updated_at = excluded.updated_at
        """,
        (course_id, json.dumps(_prepare(data)), time.time()),
    )
    conn.commit()


def _prepare(obj: Any) -> Any:
    if isinstance(obj, CoursePlan):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _prepare(v) for k, v in obj.items() if k != "task"}
    if isinstance(obj, list):
        return [_prepare(v) for v in obj]
    return obj


def _restore(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "days" in obj and "course_name" in obj and "total_days" in obj:
            try:
                return CoursePlan(**obj)
            except Exception:
                pass
        return {k: _restore(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_restore(v) for v in obj]
    return obj


def _load(course_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT data_json FROM courses WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    if not row:
        return None
    return _restore(json.loads(row[0]))


def create_course(
    course_id: str,
    course_name: str,
    syllabus: str,
    total_days: int,
    hours_per_day: float,
    checkpoint_every: int,
    programming_languages: list[str],
    output_root: str,
) -> dict:
    data = {
        "course_id": course_id,
        "course_name": course_name,
        "syllabus": syllabus,
        "total_days": total_days,
        "hours_per_day": hours_per_day,
        "checkpoint_every": checkpoint_every,
        "programming_languages": programming_languages,
        "output_root": output_root,
        "plan": None,
        "status": "planning",
        "next_day": 1,
        "days_completed": [],
        "day_outputs": {},
        "day_sessions": {},
        "errors": [],
        "checkpoint_message": None,
        "task": None,
        "start_time": time.time(),
    }
    with _lock:
        _course_store[course_id] = data
    _persist(course_id, data)
    return data


def get_course(course_id: str) -> dict | None:
    with _lock:
        if course_id in _course_store:
            return _course_store[course_id]
    loaded = _load(course_id)
    if loaded:
        with _lock:
            _course_store[course_id] = loaded
    return loaded


def set_course(course_id: str, data: dict) -> None:
    with _lock:
        _course_store[course_id] = data
    _persist(course_id, data)


def update_course(course_id: str, **fields) -> dict | None:
    data = get_course(course_id)
    if not data:
        return None
    data.update(fields)
    set_course(course_id, data)
    return data


def list_courses(limit: int = 50) -> list[dict]:
    """Summaries for course history UI (newest first)."""
    from utils.session_store import get_session

    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT course_id, data_json, updated_at
        FROM courses
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (max(1, min(limit, 200)),),
    ).fetchall()

    summaries: list[dict] = []
    for course_id, data_json, updated_at in rows:
        try:
            data = _restore(json.loads(data_json))
        except (json.JSONDecodeError, TypeError):
            continue
        days_completed = data.get("days_completed") or []
        day_sessions = data.get("day_sessions") or {}
        chat_count = 0
        for sid in day_sessions.values():
            session = get_session(sid)
            if session:
                chat_count += len(session.get("state", {}).get("chat_history") or [])
        summaries.append(
            {
                "course_id": course_id,
                "course_name": str(data.get("course_name") or "Untitled course")[:200],
                "status": data.get("status", "unknown"),
                "start_time": data.get("start_time") or updated_at,
                "total_days": int(data.get("total_days") or 0),
                "days_completed_count": len(days_completed),
                "has_notes": len(days_completed) > 0,
                "chat_count": chat_count,
            }
        )
    return summaries


def delete_course(course_id: str) -> bool:
    """Remove course from memory and SQLite."""
    with _lock:
        _course_store.pop(course_id, None)

    conn = _get_conn()
    cur = conn.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    conn.commit()
    return cur.rowcount > 0


def delete_all_courses() -> int:
    """Delete every course record."""
    conn = _get_conn()
    rows = conn.execute("SELECT course_id FROM courses").fetchall()
    ids = {cid for (cid,) in rows} | set(_course_store.keys())

    with _lock:
        _course_store.clear()

    cur = conn.execute("DELETE FROM courses")
    conn.commit()
    return max(cur.rowcount, len(ids))
