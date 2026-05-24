# /arch — System Architect

**Activates:** System Architect agent

## Agent Activation Prompt

You are now the **System Architect** for `ai-notes-generator`. Conduct an architecture review immediately.

1. Read `graph/graph_builder.py`, `graph/state.py`, `utils/helpers.py`, `services/file_service.py`
2. Map the current module boundaries and data flow
3. Identify the architectural issues listed in your briefing
4. Produce an Architecture Review Document (ARD)

## Critical issues to find and assess
- In-memory session store lost on restart → evaluate Redis or SQLite-backed MemorySaver
- Output path uses `Path.cwd()` → should be `generated_notes/{slug}/`
- `utils/helpers.py` is a god module — session store + validators + string utils all mixed
- Gap bridger has inline prompt strings — violates node/prompt separation pattern
- Duplicate `slugify` and `strip_json_fences` across modules

## Output format
```
SYSTEM ARCHITECT REVIEW
Status: ✅ APPROVED / ❌ CHANGES REQUIRED / 🔄 REVIEW IN PROGRESS

CRITICAL FINDINGS
- [finding] → [recommendation]

DESIGN IMPROVEMENTS
- [smell] → [fix]

APPROVED PATTERNS
- [pattern that should stay]
```

## Full briefing
→ `.cursor/rules/03-system-architect.mdc`
