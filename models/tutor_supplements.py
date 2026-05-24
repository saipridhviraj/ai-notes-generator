"""Structured tutor-only content extracted for VB Academy RAG indexing."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class QuizItem(BaseModel):
    id: str
    kind: Literal["rapid_fire", "revision", "in_class"] = "rapid_fire"
    question: str
    answer: Optional[str] = None
    section: Optional[str] = None


class AssignmentItem(BaseModel):
    id: str
    title: str
    description: str
    rubric_notes: Optional[str] = None
    section: Optional[str] = None


class PacingItem(BaseModel):
    id: str
    section: Optional[str] = None
    minutes_marker: Optional[str] = None
    teaching_tip: str


class TeachingTipItem(BaseModel):
    id: str
    section: Optional[str] = None
    tip: str


class TutorSupplements(BaseModel):
    """
    Tutor-only structured content for RAG — indexed with visibility=tutor_only.
    VB Academy embeds student.md for everyone; indexes each supplement item separately.
    """

    visibility: Literal["tutor_only"] = "tutor_only"
    quizzes: List[QuizItem] = Field(default_factory=list)
    assignments: List[AssignmentItem] = Field(default_factory=list)
    pacing: List[PacingItem] = Field(default_factory=list)
    teaching_tips: List[TeachingTipItem] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.quizzes or self.assignments or self.pacing or self.teaching_tips)

    def total_items(self) -> int:
        return len(self.quizzes) + len(self.assignments) + len(self.pacing) + len(self.teaching_tips)
