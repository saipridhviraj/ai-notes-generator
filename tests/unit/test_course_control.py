"""Tests for course control helpers."""
import pytest
from unittest.mock import patch

from utils import course_store
from utils import job_health


@pytest.fixture(autouse=True)
def _reset():
    course_store._course_store.clear()
    job_health._course_tasks.clear()
    yield
    course_store._course_store.clear()
    job_health._course_tasks.clear()


def _make_course(course_id: str = "c-ctrl", status: str = "generating"):
    course_store.create_course(
        course_id=course_id,
        course_name="Test",
        syllabus="x" * 60,
        total_days=3,
        hours_per_day=1.5,
        checkpoint_every=2,
        programming_languages=["python"],
        output_root="/tmp/out",
    )
    course_store.update_course(course_id, status=status, plan=None, next_day=1)


def test_cancel_course_pauses_generation():
    _make_course()
    course_store.update_course(
        "c-ctrl",
        current_session_id="sess-1",
        current_generating_day=1,
    )
    with patch("services.course_control._cancel_session_task") as mock_cancel:
        from services.course_control import cancel_course_generation

        result = cancel_course_generation("c-ctrl")
    mock_cancel.assert_called_once_with("sess-1")
    assert result["status"] == "paused"


def test_resume_course_batch_starts_task():
    _make_course(status="paused")
    with patch("services.course_control.start_course_batch_task") as mock_start:
        from services.course_control import resume_course_batch

        result = resume_course_batch("c-ctrl")
    assert result["status"] == "generating"
    mock_start.assert_called_once()


def test_retry_course_day_resets_day_state():
    _make_course(status="failed")
    course_store.update_course(
        "c-ctrl",
        days_completed=[1],
        day_outputs={"1": ["a.md"]},
        day_sessions={"1": "s1"},
        next_day=2,
        errors=["Day 2 failed"],
    )
    with patch("services.course_control.start_course_batch_task"):
        from services.course_control import retry_course_day

        result = retry_course_day("c-ctrl", day=2)
    assert result["status"] == "generating"
    assert result["days_completed"] == [1]
    assert "2" not in result["day_sessions"]
    assert result["next_day"] == 2
    assert result["errors"] == []
