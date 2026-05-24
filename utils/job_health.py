"""Track live asyncio tasks and detect jobs interrupted by server restart."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_course_tasks: dict[str, asyncio.Task[Any]] = {}


def session_task_alive(session: dict | None) -> bool:
    if not session:
        return False
    task = session.get("task")
    return task is not None and not task.done()


def session_interrupted(session: dict | None) -> bool:
    if not session:
        return False
    status = session.get("state", {}).get("status")
    return status == "running" and not session_task_alive(session)


def register_course_task(course_id: str, task: asyncio.Task[Any]) -> None:
    _course_tasks[course_id] = task

    def _done(t: asyncio.Task[Any]) -> None:
        if _course_tasks.get(course_id) is t:
            _course_tasks.pop(course_id, None)

    task.add_done_callback(_done)


def course_batch_alive(course_id: str) -> bool:
    task = _course_tasks.get(course_id)
    return task is not None and not task.done()


def course_interrupted(course: dict | None, course_id: str) -> bool:
    if not course:
        return False
    return course.get("status") == "generating" and not course_batch_alive(course_id)


def start_course_batch_task(course_id: str, coro) -> asyncio.Task[Any]:
    task = asyncio.create_task(coro)
    register_course_task(course_id, task)
    return task


def cancel_course_task(course_id: str) -> None:
    task = _course_tasks.get(course_id)
    if task and not task.done():
        task.cancel()
    _course_tasks.pop(course_id, None)


async def reconcile_stale_jobs_on_startup() -> None:
    """Log sessions/courses left in-flight after a process restart."""
    from utils.course_store import list_courses, get_course
    from utils.session_store import list_sessions, get_session

    stale_sessions = 0
    for row in list_sessions(limit=200):
        session = get_session(row["session_id"])
        if session_interrupted(session):
            stale_sessions += 1

    stale_courses = 0
    for row in list_courses(limit=200):
        course = get_course(row["course_id"])
        if course_interrupted(course, row["course_id"]):
            stale_courses += 1

    if stale_sessions or stale_courses:
        logger.warning(
            "Stale in-flight jobs after restart: sessions=%s courses=%s",
            stale_sessions,
            stale_courses,
        )
