# AI Notes Generator

An agentic AI backend that generates structured student and tutor Markdown notes using **LangGraph**, **Groq**, and **Tavily**. A lightweight React dashboard lets you trigger generation and respond to tutor review prompts.

---

## Contents

- [Architecture overview](#architecture-overview)
- [Codebase map](docs/CODEBASE.md) — module layout, diagram modes, where to add code
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Running with Docker](#running-with-docker)
- [API reference](#api-reference)
- [Frontend dashboard](#frontend-dashboard)
- [Running tests](#running-tests)
- [Configuration](#configuration)
- [Known limitations](#known-limitations)

---

## Architecture overview

```
User → POST /generate
         │
         ▼
    [planner]         — LLM extracts topic, keywords, subtopics
         │
         ▼
    [consult_tutor]   — Pauses graph; waits for POST /tutor/respond
         │  ◄── human approves or rejects
         │
    (approved)        (rejected → END, status: "rejected")
         │
         ▼
    [research]        — Tavily web search (if needs_web_search=True)
         │
         ▼
    [student_notes]   — Generates student Markdown notes
         │
         ▼
    [tutor_notes]     — Generates annotated tutor notes
         │
         ▼
    [evaluator]       — Scores notes; validates Mermaid diagrams
         │
    (passed=False, retry < max)
         │
         ▼
    [gap_bridger]     — Fills missing topics, fixes diagrams
         │
         └─► [evaluator] (loops until passed or max retries)
         │
    (passed=True or max retries)
         │
         ▼
    [final_response]  — Saves Markdown to generated_notes/<topic_slug>/
         │
         ▼
       END
```

---

## Prerequisites

- Python 3.11+
- [Groq API key](https://console.groq.com)
- [Tavily API key](https://tavily.com)

---

## Quick start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ai-notes-generator

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your real API keys

# 5. Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at `http://localhost:8000`. Visit `/docs` for the auto-generated OpenAPI UI.

---

## Running with Docker

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Generated notes are persisted in the `notes_data` Docker volume and survive container restarts.

---

## API reference

All mutating endpoints require the `X-API-Key` header. Set `APP_API_KEY` in `.env`.

### Start note generation

```
POST /generate
X-API-Key: <your-key>
Content-Type: application/json

{ "topic": "Python Decorators" }
```

**Response:**
```json
{
  "session_id": "f47ac10b-...",
  "status": "running",
  "message": "Note generation started. Poll /status/{session_id} for updates."
}
```

### Poll status

```
GET /status/{session_id}
```

**Possible statuses:** `running`, `awaiting_tutor`, `completed`, `failed`, `max_retries_reached`, `rejected`

### Respond as tutor

When status is `awaiting_tutor`:

```
POST /tutor/respond/{session_id}
X-API-Key: <your-key>
Content-Type: application/json

{ "approved": true, "feedback": "Add more on closures" }
```

To reject a plan:

```json
{ "approved": false, "feedback": "Topic is out of scope" }
```

### Get final result

```
GET /result/{session_id}
```

### Health check

```
GET /health
```

---

## Frontend dashboard

```bash
cd frontend
npm install
npm run dev      # starts on http://localhost:5173
```

Create `frontend/.env.local`:
```
VITE_API_KEY=your_secret_api_key
```

The Vite dev server proxies all API calls to `http://localhost:8000`.

---

## Running tests

```bash
pip install pytest pytest-asyncio pytest-cov httpx

pytest tests/ --tb=short --cov=. --cov-report=term-missing
```

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes (Groq mode) | — | Groq API key |
| `USE_OLLAMA` | No | `false` | Set `true` to use local Ollama instead of Groq |
| `USE_PRODUCTION_PROMPTS` | No | auto | `true` = full prompts; auto-on with Ollama |
| `PROMPT_PROFILE` | No | auto | `dev` or `production` (alternative to above) |
| `DEV_NOTE_MAX_TOKENS` | No | `2048` | Max tokens per note call in dev profile |
| `PRODUCTION_NOTE_MAX_TOKENS` | No | `8192` | Max tokens per note call in production profile |
| `LLM_PROVIDER` | No | `groq` | `groq` or `ollama` (alternative to `USE_OLLAMA`) |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `qwen2.5:14b-instruct-q4_K_M` | Model tag from `ollama list` |
| `OLLAMA_NUM_CTX` | No | `8192` | Context window (lower if RAM is tight) |
| `OLLAMA_TIMEOUT` | No | `600` | Seconds to wait per LLM call |
| `TAVILY_API_KEY` | Yes | — | Tavily search API key |
| `APP_API_KEY` | Yes (production) | — | API auth key — set `X-API-Key` header to this value |
| `MAX_EVAL_RETRIES` | No | `3` | Max evaluation + gap-bridger loops |
| `APP_HOST` | No | `0.0.0.0` | Uvicorn host |
| `APP_PORT` | No | `8000` | Uvicorn port |

### Switch to local Ollama

Add to `.env` (one-line toggle):

```bash
USE_OLLAMA=true
OLLAMA_MODEL=qwen2.5:14b-instruct-q4_K_M
```

This also switches to **production prompts** automatically (full few-shot examples, no truncation, 8192 max tokens). Prompt files live in `prompts/profiles/dev/` and `prompts/profiles/production/`.

Force dev prompts on Ollama (for testing):

```bash
USE_PRODUCTION_PROMPTS=false
```

Keep Ollama running (`ollama serve` or the Ollama app). Switch back to Groq by setting `USE_OLLAMA=false` or removing the line. No code changes needed — all nodes use the same `groq_client` interface.

---

## Known limitations

See **[docs/known-limitations.md](docs/known-limitations.md)** for the full register.

| # | Limitation | Impact | Plan |
|---|-----------|--------|------|
| 1 | LangGraph checkpoints | `SqliteSaver` at `data/checkpoints.db` | ✅ v1.1 |
| 2 | Rate limiting | `slowapi` on generate/tutor/course actions | ✅ v1.1 |
| 3 | CORS allowlist | Set `CORS_ORIGINS` for non-localhost deploys | ✅ Configured in `main.py` |
| 4 | Jobs die on restart | Interrupted banner + restart/resume endpoints | ✅ v1.2 mitigated |
| 5 | No browser E2E in CI | Manual checklist: `docs/manual-e2e-checklist.md` | ⬜ Pending sign-off |
| 6 | Dev prompts on Groq free tier | Use Ollama + production profile | 🟡 See `production_backlog.md` |
