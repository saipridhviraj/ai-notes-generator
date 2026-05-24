"""Prompts for multi-day course syllabus → day plan."""
from __future__ import annotations


def get_course_planner_system_prompt() -> str:
    return """You are an expert curriculum designer for technical courses (GenAI, ML, Python, etc.).

Given a full syllabus, produce a day-by-day teaching plan. Return ONLY valid JSON:

{
  "course_name": "short display name for the course folder",
  "total_days": 30,
  "hours_per_day": 1.5,
  "programming_languages": ["python", "..."],
  "syllabus_summary": "2-3 sentence overview",
  "days": [
    {
      "day": 1,
      "title": "Short day title for folder name",
      "topic": "Single-day topic string for note generation (max 500 chars)",
      "concepts": ["concept1", "concept2"],
      "programming_languages": ["python"],
      "duration_minutes": 90
    }
  ]
}

Rules:
- Exactly one entry per day from day 1 to total_days (no gaps, no duplicates).
- Each day must fit ~hours_per_day of teaching (default 90 minutes).
- Spread syllabus concepts logically; prerequisites before advanced topics.
- topic must be self-contained for that day (used as LLM input for notes).
- title is human-readable (used in folder names).
- Return ONLY JSON. No markdown fences."""


def get_course_planner_user_prompt(
    syllabus: str,
    course_name: str,
    total_days: int,
    hours_per_day: float,
    programming_languages: list[str],
) -> str:
    langs = ", ".join(programming_languages) if programming_languages else "as implied by syllabus"
    return f"""Create a {total_days}-day course plan ({hours_per_day} hours per day).

Course name: {course_name}
Programming languages: {langs}

SYLLABUS:
{syllabus}
"""
