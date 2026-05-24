"""Tests for course checkpoint batch logic."""
import pytest
from unittest.mock import patch

from graph.course_models import CoursePlan, DayPlan
from services.course_runner import (
    _checkpoint_message,
    course_output_root,
    day_output_dir,
    run_course_batch,
)
from utils.course_store import create_course, get_course


class TestCoursePaths:
    def test_day_output_dir_structure(self):
        course = {
            "output_root": "/tmp/full-gen-ai-syllabus",
        }
        day = DayPlan(
            day=3,
            title="Intro to Transformers",
            topic="Transformer architecture basics",
            concepts=["attention"],
            duration_minutes=90,
        )
        path = day_output_dir(course, day)
        assert "day-03" in str(path)
        assert "intro" in str(path).lower()
        assert str(path).startswith("/tmp/full-gen-ai-syllabus")

    def test_checkpoint_message(self):
        course = {
            "output_root": "/notes/genai",
            "checkpoint_every": 4,
        }
        msg = _checkpoint_message(course, 4)
        assert "days 1–4" in msg
        assert "/notes/genai" in msg


class TestCoursePlanModel:
    def test_validate_day_count(self):
        days = [
            DayPlan(
                day=i,
                title=f"Day {i}",
                topic=f"Topic {i}",
                duration_minutes=90,
            )
            for i in range(1, 4)
        ]
        plan = CoursePlan(
            course_name="GenAI",
            total_days=3,
            hours_per_day=1.5,
            days=days,
        )
        plan.validate_day_count()


@pytest.mark.asyncio
async def test_run_course_batch_pauses_after_four_days(tmp_path):
    days = [
        DayPlan(day=i, title=f"Day {i}", topic=f"Topic {i}", duration_minutes=90)
        for i in range(1, 6)
    ]
    plan = CoursePlan(
        course_name="GenAI",
        total_days=5,
        hours_per_day=1.5,
        days=days,
    )
    create_course(
        course_id="batch-1",
        course_name="GenAI",
        syllabus="x" * 60,
        total_days=5,
        hours_per_day=1.5,
        checkpoint_every=4,
        programming_languages=[],
        output_root=str(tmp_path),
    )
    course = get_course("batch-1")
    course["plan"] = plan
    course["status"] = "generating"
    course["next_day"] = 1
    from utils.course_store import set_course

    async def fake_generate(course_id: str, day_number: int) -> bool:
        c = get_course(course_id)
        done = list(c.get("days_completed", []))
        done.append(day_number)
        c["days_completed"] = done
        c["next_day"] = day_number + 1
        set_course(course_id, c)
        return True

    with patch("services.course_runner.generate_single_day", side_effect=fake_generate):
        await run_course_batch("batch-1")

    updated = get_course("batch-1")
    assert updated["status"] == "awaiting_checkpoint"
    assert updated["next_day"] == 5
    assert len(updated["days_completed"]) == 4


def test_course_output_root_slug():
    path = course_output_root("Full Gen AI Syllabus!")
    assert "full_gen_ai" in str(path).lower() or "gen_ai" in str(path).lower()
