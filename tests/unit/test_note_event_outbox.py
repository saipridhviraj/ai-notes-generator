"""Tests for note.ready outbox."""
import json
import os
import time

import pytest

from models.note_ready import NoteReadyEvent
from utils import note_event_outbox as outbox


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path, monkeypatch):
    db = str(tmp_path / "note_events.db")
    monkeypatch.setenv("NOTE_READY_OUTBOX_DB_PATH", db)
    outbox.reset_connection()
    yield
    outbox.reset_connection()


def _sample_payload(event_id: str = "evt-1") -> dict:
    return NoteReadyEvent(
        event_id=event_id,
        session_id="sess-1",
        title="Python Decorators",
        topic="Python Decorators",
        student_uri="/tmp/s.md",
        tutor_uri="/tmp/t.md",
        output_root="/tmp/out",
    ).model_dump()


class TestNoteEventOutbox:
    def test_enqueue_and_mark_delivered(self):
        outbox.enqueue(_sample_payload("evt-1"))
        assert outbox.count_by_status("pending") == 1
        outbox.mark_delivered("evt-1")
        assert outbox.count_by_status("pending") == 0
        assert outbox.count_by_status("delivered") == 1

    def test_record_failure_increments_attempts(self):
        outbox.enqueue(_sample_payload("evt-2"))
        status = outbox.record_failure("evt-2", "connection refused", max_attempts=5, backoff_sec=60)
        assert status == "pending"
        row = outbox.get_event("evt-2")
        assert row["attempts"] == 1
        assert row["last_error"] == "connection refused"

    def test_record_failure_marks_dead_at_max(self):
        outbox.enqueue(_sample_payload("evt-3"))
        for _ in range(3):
            outbox.record_failure("evt-3", "fail", max_attempts=3, backoff_sec=1)
        row = outbox.get_event("evt-3")
        assert row["status"] == "dead"
        assert row["attempts"] == 3

    def test_list_due_pending_respects_next_retry_at(self):
        outbox.enqueue(_sample_payload("evt-4"))
        outbox.record_failure("evt-4", "fail", max_attempts=10, backoff_sec=3600)
        assert outbox.list_due_pending() == []
        outbox._get_conn().execute(
            "UPDATE note_events SET next_retry_at = ? WHERE event_id = ?",
            (time.time() - 1, "evt-4"),
        )
        outbox._get_conn().commit()
        due = outbox.list_due_pending()
        assert len(due) == 1
        assert due[0]["event_id"] == "evt-4"

    def test_list_pending_for_catch_up_api(self):
        outbox.enqueue(_sample_payload("evt-5"))
        pending = outbox.list_pending()
        assert len(pending) == 1
        assert pending[0]["payload"]["session_id"] == "sess-1"
