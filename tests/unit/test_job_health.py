"""Tests for job health and stale job detection."""
import asyncio

import pytest

from utils import job_health


@pytest.fixture(autouse=True)
def _clear_course_tasks():
    job_health._course_tasks.clear()
    yield
    job_health._course_tasks.clear()


def test_session_interrupted_when_running_without_task():
    session = {"state": {"status": "running"}, "task": None}
    assert job_health.session_interrupted(session) is True


def test_session_not_interrupted_when_task_alive():
    loop = asyncio.new_event_loop()
    try:
        async def _noop():
            await asyncio.sleep(10)

        task = loop.create_task(_noop())
        session = {"state": {"status": "running"}, "task": task}
        assert job_health.session_interrupted(session) is False
        assert job_health.session_task_alive(session) is True
        task.cancel()
    finally:
        loop.close()


def test_course_interrupted_when_generating_without_batch():
    course = {"status": "generating"}
    assert job_health.course_interrupted(course, "c-1") is True


def test_course_batch_alive_with_registered_task():
    loop = asyncio.new_event_loop()
    try:
        async def _noop():
            await asyncio.sleep(10)

        task = loop.create_task(_noop())
        job_health.register_course_task("c-2", task)
        assert job_health.course_batch_alive("c-2") is True
        task.cancel()
    finally:
        loop.close()
