# Spec 00 — Project Overview & Tech Stack

## What We Are Building

A **production-ready Agentic AI backend** that accepts a topic (or list of topics) and autonomously generates **two beautifully structured Markdown note files** — one for students and one for tutors — mimicking the style of a professional Generative AI course.

Features:
- Rich Mermaid.js diagrams with a fixed dark-theme color palette
- Emoji headers, blockquote callouts, structured sections, revision questions
- LangGraph stateful agent graph exposed via FastAPI REST API
- Human-in-the-loop ConsultTutor mechanism (tutor verifies the plan before generation)
- Groq-hosted LLMs with model routing by task complexity
- Tavily web search for cutting-edge / rapidly-changing topics
- Evaluation loop with gap-bridging (surgical merge — no full regen on retry)

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Agent Framework | LangGraph (`langgraph`) | 0.2.28 | Stateful node graph orchestration |
| API Layer | FastAPI + Uvicorn | 0.115.0 / 0.30.0 | REST endpoints |
| LLM Provider | Groq API (`groq`) | 0.11.0 | Fast inference on open models |
| Web Search | Tavily (`tavily-python`) | 0.5.0 | Optional research augmentation |
| Data Validation | Pydantic v2 | 2.9.0 | State schema + API models |
| Env Management | python-dotenv | 1.0.1 | API key management |
| File I/O | Python `pathlib` | stdlib | Markdown file output |
| Async | `asyncio` + `httpx` | stdlib / 0.27.0 | Non-blocking I/O |
| LangChain Core | `langchain-core` | 0.3.0 | LangGraph dependency |

---

## Groq Model Assignments (CRITICAL — must not be changed)

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

Model size aliases in `services/groq_client.py`:
- `"small"` → `llama-3.1-8b-instant`
- `"large"` → `llama-3.3-70b-versatile`
- `"reasoning"` → `deepseek-r1-distill-llama-70b`

---

## Temperature & Token Settings

| Node | temperature | max_tokens |
|---|---|---|
| PlannerNode | 0.1 | 1024 |
| ResearchNode (decide) | 0.1 | 64 |
| ResearchNode (synthesize) | 0.3 | 8192 |
| StudentNotesCreator | 0.7 | 8192 |
| TutorNotesCreator | 0.7 | 8192 |
| EvaluatorNode | 0.1 | 1024 |
| GapBridgerNode | 0.7 | 8192 |
| FinalResponseNode | 0.1 | 256 |

---

## Mermaid Color Palette (NON-NEGOTIABLE — used everywhere)

```
fills  : #1a1a2e  #16213e  #0f3460  #312e81  #4c1d95  #1e3a5f
strokes: #7c3aed  #2563eb  #0891b2  #d946ef  #8b5cf6  #10b981  #f59e0b  #3b82f6
text   : always #e2e8f0
```

Every Mermaid node MUST have an explicit `style` declaration using colors from the above palette.
Minimum 4 Mermaid diagrams per generated file.

---

## Phase Map

| Phase | Name | Key Deliverables |
|---|---|---|
| Phase 1 | Foundation | Directory skeleton, `.env`, `requirements.txt`, state schema, Pydantic API models |
| Phase 2 | Services | Groq client, Tavily client, file service |
| Phase 3 | Prompts | All system + user prompt templates for every node |
| Phase 4 | Nodes | All 8 LangGraph node implementations |
| Phase 5 | Graph | Graph builder, routing functions, MemorySaver checkpoint |
| Phase 6 | API | FastAPI routes (5 endpoints), `main.py` entry point |
| Phase 7 | Utils | `helpers.py` — Mermaid validator, slug generator, session store |
| Phase 8 | Integration | Examples setup, end-to-end smoke test, run guide |
