"""Validate diagram JSON specs and compile to guaranteed-valid Mermaid flowcharts."""

from __future__ import annotations

import re

ALLOWED_TYPES = frozenset({"process", "input", "output", "database", "decision"})
ALLOWED_COLORS = frozenset({"blue", "purple", "green", "orange", "red"})
ALLOWED_LAYOUTS = frozenset({"LR", "TD"})
MIN_NODES = 4
MIN_EDGES = 3

_COLOR_STYLES: dict[str, tuple[str, str]] = {
    "blue": ("#16213e", "#2563eb"),
    "purple": ("#1a1a2e", "#7c3aed"),
    "green": ("#0f3460", "#10b981"),
    "orange": ("#1e3a5f", "#f59e0b"),
    "red": ("#312e81", "#ef4444"),
}

_ICON_PREFIX: dict[str, str] = {
    "user": "User",
    "search": "Search",
    "database": "Data",
    "bot": "AI",
    "process": "Step",
    "input": "In",
    "output": "Out",
    "decision": "Choice",
}


def _word_count(label: str) -> int:
    return len(re.findall(r"\w+", label or ""))


def validate_diagram_spec(spec: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(spec, dict):
        return ["Diagram spec must be a JSON object"]

    layout = str(spec.get("layout", "TD")).upper()
    if layout not in ALLOWED_LAYOUTS:
        issues.append(f"layout must be LR or TD, got '{layout}'")

    nodes = spec.get("nodes")
    edges = spec.get("edges")
    if not isinstance(nodes, list):
        issues.append("nodes must be an array")
        return issues
    if not isinstance(edges, list):
        issues.append("edges must be an array")
        return issues

    if len(nodes) < MIN_NODES:
        issues.append(f"Need at least {MIN_NODES} nodes, got {len(nodes)}")
    if len(edges) < MIN_EDGES:
        issues.append(f"Need at least {MIN_EDGES} edges, got {len(edges)}")

    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            issues.append(f"Node {i + 1} must be an object")
            continue
        nid = str(node.get("id", "")).strip()
        if not nid:
            issues.append(f"Node {i + 1} missing id")
            continue
        node_ids.add(nid)
        label = str(node.get("label", "")).strip()
        if not label:
            issues.append(f"Node {nid} missing label")
        elif _word_count(label) > 3:
            issues.append(f"Node {nid} label exceeds 3 words: '{label}'")
        if ":" in label:
            issues.append(f"Node {nid} label must not contain colons")
        ntype = str(node.get("type", "")).strip()
        if ntype not in ALLOWED_TYPES:
            issues.append(f"Node {nid} invalid type '{ntype}'")
        color = str(node.get("color", "")).strip().lower()
        if color not in ALLOWED_COLORS:
            issues.append(f"Node {nid} invalid color '{color}'")

    connected: set[str] = set()
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"Edge {i + 1} must be an object")
            continue
        src = str(edge.get("source", "")).strip()
        tgt = str(edge.get("target", "")).strip()
        if src not in node_ids:
            issues.append(f"Edge source '{src}' not in nodes")
        if tgt not in node_ids:
            issues.append(f"Edge target '{tgt}' not in nodes")
        connected.update({src, tgt})

    isolated = node_ids - connected
    if node_ids and isolated:
        issues.append(f"Isolated nodes: {', '.join(sorted(isolated)[:6])}")

    return issues


def _display_label(node: dict) -> str:
    label = str(node.get("label", "")).strip()
    label = re.sub(r'["\\]', "", label)
    label = re.sub(r"\s{2,}", " ", label)
    return label[:48] or "Node"


def compile_diagram_to_mermaid(spec: dict) -> str:
    """Compile validated JSON spec to Mermaid flowchart (raises ValueError if invalid)."""
    issues = validate_diagram_spec(spec)
    if issues:
        raise ValueError("; ".join(issues[:4]))

    layout = str(spec.get("layout", "TD")).upper()
    if layout not in ALLOWED_LAYOUTS:
        layout = "TD"

    lines = [f"flowchart {layout}", ""]
    for node in spec["nodes"]:
        nid = str(node["id"]).strip()
        lines.append(f'{nid}["{_display_label(node)}"]')

    lines.append("")
    for edge in spec["edges"]:
        src = str(edge["source"]).strip()
        tgt = str(edge["target"]).strip()
        elabel = str(edge.get("label", "")).strip()
        elabel = re.sub(r'["\\]', "", elabel)
        if elabel and _word_count(elabel) <= 3:
            lines.append(f'{src} -->|"{elabel}"| {tgt}')
        else:
            lines.append(f"{src} --> {tgt}")

    lines.append("")
    for node in spec["nodes"]:
        nid = str(node["id"]).strip()
        color = str(node.get("color", "purple")).lower()
        fill, stroke = _COLOR_STYLES.get(color, _COLOR_STYLES["purple"])
        lines.append(
            f"style {nid} fill:{fill},stroke:{stroke},stroke-width:2px,color:#e2e8f0"
        )

    return "\n".join(lines).strip() + "\n"


def spec_to_mermaid_block(spec: dict) -> str:
    return f"```mermaid\n{compile_diagram_to_mermaid(spec)}```"


def wrap_after_heading(heading: str, spec: dict) -> str:
    return f"<!-- after: {heading} -->\n\n{spec_to_mermaid_block(spec)}\n"


def wrap_replace_index(index: int, spec: dict) -> str:
    return f"<!-- replace: {index} -->\n\n{spec_to_mermaid_block(spec)}\n"
