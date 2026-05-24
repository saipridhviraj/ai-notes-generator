"""API-level E2E checklist — covers manual E2E items without a browser."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

AUTH_HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture
def live_client():
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


@pytest.mark.integration
class TestAuthChecklist:
    def test_sessions_requires_key(self, live_client):
        assert live_client.get("/sessions").status_code == 401
        assert live_client.get("/sessions", headers=AUTH_HEADERS).status_code == 200

    def test_status_requires_key(self, live_client):
        assert live_client.get("/status/no-id").status_code == 401

    def test_result_requires_key(self, live_client):
        assert live_client.get("/result/no-id").status_code == 401

    def test_course_list_requires_key(self, live_client):
        assert live_client.get("/course/courses").status_code == 401


@pytest.mark.integration
class TestSessionHubChecklist:
    def test_generate_list_status_result_flow(self, live_client):
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            gen = live_client.post(
                "/generate",
                json={"topic": "E2E checklist topic"},
                headers=AUTH_HEADERS,
            )
        assert gen.status_code == 200
        session_id = gen.json()["session_id"]

        listed = live_client.get("/sessions?limit=5", headers=AUTH_HEADERS)
        assert listed.status_code == 200
        ids = [s["session_id"] for s in listed.json()["sessions"]]
        assert session_id in ids

        status = live_client.get(f"/status/{session_id}", headers=AUTH_HEADERS)
        assert status.status_code == 200
        body = status.json()
        assert body["session_id"] == session_id
        assert "interrupted" in body
        assert "pipeline_steps" in body

    def test_session_chat_rejects_without_notes(self, live_client):
        from utils.helpers import create_session

        create_session(
            "chat-e2e",
            {
                "user_input": "x",
                "session_id": "chat-e2e",
                "status": "running",
                "student_notes": "",
                "tutor_notes": "",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
                "chat_history": [],
            },
        )
        res = live_client.post(
            "/sessions/chat-e2e/chat",
            json={"message": "Add a section on lists"},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 400

    def test_interrupted_session_shows_flag(self, live_client):
        from utils.helpers import create_session

        create_session(
            "intr-e2e",
            {
                "user_input": "Interrupted test",
                "session_id": "intr-e2e",
                "status": "running",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
                "chat_history": [],
            },
        )
        status = live_client.get("/status/intr-e2e", headers=AUTH_HEADERS)
        assert status.status_code == 200
        assert status.json()["interrupted"] is True

    def test_restart_interrupted_session(self, live_client):
        from utils.helpers import create_session

        create_session(
            "restart-e2e",
            {
                "user_input": "Restart test",
                "session_id": "restart-e2e",
                "status": "running",
                "errors": [],
                "output_files": [],
                "retry_count": 0,
                "chat_history": [],
            },
        )
        mock_graph = MagicMock()

        async def _empty():
            return
            yield {}

        mock_graph.astream = MagicMock(return_value=_empty())
        with (
            patch("graph.graph", mock_graph),
            patch("api.routes.consume_graph_stream", new_callable=AsyncMock),
            patch("api.routes.asyncio.create_task", return_value=MagicMock()),
        ):
            res = live_client.post("/restart/restart-e2e", headers=AUTH_HEADERS)
        assert res.status_code == 200
        assert res.json()["status"] == "running"


@pytest.mark.integration
class TestCourseHubChecklist:
    def test_course_plan_list_status_controls(self, live_client):
        from graph.course_models import CoursePlan, DayPlan
        from utils.course_store import get_course

        plan = CoursePlan(
            course_name="E2E Course Hub",
            total_days=2,
            hours_per_day=1.5,
            programming_languages=["python"],
            syllabus_summary="Two day course",
            days=[
                DayPlan(day=1, title="Day One", topic="Intro topic", duration_minutes=90),
                DayPlan(day=2, title="Day Two", topic="Advanced topic", duration_minutes=90),
            ],
        )
        with patch("api.course_routes.build_course_plan", return_value=plan):
            created = live_client.post(
                "/course/plan",
                json={
                    "course_name": "E2E Course Hub",
                    "syllabus": "A" * 60,
                    "total_days": 2,
                    "hours_per_day": 1.5,
                    "checkpoint_every": 2,
                },
                headers=AUTH_HEADERS,
            )
        assert created.status_code == 200
        course_id = created.json()["course_id"]

        listed = live_client.get("/course/courses", headers=AUTH_HEADERS)
        assert any(c["course_id"] == course_id for c in listed.json()["courses"])

        st = live_client.get(f"/course/{course_id}/status", headers=AUTH_HEADERS)
        assert st.json()["status"] == "awaiting_plan_approval"
        assert len(st.json()["plan_days"]) == 2

        with patch("api.course_routes.launch_course_batch") as mock_launch:
            mock_launch.return_value = MagicMock()
            approved = live_client.post(
                f"/course/{course_id}/plan/respond",
                json={"approved": True},
                headers=AUTH_HEADERS,
            )
        assert approved.status_code == 200

        course = get_course(course_id)
        course["status"] = "generating"
        course["current_session_id"] = "day-sess-1"
        from utils.course_store import set_course
        set_course(course_id, course)

        cancelled = live_client.post(f"/course/{course_id}/cancel", headers=AUTH_HEADERS)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "paused"

        with patch("services.course_control.launch_course_batch") as mock_launch:
            mock_launch.return_value = MagicMock()
            resumed = live_client.post(f"/course/{course_id}/resume-batch", headers=AUTH_HEADERS)
        assert resumed.status_code == 200
        assert resumed.json()["status"] == "generating"
