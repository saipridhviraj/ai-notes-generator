# Codebase structure

Canonical map for `ai-notes-generator`. Use this when adding features or choosing where code belongs.

---

## Top-level layout

```
ai-notes-generator/
├── main.py                 # FastAPI app entry
├── api/                    # HTTP routes, request/response models, auth
├── graph/                  # LangGraph state, builder, nodes
├── services/               # LLM clients, config, file I/O, publishers
├── prompts/                # All LLM prompt templates (by node + profile)
├── models/                 # Shared Pydantic schemas (diagram spec, events)
├── utils/                  # Pure helpers — no FastAPI, no graph wiring
│   ├── mermaid/            # Mermaid validate / repair / sanitize (default path)
│   └── diagram/            # JSON→SVG pipeline (opt-in, DIAGRAM_PIPELINE=true)
├── tests/
│   ├── unit/               # Nodes, utils, services — mocked LLM/Tavily
│   ├── integration/        # FastAPI routes via httpx TestClient
│   └── e2e/                # Full pipeline smoke (optional, marked e2e)
├── frontend/               # React + Vite tutor dashboard
├── examples/               # Few-shot style references for prompts
├── generated_notes/        # Runtime output (gitignored content)
├── data/                   # SQLite checkpoints + sessions
├── docs/                   # Specs, checklists, this file
├── specs/                  # Product requirements
└── team_logs/              # CEO sprint history
```

---

## Request flow

```
Browser / API client
    → api/routes.py
    → graph/graph_runner.py (async stream)
    → graph/graph_builder.py (compiled LangGraph)
    → graph/nodes/*.py
    → services/groq_client.py (LLM)
    → services/file_service.py (save to generated_notes/)
```

Human-in-the-loop pause happens at `consult_tutor_node` until `POST /tutor/respond`.

---

## Graph nodes (execution order)

| Node | Module | Responsibility |
|------|--------|----------------|
| planner | `graph/nodes/planner_node.py` | Topic → KeywordPlan |
| consult_tutor | `graph/nodes/consult_tutor_node.py` | Plan approval gate |
| research | `graph/nodes/research_node.py` | Tavily + research brief |
| student_notes | `graph/nodes/student_notes_creator.py` | Student markdown + Mermaid enforce |
| diagram_generator | `graph/nodes/diagram_generator_node.py` | **Only if** `DIAGRAM_PIPELINE=true` |
| tutor_notes | `graph/nodes/tutor_notes_creator.py` | Tutor guide |
| evaluator | `graph/nodes/evaluator_node.py` | Quality scores + diagram validation |
| gap_bridger | `graph/nodes/gap_bridger_node.py` | Retry content gaps |
| mermaid_repair | `graph/nodes/mermaid_repair_node.py` | Resume-only diagram repair |
| final_response | `graph/nodes/final_response_node.py` | Write files, publish events |

Default path (8 steps): **no** `diagram_generator`.  
Opt-in path (9 steps): `DIAGRAM_PIPELINE=true`.

---

## Diagram modes (important)

Two separate flags — do not conflate them.

| Flag | Default | Effect |
|------|---------|--------|
| `DIAGRAM_PIPELINE` | `false` | Student notes use inline ` ```mermaid ` blocks |
| `MERMAID_GENERATION_MODE` | `json` | How **supplement/repair** generates diagrams when validation fails |

**Default (recommended for Qwen / local Ollama):**

- LLM writes Mermaid in student notes
- Python validates in `utils/mermaid_enforce.py`
- On failure only: JSON worksheet → `utils/diagram_compiler.py` → valid Mermaid

**Opt-in SVG pipeline** (`DIAGRAM_PIPELINE=true`):

- Placeholders in notes → `utils/diagram_pipeline.py` → SVG + `diagram-json` embeds
- Frontend `DiagramFlow.tsx` renders React Flow

---

## Module ownership

### `api/`

HTTP surface only. No business logic. Delegates to graph runner and session store.

### `graph/nodes/`

One file per LangGraph node. Nodes may call `services/` and `utils/` but **must not** define prompt strings inline — use `prompts/`.

### `prompts/`

| Area | Location |
|------|----------|
| Production profile | `prompts/profiles/production/` |
| Dev / Groq tier | `prompts/profiles/dev/` |
| Mermaid rules | `prompts/mermaid_prompts.py` |
| Diagram JSON (repair) | `prompts/diagram_json_prompts.py` |
| Diagram placeholders (SVG) | `prompts/diagram_rules.py` |

Profile selection: `services/prompt_config.py`.

### `services/`

| Module | Role |
|--------|------|
| `llm_client.py` | Groq + Ollama unified client |
| `prompt_config.py` | Env-driven caps, diagram mode, eval mode |
| `file_service.py` | Examples + `generated_notes/` paths |
| `session_store.py` | HTTP session SQLite |
| `note_ready_publisher.py` | Webhook / outbox for completed notes |

### `utils/` domains

| Domain | Modules | Notes |
|--------|---------|-------|
| **Mermaid** | `mermaid/` package + `mermaid_enforce.py` shim | Default diagram path |
| **Diagram (SVG)** | `diagram/` package + `diagram_*.py` shims | Opt-in pipeline |
| **Validation** | `helpers.py` | Mermaid block validators, slugify, session helpers |
| **Eval** | `fast_eval.py`, `eval_summary.py` | Evaluator helpers |
| **Notes merge** | `tutor_merge.py`, `notes_sections.py`, `student_notes_clean.py` | Tutor supplement merge |
| **Graph UX** | `pipeline_progress.py`, `node_artifacts.py`, `node_lifecycle.py`, `status_events.py` | Progress bar + SSE |
| **Persistence** | `session_store.py`, `course_store.py`, `note_event_outbox.py` | SQLite |
| **Streaming** | `stream_bus.py` | Token + status SSE |

Import convention: prefer domain packages for new code (`from utils.mermaid import ensure_mermaid_diagrams`). Legacy flat imports remain supported via shims.

---

## Frontend

```
frontend/src/
├── api/           # fetch wrappers
├── components/    # StatusPanel, MarkdownDocument, MermaidDiagram, DiagramFlow
├── hooks/         # SSE, session state
├── constants/     # Pipeline step labels
└── types/         # Shared TS types
```

`MermaidDiagram.tsx` — default renderer.  
`DiagramFlow.tsx` — only when notes contain `diagram-json` fences.

---

## Tests

```
tests/
├── conftest.py       # Shared fixtures (app, client, mocks)
├── unit/             # Pure logic, mocked external APIs
├── integration/      # httpx TestClient against FastAPI
└── e2e/              # Full runs; excluded by default (-m "not e2e")
```

Run:

```bash
pytest tests/ -v                    # unit + integration (default)
pytest tests/e2e -m e2e -v          # e2e only (needs Ollama)
pytest tests/unit -v                # unit only
pytest tests/integration -v         # API layer only
```

---

## Configuration

Single source: `.env` → `services/prompt_config.py`.

Key vars for local teaching:

```bash
USE_OLLAMA=true
OLLAMA_MODEL=qwen3.5:9b-q4_K_M
DIAGRAM_PIPELINE=false
MERMAID_GENERATION_MODE=json
USE_PRODUCTION_PROMPTS=true
```

See `.env.example` for full list.

---

## Adding a new graph node

1. Create `graph/nodes/my_node.py` with `def my_node(state: GraphState) -> dict`
2. Register in `graph/graph_builder.py` + `graph/nodes/__init__.py`
3. Add prompts under `prompts/`
4. Add persona in `utils/node_personas.py` + step in `utils/pipeline_progress.py`
5. Unit test in `tests/unit/test_my_node.py`
6. Update this doc and README architecture diagram

---

## Known structural debt (accepted / planned)

| Item | Status | Target |
|------|--------|--------|
| `helpers.py` mixes validators + session utils | 🟡 | Split validators → `utils/mermaid/validate.py` |
| Flat `utils/diagram_*.py` shims | ✅ | Facade via `utils/diagram/` package |
| Groq production prompts on Dev tier | 🟡 | Use Ollama locally until tier upgrade |

See `docs/known-limitations.md` for runtime accepted risks.
