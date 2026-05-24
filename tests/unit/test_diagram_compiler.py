"""Tests for JSON diagram spec validation and Mermaid compilation."""

import pytest

from utils.diagram_compiler import (
    compile_diagram_to_mermaid,
    validate_diagram_spec,
    wrap_replace_index,
)

VALID_SPEC = {
    "title": "AI Stack",
    "layout": "TD",
    "nodes": [
        {"id": "N1", "label": "User Input", "type": "input", "icon": "user", "color": "blue"},
        {"id": "N2", "label": "Processing", "type": "process", "icon": "process", "color": "purple"},
        {"id": "N3", "label": "Knowledge Base", "type": "database", "icon": "database", "color": "green"},
        {"id": "N4", "label": "Model Output", "type": "output", "icon": "bot", "color": "orange"},
    ],
    "edges": [
        {"source": "N1", "target": "N2", "label": "send"},
        {"source": "N2", "target": "N3", "label": "fetch"},
        {"source": "N3", "target": "N4", "label": "reply"},
    ],
}


class TestDiagramCompiler:
    def test_validate_accepts_valid_spec(self):
        assert validate_diagram_spec(VALID_SPEC) == []

    def test_validate_rejects_short_labels_with_colon(self):
        bad = {
            **VALID_SPEC,
            "nodes": [
                {**VALID_SPEC["nodes"][0], "label": "Bad: label"},
                *VALID_SPEC["nodes"][1:],
            ],
        }
        assert any("colon" in i for i in validate_diagram_spec(bad))

    def test_compile_produces_flowchart(self):
        mermaid = compile_diagram_to_mermaid(VALID_SPEC)
        assert mermaid.startswith("flowchart TD")
        assert 'N1["User Input"]' in mermaid
        assert "N1 --> N2" in mermaid or 'N1 -->|"send"| N2' in mermaid
        assert "style N1" in mermaid
        assert "color:#e2e8f0" in mermaid

    def test_wrap_replace_index(self):
        wrapped = wrap_replace_index(2, VALID_SPEC)
        assert "<!-- replace: 2 -->" in wrapped
        assert "```mermaid" in wrapped

    def test_compile_raises_on_invalid(self):
        with pytest.raises(ValueError):
            compile_diagram_to_mermaid({"nodes": [], "edges": []})
