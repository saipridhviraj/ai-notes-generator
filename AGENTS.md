# AGENTS.md — AI Notes Generator

Guide for AI coding agents working in this repository.

## What this project is

FastAPI + LangGraph app that generates paired student/tutor Markdown notes from a topic. Human-in-the-loop plan approval via tutor interrupt. Optional local LLM via Ollama.

## Entry points

| Path | Role |
|------|------|
| `main.py` | FastAPI app, CORS, lifespan |
| `api/routes.py` | REST: `/generate`, `/status`, `/stream`, `/cancel`, `/tutor/respond`, `/result`, `/health` |
| `graph/graph_builder.py` | 8-node LangGraph pipeline |
| `services/llm_client.py` | Groq + Ollama unified client (prefer over `groq_client.py`) |
| `utils/session_store.py` | SQLite HTTP session persistence |
| `utils/stream_bus.py` | In-memory LLM token pub/sub for SSE |
| `frontend/` | Vite + React status UI |

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set GROQ_API_KEY, APP_API_KEY; USE_OLLAMA=true for local LLM
uvicorn main:app --reload
cd frontend && npm install && npm run dev
```

## Tests

```bash
pytest --cov --cov-report=term-missing
```

Target: **≥ 80%** coverage (enforced in CI). Mock `services.groq_client.groq_client` or `services.llm_client.llm_client` in tests — do not call real APIs.

## Conventions

- **LLM imports:** New code → `from services.llm_client import llm_client`. `groq_client` is a backward-compat alias.
- **Sessions:** Use `create_session` / `get_session` / `set_session` from `utils.helpers` (backed by SQLite).
- **Prompts:** Dev vs production profiles in `prompts/profiles/`; controlled by `USE_PRODUCTION_PROMPTS` / Ollama auto.
- **Checkpoints:** LangGraph SqliteSaver at `data/checkpoints.db` (`CHECKPOINT_DB_PATH`).
- **Streaming:** Pass `session_id` + `stream_node` to `llm_client.complete()`; UI subscribes via `GET /stream/{session_id}` (SSE). Toggle with `LLM_STREAMING`.
- **Scope:** Minimal diffs; match existing patterns; no drive-by refactors.

## Virtual team (Cursor)

Slash commands in `.cursor/commands/` route to specialist agents. Task router: `.cursor/rules/00-task-router.mdc`. CEO orchestrator: `.cursor/rules/00-ceo-orchestrator.mdc`.

| Command | Use when |
|---------|----------|
| `/backend` | API, graph nodes, services |
| `/frontend` | React UI |
| `/qa` | Tests, coverage |
| `/sprint` | Multi-agent fix cycle |
| `/status` | Quick snapshot |

## Env vars (common)

See `.env.example`. Key ones: `USE_OLLAMA`, `OLLAMA_MODEL`, `SESSION_DB_PATH`, `LLM_FALLBACK_GROQ`, `LLM_STREAMING`, `CORS_ORIGINS`, `APP_API_KEY`.

## Do not

- Commit `.env` or API keys
- Skip auth on protected routes
- Remove backward-compat `groq_client` re-exports without updating all imports and tests
