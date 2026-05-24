"""Fix common LLM Mermaid mistakes so diagrams render in Mermaid v11."""

from __future__ import annotations

import re

# Characters that break unquoted flowchart node labels in Mermaid v11.
_RISKY_LABEL_CHARS = re.compile(r'[:()#;,|]')

_FLOWCHART_HEADERS = ("flowchart TD", "flowchart LR", "flowchart TB", "graph TD", "graph LR", "graph TB")
_DIAGRAM_TYPE_PREFIXES = (
    "flowchart ",
    "graph ",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
)
_FLOWCHART_ONLY = True  # pipeline policy: teaching notes use flowcharts only
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F600-\U0001F64F"
    "]+",
    flags=re.UNICODE,
)
_DEFAULT_NODE_STYLE = "fill:#1a1a2e,stroke:#7c3aed,stroke-width:2px,color:#e2e8f0"
_QUOTED_NODE_RE = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\["')
_STYLE_NODE_RE = re.compile(r"^\s*style\s+(\w+)", re.MULTILINE)
_EDGE_SOURCE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*-->")
_EDGE_TARGET_RE = re.compile(r'-->\s*(?:\|?"[^"]*"\|?\s*)?([A-Za-z][A-Za-z0-9_]*)\b')


def _subgraph_ids(block: str) -> set[str]:
    return set(re.findall(r"^\s*subgraph\s+(\w+)", block, re.MULTILINE))


def strip_invalid_content(block: str) -> str:
    """Remove accidental markdown fences, HTML comments, and prose lines."""
    if not block:
        return block
    cleaned: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if stripped.startswith("```"):
            continue
        if stripped.startswith("<!--") and "-->" in stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("##"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def auto_quote_all_labels(block: str) -> str:
    """Quote every unquoted rectangular node label."""

    def repl(match: re.Match[str]) -> str:
        node_id, label = match.group(1), match.group(2)
        escaped = label.replace('"', "#quot;")
        return f'{node_id}["{escaped}"]'

    return re.sub(r"(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]\"\n]+)\]", repl, block)


def ensure_flowchart_header(block: str) -> str:
    """Ensure first line is flowchart TD/LR; upgrade graph * → flowchart *."""
    text = (block or "").strip()
    if not text:
        return "flowchart TD\n"

    lines = text.splitlines()
    first = lines[0].strip()
    if any(first.startswith(header) for header in _FLOWCHART_HEADERS):
        if first.startswith("graph "):
            lines[0] = first.replace("graph ", "flowchart ", 1)
        return "\n".join(lines)

    return "flowchart TD\n" + text


def _collect_node_ids(block: str) -> set[str]:
    ids = set(_QUOTED_NODE_RE.findall(block))
    ids.update(_EDGE_SOURCE_RE.findall(block))
    ids.update(_EDGE_TARGET_RE.findall(block))
    return ids


def ensure_node_styles(block: str) -> str:
    """Append default style lines for nodes missing explicit styles."""
    styled = set(_STYLE_NODE_RE.findall(block))
    subgraphs = _subgraph_ids(block)
    missing = sorted(n for n in _collect_node_ids(block) if n not in styled and n not in subgraphs)
    if not missing:
        return block
    additions = "\n".join(f"style {node_id} {_DEFAULT_NODE_STYLE}" for node_id in missing)
    return block.rstrip() + "\n\n" + additions + "\n"


def _remove_invalid_subgraph_styles(block: str) -> str:
    subgraphs = _subgraph_ids(block)
    if not subgraphs:
        return block
    out_lines: list[str] = []
    for line in block.splitlines():
        style_match = re.match(r"^(\s*style\s+)(\w+)(\s+.+)$", line)
        if style_match and style_match.group(2) in subgraphs:
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def strip_emojis_from_labels(block: str) -> str:
    """Remove emoji from node labels — they often break Mermaid v11 rendering."""

    def repl(match: re.Match[str]) -> str:
        node_id, label = match.group(1), match.group(2)
        cleaned = _EMOJI_RE.sub("", label).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return f'{node_id}["{cleaned}"]'

    return re.sub(r'(\b[A-Za-z][A-Za-z0-9_]*)\["([^"\n]+)"\]', repl, block)


def _diagram_header_lines(block: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for i, line in enumerate(block.splitlines()):
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in _DIAGRAM_TYPE_PREFIXES):
            out.append((i, stripped))
    return out


def dedupe_diagram_headers(block: str) -> str:
    """Keep a single flowchart header; drop mixed sequence/class headers."""
    lines = block.splitlines()
    headers = _diagram_header_lines(block)
    if not headers:
        return block

    flow_idx = next(
        (i for i, h in headers if h.startswith("flowchart ") or h.startswith("graph ")),
        None,
    )
    seq_idx = next((i for i, h in headers if h.startswith("sequenceDiagram")), None)
    if flow_idx is not None and seq_idx is not None:
        # Mixed headers — drop flowchart line so validator flags sequence for repair.
        drop = {i for i, h in headers if h.startswith("flowchart ") or h.startswith("graph ")}
        lines = [line for j, line in enumerate(lines) if j not in drop]
        return "\n".join(lines)

    if flow_idx is not None and len(headers) > 1:
        drop = {i for i, _ in headers if i != flow_idx}
        lines = [line for j, line in enumerate(lines) if j not in drop]
        return "\n".join(lines)

    if len(headers) == 1:
        return block

    # Multiple non-flow headers — keep the last (unlikely)
    keep = headers[-1][0]
    drop = {i for i, _ in headers if i != keep}
    return "\n".join(line for j, line in enumerate(lines) if j not in drop)


def is_non_flowchart_diagram(block: str) -> bool:
    stripped = (block or "").strip()
    if not stripped:
        return False
    first = stripped.splitlines()[0].strip()
    if first.startswith("flowchart ") or first.startswith("graph "):
        return False
    return any(
        token in stripped
        for token in (
            "sequenceDiagram",
            "classDiagram",
            "stateDiagram",
            "erDiagram",
            "participant ",
            "->>",
        )
    )


def normalize_mermaid_block(block: str) -> str:
    """
    Deterministic post-generation fixes before validation.

    Pipeline: strip → dedupe headers → quote labels → strip emojis →
              header → remove invalid subgraph styles → add missing node styles →
              ensure text color on all style lines.
    """
    if not block or not block.strip():
        return block

    if is_non_flowchart_diagram(block):
        # Cannot safely auto-convert sequence/class → flowchart; leave for repair LLM.
        return block.strip() + "\n"

    code = strip_invalid_content(block)
    code = dedupe_diagram_headers(code)
    code = auto_quote_all_labels(code)
    code = strip_emojis_from_labels(code)
    code = ensure_flowchart_header(code)
    code = _remove_invalid_subgraph_styles(code)
    code = ensure_node_styles(code)
    code = ensure_text_color_in_styles(code)  # fix partial styles missing color:#e2e8f0
    return code.strip() + "\n"


def sanitize_mermaid_block(block: str) -> str:
    """Backward-compatible alias — full normalize pass."""
    return normalize_mermaid_block(block)


def sanitize_markdown_mermaid(markdown: str) -> str:
    """Normalize every ```mermaid block in markdown."""
    if not markdown or "```mermaid" not in markdown:
        return markdown

    def repl(match: re.Match[str]) -> str:
        body = match.group(1)
        fixed = normalize_mermaid_block(body)
        if fixed == body:
            return match.group(0)
        return f"```mermaid\n{fixed}\n```"

    return re.sub(r"```mermaid\n(.*?)```", repl, markdown, flags=re.DOTALL)


# Alias used in enforce pipeline docs
normalize_markdown_mermaid = sanitize_markdown_mermaid


def find_unquoted_colon_labels(block: str) -> list[str]:
    """Labels with ':' that are not double-quoted — invalid in Mermaid v11."""
    issues: list[str] = []
    for match in re.finditer(r"(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]\"\n]+)\]", block):
        label = match.group(2)
        if ":" in label:
            issues.append(label)
    return issues


_TEXT_COLOR = "#e2e8f0"
_STYLE_LINE_RE = re.compile(r"^(\s*style\s+\w+\s+fill:[^,\n]+(?:,[^,\n]+)*)$", re.MULTILINE)


def ensure_text_color_in_styles(block: str) -> str:
    """
    Ensure every 'style X fill:...' line has color:#e2e8f0.

    Groq frequently writes style lines without the text color:
      style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px   ← missing!
    This function adds it when absent and corrects it when wrong.
    """
    if not block:
        return block

    def fix_style_line(line: str) -> str:
        stripped = line.strip()
        if not stripped.startswith("style ") or "fill:" not in stripped:
            return line
        if f"color:{_TEXT_COLOR}" in stripped:
            return line  # already correct
        if "color:" in stripped:
            # Wrong text color — replace it
            return re.sub(r"color:#[0-9a-fA-F]{3,8}", f"color:{_TEXT_COLOR}", line)
        # Missing text color entirely — append it
        return line.rstrip() + f",color:{_TEXT_COLOR}"

    return "\n".join(fix_style_line(line) for line in block.splitlines())


def missing_style_node_ids(block: str) -> list[str]:
    """Node IDs referenced in the diagram but without a style line."""
    styled = set(_STYLE_NODE_RE.findall(block))
    subgraphs = _subgraph_ids(block)
    return sorted(n for n in _collect_node_ids(block) if n not in styled and n not in subgraphs)
