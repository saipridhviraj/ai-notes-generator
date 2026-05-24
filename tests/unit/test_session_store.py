"""Tests for SQLite-backed HTTP session store."""
import json
import sqlite3

import pytest

from graph.state import EvaluationResult, KeywordPlan


@pytest.fixture
def session_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "sessions.db")
    monkeypatch.setenv("SESSION_DB_PATH", db_path)

    import utils.session_store as store

    store._db_path = None
    store._conn = None
    store.session_store.clear()
    yield store
    store._conn and store._conn.close()
    store._conn = None
    store._db_path = None
    store.session_store.clear()


class TestSessionStorePersistence:
    def test_create_persists_to_sqlite(self, session_db, tmp_path, monkeypatch):
        monkeypatch.setenv("SESSION_DB_PATH", str(tmp_path / "sessions.db"))
        session_db.create_session("persist-001", {"status": "running", "errors": [], "output_files": []})

        conn = sqlite3.connect(str(tmp_path / "sessions.db"))
        row = conn.execute(
            "SELECT state_json FROM sessions WHERE session_id = ?", ("persist-001",)
        ).fetchone()
        conn.close()

        assert row is not None
        state = json.loads(row[0])
        assert state["status"] == "running"

    def test_reload_from_db_after_memory_clear(self, session_db):
        session_db.create_session("reload-001", {"status": "awaiting_tutor", "errors": [], "output_files": []})
        session_db.session_store.clear()

        loaded = session_db.get_session("reload-001")
        assert loaded is not None
        assert loaded["state"]["status"] == "awaiting_tutor"

    def test_pydantic_models_round_trip(self, session_db):
        plan = KeywordPlan(
            topic="Loops",
            domain="python",
            intent="comprehensive_notes",
            keywords=["for"],
            subtopics=["iteration"],
            needs_web_search=False,
        )
        eval_result = EvaluationResult(
            student_notes_score=90,
            tutor_notes_score=88,
            missing_topics=[],
            diagram_issues=[],
            alignment_issues=[],
            passed=True,
        )
        session_db.create_session(
            "model-001",
            {
                "status": "completed",
                "planner_output": plan,
                "evaluation_result": eval_result,
                "errors": [],
                "output_files": [],
            },
        )
        session_db.session_store.clear()
        loaded = session_db.get_session("model-001")

        assert loaded["state"]["planner_output"].topic == "Loops"
        assert loaded["state"]["evaluation_result"].passed is True

    def test_set_session_updates_db(self, session_db):
        session_db.create_session("update-001", {"status": "running", "errors": [], "output_files": []})
        session = session_db.get_session("update-001")
        session["state"]["status"] = "completed"
        session_db.set_session("update-001", session)
        session_db.session_store.clear()

        reloaded = session_db.get_session("update-001")
        assert reloaded["state"]["status"] == "completed"

    def test_delete_session_removes_db_row(self, session_db):
        session_db.create_session("delete-001", {"status": "completed", "errors": [], "output_files": []})
        assert session_db.delete_session("delete-001") is True
        assert session_db.get_session("delete-001") is None

    def test_clear_chat_keeps_notes(self, session_db):
        session_db.create_session(
            "chat-001",
            {
                "status": "completed",
                "student_notes": "hello",
                "errors": [],
                "output_files": [],
                "chat_history": [{"role": "user", "content": "x", "ts": 1.0}],
            },
        )
        assert session_db.clear_session_chat("chat-001") is True
        loaded = session_db.get_session("chat-001")
        assert loaded["state"]["chat_history"] == []
        assert loaded["state"]["student_notes"] == "hello"
