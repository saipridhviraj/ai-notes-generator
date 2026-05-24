"""note.ready event payload for VB Academy indexing."""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from models.tutor_supplements import TutorSupplements


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class NoteReadyEvent(BaseModel):
    event: str = "note.ready"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: str = Field(default_factory=utc_now_iso)
    course_id: Optional[str] = None
    session_id: str
    day: Optional[int] = None
    title: str
    topic: str
    course_name: Optional[str] = None
    # Primary RAG source — VB Academy chunks + embeds this only for lesson content
    student_uri: str
    # Human-readable tutor guide on disk (not embedded by default)
    tutor_uri: Optional[str] = None
    # Structured tutor-only items for metadata-filtered RAG chunks
    supplements: TutorSupplements = Field(default_factory=TutorSupplements)
    supplements_uri: Optional[str] = None
    supplements_item_count: int = 0
    output_root: str
    programming_languages: List[str] = Field(default_factory=list)
    hours_per_day: Optional[float] = None
    indexing_hint: str = (
        "Embed student_uri as source_type=lesson visibility=student. "
        "Index each supplements.* item as tutor_only with source_type quiz|assignment|pacing|teaching_tip."
    )
