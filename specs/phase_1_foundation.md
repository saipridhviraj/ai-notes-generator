# Phase 1 — Foundation

**Goal:** Scaffold the entire directory tree, install dependencies, configure environment variables, define the LangGraph state schema, and define all Pydantic API models. Nothing runs yet, but the skeleton is complete and importable.

---

## Task 1.1 — Directory Skeleton

Create the following directory and file tree exactly as specified. All Python packages must include `__init__.py`.

```
ai-notes-generator/
├── main.py                          # FastAPI app entry point (stub)
├── .env                             # API keys (never commit)
├── .env.example                     # Template for keys
├── requirements.txt
│
├── examples/                        # Few-shot reference files
│   ├── day1_student_notes.md        # (copy in Phase 8 — must exist before running)
│   └── day1_tutor_notes.md          # (copy in Phase 8 — must exist before running)
│
├── graph/
│   ├── __init__.py
│   ├── state.py
│   ├── graph_builder.py
│   └── nodes/
│       ├── __init__.py
│       ├── planner_node.py
│       ├── research_node.py
│       ├── student_notes_creator.py
│       ├── tutor_notes_creator.py
│       ├── evaluator_node.py
│       ├── gap_bridger_node.py
│       ├── final_response_node.py
│       └── consult_tutor_node.py
│
├── api/
│   ├── __init__.py
│   ├── routes.py
│   └── models.py
│
├── services/
│   ├── __init__.py
│   ├── groq_client.py
│   ├── tavily_client.py
│   └── file_service.py
│
├── prompts/
│   ├── __init__.py
│   ├── planner_prompts.py
│   ├── research_prompts.py
│   ├── student_notes_prompts.py
│   ├── tutor_notes_prompts.py
│   └── evaluator_prompts.py
│
└── utils/
    ├── __init__.py
    └── helpers.py
```

**Acceptance criteria:**
- All directories exist.
- Every Python package directory has an `__init__.py`.
- All `.py` files start as empty stubs (just a module docstring is fine).

---

## Task 1.2 — Environment & Dependencies

### `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
langgraph==0.2.28
langchain-core==0.3.0
groq==0.11.0
tavily-python==0.5.0
pydantic==2.9.0
python-dotenv==1.0.1
httpx==0.27.0
```

### `.env.example`

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
APP_HOST=0.0.0.0
APP_PORT=8000
MAX_EVAL_RETRIES=3
```

### `.env`

Copy from `.env.example` and fill in real keys. **Never commit `.env` to version control.**

Add `.env` to `.gitignore`.

### `.gitignore`

```
.env
__pycache__/
*.pyc
*.pyo
.venv/
venv/
dist/
*.egg-info/
generated_notes/
```

**Acceptance criteria:**
- `pip install -r requirements.txt` completes with no errors.
- `python -c "import langgraph, fastapi, groq, tavily"` succeeds.

---

## Task 1.3 — LangGraph State Schema (`graph/state.py`)

Define the full `GraphState` TypedDict and supporting Pydantic models. This file is the single source of truth for all data flowing through the graph.

### Models to define

#### `KeywordPlan` (Pydantic BaseModel)

| Field | Type | Description |
|---|---|---|
| `topic` | `str` | Primary topic name |
| `domain` | `str` | One of: `python`, `fastapi`, `ml`, `dl`, `genai`, `system_design`, `genai_system_design`, `data_structures` |
| `intent` | `str` | Always `"comprehensive_notes"` for MVP |
| `keywords` | `List[str]` | Max 10 keywords — most important concepts to cover |
| `subtopics` | `List[str]` | Detailed breakdown of the topic |
| `needs_web_search` | `bool` | True for GenAI, recent model architectures, rapidly-changing topics |

#### `EvaluationResult` (Pydantic BaseModel)

| Field | Type | Description |
|---|---|---|
| `student_notes_score` | `int` | 0–100 |
| `tutor_notes_score` | `int` | 0–100 |
| `missing_topics` | `List[str]` | Topics not covered in student notes |
| `diagram_issues` | `List[str]` | Mermaid diagram problems detected |
| `alignment_issues` | `List[str]` | Tutor vs student content misalignment |
| `passed` | `bool` | `True` if BOTH scores >= 80 |

#### `GraphState` (TypedDict)

```python
class GraphState(TypedDict):
    # INPUT
    user_input: str                         # Raw topic from user
    session_id: str                         # Unique session identifier

    # PLANNER
    planner_output: Optional[KeywordPlan]
    planner_verified: bool                  # True after ConsultTutor approves
    planner_feedback: Optional[str]         # Tutor feedback on the plan

    # CONSULT TUTOR
    tutor_question: Optional[str]           # Question posed to tutor
    tutor_response: Optional[str]           # Tutor's response via POST endpoint
    awaiting_tutor: bool                    # True while polling for tutor input

    # RESEARCH
    research_data: Optional[str]            # Synthesized research content
    used_web_search: bool

    # NOTES
    student_notes: Optional[str]            # Markdown string
    tutor_notes: Optional[str]              # Markdown string
    student_filename: Optional[str]         # e.g. "python_basics_student.md"
    tutor_filename: Optional[str]           # e.g. "python_basics_tutor.md"

    # EVALUATION
    evaluation_result: Optional[EvaluationResult]
    retry_count: int                        # Incremented each time GapBridger runs

    # FINAL
    output_files: List[str]                 # Saved absolute file paths
    final_summary: Optional[str]
    errors: List[str]                       # Non-fatal errors/warnings appended here
    status: Literal["running", "awaiting_tutor", "completed", "failed", "max_retries_reached"]
```

**Imports required:**
```python
from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel
```

**Acceptance criteria:**
- `from graph.state import GraphState, KeywordPlan, EvaluationResult` works with no errors.
- All fields match the spec above exactly — no additions, no removals.

---

## Task 1.4 — Pydantic API Models (`api/models.py`)

Define all request and response bodies used by the FastAPI routes.

### Request models

#### `GenerateRequest`
```python
class GenerateRequest(BaseModel):
    topic: str
    session_id: Optional[str] = None    # Auto-generated (UUID4) if not provided
```

#### `TutorRespondRequest`
```python
class TutorRespondRequest(BaseModel):
    approved: bool
    feedback: str = ""
    response_to: Literal["plan_verification", "error_clarification"] = "plan_verification"
```

### Response models

#### `GenerateResponse`
```python
class GenerateResponse(BaseModel):
    session_id: str
    status: str
    message: str
```

#### `StatusResponse`
```python
class StatusResponse(BaseModel):
    session_id: str
    status: str
    current_node: Optional[str] = None
    retry_count: int = 0
    tutor_question: Optional[str] = None
    output_files: List[str] = []
    errors: List[str] = []
```

#### `TutorRespondResponse`
```python
class TutorRespondResponse(BaseModel):
    session_id: str
    message: str
    status: str
```

#### `ResultResponse`
```python
class ResultResponse(BaseModel):
    session_id: str
    status: str
    topic: Optional[str] = None
    student_file: Optional[str] = None
    tutor_file: Optional[str] = None
    evaluation_score: Optional[dict] = None   # {"student": int, "tutor": int}
    retry_count: int = 0
    used_web_search: bool = False
    summary: Optional[str] = None
```

#### `HealthResponse`
```python
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
```

**Acceptance criteria:**
- `from api.models import GenerateRequest, StatusResponse, ResultResponse` works.
- All fields match exactly — types, optionality, defaults.
