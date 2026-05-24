"""Tests for course store persistence."""
import pytest

from utils import course_store


@pytest.fixture(autouse=True)
def _reset():
    course_store._course_store.clear()
    yield
    course_store._course_store.clear()


def test_create_and_get_course(tmp_path, monkeypatch):
    db = str(tmp_path / "courses.db")
    monkeypatch.setenv("COURSE_DB_PATH", db)
    course_store._conn = None

    course_store.create_course(
        course_id="c-1",
        course_name="GenAI",
        syllabus="syllabus text",
        total_days=30,
        hours_per_day=1.5,
        checkpoint_every=4,
        programming_languages=["python"],
        output_root=str(tmp_path / "genai"),
    )
    loaded = course_store.get_course("c-1")
    assert loaded is not None
    assert loaded["course_name"] == "GenAI"
    assert loaded["status"] == "planning"

    course_store._course_store.clear()
    reloaded = course_store.get_course("c-1")
    assert reloaded["total_days"] == 30


def test_task_not_persisted(tmp_path, monkeypatch):
    db = str(tmp_path / "courses.db")
    monkeypatch.setenv("COURSE_DB_PATH", db)
    course_store._conn = None

    course_store.create_course(
        course_id="c-2",
        course_name="Test",
        syllabus="x" * 60,
        total_days=5,
        hours_per_day=1.5,
        checkpoint_every=4,
        programming_languages=[],
        output_root="/tmp/out",
    )
    data = course_store.get_course("c-2")
    data["task"] = "fake-async-task"
    course_store.set_course("c-2", data)
    course_store._course_store.clear()
    loaded = course_store.get_course("c-2")
    assert "task" not in loaded or loaded.get("task") is None


def test_list_courses_newest_first(tmp_path, monkeypatch):
    db = str(tmp_path / "courses.db")
    monkeypatch.setenv("COURSE_DB_PATH", db)
    course_store._conn = None

    for i, name in enumerate(["Alpha", "Beta"]):
        course_store.create_course(
            course_id=f"c-list-{i}",
            course_name=name,
            syllabus="x" * 60,
            total_days=5,
            hours_per_day=1.5,
            checkpoint_every=4,
            programming_languages=[],
            output_root=f"/tmp/{name}",
        )
        if i == 1:
            data = course_store.get_course("c-list-1")
            data["days_completed"] = [1, 2]
            data["status"] = "generating"
            course_store.set_course("c-list-1", data)

    course_store._course_store.clear()
    rows = course_store.list_courses(limit=10)
    assert len(rows) == 2
    assert rows[0]["course_name"] == "Beta"
    assert rows[0]["days_completed_count"] == 2
    assert rows[0]["has_notes"] is True
    assert rows[1]["course_name"] == "Alpha"
    assert rows[1]["days_completed_count"] == 0
