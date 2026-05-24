"""Generate a multi-day course plan from a full syllabus."""
from __future__ import annotations

import json

from graph.course_models import CoursePlan
from prompts.course_planner_prompts import (
    get_course_planner_system_prompt,
    get_course_planner_user_prompt,
)
from services.llm_client import _strip_json_fences, llm_client


def build_course_plan(
    syllabus: str,
    course_name: str,
    total_days: int = 30,
    hours_per_day: float = 1.5,
    programming_languages: list[str] | None = None,
) -> CoursePlan:
    langs = programming_languages or []
    raw = llm_client.complete(
        prompt=get_course_planner_user_prompt(
            syllabus=syllabus,
            course_name=course_name,
            total_days=total_days,
            hours_per_day=hours_per_day,
            programming_languages=langs,
        ),
        size="large",
        system=get_course_planner_system_prompt(),
        temperature=0.2,
        max_tokens=16384,
    )
    cleaned = _strip_json_fences(raw)
    plan = CoursePlan(**json.loads(cleaned))
    plan.validate_day_count()
    return plan
