"""Shared course batch control helpers."""
from __future__ import annotations

import asyncio

from services.course_runner import run_course_batch
from utils.course_store import get_course, update_course
from utils.helpers import get_session, set_session
from utils.job_health import course_batch_alive, start_course_batch_task
from utils.stream_bus import clear_session


def _cancel_session_task(session_id: str) -> None:
    session = get_session(session_id)
    if not session:
        return
    task = session.get("task")
    if task and not task.done():
        task.cancel()
    session["state"]["status"] = "cancelled"
    set_session(session_id, session)
    clear_session(session_id)


def launch_course_batch(course_id: str) -> asyncio.Task:
    """Start or resume batch generation with in-memory task tracking."""
    return start_course_batch_task(course_id, run_course_batch(course_id))


def cancel_course_generation(course_id: str) -> dict:
    course = get_course(course_id)
    if not course:
        raise ValueError("Course not found.")
    if course.get("status") not in ("generating",):
        raise ValueError(f"Course status is {course.get('status')}")

    sid = course.get("current_session_id")
    if sid:
        _cancel_session_task(sid)

    course = update_course(
        course_id,
        status="paused",
        current_generating_day=None,
        current_day_title=None,
        current_session_id=None,
    )
    return course


def resume_course_batch(course_id: str) -> dict:
    course = get_course(course_id)
    if not course:
        raise ValueError("Course not found.")
    if course.get("status") not in ("generating", "paused", "failed"):
        raise ValueError(f"Course cannot resume from status {course.get('status')}")
    if course_batch_alive(course_id):
        raise ValueError("Course batch is already running.")

    course = update_course(course_id, status="generating")
    launch_course_batch(course_id)
    return course


def retry_course_day(course_id: str, day: int | None = None) -> dict:
    course = get_course(course_id)
    if not course:
        raise ValueError("Course not found.")
    if course_batch_alive(course_id):
        raise ValueError("Course batch is already running.")

    target = day or course.get("next_day", 1)
    if target < 1:
        raise ValueError("Invalid day.")

    completed = [d for d in course.get("days_completed", []) if d != target]
    day_outputs = dict(course.get("day_outputs", {}))
    day_sessions = dict(course.get("day_sessions", {}))
    day_outputs.pop(str(target), None)
    day_sessions.pop(str(target), None)

    course = update_course(
        course_id,
        status="generating",
        days_completed=sorted(completed),
        day_outputs=day_outputs,
        day_sessions=day_sessions,
        next_day=target,
        current_generating_day=None,
        current_day_title=None,
        current_session_id=None,
        errors=[],
    )
    launch_course_batch(course_id)
    return course
