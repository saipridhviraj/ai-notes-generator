"""Tests for note.ready publisher and webhook delivery."""
from unittest.mock import patch

import pytest

from models.note_ready import NoteReadyEvent
from services import note_ready_publisher as publisher
from utils import note_event_outbox as outbox


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path, monkeypatch):
    db = str(tmp_path / "note_events.db")
    monkeypatch.setenv("NOTE_READY_OUTBOX_DB_PATH", db)
    outbox.reset_connection()
    yield
    outbox.reset_connection()


@pytest.fixture
def keyword_plan():
    from graph.state import KeywordPlan

    return KeywordPlan(
        topic="Python Decorators",
        domain="programming",
        intent="teach",
        keywords=["decorators"],
        subtopics=["wraps"],
        needs_web_search=False,
    )


@pytest.fixture
def base_state(keyword_plan):
    return {
        "user_input": "Python Decorators",
        "session_id": "sess-pub-1",
        "planner_output": keyword_plan,
        "course_id": None,
        "course_day": None,
    }


class TestNoteReadyPublisher:
    def test_disabled_when_not_configured(self, monkeypatch):
        monkeypatch.delenv("NOTE_READY_ENABLED", raising=False)
        monkeypatch.delenv("NOTE_READY_WEBHOOK_URL", raising=False)
        assert publisher.is_enabled() is False

    def test_enabled_requires_url(self, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://localhost:9000/hook")
        assert publisher.is_enabled() is True

    def test_build_event_single_lesson(self, base_state, tmp_path):
        student = tmp_path / "s.md"
        tutor = tmp_path / "t.md"
        student.write_text("s")
        tutor.write_text("t")
        from models.tutor_supplements import TutorSupplements

        event = publisher.build_event(
            base_state, student, tutor, tmp_path, TutorSupplements(), None
        )
        assert event.event == "note.ready"
        assert event.session_id == "sess-pub-1"
        assert event.day is None
        assert event.topic == "Python Decorators"
        assert event.supplements_item_count == 0

    def test_build_event_includes_supplements(self, base_state, tmp_path):
        from models.tutor_supplements import AssignmentItem, TutorSupplements

        student = tmp_path / "day-01_topic_student.md"
        tutor = tmp_path / "day-01_topic_tutor.md"
        student.write_text("s")
        tutor.write_text("t")
        sup_path = tmp_path / "day-01_topic_supplements.json"
        sup = TutorSupplements(
            assignments=[AssignmentItem(id="a1", title="HW", description="Read ch1")]
        )
        event = publisher.build_event(base_state, student, tutor, tmp_path, sup, sup_path)
        assert event.supplements_item_count == 1
        assert event.supplements_uri is not None
        assert event.indexing_hint

    def test_publish_enqueues_and_delivers(self, base_state, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://academy.test/hook")
        student = tmp_path / "s.md"
        tutor = tmp_path / "t.md"
        student.write_text("s")
        tutor.write_text("t")

        with patch.object(publisher, "deliver_payload") as mock_deliver:
            publisher.publish_note_ready(base_state, student, tutor, tmp_path)

        mock_deliver.assert_called_once()
        assert outbox.count_by_status("delivered") == 1
        assert outbox.count_by_status("pending") == 0

    def test_publish_keeps_pending_when_academy_down(self, base_state, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://academy.test/hook")

        student = tmp_path / "s.md"
        tutor = tmp_path / "t.md"
        student.write_text("s")
        tutor.write_text("t")

        with patch.object(publisher, "deliver_payload", side_effect=RuntimeError("connection refused")):
            publisher.publish_note_ready(base_state, student, tutor, tmp_path)

        assert outbox.count_by_status("pending") == 1
        row = outbox.get_event(outbox.list_pending()[0]["event_id"])
        assert "connection refused" in row["last_error"]

    def test_retry_due_events_delivers_when_back_up(self, base_state, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://academy.test/hook")

        payload = NoteReadyEvent(
            session_id="sess-retry",
            title="T",
            topic="T",
            student_uri="/s.md",
            tutor_uri="/t.md",
            output_root="/out",
        ).model_dump()
        event_id = outbox.enqueue(payload)
        outbox.record_failure(event_id, "down", max_attempts=10, backoff_sec=0)

        with patch.object(publisher, "deliver_payload") as mock_deliver:
            count = publisher.retry_due_events()

        assert count == 1
        mock_deliver.assert_called_once()
        assert outbox.count_by_status("delivered") == 1

    def test_hmac_signature_when_secret_set(self, monkeypatch):
        monkeypatch.setenv("NOTE_READY_WEBHOOK_SECRET", "test-secret")
        body = b'{"event":"note.ready"}'
        sig = publisher._sign_body(body)
        assert sig is not None
        assert sig.startswith("sha256=")

    def test_publish_writes_supplements_json(self, base_state, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://academy.test/hook")
        tutor_md = """
## Homework
> **👨‍🏫 RAPID-FIRE QUIZ:**
> 1. "Q1?" → A1
"""
        state = {
            **base_state,
            "tutor_notes": tutor_md,
            "student_filename": "topic_student.md",
        }
        student = tmp_path / "topic_student.md"
        tutor = tmp_path / "topic_tutor.md"
        student.write_text("student")
        tutor.write_text("tutor")

        with patch.object(publisher, "deliver_payload") as mock_deliver:
            publisher.publish_note_ready(state, student, tutor, tmp_path)

        sup_file = tmp_path / "topic_supplements.json"
        assert sup_file.exists()
        payload = mock_deliver.call_args[0][0]
        assert payload["supplements_item_count"] >= 1
        assert payload["supplements"]["quizzes"]

    def test_publish_never_raises_on_failure(self, base_state, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://academy.test/hook")
        student = tmp_path / "s.md"
        tutor = tmp_path / "t.md"
        student.write_text("s")
        tutor.write_text("t")

        with patch.object(publisher, "deliver_payload", side_effect=Exception("boom")):
            publisher.publish_note_ready(base_state, student, tutor, tmp_path)

        assert outbox.count_by_status("pending") == 1
