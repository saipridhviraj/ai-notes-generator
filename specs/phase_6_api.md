# Phase 6 — API Layer

**Goal:** Implement 5 FastAPI endpoints in `api/routes.py`, set up the session store in `utils/helpers.py`, and create the `main.py` entry point that mounts everything.

---

## Task 6.1 — Session Store (in `utils/helpers.py` — built in Phase 7, referenced here)

The session store is an in-memory dict keyed by `session_id`. It holds the live graph state snapshot for polling.

```python
# utils/helpers.py
from typing import Dict, Any
import asyncio

# In-memory store: {session_id: {"state": GraphState, "task": asyncio.Task}}
session_store: Dict[str, Dict[str, Any]] = {}

def get_session(session_id: str) -> dict | None:
    return session_store.get(session_id)

def set_session(session_id: str, data: dict) -> None:
    session_store[session_id] = data

def get_graph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}
```

---

## Task 6.2 — FastAPI Routes (`api/routes.py`)

### Setup

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.models import (
    GenerateRequest, GenerateResponse,
    StatusResponse, TutorRespondRequest, TutorRespondResponse,
    ResultResponse, HealthResponse,
)
from graph import graph
from graph.state import GraphState
from utils.helpers import session_store, get_graph_config, set_session, get_session
import uuid, asyncio

router = APIRouter()
```

---

### Endpoint 1: `POST /generate`

**Purpose:** Start an async note generation job for the given topic.

**Request body:** `GenerateRequest` (`topic`, optional `session_id`)

**Behavior:**
1. Generate `session_id` via `str(uuid.uuid4())` if not provided.
2. Build initial `GraphState`:
   ```python
   initial_state: GraphState = {
       "user_input": request.topic,
       "session_id": session_id,
       "planner_output": None,
       "planner_verified": False,
       "planner_feedback": None,
       "tutor_question": None,
       "tutor_response": None,
       "awaiting_tutor": False,
       "research_data": None,
       "used_web_search": False,
       "student_notes": None,
       "tutor_notes": None,
       "student_filename": None,
       "tutor_filename": None,
       "evaluation_result": None,
       "retry_count": 0,
       "output_files": [],
       "final_summary": None,
       "errors": [],
       "status": "running",
   }
   ```
3. Store session in `session_store`:
   ```python
   set_session(session_id, {"state": initial_state, "task": None, "current_node": "planner"})
   ```
4. Launch background async task:
   ```python
   async def run_graph():
       config = get_graph_config(session_id)
       async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
           # Update session_store with latest state after each node
           node_name = list(event.keys())[0]
           node_output = event[node_name]
           current = get_session(session_id)
           current["state"].update(node_output)
           current["current_node"] = node_name
           set_session(session_id, current)
   
   task = asyncio.create_task(run_graph())
   session_store[session_id]["task"] = task
   ```
5. Return `GenerateResponse(session_id=session_id, status="running", message="Note generation started. Poll /status/{session_id} for updates.")`.

**Response:** `GenerateResponse`

---

### Endpoint 2: `GET /status/{session_id}`

**Purpose:** Poll the current status of an in-progress or completed job.

**Behavior:**
1. Look up `get_session(session_id)`.
2. If not found → raise `HTTPException(status_code=404, detail="Session not found")`.
3. Read `state` from the session.
4. Return:
   ```python
   StatusResponse(
       session_id=session_id,
       status=state["status"],
       current_node=session["current_node"],
       retry_count=state.get("retry_count", 0),
       tutor_question=state.get("tutor_question"),
       output_files=state.get("output_files", []),
       errors=state.get("errors", []),
   )
   ```

**Response:** `StatusResponse`

---

### Endpoint 3: `POST /tutor/respond/{session_id}`

**Purpose:** Tutor submits their verification/feedback to unblock the ConsultTutor node.

**Request body:** `TutorRespondRequest` (`approved`, `feedback`, `response_to`)

**Behavior:**
1. Look up session — 404 if not found.
2. Check `state["status"]` is `"awaiting_tutor"` — raise `HTTPException(400, "Session is not awaiting tutor input")` otherwise.
3. Build response string:
   ```python
   response_text = "approved" if request.approved else f"rejected: {request.feedback}"
   if request.feedback:
       response_text = f"approved with feedback: {request.feedback}"
   ```
4. Update session state:
   ```python
   session["state"]["tutor_response"] = response_text
   session["state"]["status"] = "running"
   set_session(session_id, session)
   ```
5. Resume LangGraph via checkpoint:
   ```python
   config = get_graph_config(session_id)
   task = asyncio.create_task(graph.ainvoke(None, config=config))
   session_store[session_id]["task"] = task
   ```
   Note: passing `None` as input with the same `config` resumes from the last checkpoint.
6. Return `TutorRespondResponse(session_id=session_id, message="Tutor response received. Resuming generation.", status="running")`.

**Response:** `TutorRespondResponse`

---

### Endpoint 4: `GET /result/{session_id}`

**Purpose:** Retrieve the final results once generation is complete.

**Behavior:**
1. Look up session — 404 if not found.
2. Read `state`.
3. Build evaluation score dict if `evaluation_result` is present:
   ```python
   eval_score = None
   if state.get("evaluation_result"):
       eval_score = {
           "student": state["evaluation_result"].student_notes_score,
           "tutor": state["evaluation_result"].tutor_notes_score,
       }
   ```
4. Return:
   ```python
   ResultResponse(
       session_id=session_id,
       status=state["status"],
       topic=state["planner_output"].topic if state.get("planner_output") else None,
       student_file=state.get("student_filename"),
       tutor_file=state.get("tutor_filename"),
       evaluation_score=eval_score,
       retry_count=state.get("retry_count", 0),
       used_web_search=state.get("used_web_search", False),
       summary=state.get("final_summary"),
   )
   ```

**Response:** `ResultResponse`

---

### Endpoint 5: `GET /health`

**Purpose:** Health check for load balancers / uptime monitors.

**Behavior:** Return `HealthResponse(status="ok", version="1.0.0")`.

**Response:** `HealthResponse`

---

## Task 6.3 — Main Entry Point (`main.py`)

```python
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from api.routes import router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: import graph to trigger compilation and example file loading
    from graph import graph  # noqa: F401 — triggers MemorySaver init
    yield
    # Shutdown: nothing to clean up for MVP

app = FastAPI(
    title="AI Notes Generator",
    description="Agentic AI backend for generating student and tutor notes using LangGraph + Groq",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
```

### Running the app

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or via env vars:
```bash
uvicorn main:app \
  --host ${APP_HOST:-0.0.0.0} \
  --port ${APP_PORT:-8000} \
  --reload
```

---

## Endpoint Summary Table

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/generate` | None | Start a new generation job |
| GET | `/status/{session_id}` | None | Poll job status |
| POST | `/tutor/respond/{session_id}` | None | Submit tutor verification |
| GET | `/result/{session_id}` | None | Get completed results |
| GET | `/health` | None | Health check |

**Acceptance criteria:**
- `GET /health` returns `{"status": "ok", "version": "1.0.0"}`.
- `POST /generate` returns a `session_id` and `status: "running"`.
- `GET /status/{unknown_id}` returns HTTP 404.
- `POST /tutor/respond/{id}` on a non-awaiting session returns HTTP 400.
- All endpoints are documented in `/docs` (Swagger UI) automatically by FastAPI.
