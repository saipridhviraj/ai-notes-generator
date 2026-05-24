"""HTTP tests for gap-fix endpoints."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

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
        yield __import__("fastapi").testclient.TestClient(app, raise_server_exceptions=True)


class TestSessionsListAuth:
    def test_list_sessions_requires_auth(self, client):
        assert client.get("/sessions").status_code == 401
        assert client.get("/sessions", headers=AUTH_HEADERS).status_code == 200

    def test_result_requires_auth(self, client):
        assert client.get("/result/no-id").status_code == 401


class TestSessionRestart:
    def test_restart_interrupted_session(self, client):
        from utils.helpers import create_session

        create_session(
            "restart-s1",
            {
                "user_input": "Python",
                "session_id": "restart-s1",
                "status": "running",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
                "chat_history": [],
            },
        )
        mock_graph = MagicMock()

        async def _empty_stream():
            return
            yield {}

        mock_graph.astream = MagicMock(return_value=_empty_stream())
        with (
            patch("graph.graph", mock_graph),
            patch("api.routes.consume_graph_stream", new_callable=AsyncMock),
            patch("api.routes.asyncio.create_task", return_value=MagicMock()),
        ):
            response = client.post("/restart/restart-s1", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json()["status"] == "running"


class TestCourseControlRoutes:
    def test_cancel_and_resume_course(self, client):
        from utils.course_store import create_course, update_course

        create_course(
            course_id="c-api",
            course_name="API Course",
            syllabus="x" * 60,
            total_days=2,
            hours_per_day=1.5,
            checkpoint_every=2,
            programming_languages=[],
            output_root="/tmp",
        )
        update_course("c-api", status="generating", current_session_id=None)

        cancel = client.post("/course/c-api/cancel", headers=AUTH_HEADERS)
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "paused"

        with patch("services.course_control.launch_course_batch") as mock_launch:
            mock_launch.return_value = MagicMock()
            resume = client.post("/course/c-api/resume-batch", headers=AUTH_HEADERS)
        assert resume.status_code == 200
        assert resume.json()["status"] == "generating"
        mock_launch.assert_called_once_with("c-api")

    def test_checkpoint_respond_rejects(self, client):
        from graph.course_models import CoursePlan, DayPlan
        from utils.course_store import create_course, update_course

        plan = CoursePlan(
            course_name="CP",
            total_days=2,
            hours_per_day=1.5,
            programming_languages=[],
            syllabus_summary="s",
            days=[
                DayPlan(day=1, title="Day One", topic="Topic one", duration_minutes=90),
                DayPlan(day=2, title="Day Two", topic="Topic two", duration_minutes=90),
            ],
        )
        create_course(
            course_id="c-cp",
            course_name="CP",
            syllabus="x" * 60,
            total_days=2,
            hours_per_day=1.5,
            checkpoint_every=2,
            programming_languages=[],
            output_root="/tmp",
        )
        update_course(
            "c-cp",
            status="awaiting_checkpoint",
            plan=plan,
            checkpoint_message="Review days 1-2",
        )
        response = client.post(
            "/course/c-cp/checkpoint/respond",
            json={"approved": False, "feedback": "Stop here"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"


class TestSessionChatRoute:
    def test_session_chat_requires_notes(self, client):
        from utils.helpers import create_session

        create_session(
            "chat-s1",
            {
                "user_input": "Topic",
                "session_id": "chat-s1",
                "status": "running",
                "student_notes": "",
                "tutor_notes": "",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
                "chat_history": [],
            },
        )
        response = client.post(
            "/sessions/chat-s1/chat",
            json={"message": "Add a section on embeddings"},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 400


class TestSessionDeleteAndChatClear:
    def test_delete_session(self, client):
        from utils.helpers import create_session, get_session

        create_session(
            "del-s1",
            {
                "user_input": "To delete",
                "session_id": "del-s1",
                "status": "completed",
                "errors": [],
                "output_files": [],
                "chat_history": [],
            },
        )
        assert client.delete("/sessions/del-s1", headers=AUTH_HEADERS).status_code == 200
        assert get_session("del-s1") is None
        assert client.get("/status/del-s1", headers=AUTH_HEADERS).status_code == 404

    def test_clear_session_chat(self, client):
        from utils.helpers import create_session, get_session

        create_session(
            "chat-clear",
            {
                "user_input": "Topic",
                "session_id": "chat-clear",
                "status": "completed",
                "student_notes": "# Notes",
                "tutor_notes": "# Tutor",
                "errors": [],
                "output_files": [],
                "chat_history": [
                    {"role": "user", "content": "Add section", "ts": 1.0},
                    {"role": "assistant", "content": "Done", "ts": 2.0},
                ],
            },
        )
        res = client.delete("/sessions/chat-clear/chat", headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()["chat_history"] == []
        session = get_session("chat-clear")
        assert session["state"]["chat_history"] == []
        assert session["state"]["student_notes"] == "# Notes"


class TestCourseDelete:
    def test_delete_course(self, client):
        from utils.course_store import create_course, get_course

        create_course(
            course_id="del-course",
            course_name="Delete Me",
            syllabus="x" * 60,
            total_days=2,
            hours_per_day=1.5,
            checkpoint_every=2,
            programming_languages=[],
            output_root="/tmp",
        )
        assert client.delete("/course/del-course", headers=AUTH_HEADERS).status_code == 200
        assert get_course("del-course") is None

    def test_delete_all_sessions(self, client):
        from utils.helpers import create_session, get_session

        create_session("bulk-1", {"user_input": "A", "status": "completed", "errors": [], "output_files": []})
        create_session("bulk-2", {"user_input": "B", "status": "completed", "errors": [], "output_files": []})
        res = client.delete("/sessions", headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()["deleted_count"] >= 2
        assert get_session("bulk-1") is None
        assert get_session("bulk-2") is None

    def test_delete_all_courses(self, client):
        from utils.course_store import create_course, get_course

        create_course(
            course_id="bulk-c1",
            course_name="One",
            syllabus="x" * 60,
            total_days=1,
            hours_per_day=1.0,
            checkpoint_every=1,
            programming_languages=[],
            output_root="/tmp",
        )
        assert client.delete("/course/courses", headers=AUTH_HEADERS).status_code == 200
        assert get_course("bulk-c1") is None
