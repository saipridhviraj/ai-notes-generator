# Phase 7 — Utilities

**Goal:** Implement `utils/helpers.py` — shared utility functions used across multiple modules. This includes the in-memory session store, Mermaid validator, slug generator, graph config helper, and timeout tracker.

---

## Task 7.1 — `utils/helpers.py`

### Imports

```python
import re
import time
import uuid
import asyncio
from typing import Dict, Any, Optional
```

---

### Session Store

```python
# In-memory dict keyed by session_id
# Each entry: {"state": dict, "task": asyncio.Task | None, "current_node": str, "start_time": float}
session_store: Dict[str, Dict[str, Any]] = {}

def get_session(session_id: str) -> Optional[dict]:
    return session_store.get(session_id)

def set_session(session_id: str, data: dict) -> None:
    session_store[session_id] = data

def create_session(session_id: str, initial_state: dict) -> None:
    session_store[session_id] = {
        "state": initial_state,
        "task": None,
        "current_node": "planner",
        "start_time": time.time(),
    }
```

---

### Graph Config Helper

```python
def get_graph_config(session_id: str) -> dict:
    """Returns the LangGraph thread config for a given session."""
    return {"configurable": {"thread_id": session_id}}
```

---

### Session ID Generator

```python
def generate_session_id() -> str:
    return str(uuid.uuid4())
```

---

### Slug Generator

```python
def slugify(text: str) -> str:
    """Convert a topic string to a filesystem-safe lowercase slug.

    Examples:
        "Python Decorators & Context Managers" -> "python_decorators_context_managers"
        "Generative AI — Transformers"         -> "generative_ai_transformers"
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # replace non-word chars with space
    text = re.sub(r"\s+", "_", text.strip()) # collapse whitespace to underscore
    text = re.sub(r"_+", "_", text)          # collapse multiple underscores
    return text.strip("_")
```

---

### ConsultTutor Timeout Checker

```python
TUTOR_TIMEOUT_SECONDS = 300  # 5 minutes

def is_tutor_timed_out(session_id: str) -> bool:
    """Returns True if the session has been awaiting tutor input for > 5 minutes."""
    session = get_session(session_id)
    if session is None:
        return False
    elapsed = time.time() - session.get("start_time", time.time())
    return elapsed > TUTOR_TIMEOUT_SECONDS
```

---

### Mermaid Diagram Validator

Used by `EvaluatorNode` to pre-check diagram blocks before sending to the LLM evaluator.

```python
VALID_GRAPH_TYPES = [
    "graph TD", "graph LR", "graph TB", "graph RL", "graph BT",
    "flowchart TD", "flowchart LR", "flowchart TB",
    "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
    "erDiagram", "gantt", "pie", "mindmap",
]

APPROVED_FILL_COLORS = {
    "#1a1a2e", "#16213e", "#0f3460", "#312e81", "#4c1d95", "#1e3a5f",
}

APPROVED_STROKE_COLORS = {
    "#7c3aed", "#2563eb", "#0891b2", "#d946ef",
    "#8b5cf6", "#10b981", "#f59e0b", "#3b82f6",
}


def validate_mermaid_block(block: str) -> list[str]:
    """Validate a single Mermaid diagram block.

    Args:
        block: The content between ```mermaid and ``` fences (without the fences).

    Returns:
        A list of issue strings. Empty list means the block is valid.
    """
    issues = []
    lines = block.strip().splitlines()

    if not lines:
        issues.append("Empty mermaid block")
        return issues

    # Check graph type declaration on first line
    first_line = lines[0].strip()
    if not any(first_line.startswith(gt) for gt in VALID_GRAPH_TYPES):
        issues.append(f"Invalid or missing graph type on first line: '{first_line}'")

    # Check for at least one arrow
    has_arrow = any("-->" in line or "->" in line or "---" in line for line in lines)
    if not has_arrow:
        issues.append("No arrows found (-->, ->, or ---)")

    # Check for style declarations
    has_style = any(line.strip().startswith("style ") for line in lines)
    if not has_style:
        issues.append("No 'style' declarations found — all nodes must have explicit styles")

    # Check text color
    if "#e2e8f0" not in block:
        issues.append("Text color #e2e8f0 not found — all node text must use #e2e8f0")

    # Check unclosed brackets (simple heuristic)
    open_brackets = block.count("[") - block.count("]")
    open_parens   = block.count("(") - block.count(")")
    if open_brackets != 0:
        issues.append(f"Unbalanced square brackets: {open_brackets} unclosed")
    if open_parens != 0:
        issues.append(f"Unbalanced parentheses: {open_parens} unclosed")

    return issues


def extract_mermaid_blocks(markdown: str) -> list[str]:
    """Extract all mermaid block contents from a markdown string."""
    pattern = r"```mermaid\n(.*?)```"
    return re.findall(pattern, markdown, re.DOTALL)


def validate_all_mermaid_in_notes(markdown: str) -> list[str]:
    """Run validate_mermaid_block on every mermaid block in a markdown string.

    Returns a flat list of all issues found across all blocks.
    """
    all_issues = []
    blocks = extract_mermaid_blocks(markdown)
    if not blocks:
        all_issues.append("No Mermaid diagrams found — minimum 4 required")
        return all_issues
    if len(blocks) < 4:
        all_issues.append(f"Only {len(blocks)} Mermaid diagram(s) found — minimum 4 required")
    for i, block in enumerate(blocks):
        block_issues = validate_mermaid_block(block)
        for issue in block_issues:
            all_issues.append(f"Diagram {i+1}: {issue}")
    return all_issues
```

---

### JSON Fence Stripper

Used by `GroqClient.complete_json` to clean LLM responses that wrap JSON in markdown fences.

```python
def strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers from LLM output."""
    text = text.strip()
    # Remove ```json or ``` opening fence
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    # Remove ``` closing fence
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()
```

---

**Acceptance criteria:**
- `slugify("Python Decorators & Context Managers")` → `"python_decorators_context_managers"`.
- `validate_mermaid_block("graph TD\nA-->B\nstyle A fill:#1a1a2e,color:#e2e8f0")` → `[]` (no issues).
- `validate_all_mermaid_in_notes(markdown_with_2_diagrams)` → includes minimum diagram count warning.
- `strip_json_fences('```json\n{"a": 1}\n```')` → `'{"a": 1}'`.
- `is_tutor_timed_out(fresh_session_id)` → `False` immediately after creation.
