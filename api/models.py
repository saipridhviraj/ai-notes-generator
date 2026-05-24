from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class PipelineStepItem(BaseModel):
    id: str
    label: str
    persona: str = ""
    persona_icon: str = "🤖"
    state: Literal["done", "active", "pending", "skipped"]


class NodeArtifactItem(BaseModel):
    node_id: str
    label: str
    persona_icon: str = "🤖"
    state: Literal["done", "active", "pending", "skipped"] = "pending"
    format: Literal["markdown", "json", "text"] = "markdown"
    available: bool = False
    char_count: int = 0
    preview: Optional[str] = None
    suggested_diagram_count: Optional[int] = None


class NodeArtifactResponse(BaseModel):
    node_id: str
    label: str
    persona_icon: str = "🤖"
    format: Literal["markdown", "json", "text"] = "markdown"
    content: str
    char_count: int = 0
    suggested_diagrams: Optional[List[str]] = None


class ResumeRequest(BaseModel):
    from_node: Literal[
        "research",
        "student_notes",
        "tutor_notes",
        "evaluator",
        "gap_bridger",
        "mermaid_repair",
    ]


class ResumeResponse(BaseModel):
    session_id: str
    from_node: str
    status: str
    message: str


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    session_id: Optional[str] = None


class TutorRespondRequest(BaseModel):
    approved: bool
    feedback: str = ""
    response_to: Literal["plan_verification", "error_clarification"] = "plan_verification"


class GenerateResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ChatMessageItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: float


class StatusResponse(BaseModel):
    session_id: str
    status: str
    current_node: Optional[str] = None
    node_label: Optional[str] = None
    active_persona: Optional[str] = None
    active_persona_icon: Optional[str] = None
    active_persona_blurb: Optional[str] = None
    elapsed_seconds: float = 0.0
    progress_percent: float = 0.0
    progress_step: int = 0
    progress_total: int = 8
    pipeline_steps: List[PipelineStepItem] = []
    node_artifacts: List[NodeArtifactItem] = []
    retry_count: int = 0
    tutor_question: Optional[str] = None
    output_files: List[str] = []
    errors: List[str] = []
    node_phase: Optional[Literal["starting", "streaming"]] = None
    status_detail: Optional[str] = None
    evaluation_passed: Optional[bool] = None
    diagram_issue_count: int = 0
    chat_history: List[ChatMessageItem] = []
    job_alive: Optional[bool] = None
    interrupted: bool = False


class RestartResponse(BaseModel):
    session_id: str
    status: str
    message: str


class CancelResponse(BaseModel):
    session_id: str
    status: str
    message: str


class TutorRespondResponse(BaseModel):
    session_id: str
    message: str
    status: str


class ResultResponse(BaseModel):
    session_id: str
    status: str
    topic: Optional[str] = None
    student_file: Optional[str] = None
    tutor_file: Optional[str] = None
    student_markdown: Optional[str] = None
    tutor_markdown: Optional[str] = None
    evaluation_score: Optional[dict] = None
    retry_count: int = 0
    used_web_search: bool = False
    summary: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    llm_provider: Optional[str] = None
    prompt_profile: Optional[str] = None
    ollama_reachable: Optional[bool] = None
    note_ready_enabled: Optional[bool] = None
    note_ready_pending: Optional[int] = None


class SessionSummaryItem(BaseModel):
    session_id: str
    topic: str
    status: str
    start_time: float
    has_notes: bool = False
    output_files: List[str] = []
    chat_count: int = 0
    student_filename: Optional[str] = None
    tutor_filename: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionSummaryItem]


class SessionChatRequest(BaseModel):
    message: str = Field(..., min_length=3, max_length=4000)


class SessionChatResponse(BaseModel):
    session_id: str
    message: str
    status: str
    output_files: List[str] = []
    chat_history: List[ChatMessageItem] = []


class DeleteSessionResponse(BaseModel):
    session_id: str
    message: str


class BulkDeleteResponse(BaseModel):
    deleted_count: int
    message: str
