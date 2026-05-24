"""API models for multi-day course generation."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CoursePlanRequest(BaseModel):
    course_name: str = Field(..., min_length=3, max_length=200)
    syllabus: str = Field(..., min_length=50, max_length=50000)
    total_days: int = Field(default=30, ge=1, le=60)
    hours_per_day: float = Field(default=1.5, ge=0.5, le=8.0)
    checkpoint_every: int = Field(default=4, ge=1, le=10)
    programming_languages: List[str] = Field(default_factory=list)


class DayPlanSummary(BaseModel):
    day: int
    title: str
    topic: str
    duration_minutes: int


class CoursePlanResponse(BaseModel):
    course_id: str
    status: str
    course_name: str
    total_days: int
    output_root: str
    days: List[DayPlanSummary]
    message: str


class CourseStatusResponse(BaseModel):
    course_id: str
    status: str
    course_name: str
    total_days: int
    days_completed: List[int]
    next_day: int
    progress_percent: float
    output_root: str
    checkpoint_every: int = 4
    hours_per_day: float = 1.5
    plan_days: List[DayPlanSummary] = Field(default_factory=list)
    current_generating_day: Optional[int] = None
    current_day_title: Optional[str] = None
    current_session_id: Optional[str] = None
    checkpoint_message: Optional[str] = None
    plan_summary: Optional[str] = None
    day_outputs: dict = Field(default_factory=dict)
    day_sessions: dict = Field(default_factory=dict)
    errors: List[str] = []
    batch_active: Optional[bool] = None
    interrupted: bool = False


class CourseRetryDayRequest(BaseModel):
    day: Optional[int] = Field(default=None, ge=1, le=60)


class CoursePlanRespondRequest(BaseModel):
    approved: bool
    feedback: str = ""


class CourseCheckpointRespondRequest(BaseModel):
    approved: bool
    feedback: str = ""


class CourseActionResponse(BaseModel):
    course_id: str
    status: str
    message: str


class CourseSummaryItem(BaseModel):
    course_id: str
    course_name: str
    status: str
    start_time: float
    total_days: int
    days_completed_count: int = 0
    has_notes: bool = False
    chat_count: int = 0


class CourseListResponse(BaseModel):
    courses: List[CourseSummaryItem]
