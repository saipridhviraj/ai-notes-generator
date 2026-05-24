"""Tests for course API routes."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from graph.course_models import CoursePlan, DayPlan

AUTH_HEADERS = {"X-API-Key": "test-key"}


def _sample_plan(total_days: int = 3) -> CoursePlan:
    return CoursePlan(
        course_name="Full Gen AI Syllabus",
        total_days=total_days,
        hours_per_day=1.5,
        programming_languages=["python"],
        syllabus_summary="GenAI course",
        days=[
            DayPlan(
                day=i,
                title=f"Day {i}",
                topic=f"Topic for day {i}",
                duration_minutes=90,
            )
            for i in range(1, total_days + 1)
        ],
    )


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


class TestCoursePlanEndpoint:
    def test_plan_course_returns_awaiting_approval(self, client):
        plan = _sample_plan(3)
        with patch("api.course_routes.build_course_plan", return_value=plan):
            response = client.post(
                "/course/plan",
                json={
                    "course_name": "Full Gen AI Syllabus",
                    "syllabus": "Day 1: intro. Day 2: transformers. Day 3: RAG." * 5,
                    "total_days": 3,
                    "hours_per_day": 1.5,
                    "checkpoint_every": 4,
                    "programming_languages": ["python"],
                },
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "awaiting_plan_approval"
        assert len(data["days"]) == 3
        assert "full_gen_ai" in data["output_root"].lower() or "gen" in data["output_root"].lower()

    def test_course_status_404(self, client):
        assert client.get("/course/no-such-id/status", headers=AUTH_HEADERS).status_code == 404

    def test_course_status_includes_plan_and_active_day(self, client):
        plan = _sample_plan(3)
        with patch("api.course_routes.build_course_plan", return_value=plan):
            created = client.post(
                "/course/plan",
                json={
                    "course_name": "GenAI Course",
                    "syllabus": "A" * 60,
                    "total_days": 3,
                    "checkpoint_every": 2,
                },
                headers=AUTH_HEADERS,
            )
            course_id = created.json()["course_id"]

        from utils.course_store import get_course, set_course

        course = get_course(course_id)
        course["current_generating_day"] = 2
        course["current_day_title"] = "Day 2"
        course["current_session_id"] = "sess-day-2"
        set_course(course_id, course)

        response = client.get(f"/course/{course_id}/status", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data["plan_days"]) == 3
        assert data["plan_days"][0]["title"] == "Day 1"
        assert data["checkpoint_every"] == 2
        assert data["current_generating_day"] == 2
        assert data["current_day_title"] == "Day 2"
        assert data["current_session_id"] == "sess-day-2"


class TestCoursePlanRespond:
    def test_approve_starts_generation(self, client):
        plan = _sample_plan(2)
        with (
            patch("api.course_routes.build_course_plan", return_value=plan),
            patch("api.course_routes.run_course_batch", new_callable=AsyncMock),
        ):
            created = client.post(
                "/course/plan",
                json={
                    "course_name": "GenAI Course",
                    "syllabus": "A" * 60,
                    "total_days": 2,
                },
                headers=AUTH_HEADERS,
            )
            course_id = created.json()["course_id"]
            response = client.post(
                f"/course/{course_id}/plan/respond",
                json={"approved": True},
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        assert response.json()["status"] == "generating"


class TestCourseList:
    def test_list_courses_returns_summaries(self, client):
        plan = _sample_plan(2)
        with patch("api.course_routes.build_course_plan", return_value=plan):
            created = client.post(
                "/course/plan",
                json={
                    "course_name": "Listed Course",
                    "syllabus": "A" * 60,
                    "total_days": 2,
                },
                headers=AUTH_HEADERS,
            )
        assert created.status_code == 200
        course_id = created.json()["course_id"]

        response = client.get("/course/courses?limit=10", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data["courses"]) >= 1
        match = next(c for c in data["courses"] if c["course_id"] == course_id)
        assert match["status"] == "awaiting_plan_approval"
        assert match["total_days"] == 2
        assert match["days_completed_count"] == 0
