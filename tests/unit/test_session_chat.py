"""Tests for session list + chat patch."""

from unittest.mock import patch

import pytest
from graph.state import KeywordPlan
from utils.session_store import list_sessions


@pytest.fixture
def session_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "sessions.db")
    monkeypatch.setenv("SESSION_DB_PATH", db_path)

    import utils.session_store as store

    store._db_path = None
    store._conn = None
    store.session_store.clear()
    yield store
    if store._conn:
        store._conn.close()
    store._conn = None
    store._db_path = None
    store.session_store.clear()


class TestListSessions:
    def test_returns_newest_first(self, session_db):
        session_db.create_session("s-old", {"status": "completed", "user_input": "Old", "errors": [], "output_files": []})
        session_db.create_session("s-new", {"status": "running", "user_input": "New", "errors": [], "output_files": []})
        rows = list_sessions(limit=10)
        ids = [r["session_id"] for r in rows]
        assert "s-new" in ids
        assert "s-old" in ids
        assert ids.index("s-new") < ids.index("s-old")


class TestSessionChat:
    def test_validate_rejects_running(self):
        from services.session_chat import validate_chat_request

        err = validate_chat_request({"status": "running", "student_notes": "x", "tutor_notes": "y"})
        assert err is not None

    def test_handle_chat_patches_and_saves(self, session_db, tmp_path, monkeypatch):
        from services.session_chat import handle_session_chat

        monkeypatch.setenv("SESSION_DB_PATH", str(tmp_path / "sessions.db"))
        plan = KeywordPlan(
            topic="Chat Test",
            domain="python",
            intent="comprehensive_notes",
            keywords=["a"],
            subtopics=["Intro"],
            needs_web_search=False,
        )
        state = {
            "session_id": "chat-1",
            "status": "completed",
            "planner_output": plan,
            "student_notes": "# Lesson\n\n## Intro\n\nBody.\n",
            "tutor_notes": "# Lesson\n\n## Intro\n\n> **👨‍🏫 TEACHING NOTE:** Hi.\n",
            "student_filename": "chat_test_student.md",
            "tutor_filename": "chat_test_tutor.md",
            "research_data": "research",
            "errors": [],
            "output_files": [],
            "chat_history": [],
        }

        with patch("services.session_chat.apply_gap_patch") as mock_patch:
            mock_patch.return_value = {
                "student_notes": state["student_notes"] + "\n## Added\n\nNew section.\n",
                "tutor_notes": state["tutor_notes"],
                "errors": [],
            }
            result = handle_session_chat(state, "Add a section on loops")

        assert "## Added" in result["student_notes"]
        assert len(result["chat_history"]) == 2
        assert result["output_files"]
