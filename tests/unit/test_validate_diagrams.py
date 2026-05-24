"""Tests for validate_diagrams_in_notes."""

import json

from utils.helpers import validate_diagrams_in_notes

SPEC = {
    "title": "Flow",
    "layout": "TD",
    "nodes": [
        {"id": "N1", "label": "User Input", "type": "input", "icon": "user", "color": "blue"},
        {"id": "N2", "label": "Process Step", "type": "process", "icon": "process", "color": "purple"},
        {"id": "N3", "label": "Data Store", "type": "database", "icon": "database", "color": "green"},
        {"id": "N4", "label": "Final Output", "type": "output", "icon": "bot", "color": "orange"},
    ],
    "edges": [
        {"source": "N1", "target": "N2", "label": "go"},
        {"source": "N2", "target": "N3", "label": "read"},
        {"source": "N3", "target": "N4", "label": "out"},
    ],
}


def _embed(n: int = 1) -> str:
    body = json.dumps(SPEC, indent=2)
    parts = []
    for i in range(n):
        parts.append(f"```diagram-json\n{body}\n```\n\n![Flow {i}](./diagrams/fig-{i}.svg)")
    return "\n\n".join(parts)


class TestValidateDiagramsInNotes:
    def test_accepts_valid_embeds(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        assert validate_diagrams_in_notes(_embed(1)) == []

    def test_rejects_mermaid_blocks(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        md = _embed(1) + "\n```mermaid\nflowchart TD\nA-->B\n```"
        issues = validate_diagrams_in_notes(md)
        assert any("mermaid" in i.lower() for i in issues)

    def test_rejects_unfilled_placeholder(self, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        issues = validate_diagrams_in_notes("<!-- diagram: ## Intro -->")
        assert any("Unfilled" in i or "No diagrams" in i for i in issues)
