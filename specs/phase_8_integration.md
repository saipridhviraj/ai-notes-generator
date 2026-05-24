# Phase 8 — Integration, Examples & Run Guide

**Goal:** Copy the real Day 1 example files into `examples/`, do a full end-to-end smoke test of the running app, and document the complete operational run guide.

---

## Task 8.1 — Copy Example Files

The LLMs use real Day 1 notes as few-shot style references. These MUST be present before starting the server.

```bash
# From the workspace root
cp "/Users/pridhvi/Desktop/GenAI_Teaching/Day 1 — Student_Introduction to Generative AI.md" \
   ai-notes-generator/examples/day1_student_notes.md

cp "/Users/pridhvi/Desktop/GenAI_Teaching/Day 1 — Tutors_AnnotatedGuide.md" \
   ai-notes-generator/examples/day1_tutor_notes.md
```

**Verify:**
```bash
ls -la ai-notes-generator/examples/
# Expected output:
# day1_student_notes.md   (non-empty)
# day1_tutor_notes.md     (non-empty)
```

If these files are missing, the app will raise `FileNotFoundError` with clear instructions on the first request to `/generate`.

---

## Task 8.2 — Install & Run

```bash
cd ai-notes-generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and fill in .env
cp .env.example .env
# Edit .env and set:
#   GROQ_API_KEY=...
#   TAVILY_API_KEY=...

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify startup:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

No `FileNotFoundError` or `ValueError` at startup = examples and API keys are configured correctly.

---

## Task 8.3 — End-to-End Smoke Test (curl)

Run each step in order. Replace `SESSION_ID` with the value returned from Step 1.

### Step 1 — Health check

```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok","version":"1.0.0"}`

---

### Step 2 — Start generation

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python Decorators and Context Managers"}'
```

Expected:
```json
{
  "session_id": "abc123",
  "status": "running",
  "message": "Note generation started. Poll /status/abc123 for updates."
}
```

---

### Step 3 — Poll status (graph pauses here, waiting for tutor)

```bash
curl http://localhost:8000/status/abc123
```

Expected (while awaiting tutor):
```json
{
  "session_id": "abc123",
  "status": "awaiting_tutor",
  "current_node": "consult_tutor",
  "retry_count": 0,
  "tutor_question": "Please verify the following curriculum plan...",
  "output_files": [],
  "errors": []
}
```

---

### Step 4 — Tutor approves the plan

```bash
curl -X POST http://localhost:8000/tutor/respond/abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "feedback": "",
    "response_to": "plan_verification"
  }'
```

Expected:
```json
{
  "session_id": "abc123",
  "message": "Tutor response received. Resuming generation.",
  "status": "running"
}
```

---

### Step 5 — Poll until completed (may take 1–3 minutes)

```bash
# Poll every 10 seconds
watch -n 10 'curl -s http://localhost:8000/status/abc123'
```

Status progression:
- `"running"` → `current_node: "research"`
- `"running"` → `current_node: "student_notes"`
- `"running"` → `current_node: "tutor_notes"`
- `"running"` → `current_node: "evaluator"`
- (if gap detected) `"running"` → `current_node: "gap_bridger"` → `"evaluator"`
- `"completed"`

---

### Step 6 — Get final result

```bash
curl http://localhost:8000/result/abc123
```

Expected:
```json
{
  "session_id": "abc123",
  "status": "completed",
  "topic": "Python Decorators and Context Managers",
  "student_file": "python_decorators_and_context_managers_student.md",
  "tutor_file": "python_decorators_and_context_managers_tutor.md",
  "evaluation_score": {"student": 92, "tutor": 88},
  "retry_count": 0,
  "used_web_search": false,
  "summary": "Generated notes covering 10/10 keywords with 5 Mermaid diagrams."
}
```

---

### Step 7 — Check output files

```bash
ls -la *.md
# python_decorators_and_context_managers_student.md
# python_decorators_and_context_managers_tutor.md
```

Open in any Markdown viewer that supports Mermaid rendering (e.g. VS Code with Mermaid preview extension).

---

## Task 8.4 — Swagger UI

FastAPI auto-generates interactive API docs at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

All 5 endpoints are visible and testable from the browser.

---

## Task 8.5 — Tutor Feedback Scenario

To test keyword injection via tutor feedback:

```bash
curl -X POST http://localhost:8000/tutor/respond/abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "feedback": "Looks good! Please also add metaclasses to the keywords.",
    "response_to": "plan_verification"
  }'
```

Expected behavior: `ConsultTutorNode` detects `"metaclasses"` in the feedback string and appends it to `planner_output.keywords` before proceeding to research.

---

## Task 8.6 — Timeout Scenario

To test auto-approve after 5-minute timeout (for development):
- Temporarily change `TUTOR_TIMEOUT_SECONDS = 10` in `utils/helpers.py`.
- Start a generation and do NOT POST to `/tutor/respond`.
- After 10 seconds, the graph should auto-approve and continue.
- `status` should move from `"awaiting_tutor"` → `"running"` without any tutor POST.

---

## Task 8.7 — Error Scenario

To test graceful error handling:
- Set `GROQ_API_KEY=invalid` in `.env`.
- Restart the server.
- POST to `/generate`.
- Expected: `/status` shows `"status": "failed"` and `"errors": ["PlannerNode failed: ..."]`.

---

## Checklist — Ready to Ship

- [ ] `examples/day1_student_notes.md` exists and is non-empty
- [ ] `examples/day1_tutor_notes.md` exists and is non-empty
- [ ] `.env` has valid `GROQ_API_KEY` and `TAVILY_API_KEY`
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `uvicorn main:app` starts without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `POST /generate` returns a `session_id`
- [ ] Status moves to `"awaiting_tutor"` with a `tutor_question`
- [ ] After `POST /tutor/respond`, status moves to `"running"`
- [ ] Status eventually reaches `"completed"`
- [ ] Two `.md` files are saved to `cwd`
- [ ] Both files have >= 4 Mermaid diagrams each
- [ ] Evaluation scores are >= 80/100 for both notes
