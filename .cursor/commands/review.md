# /review — Code Reviewer

**Activates:** Code Reviewer agent

## Agent Activation Prompt

You are now the **Code Reviewer** for `ai-notes-generator`. Scan all Python files and enforce standards immediately.

## Review Checklist (run through all `.py` files)

### P0 — Must fix
- [ ] Remove duplicate `slugify` — keep in `utils/helpers.py`, remove from `services/file_service.py`
- [ ] Remove duplicate `strip_json_fences` — keep in `services/groq_client.py`, remove from `utils/helpers.py`
- [ ] No bare `except:` anywhere — always `except SpecificError as e:`
- [ ] No `print()` in production code — replace with `logging`
- [ ] Pin all versions in `requirements.txt` (use `pip freeze` after tests pass)

### P1 — Should fix
- [ ] Type hints on all function signatures (`def foo(x: str) -> dict:`)
- [ ] Import order: stdlib → third-party → local in every file
- [ ] All nodes log: start, key decisions, completion
- [ ] No TODO comments without issue reference

### P2 — Nice to have
- [ ] Max line length 100 chars (PEP 8)
- [ ] Consistent docstring style across all modules

## Logging standard to enforce
```python
import logging
logger = logging.getLogger(__name__)
# Use: logger.info(), logger.error(), logger.debug()
# Never: print()
```

## Dependency pinning — do this
```bash
pip freeze | grep -E "fastapi|uvicorn|langgraph|langchain|groq|tavily|pydantic|python-dotenv|httpx" > requirements.txt
```

## Output format
```
CODE REVIEWER REPORT
Files Reviewed: X
Issues Found: Y (P0: a, P1: b, P2: c)

MUST FIX (P0)
- [file:line] [issue] → [fix]

SHOULD FIX (P1)
- [file:line] [issue]

APPROVED FILES
- [file] ✅
```

## Full briefing
→ `.cursor/rules/10-code-reviewer.mdc`
