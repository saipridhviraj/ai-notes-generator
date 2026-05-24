"""Pydantic models for multi-day course generation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DayPlan(BaseModel):
    day: int = Field(..., ge=1, le=60)
    title: str = Field(..., min_length=3, max_length=200)
    topic: str = Field(..., min_length=3, max_length=500)
    concepts: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(default=90, ge=30, le=240)


class CoursePlan(BaseModel):
    course_name: str
    total_days: int
    hours_per_day: float
    programming_languages: list[str] = Field(default_factory=list)
    syllabus_summary: str = ""
    days: list[DayPlan]

    def validate_day_count(self) -> None:
        if len(self.days) != self.total_days:
            raise ValueError(
                f"Plan has {len(self.days)} days but total_days={self.total_days}"
            )


CourseStatus = Literal[
    "planning",
    "awaiting_plan_approval",
    "generating",
    "awaiting_checkpoint",
    "completed",
    "failed",
    "rejected",
]
