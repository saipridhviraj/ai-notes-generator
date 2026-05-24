"""Publish note.ready events to VB Academy with outbox retry."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import httpx

from graph.state import GraphState
from models.note_ready import NoteReadyEvent
from models.tutor_supplements import TutorSupplements
from services.tutor_supplements_extractor import (
    extract_supplements,
    supplements_filename,
    write_supplements_json,
)
from utils import note_event_outbox as outbox

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    if os.getenv("NOTE_READY_ENABLED", "").strip().lower() in ("1", "true", "yes", "on"):
        return bool(webhook_url())
    return False


def webhook_url() -> str:
    return os.getenv("NOTE_READY_WEBHOOK_URL", "").strip()


def _max_attempts() -> int:
    return int(os.getenv("NOTE_READY_MAX_ATTEMPTS", "20"))


def _retry_interval_sec() -> float:
    return float(os.getenv("NOTE_READY_RETRY_INTERVAL_SEC", "300"))


def _webhook_timeout_sec() -> float:
    return float(os.getenv("NOTE_READY_WEBHOOK_TIMEOUT_SEC", "10"))


def _backoff_sec(attempts: int) -> float:
    base = float(os.getenv("NOTE_READY_RETRY_BACKOFF_SEC", "30"))
    return min(_retry_interval_sec(), base * (2 ** min(attempts, 6)))


def _sign_body(body: bytes) -> Optional[str]:
    secret = os.getenv("NOTE_READY_WEBHOOK_SECRET", "").strip()
    if not secret:
        return None
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_event(
    state: GraphState,
    student_path: Path,
    tutor_path: Path,
    output_dir: Path,
    supplements: TutorSupplements,
    supplements_path: Optional[Path] = None,
) -> NoteReadyEvent:
    plan = state["planner_output"]
    course_id = state.get("course_id")
    course_name: Optional[str] = None
    hours_per_day: Optional[float] = None
    programming_languages: list[str] = []

    if course_id:
        from utils.course_store import get_course

        course = get_course(course_id)
        if course:
            course_name = course.get("course_name")
            hours_per_day = course.get("hours_per_day")
            programming_languages = list(course.get("programming_languages") or [])

    title = plan.topic
    if state.get("course_day"):
        title = state["user_input"].split("\n", 1)[0].replace(f"Course day {state['course_day']}: ", "")

    return NoteReadyEvent(
        course_id=course_id,
        session_id=state["session_id"],
        day=state.get("course_day"),
        title=title,
        topic=plan.topic,
        course_name=course_name,
        student_uri=str(student_path.resolve()),
        tutor_uri=str(tutor_path.resolve()),
        supplements=supplements,
        supplements_uri=str(supplements_path.resolve()) if supplements_path else None,
        supplements_item_count=supplements.total_items(),
        output_root=str(output_dir.resolve()),
        programming_languages=programming_languages,
        hours_per_day=hours_per_day,
    )


def deliver_payload(payload: dict[str, Any]) -> None:
    """POST to VB Academy. Raises on failure."""
    url = webhook_url()
    if not url:
        raise RuntimeError("NOTE_READY_WEBHOOK_URL is not configured")

    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    signature = _sign_body(body)
    if signature:
        headers["X-Note-Ready-Signature"] = signature

    with httpx.Client(timeout=_webhook_timeout_sec()) as client:
        response = client.post(url, content=body, headers=headers)

    if response.status_code not in (200, 201, 202, 204):
        raise RuntimeError(
            f"note.ready webhook returned {response.status_code}: {response.text[:500]}"
        )


def _try_deliver(event_id: str, payload: dict[str, Any], *, current_attempts: int = 0) -> bool:
    try:
        deliver_payload(payload)
        outbox.mark_delivered(event_id)
        logger.info(
            "[note_ready] delivered | event_id=%s session_id=%s day=%s",
            event_id,
            payload.get("session_id"),
            payload.get("day"),
        )
        return True
    except Exception as e:
        status = outbox.record_failure(
            event_id,
            str(e),
            max_attempts=_max_attempts(),
            backoff_sec=_backoff_sec(current_attempts),
        )
        logger.warning(
            "[note_ready] delivery failed | event_id=%s status=%s error=%s",
            event_id,
            status,
            e,
        )
        return False


def publish_note_ready(
    state: GraphState,
    student_path: Path,
    tutor_path: Path,
    output_dir: Path,
) -> None:
    """
    Enqueue note.ready and attempt immediate delivery.
    Never raises — generation must not fail if VB Academy is down.
    """
    if not is_enabled():
        return

    tutor_markdown = state.get("tutor_notes") or ""
    supplements = extract_supplements(tutor_markdown)
    supplements_path: Optional[Path] = None
    student_filename = state.get("student_filename") or student_path.name
    if not supplements.is_empty():
        try:
            supplements_path = write_supplements_json(
                supplements,
                output_dir,
                supplements_filename(student_filename),
            )
        except Exception as e:
            logger.warning("[note_ready] could not write supplements json | error=%s", e)

    event = build_event(
        state,
        student_path,
        tutor_path,
        output_dir,
        supplements,
        supplements_path,
    )
    payload = event.model_dump()
    event_id = outbox.enqueue(payload)
    _try_deliver(event_id, payload)


def retry_due_events() -> int:
    """Retry pending events whose next_retry_at has passed. Returns count attempted."""
    if not is_enabled():
        return 0

    attempted = 0
    for row in outbox.list_due_pending():
        if row["attempts"] >= _max_attempts():
            continue
        _try_deliver(row["event_id"], row["payload"], current_attempts=row["attempts"])
        attempted += 1
    return attempted


async def retry_loop(stop_event) -> None:
    """Background worker — runs until stop_event is set."""
    import asyncio

    interval = _retry_interval_sec()
    logger.info("[note_ready] retry worker started | interval=%ss", interval)
    while not stop_event.is_set():
        try:
            count = await asyncio.to_thread(retry_due_events)
            if count:
                logger.info("[note_ready] retry batch | attempted=%s", count)
        except Exception:
            logger.exception("[note_ready] retry worker error")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("[note_ready] retry worker stopped")
