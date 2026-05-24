# 🤖 Cursor Implementation Prompt — Agentic AI Notes Generator

> Paste this entire document into Cursor Composer (Cmd+I / Ctrl+I) to scaffold the project.

---

## 📌 Project Overview

Build a **production-ready Agentic AI backend** that accepts a topic (or list of topics) as input and autonomously generates **two beautifully structured Markdown note files** — one for students and one for tutors — mimicking the style of a professional Generative AI course (rich Mermaid.js diagrams, tables, callouts, emoji headers, structured sections).

The system is built as a **LangGraph stateful agent graph** exposed via a **FastAPI REST API**. It uses **Groq-hosted LLMs** (routing small models to fast tasks and larger reasoning models to complex tasks) and **Tavily** for optional web search in the research phase. A **human-in-the-loop ConsultTutor** mechanism allows the tutor to verify the plan and answer questions via a polling endpoint.

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Agent Framework** | LangGraph (`langgraph`) | Stateful node graph orchestration |
| **API Layer** | FastAPI + Uvicorn | REST endpoints |
| **LLM Provider** | Groq API (`groq`) | Fast inference on open models |
| **Web Search** | Tavily (`tavily-python`) | Optional research augmentation |
| **Data Validation** | Pydantic v2 | State schema + API models |
| **Env Management** | python-dotenv | API key management |
| **File I/O** | Python `pathlib` | Markdown file output |
| **Async** | `asyncio` + `httpx` | Non-blocking I/O |

### Groq Model Assignments (CRITICAL — assign by complexity)

| Node | Model | Reason |
|---|---|---|
| PlannerNode | `llama-3.1-8b-instant` | Fast JSON extraction, simple intent parsing |
| ResearchNode (decide) | `llama-3.1-8b-instant` | Binary decision: search or not |
| ResearchNode (synthesize) | `llama-3.3-70b-versatile` | Deep domain knowledge synthesis |
| StudentNotesCreator | `llama-3.3-70b-versatile` | High-quality long-form markdown generation |
| TutorNotesCreator | `llama-3.3-70b-versatile` | High-quality long-form markdown generation |
| EvaluatorNode | `deepseek-r1-distill-llama-70b` | Reasoning-heavy evaluation & gap detection |
| GapBridgerNode | `llama-3.3-70b-versatile` | Content generation for missing topics |
| FinalResponseNode | `llama-3.1-8b-instant` | Simple file naming & summary |
| ConsultTutorNode | No LLM — pure logic | Human-in-the-loop polling |

---

## 📁 Project Structure

```
ai-notes-generator/
├── main.py                          # FastAPI app entry point
├── .env                             # API keys (never commit)
├── .env.example                     # Template for keys
├── requirements.txt
│
├── examples/                        # Few-shot reference files (REQUIRED — copy before running)
│   ├── day1_student_notes.md        # Real student notes — LLM uses this as style reference
│   └── day1_tutor_notes.md          # Real tutor guide — LLM uses this as style reference
│
├── graph/
│   ├── __init__.py
│   ├── state.py                     # LangGraph GraphState TypedDict
│   ├── graph_builder.py             # LangGraph graph assembly
│   │
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
│   ├── routes.py                    # All FastAPI routes
│   └── models.py                    # Pydantic request/response models
│
├── services/
│   ├── __init__.py
│   ├── groq_client.py               # Groq LLM wrapper with model routing
│   ├── tavily_client.py             # Tavily search wrapper
│   └── file_service.py             # Markdown file save logic
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
    └── helpers.py                   # Shared utility functions
```

---

## 🔑 Environment Variables

Create `.env` with:

```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
APP_HOST=0.0.0.0
APP_PORT=8000
MAX_EVAL_RETRIES=3
```

---

## 📐 LangGraph State Schema (`graph/state.py`)

```python
from typing import TypedDict, Optional, List, Literal, Any
from pydantic import BaseModel

class KeywordPlan(BaseModel):
    topic: str
    domain: str                        # e.g., "machine_learning", "web_framework"
    intent: str                        # e.g., "comprehensive_notes", "quick_reference"
    keywords: List[str]                # Max 10 keywords/concepts to cover
    subtopics: List[str]               # Derived subtopics
    needs_web_search: bool             # Hint from planner

class EvaluationResult(BaseModel):
    student_notes_score: int           # 0-100
    tutor_notes_score: int             # 0-100
    missing_topics: List[str]          # Topics not covered
    diagram_issues: List[str]          # Mermaid diagram problems
    alignment_issues: List[str]        # Tutor vs student misalignment
    passed: bool                       # True if both scores >= 80

class GraphState(TypedDict):
    # ── INPUT ────────────────────────────────────────────────
    user_input: str                    # Raw topic input from user
    session_id: str                    # Unique session identifier

    # ── PLANNER ──────────────────────────────────────────────
    planner_output: Optional[KeywordPlan]
    planner_verified: bool             # Set True after ConsultTutor verifies
    planner_feedback: Optional[str]    # Tutor feedback on plan

    # ── CONSULT TUTOR ────────────────────────────────────────
    tutor_question: Optional[str]      # Question posed to tutor
    tutor_response: Optional[str]      # Tutor's response (from polling)
    awaiting_tutor: bool               # True while polling

    # ── RESEARCH ─────────────────────────────────────────────
    research_data: Optional[str]       # Synthesized research content
    used_web_search: bool

    # ── NOTES ────────────────────────────────────────────────
    student_notes: Optional[str]       # Markdown content
    tutor_notes: Optional[str]         # Markdown content
    student_filename: Optional[str]    # e.g., "python_basics_student.md"
    tutor_filename: Optional[str]      # e.g., "python_basics_tutor.md"

    # ── EVALUATION ───────────────────────────────────────────
    evaluation_result: Optional[EvaluationResult]
    retry_count: int                   # Current retry count (max = MAX_EVAL_RETRIES)

    # ── FINAL ────────────────────────────────────────────────
    output_files: List[str]            # Saved file paths
    final_summary: Optional[str]       # Summary of what was generated
    errors: List[str]                  # Non-fatal errors/warnings
    status: Literal[
        "running", "awaiting_tutor", "completed", "failed", "max_retries_reached"
    ]
```

---

## 🔗 LangGraph Graph Assembly (`graph/graph_builder.py`)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import GraphState
from graph.nodes import (
    planner_node, consult_tutor_node, research_node,
    student_notes_creator, tutor_notes_creator,
    evaluator_node, gap_bridger_node, final_response_node
)

def build_graph():
    builder = StateGraph(GraphState)

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("consult_tutor", consult_tutor_node)
    builder.add_node("research", research_node)
    builder.add_node("student_notes", student_notes_creator)
    builder.add_node("tutor_notes", tutor_notes_creator)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("gap_bridger", gap_bridger_node)
    builder.add_node("final_response", final_response_node)

    # Entry
    builder.set_entry_point("planner")

    # Planner → ConsultTutor (always verify plan first)
    builder.add_edge("planner", "consult_tutor")

    # ConsultTutor → Research (after tutor verifies OR timeout)
    builder.add_conditional_edges(
        "consult_tutor",
        route_after_tutor,
        {
            "research": "research",
            "consult_tutor": "consult_tutor",   # still waiting
        }
    )

    # Research → StudentNotes → TutorNotes → Evaluator
    builder.add_edge("research", "student_notes")
    builder.add_edge("student_notes", "tutor_notes")
    builder.add_edge("tutor_notes", "evaluator")

    # Evaluator → Pass (FinalResponse) or Fail (GapBridger)
    builder.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {
            "final_response": "final_response",
            "gap_bridger": "gap_bridger",
            "final_response_max_retries": "final_response",  # give up gracefully
        }
    )

    # GapBridger → directly back to Evaluator (surgical merge, no full regen)
    builder.add_edge("gap_bridger", "evaluator")

    # FinalResponse → END
    builder.add_edge("final_response", END)

    return builder.compile(checkpointer=MemorySaver())


def route_after_tutor(state: GraphState) -> str:
    if state["awaiting_tutor"]:
        return "consult_tutor"
    return "research"


def route_after_evaluation(state: GraphState) -> str:
    result = state["evaluation_result"]
    max_retries = int(os.getenv("MAX_EVAL_RETRIES", "3"))

    if result.passed:
        return "final_response"
    if state["retry_count"] >= max_retries:
        return "final_response_max_retries"
    return "gap_bridger"
```

---

## 🧠 Node Implementations

### 1. `planner_node.py`

**Model:** `llama-3.1-8b-instant`
**Input:** `user_input`
**Output:** `planner_output` (KeywordPlan JSON)

**System Prompt:**
```
You are an expert AI curriculum planner. Given a topic or list of topics, analyze and return a structured JSON plan.

Return ONLY valid JSON with these exact keys:
{
  "topic": "primary topic name",
  "domain": "one of: python | fastapi | ml | dl | genai | system_design | genai_system_design | data_structures",
  "intent": "comprehensive_notes",
  "keywords": ["keyword1", ..., "keyword10"],   // MAX 10 - most important concepts
  "subtopics": ["subtopic1", ...],               // detailed breakdown
  "needs_web_search": true/false                 // true for cutting-edge or recent topics
}

Topics this system covers: Python, FastAPI, ML, Deep Learning (all architectures), 
Generative AI, System Design, GenAI System Design, Data Structures.

For needs_web_search: set true only for GenAI, recent model architectures, 
or anything that changes rapidly.
```

**Logic:**
- Call Groq with `llama-3.1-8b-instant`
- Parse JSON response → KeywordPlan
- Set `planner_verified = False`, `awaiting_tutor = True`
- Set `tutor_question` = formatted question asking tutor to verify the plan

---

### 2. `consult_tutor_node.py`

**No LLM — Pure logic node (Human-in-the-loop)**
**Input:** `awaiting_tutor`, `tutor_response`, `planner_output`
**Output:** Updates `planner_verified`, `planner_feedback`, `awaiting_tutor`

**Logic:**
- Check if `tutor_response` is populated (tutor has replied via POST endpoint)
- If YES:
  - Parse tutor response
  - If approved → set `planner_verified = True`, `awaiting_tutor = False`
  - If feedback → update `planner_output` keywords based on feedback, set `planner_verified = True`
- If NO → return state unchanged (graph will re-enter this node)
- Include a **timeout** of 5 minutes — if no response after timeout, auto-approve and continue

**This node is also triggered whenever:**
- The application encounters an unrecoverable error
- The EvaluatorNode finds issues it cannot resolve automatically

---

### 3. `research_node.py`

**Models:** `llama-3.1-8b-instant` (decide) + `llama-3.3-70b-versatile` (synthesize)
**Input:** `planner_output`
**Output:** `research_data`, `used_web_search`

**Logic:**

Step 1 — Decide (small model):
```
Given this topic plan: {planner_output}
Should I use web search to gather current information? 
The topic is: {topic}
needs_web_search hint: {needs_web_search}
Reply with ONLY: "yes" or "no"
```

Step 2a — If web search needed:
- Call Tavily with each keyword from planner_output.keywords
- Collect top 3 results per keyword
- Deduplicate and format into context

Step 2b — Synthesize (large model):
```
You are an expert educator and technical writer specializing in {domain}.

Topic: {topic}
Keywords to cover: {keywords}
Subtopics: {subtopics}
{if web_results: "Additional web research context: {web_results}"}

Provide a comprehensive, deep knowledge dump on all the above.
Cover each keyword with:
- Core concept explanation
- How it works (step by step)
- Real-world examples
- Common analogies for students
- Where it fits in the bigger picture

This will be used to generate educational notes. Be thorough.
```

---

### 4. `student_notes_creator.py`

**Model:** `llama-3.3-70b-versatile`
**Input:** `research_data`, `planner_output`
**Output:** `student_notes` (markdown string), `student_filename`

**CRITICAL — Few-Shot Example Loading:**

Load the real Day 1 reference file at module level and inject it into every prompt.
This is the primary quality driver — the LLM mirrors the real file, not a skeleton description.

```python
from pathlib import Path

def load_example(filename: str) -> str:
    path = Path("examples") / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required example file: examples/{filename}\n"
            f"Copy your Day 1 notes into the examples/ folder before running."
        )
    return path.read_text(encoding="utf-8")

# Load once at module level — reused across all sessions
STUDENT_EXAMPLE = load_example("day1_student_notes.md")
```

**System Prompt (with injected few-shot example):**

```python
system_prompt = f"""
You are an expert technical educator and markdown content creator.

Study the reference example below carefully and replicate its style EXACTLY:
- Same emoji density in every heading
- Same dark-theme Mermaid diagram color palette
- Same section order and structure
- Same blockquote definitions, emoji tables, callout boxes
- Same revision questions, homework, and next class preview sections

═══════════════════════════════════════════
REFERENCE EXAMPLE (real Day 1 student notes — match this style):
═══════════════════════════════════════════
{STUDENT_EXAMPLE}
═══════════════════════════════════════════

MERMAID COLOR RULES (non-negotiable):
  fills : #1a1a2e  #16213e  #0f3460  #312e81  #4c1d95  #1e3a5f
  strokes: #7c3aed  #2563eb  #0891b2  #d946ef  #8b5cf6  #10b981  #f59e0b  #3b82f6
  text  : always #e2e8f0
  Every node MUST have an explicit style declaration.
  Minimum 4 Mermaid diagrams per file.

Output ONLY the markdown. No preamble. No explanation.
"""

user_prompt = f"""
Generate student notes for:

TOPIC   : {planner_output.topic}
DOMAIN  : {planner_output.domain}
KEYWORDS (all must appear): {planner_output.keywords}
SUBTOPICS: {planner_output.subtopics}

RESEARCH DATA:
{research_data}
"""
```

**Filename Logic:**
- Default: `{{topic_slug}}_student.md`  e.g. `python_decorators_student.md`
- If user specified a name in input → use that

---

### 5. `tutor_notes_creator.py`

**Model:** `llama-3.3-70b-versatile`
**Input:** `student_notes`, `planner_output`
**Output:** `tutor_notes` (markdown string), `tutor_filename`

**CRITICAL — Few-Shot Example Loading:**

```python
# Load once at module level
TUTOR_EXAMPLE = load_example("day1_tutor_notes.md")
```

**Logic:**
The tutor notes are built on top of the already-generated `student_notes`.
The LLM sees both the real tutor reference AND the freshly generated student notes,
so it knows exactly what to annotate and where.

**System Prompt (with injected few-shot example):**

```python
system_prompt = f"""
You are an expert instructional designer creating a Teacher's Annotated Guide.

Study the reference example below — it shows EXACTLY how a tutor guide should look
alongside its student notes. Replicate the annotation style precisely:
  > **👨‍🏫 TEACHING NOTE:** blocks before each section
  > **👨‍🏫 SAY THIS:** exact verbal scripts
  > **👨‍🏫 INTERACTIVE MOMENT:** class engagement prompts
  > **👨‍🏫 TIME CHECK:** pacing markers
  > **👨‍🏫 QUICK ACTIVITY:** exercises
  <details> collapsible prep checklist at top
  <details> collapsible post-session checklist at bottom
  Rapid-fire quizzes after every comparison/contrast section
  Teaching tips for every Mermaid diagram

═══════════════════════════════════════════
REFERENCE EXAMPLE (real Day 1 tutor guide — match this annotation style):
═══════════════════════════════════════════
{TUTOR_EXAMPLE}
═══════════════════════════════════════════

RULES:
1. Keep 100% of the student content — every diagram, table, section
2. Add teaching annotations inline throughout — do not summarise or skip
3. Every diagram must get a > **👨‍🏫 TEACHING NOTE:** on how to explain it
4. Output ONLY the markdown. No preamble. No explanation.
"""

user_prompt = f"""
Transform the student notes below into a Teacher's Annotated Guide.

TOPIC   : {planner_output.topic}
KEYWORDS: {planner_output.keywords}

STUDENT NOTES TO ANNOTATE:
{student_notes}
"""
```

**Filename:**
- `{{topic_slug}}_tutor.md`  e.g. `python_decorators_tutor.md`

---

### 6. `evaluator_node.py`

**Model:** `deepseek-r1-distill-llama-70b`
**Input:** `student_notes`, `tutor_notes`, `planner_output`, `retry_count`
**Output:** `evaluation_result` (EvaluationResult), incremented `retry_count`

**Evaluation Criteria:**

**Student Notes:**
- Coverage: Are all 10 keywords present? (10 pts each = 100)
- Deduct 10 pts per missing keyword
- Deduct 5 pts per broken/malformed Mermaid diagram
- Deduct 5 pts if no revision questions
- Deduct 5 pts if no homework section

**Tutor Notes:**
- Does it contain all student diagrams? (25 pts)
- Does it have teaching annotations for each section? (25 pts)
- Does it have a prep checklist? (25 pts)
- Does it have a post-session checklist? (25 pts)

**Mermaid Diagram Check (IMPORTANT):**
Check each ```mermaid block for:
- Valid graph type declaration (`graph TD`, `flowchart LR`, etc.)
- All nodes have style declarations
- Correct color hex values (from approved palette)
- No syntax errors (unclosed brackets, missing arrows)

**Pass Threshold:** Both scores >= 80/100

**System Prompt:**
```
You are a strict quality evaluator for educational AI-generated notes.

STUDENT NOTES:
{student_notes}

TUTOR NOTES:
{tutor_notes}

KEYWORDS THAT MUST BE COVERED: {keywords}

Evaluate both sets of notes and return ONLY valid JSON:
{
  "student_notes_score": <0-100>,
  "tutor_notes_score": <0-100>,
  "missing_topics": ["topic1", ...],
  "diagram_issues": ["issue description", ...],
  "alignment_issues": ["issue description", ...],
  "passed": <true/false>
}

Score student notes: 100 - (10 * missing_keywords) - (5 * broken_diagrams) - (5 * missing_sections)
Score tutor notes: 25 per criteria (all student diagrams present, annotations exist, prep checklist, post checklist)
passed = true only if BOTH scores >= 80
```

**Retry Logic:**
```python
MAX_RETRIES = int(os.getenv("MAX_EVAL_RETRIES", "3"))  # Default: 3

state["retry_count"] += 1

if not result.passed and state["retry_count"] >= MAX_RETRIES:
    state["status"] = "max_retries_reached"
    state["errors"].append(f"Max retries ({MAX_RETRIES}) reached. Saving best attempt.")
```

---

### 7. `gap_bridger_node.py`

**Model:** `llama-3.3-70b-versatile`
**Input:** `evaluation_result.missing_topics`, `evaluation_result.diagram_issues`, `student_notes`, `tutor_notes`, `research_data`
**Output:** Updated `student_notes`, updated `tutor_notes` (surgical merge — no full regen)
**Routes to:** `evaluator` directly (skips StudentNotesCreator and TutorNotesCreator entirely)

**Logic — 3 Steps:**

**Step 1 — Generate gap content:**
```
You are a content gap filler for educational notes.

MISSING TOPICS: {missing_topics}
DIAGRAM ISSUES: {diagram_issues}
ORIGINAL RESEARCH DATA: {research_data}

For each missing topic, generate:
1. A comprehensive explanation with examples
2. A Mermaid.js diagram using ONLY these dark theme colors:
   fills: #1a1a2e, #16213e, #0f3460, #312e81, #4c1d95, #1e3a5f
   strokes: #7c3aed, #2563eb, #d946ef, #8b5cf6, #10b981, #f59e0b, #3b82f6
   text: always #e2e8f0
3. 2-3 key takeaway points

For each diagram issue, generate ONLY the corrected Mermaid block.

Output ONLY clean markdown sections using the same emoji + heading style.
Do NOT include any preamble or explanation.
```

**Step 2 — Identify insertion point in student notes:**
```
You are a markdown editor. Given existing notes and new content sections, 
identify WHERE each new section should be inserted.

EXISTING STUDENT NOTES:
{student_notes}

NEW CONTENT SECTIONS:
{gap_content}

For each new section, return ONLY a JSON array:
[
  {
    "insert_after": "## 2. 📊 Machine Learning vs Deep Learning",  // exact heading to insert after
    "content": "## 3. 🔴 {Missing Topic}\n..."                    // the new markdown section
  }
]
```

**Step 3 — Merge into both notes:**
```python
# Python merge logic (no LLM needed for actual string insertion)
def merge_sections(existing_notes: str, insertions: list[dict]) -> str:
    for item in insertions:
        anchor = item["insert_after"]
        new_section = item["content"]
        if anchor in existing_notes:
            existing_notes = existing_notes.replace(
                anchor,
                anchor + "\n\n---\n\n" + new_section
            )
    return existing_notes

# Apply to student notes
state["student_notes"] = merge_sections(state["student_notes"], insertions)

# For tutor notes — same merge, but wrap new sections with teaching annotations
# Use LLM to add teaching annotations to the new sections only
annotated_gap = add_tutor_annotations(gap_content)  # small LLM call
state["tutor_notes"] = merge_sections(state["tutor_notes"], annotated_insertions)
```

**Key benefit:** StudentNotesCreator and TutorNotesCreator are called exactly ONCE.
GapBridger handles all subsequent fixes surgically and routes straight to Evaluator.

---

### 8. `final_response_node.py`

**Model:** `llama-3.1-8b-instant`
**Input:** `student_notes`, `tutor_notes`, `student_filename`, `tutor_filename`, `session_id`
**Output:** `output_files`, `final_summary`, `status = "completed"`

**Logic:**
```python
# Save files to current working directory
import pathlib

def save_notes(state: GraphState) -> GraphState:
    cwd = pathlib.Path.cwd()
    
    student_path = cwd / state["student_filename"]
    tutor_path = cwd / state["tutor_filename"]
    
    student_path.write_text(state["student_notes"], encoding="utf-8")
    tutor_path.write_text(state["tutor_notes"], encoding="utf-8")
    
    state["output_files"] = [str(student_path), str(tutor_path)]
    state["status"] = "completed"
    
    # Generate a short summary (small model)
    state["final_summary"] = f"Generated {state['student_filename']} and {state['tutor_filename']} for topic: {state['planner_output'].topic}"
    
    return state
```

---

## 🌐 FastAPI Endpoints (`api/routes.py`)

### POST `/generate` — Start note generation

```
Request:
{
  "topic": "Python Decorators and Context Managers",
  "session_id": "optional-custom-id"  // auto-generated if not provided
}

Response (immediate — async job started):
{
  "session_id": "abc123",
  "status": "running",
  "message": "Note generation started. Poll /status/{session_id} for updates."
}
```

### GET `/status/{session_id}` — Poll job status

```
Response:
{
  "session_id": "abc123",
  "status": "running" | "awaiting_tutor" | "completed" | "failed" | "max_retries_reached",
  "current_node": "student_notes",
  "retry_count": 1,
  "tutor_question": null | "Please verify this plan: ...",
  "output_files": [],
  "errors": []
}
```

### POST `/tutor/respond/{session_id}` — Tutor posts verification/response

```
Request:
{
  "approved": true,
  "feedback": "Looks good! Please also add 'metaclasses' to the keywords.",
  "response_to": "plan_verification" | "error_clarification"
}

Response:
{
  "session_id": "abc123",
  "message": "Tutor response received. Resuming generation.",
  "status": "running"
}
```

### GET `/result/{session_id}` — Get completed results

```
Response:
{
  "session_id": "abc123",
  "status": "completed",
  "topic": "Python Decorators",
  "student_file": "python_decorators_student.md",
  "tutor_file": "python_decorators_tutor.md",
  "evaluation_score": { "student": 92, "tutor": 88 },
  "retry_count": 1,
  "used_web_search": false,
  "summary": "Generated notes covering 9/10 keywords with 5 Mermaid diagrams."
}
```

### GET `/health` — Health check

---

## 📊 Groq Client (`services/groq_client.py`)

```python
from groq import Groq
import os

MODELS = {
    "small": "llama-3.1-8b-instant",
    "large": "llama-3.3-70b-versatile",
    "reasoning": "deepseek-r1-distill-llama-70b",
}

class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    def complete(self, prompt: str, size: str = "large", system: str = "", 
                 temperature: float = 0.7, max_tokens: int = 8192) -> str:
        model = MODELS[size]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
```

---

## 📝 Output Format Reference — Real Example Files

The LLMs use the actual files in `examples/` as few-shot references — not a skeleton.
Do NOT delete or modify these files. They are the ground truth for style, tone,
diagram colors, section order, and annotation format.

| File | Purpose |
|---|---|
| `examples/day1_student_notes.md` | Student notes style reference injected into StudentNotesCreator prompt |
| `examples/day1_tutor_notes.md` | Tutor guide style reference injected into TutorNotesCreator prompt |

**To set up:** Copy both files from your desktop into the `examples/` folder before running:

```bash
cp "/Users/pridhvi/Desktop/GenAI_Teaching/Day 1 — Student_Introduction to Generative AI.md" \
   examples/day1_student_notes.md

cp "/Users/pridhvi/Desktop/GenAI_Teaching/Day 1 — Tutors_AnnotatedGuide.md" \
   examples/day1_tutor_notes.md
```

The app will throw a clear `FileNotFoundError` with instructions if these files are missing.

---

## ⚙️ Implementation Notes for Cursor

1. **Start with the state schema and graph builder** — get the skeleton working before nodes.

2. **Use `asyncio.Queue` or an in-memory dict** to store session states for polling (no database needed for MVP).

3. **ConsultTutor timeout:** Use `asyncio.wait_for` with a 5-minute timeout. If tutor doesn't respond, auto-approve.

4. **Mermaid validation:** Write a simple regex-based validator in `utils/helpers.py` that checks for:
   - Opening ` ```mermaid ` and closing ` ``` `
   - A valid graph type keyword on the first line
   - At least one `-->` or `->` arrow
   - `style` declarations

5. **LangGraph interrupt for ConsultTutor:** Use LangGraph's `interrupt()` mechanism to pause the graph at `consult_tutor` and resume it when `POST /tutor/respond/{session_id}` is called.

6. **Error handling:** Every node should wrap its logic in try/except. On error, append to `state["errors"]` and trigger `ConsultTutorNode` with the error details.

7. **Tavily:** Use `tavily.search(query=keyword, max_results=3)` per keyword. Limit to 3 web searches total to control latency.

8. **Temperature settings:**
   - PlannerNode: `temperature=0.1` (deterministic JSON)
   - ResearchNode: `temperature=0.3` (factual)
   - NotesCreators: `temperature=0.7` (creative but consistent)
   - EvaluatorNode: `temperature=0.1` (deterministic scoring)

9. **Max tokens:**
   - Notes creators: `max_tokens=8192` (long-form content)
   - Planner/Evaluator: `max_tokens=1024`

10. **File naming convention:**
    - `{topic_slug}_student.md` — topic slug is lowercase, underscored
    - `{topic_slug}_tutor.md`
    - Both saved to `Path.cwd()`

---

## 📦 `requirements.txt`

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

---

## 🚀 Run the App

```bash
# Install dependencies
pip install -r requirements.txt

# Add your API keys to .env
cp .env.example .env

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Quick Test Flow

```bash
# 1. Start generation
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python Decorators and Context Managers"}'

# 2. Check status (returns tutor_question if waiting)
curl http://localhost:8000/status/abc123

# 3. Tutor verifies the plan
curl -X POST http://localhost:8000/tutor/respond/abc123 \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "", "response_to": "plan_verification"}'

# 4. Poll until completed
curl http://localhost:8000/status/abc123

# 5. Get result
curl http://localhost:8000/result/abc123
```

---

*Built with LangGraph + FastAPI + Groq | Agentic AI Notes Generator v1.0*
