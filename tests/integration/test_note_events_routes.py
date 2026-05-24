"""Tests for internal note-events catch-up API."""
import pytest
from unittest.mock import patch, MagicMock

from models.note_ready import NoteReadyEvent
from utils import note_event_outbox as outbox

AUTH_HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture(autouse=True)
def isolated_outbox(tmp_path, monkeypatch):
    db = str(tmp_path / "note_events.db")
    monkeypatch.setenv("NOTE_READY_OUTBOX_DB_PATH", db)
    outbox.reset_connection()
    yield
    outbox.reset_connection()


@pytest.fixture
def client():
    with (
        patch.dict("os.environ", {"APP_API_KEY": "test-key"}),
        patch("services.groq_client.groq_client", new=MagicMock()),
        patch("graph.graph_builder.build_graph", return_value=MagicMock()),
    ):
        import importlib
        import api.auth
        importlib.reload(api.auth)
        from main import app
        yield __import__("fastapi").testclient.TestClient(app, raise_server_exceptions=True)


class TestNoteEventsRoutes:
    def test_list_pending_requires_auth(self, client):
        assert client.get("/internal/note-events/pending").status_code == 401

    def test_list_pending_returns_undelivered(self, client):
        payload = NoteReadyEvent(
            session_id="sess-api",
            title="Day 1",
            topic="Intro",
            student_uri="/s.md",
            tutor_uri="/t.md",
            output_root="/out",
        ).model_dump()
        outbox.enqueue(payload)

        response = client.get("/internal/note-events/pending", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["events"][0]["payload"]["session_id"] == "sess-api"
        assert data["events"][0]["status"] == "pending"

    def test_get_event_by_id(self, client):
        payload = NoteReadyEvent(
            event_id="evt-api-1",
            session_id="sess-api",
            title="Day 1",
            topic="Intro",
            student_uri="/s.md",
            tutor_uri="/t.md",
            output_root="/out",
        ).model_dump()
        outbox.enqueue(payload)

        response = client.get("/internal/note-events/evt-api-1", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json()["event_id"] == "evt-api-1"

    def test_health_shows_note_ready_pending(self, client, monkeypatch):
        monkeypatch.setenv("NOTE_READY_ENABLED", "true")
        monkeypatch.setenv("NOTE_READY_WEBHOOK_URL", "http://localhost:9000/hook")
        outbox.enqueue(
            NoteReadyEvent(
                session_id="s",
                title="T",
                topic="T",
                student_uri="/s.md",
                tutor_uri="/t.md",
                output_root="/o",
            ).model_dump()
        )

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["note_ready_enabled"] is True
        assert data["note_ready_pending"] == 1
