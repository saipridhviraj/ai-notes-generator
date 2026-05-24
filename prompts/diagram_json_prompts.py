"""Prompts for JSON diagram structure generation (compiled to Mermaid in Python)."""

from __future__ import annotations

from prompts.common import DIRECT_OUTPUT_RULE

DIAGRAM_JSON_EXAMPLE = """{
  "title": "RAG Workflow",
  "layout": "LR",
  "nodes": [
    {"id": "N1", "label": "User Query", "type": "input", "icon": "user", "color": "blue"},
    {"id": "N2", "label": "Vector Search", "type": "process", "icon": "search", "color": "purple"},
    {"id": "N3", "label": "Knowledge Base", "type": "database", "icon": "database", "color": "green"},
    {"id": "N4", "label": "LLM Response", "type": "output", "icon": "bot", "color": "orange"}
  ],
  "edges": [
    {"source": "N1", "target": "N2", "label": "query"},
    {"source": "N2", "target": "N3", "label": "retrieve"},
    {"source": "N3", "target": "N4", "label": "context"}
  ]
}"""


def get_diagram_json_system_prompt() -> str:
    return f"""You are a diagram structure generator for an educational notes system.

TASK:
Generate ONLY valid JSON describing a diagram structure.

DO NOT generate:
- Mermaid
- explanations
- markdown
- HTML
- code fences
- comments
- React code
- SVG code

OUTPUT FORMAT:
{{
  "title": "string",
  "layout": "LR",
  "nodes": [
    {{"id": "string", "label": "string", "type": "process", "icon": "string", "color": "string"}}
  ],
  "edges": [
    {{"source": "string", "target": "string", "label": "string"}}
  ]
}}

RULES:
1. Output ONLY JSON.
2. Node IDs: use simple sequential IDs N1, N2, N3, N4...
3. Labels: maximum 3 words, human readable, no colons or special characters.
4. Allowed node types: process, input, output, database, decision
5. Allowed colors: blue, purple, green, orange, red
6. Every node MUST have id, label, type, icon, color
7. Every node must be connected via edges
8. Minimum 4 nodes and 3 edges; no isolated nodes
9. layout must be LR or TD
10. If uncertain, generate a simpler diagram

EXAMPLE:
{DIAGRAM_JSON_EXAMPLE}

{DIRECT_OUTPUT_RULE}"""


def get_diagram_batch_system_prompt() -> str:
    return f"""You are a batch diagram structure generator for an educational notes system.

TASK:
Generate ONLY valid JSON with a "diagrams" array — one object per requested section anchor.

DO NOT generate Mermaid, markdown, HTML, SVG, or explanations.

OUTPUT FORMAT:
{{
  "diagrams": [
    {{
      "anchor": "## Exact H2 heading from request",
      "title": "Short diagram title",
      "layout": "LR",
      "nodes": [
        {{"id": "N1", "label": "User Query", "type": "input", "icon": "user", "color": "blue"}}
      ],
      "edges": [
        {{"source": "N1", "target": "N2", "label": "query"}}
      ]
    }}
  ]
}}

RULES:
1. Output ONLY JSON with a top-level "diagrams" array.
2. Include exactly one diagram per anchor listed in the user message.
3. Copy each anchor string exactly as provided.
4. Node IDs: N1, N2, N3… | labels max 3 words, no colons.
5. Types: process, input, output, database, decision | colors: blue, purple, green, orange, red.
6. Minimum 4 nodes and 3 edges per diagram; every node connected.
7. layout: LR or TD

EXAMPLE SINGLE ITEM:
{DIAGRAM_JSON_EXAMPLE}

Wrap the example shape inside "diagrams": [ ... ] when multiple anchors are requested.

{DIRECT_OUTPUT_RULE}"""


def get_diagram_batch_user_prompt(
    *,
    topic: str,
    anchors: list[tuple[str, str]],
    issues: list[str] | None = None,
) -> str:
    issue_block = ""
    if issues:
        issue_block = "\nFIX PRIOR ERRORS:\n" + "\n".join(f"- {i}" for i in issues[:8]) + "\n"
    lines = []
    for anchor, context in anchors:
        ctx = (context or anchor).strip()
        if len(ctx) > 400:
            ctx = ctx[:400] + "…"
        lines.append(f"- anchor: {anchor}\n  context: {ctx}")
    anchor_block = "\n".join(lines)
    return (
        f"Generate diagram JSON for ALL anchors below (one diagram each).\n\n"
        f"TOPIC: {topic}\n"
        f"{issue_block}\n"
        f"ANCHORS:\n{anchor_block}\n\n"
        f"Return ONLY the JSON object with a diagrams array."
    )


def get_diagram_json_user_prompt(*, topic: str, context: str, issues: list[str] | None = None) -> str:
    issue_block = ""
    if issues:
        issue_block = "\nFIX THESE ISSUES FROM PRIOR ATTEMPT:\n" + "\n".join(f"- {i}" for i in issues[:6]) + "\n"
    ctx = (context or "General concept overview for this section.").strip()
    if len(ctx) > 800:
        ctx = ctx[:800] + "…"
    return (
        f"Generate the diagram JSON for:\n\n"
        f"TOPIC: {topic}\n"
        f"CONTEXT: {ctx}\n"
        f"{issue_block}\n"
        f"Return ONLY the JSON object."
    )
