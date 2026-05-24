"""Tests for course planner and day input builder."""
import json
from unittest.mock import patch

from graph.course_models import CoursePlan, DayPlan
from services.course_runner import build_day_user_input
from services.course_planner import build_course_plan


class TestBuildDayUserInput:
    def test_includes_duration_and_assignments(self):
        course = {
            "hours_per_day": 1.5,
            "programming_languages": ["python"],
        }
        day = DayPlan(
            day=1,
            title="Intro to GenAI",
            topic="What is generative AI",
            concepts=["LLM", "tokens"],
            duration_minutes=90,
        )
        text = build_day_user_input(day, course)
        assert "90 minutes" in text
        assert "homework assignment" in text
        assert "python" in text


class TestBuildCoursePlan:
    def test_parses_llm_json(self, monkeypatch):
        payload = {
            "course_name": "GenAI 30 Day",
            "total_days": 2,
            "hours_per_day": 1.5,
            "programming_languages": ["python"],
            "syllabus_summary": "Overview",
            "days": [
                {
                    "day": 1,
                    "title": "Intro",
                    "topic": "Introduction to GenAI",
                    "concepts": ["AI"],
                    "duration_minutes": 90,
                },
                {
                    "day": 2,
                    "title": "Prompting",
                    "topic": "Prompt engineering basics",
                    "concepts": ["prompts"],
                    "duration_minutes": 90,
                },
            ],
        }
        with patch("services.course_planner.llm_client") as mock_llm:
            mock_llm.complete.return_value = json.dumps(payload)
            plan = build_course_plan("syllabus " * 20, "GenAI", total_days=2)
        assert isinstance(plan, CoursePlan)
        assert len(plan.days) == 2
