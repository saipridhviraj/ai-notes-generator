"""SQLite outbox for note.ready events — retry when VB Academy is down."""
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

_db_path: str | None = None
_conn: sqlite3.Connection | None = None


def _db_path_resolved() -> str:
    global _db_path
    if _db_path is None:
        _db_path = os.getenv("NOTE_READY_OUTBOX_DB_PATH", "data/note_events.db")
    return _db_path


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = _db_path_resolved()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS note_events (
                event_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                next_retry_at REAL NOT NULL
            )
            """
        )
        _conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_note_events_status_retry "
            "ON note_events(status, next_retry_at)"
        )
        _conn.commit()
    return _conn


def reset_connection() -> None:
    """Close DB connection (tests)."""
    global _conn, _db_path
    if _conn is not None:
        _conn.close()
        _conn = None
    _db_path = None


def enqueue(payload: Dict[str, Any]) -> str:
    event_id = payload["event_id"]
    now = time.time()
    _get_conn().execute(
        """
        INSERT INTO note_events
            (event_id, payload_json, status, attempts, last_error, created_at, updated_at, next_retry_at)
        VALUES (?, ?, 'pending', 0, NULL, ?, ?, ?)
        """,
        (event_id, json.dumps(payload), now, now, now),
    )
    _get_conn().commit()
    return event_id


def mark_delivered(event_id: str) -> None:
    now = time.time()
    _get_conn().execute(
        """
        UPDATE note_events
        SET status = 'delivered', updated_at = ?, last_error = NULL
        WHERE event_id = ?
        """,
        (now, event_id),
    )
    _get_conn().commit()


def record_failure(event_id: str, error: str, *, max_attempts: int, backoff_sec: float) -> str:
    """Increment attempts; mark dead if max reached. Returns new status."""
    now = time.time()
    row = _get_conn().execute(
        "SELECT attempts FROM note_events WHERE event_id = ?",
        (event_id,),
    ).fetchone()
    if not row:
        return "missing"

    attempts = int(row["attempts"]) + 1
    if attempts >= max_attempts:
        status = "dead"
        next_retry = now
    else:
        status = "pending"
        next_retry = now + backoff_sec

    _get_conn().execute(
        """
        UPDATE note_events
        SET status = ?, attempts = ?, last_error = ?, updated_at = ?, next_retry_at = ?
        WHERE event_id = ?
        """,
        (status, attempts, error[:2000], now, next_retry, event_id),
    )
    _get_conn().commit()
    return status


def list_due_pending(limit: int = 50) -> List[Dict[str, Any]]:
    now = time.time()
    rows = _get_conn().execute(
        """
        SELECT event_id, payload_json, status, attempts, last_error, created_at, updated_at
        FROM note_events
        WHERE status = 'pending' AND next_retry_at <= ?
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (now, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_pending(limit: int = 100) -> List[Dict[str, Any]]:
    rows = _get_conn().execute(
        """
        SELECT event_id, payload_json, attempts, last_error, created_at, updated_at, status
        FROM note_events
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_by_status(status: Optional[str] = None) -> int:
    if status:
        row = _get_conn().execute(
            "SELECT COUNT(*) AS c FROM note_events WHERE status = ?",
            (status,),
        ).fetchone()
    else:
        row = _get_conn().execute("SELECT COUNT(*) AS c FROM note_events").fetchone()
    return int(row["c"]) if row else 0


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    row = _get_conn().execute(
        """
        SELECT event_id, payload_json, attempts, last_error, created_at, updated_at, status
        FROM note_events WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    payload = json.loads(row["payload_json"])
    return {
        "event_id": row["event_id"],
        "status": row["status"],
        "attempts": row["attempts"],
        "last_error": row["last_error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "payload": payload,
    }
