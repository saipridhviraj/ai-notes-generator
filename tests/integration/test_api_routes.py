"""P0 tests for FastAPI routes — BUG-2 and BUG-3 regression coverage."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

AUTH_HEADERS = {"X-API-Key": "test-key"}


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
        yield TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ok", "degraded")
        assert "version" in data
        assert "llm_provider" in data
        assert "prompt_profile" in data


class TestCancelEndpoint:
    def test_cancel_running_session(self, client):
        from utils.helpers import create_session, get_session

        create_session("cancel-001", {"status": "running", "errors": [], "output_files": []})
        response = client.post("/cancel/cancel-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert get_session("cancel-001")["state"]["status"] == "cancelled"

    def test_cancel_completed_session_rejected(self, client):
        from utils.helpers import create_session

        create_session("cancel-002", {"status": "completed", "errors": [], "output_files": []})
        response = client.post("/cancel/cancel-002", headers=AUTH_HEADERS)
        assert response.status_code == 400

    def test_cancel_missing_session_404(self, client):
        response = client.post("/cancel/no-such-id", headers=AUTH_HEADERS)
        assert response.status_code == 404


class TestStatusProgressFields:
    def test_status_includes_node_label_and_elapsed(self, client):
        from utils.helpers import create_session, session_store

        create_session("progress-001", {"status": "running", "errors": [], "output_files": []})
        session_store["progress-001"]["current_node"] = "research"

        response = client.get("/status/progress-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["node_label"] == "Writer instructions"
        assert data["current_node"] == "research"
        assert "elapsed_seconds" in data
        assert "progress_percent" in data
        assert data["progress_total"] == 8
        assert len(data["pipeline_steps"]) == 8
        assert data["pipeline_steps"][2]["persona"] == "Research Analyst"
        assert data.get("active_persona") == "Research Analyst"
        assert "node_artifacts" in data
        assert len(data["node_artifacts"]) == 8

    def test_status_stream_returns_sse_snapshot(self, client):
        from utils.helpers import create_session

        create_session(
            "sse-001",
            {"status": "completed", "errors": [], "output_files": [], "retry_count": 0},
        )

        response = client.get("/status-stream/sse-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        assert body.startswith("data: ")
        import json

        event = json.loads(body.strip().split("\n\n")[0].removeprefix("data: "))
        assert event["type"] == "status"
        assert event["data"]["session_id"] == "sse-001"
        assert event["data"]["status"] == "completed"


class TestArtifactsEndpoint:
    def test_artifacts_missing_session_404(self, client):
        response = client.get("/artifacts/no-session/research", headers=AUTH_HEADERS)
        assert response.status_code == 404

    def test_artifacts_node_not_ready_404(self, client):
        from utils.helpers import create_session

        create_session("art-001", {"status": "running", "errors": [], "output_files": []})
        response = client.get("/artifacts/art-001/research", headers=AUTH_HEADERS)
        assert response.status_code == 404

    def test_artifacts_returns_research_content(self, client):
        from utils.helpers import create_session

        create_session(
            "art-002",
            {
                "status": "running",
                "research_data": "## Writer instructions\nCover decorators.",
                "errors": [],
                "output_files": [],
            },
        )
        response = client.get("/artifacts/art-002/research", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "research"
        assert "decorators" in data["content"]
        assert data["format"] == "markdown"


class TestResumeEndpoint:
    def test_resume_missing_session_404(self, client):
        response = client.post(
            "/resume/no-session/tutor_notes",
            json={"from_node": "tutor_notes"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 404

    def test_resume_without_student_notes_400(self, client):
        from utils.helpers import create_session
        from graph.state import KeywordPlan

        create_session(
            "resume-bad",
            {
                "status": "max_retries_reached",
                "planner_output": KeywordPlan(
                    topic="OOP",
                    domain="python",
                    intent="comprehensive_notes",
                    keywords=["class"],
                    subtopics=["a"],
                    needs_web_search=False,
                ),
                "planner_verified": True,
                "student_notes": "tiny",
                "errors": [],
                "output_files": [],
            },
        )
        response = client.post(
            "/resume/resume-bad",
            json={"from_node": "tutor_notes"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 400
        assert "student_notes" in response.json()["detail"]

    def test_resume_from_tutor_accepted(self, client):
        from utils.helpers import create_session
        from graph.state import KeywordPlan

        create_session(
            "resume-ok",
            {
                "status": "max_retries_reached",
                "planner_output": KeywordPlan(
                    topic="OOP",
                    domain="python",
                    intent="comprehensive_notes",
                    keywords=["class"],
                    subtopics=["a"],
                    needs_web_search=False,
                ),
                "planner_verified": True,
                "research_data": "## brief",
                "student_notes": "# Notes\n\n" + ("content " * 40),
                "errors": ["TutorNotesCreator: failed"],
                "output_files": [],
                "retry_count": 1,
            },
        )
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            response = client.post(
                "/resume/resume-ok",
                json={"from_node": "tutor_notes"},
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["from_node"] == "tutor_notes"
        assert data["status"] == "running"


class TestStreamEndpoint:
    def test_stream_missing_session_404(self, client):
        response = client.get("/stream/no-such-session", headers=AUTH_HEADERS)
        assert response.status_code == 404

    def test_stream_existing_session_returns_sse(self, client):
        from utils.helpers import create_session

        async def mock_subscribe(_session_id):
            yield {"type": "start", "node": "research"}

        create_session("stream-001", {"status": "running", "errors": [], "output_files": []})
        with patch("utils.stream_bus.subscribe", side_effect=mock_subscribe):
            response = client.get("/stream/stream-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "data:" in response.text


class TestInputValidation:
    def test_topic_too_short_rejected(self, client):
        """Pydantic min_length=3 enforced on topic."""
        response = client.post("/generate", json={"topic": "ab"}, headers=AUTH_HEADERS)
        assert response.status_code == 422

    def test_topic_too_long_rejected(self, client):
        """Pydantic max_length=500 enforced on topic."""
        response = client.post("/generate", json={"topic": "x" * 501}, headers=AUTH_HEADERS)
        assert response.status_code == 422

    def test_valid_topic_accepted(self, client):
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            response = client.post("/generate", json={"topic": "Python Basics"}, headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "running"


class TestStatusEndpoint:
    def test_missing_session_returns_404(self, client):
        response = client.get("/status/nonexistent-session-id", headers=AUTH_HEADERS)
        assert response.status_code == 404

    def test_existing_session_returns_status(self, client):
        from utils.helpers import create_session
        create_session("test-status-001", {
            "status": "running",
            "output_files": [],
            "errors": [],
            "retry_count": 0,
        })
        response = client.get("/status/test-status-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-status-001"
        assert data["status"] == "running"


class TestTutorRejectionRoute:
    """BUG-2 regression tests — rejection must set status='rejected' and halt graph."""

    def test_tutor_respond_rejects_when_not_awaiting(self, client):
        from utils.helpers import create_session
        create_session("test-reject-001", {"status": "running", "errors": [], "output_files": []})
        response = client.post(
            "/tutor/respond/test-reject-001",
            json={"approved": False, "feedback": "Topic too broad"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 400

    def test_tutor_rejection_stored_correctly(self, client):
        from utils.helpers import create_session, get_session
        create_session("test-reject-002", {
            "status": "awaiting_tutor",
            "errors": [],
            "output_files": [],
        })
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            response = client.post(
                "/tutor/respond/test-reject-002",
                json={"approved": False, "feedback": "Out of scope"},
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        state = get_session("test-reject-002")["state"]
        assert state["tutor_response"].startswith("rejected:")


class TestResponseToField:
    """BUG-3 regression — response_to must be stored in session state."""

    def test_response_to_stored_in_state(self, client):
        from utils.helpers import create_session, get_session
        create_session("test-resp-to-001", {
            "status": "awaiting_tutor",
            "errors": [],
            "output_files": [],
        })
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            response = client.post(
                "/tutor/respond/test-resp-to-001",
                json={
                    "approved": True,
                    "feedback": "",
                    "response_to": "plan_verification",
                },
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        state = get_session("test-resp-to-001")["state"]
        assert state["response_to"] == "plan_verification"


class TestResultEndpoint:
    def test_missing_session_returns_404(self, client):
        response = client.get("/result/no-such-session", headers=AUTH_HEADERS)
        assert response.status_code == 404

    def test_completed_session_returns_result(self, client):
        from graph.state import EvaluationResult, KeywordPlan
        from utils.helpers import create_session

        plan = KeywordPlan(
            topic="Python Loops",
            domain="python",
            intent="comprehensive_notes",
            keywords=["for", "while"],
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
        create_session("test-result-001", {
            "status": "completed",
            "planner_output": plan,
            "student_filename": "loops_student.md",
            "tutor_filename": "loops_tutor.md",
            "student_notes": "# Loops\n\nStudent content.",
            "tutor_notes": "# Loops Tutor\n\n> Teaching note.",
            "evaluation_result": eval_result,
            "retry_count": 1,
            "used_web_search": False,
            "final_summary": "Done.",
            "errors": [],
            "output_files": [],
        })
        response = client.get("/result/test-result-001", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "Python Loops"
        assert data["evaluation_score"]["student"] == 90
        assert "Student content" in data["student_markdown"]
        assert "Teaching note" in data["tutor_markdown"]
