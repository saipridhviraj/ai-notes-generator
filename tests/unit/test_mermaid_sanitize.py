"""Tests for Mermaid v11 normalization."""

from utils.mermaid_sanitize import (
    auto_quote_all_labels,
    dedupe_diagram_headers,
    ensure_flowchart_header,
    ensure_node_styles,
    missing_style_node_ids,
    normalize_mermaid_block,
    sanitize_markdown_mermaid,
)

BROKEN_DIAGRAM = """
graph TD
    subgraph Traditional_AI ["Traditional AI"]
    T1[Humans write rules] --> T2[Strict Map] --> T3[Limitation: Stops if no rule]
    end
    style Traditional_AI fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0
    style T1 fill:#16213e,stroke:#2563eb,color:#e2e8f0
"""


def test_auto_quote_all_labels():
    fixed = auto_quote_all_labels("A[Hello] --> B[Step: two]")
    assert 'A["Hello"]' in fixed
    assert 'B["Step: two"]' in fixed


def test_ensure_flowchart_header_from_graph():
    out = ensure_flowchart_header("graph TD\nA --> B")
    assert out.startswith("flowchart TD")


def test_ensure_flowchart_header_prepends_when_missing():
    out = ensure_flowchart_header("A --> B")
    assert out.startswith("flowchart TD")


def test_ensure_node_styles_fills_missing():
    block = 'flowchart TD\nA["One"] --> B["Two"]\nstyle A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0'
    out = ensure_node_styles(block)
    assert "style B" in out
    assert missing_style_node_ids(out) == []


def test_normalize_fixes_colons_subgraph_style_and_missing_styles():
    out = normalize_mermaid_block(BROKEN_DIAGRAM)
    assert out.startswith("flowchart TD")
    assert 'T3["Limitation: Stops if no rule"]' in out
    assert "style Traditional_AI" not in out
    assert "style T2" in out
    assert "style T3" in out


def test_dedupe_removes_flowchart_before_sequence():
    block = "flowchart TD\nsequenceDiagram\nparticipant A\nA->>B: hi"
    out = dedupe_diagram_headers(block)
    assert out.startswith("sequenceDiagram")
    assert not out.strip().startswith("flowchart")


def test_validate_rejects_sequence_and_mixed_headers():
    from utils.helpers import validate_mermaid_block

    mixed = "flowchart TD\nsequenceDiagram\nparticipant A\nA->>B: x\nstyle A fill:#1a1a2e,stroke:#7c3aed,color:#e2e8f0"
    issues = validate_mermaid_block(mixed)
    assert any("Unsupported" in i or "Multiple" in i for i in issues)


def test_sanitize_markdown_wraps_blocks():
    md = f"# Notes\n\n```mermaid\n{BROKEN_DIAGRAM.strip()}\n```\n"
    out = sanitize_markdown_mermaid(md)
    assert 'T3["Limitation: Stops if no rule"]' in out
