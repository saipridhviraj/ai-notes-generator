import re
import time
import uuid

from services.prompt_config import get_min_mermaid_diagrams
from utils.session_store import (  # noqa: F401
    create_session,
    get_session,
    set_session,
    session_store,
)

TUTOR_TIMEOUT_SECONDS = 300  # 5 minutes

# ── Graph Config ──────────────────────────────────────────────────────────────

def get_graph_config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


# ── ID Generation ─────────────────────────────────────────────────────────────

def generate_session_id() -> str:
    return str(uuid.uuid4())


# ── Slug ──────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


# ── Timeout ───────────────────────────────────────────────────────────────────

def is_tutor_timed_out(session_id: str) -> bool:
    session = get_session(session_id)
    if session is None:
        return False
    elapsed = time.time() - session.get("start_time", time.time())
    return elapsed > TUTOR_TIMEOUT_SECONDS


# ── Mermaid Validator ─────────────────────────────────────────────────────────

VALID_GRAPH_TYPES = [
    "graph TD", "graph LR", "graph TB", "graph RL", "graph BT",
    "flowchart TD", "flowchart LR", "flowchart TB",
]

# Teaching pipeline: only flowchart/graph in student notes (sequence/class break often).
_ALLOWED_STUDENT_DIAGRAM_TYPES = (
    "graph TD", "graph LR", "graph TB", "graph RL", "graph BT",
    "flowchart TD", "flowchart LR", "flowchart TB",
)

_FORBIDDEN_DIAGRAM_MARKERS = (
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram-v2",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "participant ",
    "->>",
)


def validate_mermaid_block(block: str) -> list:
    issues = []
    lines = block.strip().splitlines()

    if not lines:
        issues.append("Empty mermaid block")
        return issues

    first_line = lines[0].strip()
    if not any(first_line.startswith(gt) for gt in _ALLOWED_STUDENT_DIAGRAM_TYPES):
        issues.append(f"Invalid or missing graph type on first line: '{first_line}'")

    header_count = sum(
        1
        for line in lines
        if line.strip()
        and any(line.strip().startswith(prefix) for prefix in (
            "flowchart ", "graph ", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram"
        ))
    )
    if header_count > 1:
        issues.append(
            f"Multiple diagram type headers ({header_count}) — use ONE flowchart TD or flowchart LR line only"
        )

    for marker in _FORBIDDEN_DIAGRAM_MARKERS:
        if marker in block:
            issues.append(
                f"Unsupported Mermaid syntax '{marker.strip()}' — use flowchart TD/LR with A[\"Label\"] nodes only"
            )
            break

    if "<br" in block.lower():
        issues.append("Contains <br/> in label — use short text instead of line breaks")

    has_arrow = any("-->" in line for line in lines)
    if not has_arrow:
        issues.append("No arrows found (-->, ->, or ---)")

    has_style = any(line.strip().startswith("style ") for line in lines)
    if not has_style:
        issues.append("No 'style' declarations found — all nodes must have explicit styles")

    if "#e2e8f0" not in block:
        issues.append("Text color #e2e8f0 not found — all node text must use #e2e8f0")

    open_brackets = block.count("[") - block.count("]")
    open_parens   = block.count("(") - block.count(")")
    if open_brackets != 0:
        issues.append(f"Unbalanced square brackets: {open_brackets} unclosed")
    if open_parens != 0:
        issues.append(f"Unbalanced parentheses: {open_parens} unclosed")

    colon_labels = [
        m.group(2)
        for m in re.finditer(r"(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]\"\n]+)\]", block)
        if ":" in m.group(2)
    ]
    if colon_labels:
        issues.append(
            "Unquoted node labels with ':' break Mermaid v11 — use [\"Label: text\"]: "
            + ", ".join(colon_labels[:3])
        )

    subgraphs = set(re.findall(r"^\s*subgraph\s+(\w+)", block, re.MULTILINE))
    for line in lines:
        style_match = re.match(r"^\s*style\s+(\w+)\s+", line)
        if style_match and style_match.group(1) in subgraphs:
            issues.append(
                f"Cannot style subgraph '{style_match.group(1)}' in Mermaid v11 — style nodes instead"
            )

    from utils.mermaid_sanitize import missing_style_node_ids

    unstyled = missing_style_node_ids(block)
    if unstyled:
        issues.append(
            "Missing style for node(s): " + ", ".join(unstyled[:8])
        )

    return issues


def extract_mermaid_blocks(markdown: str) -> list:
    pattern = r"```mermaid\n(.*?)```"
    return re.findall(pattern, markdown, re.DOTALL)


def extract_mermaid_blocks_indexed(markdown: str) -> list[tuple[int, str]]:
    """Return (1-based index, inner block text) for each ```mermaid fence."""
    pattern = r"```mermaid\n(.*?)```"
    return [(i + 1, m.group(1)) for i, m in enumerate(re.finditer(pattern, markdown or "", re.DOTALL))]


def replace_mermaid_block_by_index(markdown: str, index: int, new_inner: str) -> str:
    """Replace the Nth mermaid block (1-based) with new_inner."""
    if index < 1 or not markdown:
        return markdown

    pattern = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
    matches = list(pattern.finditer(markdown))
    if index > len(matches):
        return markdown

    match = matches[index - 1]
    inner = (new_inner or "").strip()
    replacement = f"```mermaid\n{inner}\n```"
    return markdown[: match.start()] + replacement + markdown[match.end() :]


def validate_all_mermaid_in_notes(markdown: str) -> list:
    all_issues = []
    blocks = extract_mermaid_blocks(markdown)
    min_required = get_min_mermaid_diagrams()

    if not blocks:
        all_issues.append(f"No Mermaid diagrams found — minimum {min_required} required")
        return all_issues

    if len(blocks) < min_required:
        all_issues.append(
            f"Only {len(blocks)} Mermaid diagram(s) found — minimum {min_required} required"
        )

    for i, block in enumerate(blocks):
        for issue in validate_mermaid_block(block):
            all_issues.append(f"Diagram {i + 1}: {issue}")

    return all_issues


def validate_diagrams_in_notes(markdown: str) -> list[str]:
    """Validate JSON+SVG diagram embeds (placeholder pipeline)."""
    from models.diagram_spec import DiagramSpec
    from utils.diagram_placeholders import (
        DIAGRAM_JSON_RE,
        PLACEHOLDER_RE,
        count_diagram_embeds,
        has_unfilled_placeholders,
    )

    text = markdown or ""
    all_issues: list[str] = []
    min_required = get_min_mermaid_diagrams()

    if "```mermaid" in text:
        all_issues.append("Legacy ```mermaid``` blocks found — use diagram-json embeds instead")

    embed_count = count_diagram_embeds(text)
    placeholder_count = len(PLACEHOLDER_RE.findall(text))

    if embed_count == 0 and placeholder_count == 0:
        all_issues.append(f"No diagrams found — minimum {min_required} required")
        return all_issues

    if embed_count < min_required:
        all_issues.append(
            f"Only {embed_count} diagram embed(s) found — minimum {min_required} required"
        )

    if has_unfilled_placeholders(text):
        all_issues.append("Unfilled diagram placeholder(s) — missing diagram-json embed")

    for i, match in enumerate(DIAGRAM_JSON_RE.finditer(text), start=1):
        raw = match.group(1).strip()
        try:
            import json

            spec = json.loads(raw)
            DiagramSpec.model_validate(spec)
        except Exception as exc:
            all_issues.append(f"Diagram {i}: invalid JSON spec — {exc}")

    return all_issues
