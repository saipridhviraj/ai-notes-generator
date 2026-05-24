# Tests

| Directory | Scope | External deps |
|-----------|--------|---------------|
| `unit/` | Nodes, utils, services, prompts | Mocked Groq/Tavily |
| `integration/` | FastAPI routes (`httpx` TestClient) | In-memory SQLite |
| `e2e/` | Full pipeline smoke | Ollama (optional) |

```bash
pytest tests/ -v                         # default: unit + integration
pytest tests/unit -v                     # unit only
pytest tests/integration -v              # API layer
pytest tests/e2e -m e2e -v --no-cov      # e2e (slow)
```

Fixtures live in `conftest.py`. Coverage target: **≥ 80%** (see `pytest.ini`).
