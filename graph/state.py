from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel


class KeywordPlan(BaseModel):
    topic: str
    domain: str
    intent: str
    keywords: List[str]
    subtopics: List[str]
    needs_web_search: bool


class EvaluationResult(BaseModel):
    student_notes_score: int
    tutor_notes_score: int
    missing_topics: List[str]
    diagram_issues: List[str]
    alignment_issues: List[str]
    passed: bool


class GraphState(TypedDict):
    # ── INPUT ────────────────────────────────────────────────
    user_input: str
    session_id: str

    # ── PLANNER ──────────────────────────────────────────────
    planner_output: Optional[KeywordPlan]
    planner_verified: bool
    planner_feedback: Optional[str]

    # ── CONSULT TUTOR ────────────────────────────────────────
    tutor_question: Optional[str]
    tutor_response: Optional[str]
    awaiting_tutor: bool

    # ── RESEARCH ─────────────────────────────────────────────
    research_data: Optional[str]
    used_web_search: bool

    # ── NOTES ────────────────────────────────────────────────
    student_notes: Optional[str]
    tutor_notes: Optional[str]
    student_filename: Optional[str]
    tutor_filename: Optional[str]

    # ── EVALUATION ───────────────────────────────────────────
    evaluation_result: Optional[EvaluationResult]
    retry_count: int

    # ── FINAL ────────────────────────────────────────────────
    output_files: List[str]
    final_summary: Optional[str]
    errors: List[str]
    status: Literal["running", "awaiting_tutor", "completed", "failed", "max_retries_reached"]
    chat_history: Optional[List[dict]]
    # Course day generation (optional)
    output_dir: Optional[str]
    course_day: Optional[int]
    course_id: Optional[str]
