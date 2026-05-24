"""Tests for diagram pipeline orchestration."""

from unittest.mock import MagicMock


from utils.diagram_pipeline import render_diagrams_in_notes

NOTES = """# Lesson

## Intro

Text here.

<!-- diagram: ## Intro -->
"""

BATCH_RESPONSE = {
    "diagrams": [
        {
            "anchor": "## Intro",
            "title": "Intro Flow",
            "layout": "LR",
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
    ]
}


class TestDiagramPipeline:
    def test_render_embeds_json_and_svg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        llm = MagicMock()
        llm.complete_json.return_value = BATCH_RESPONSE

        out = render_diagrams_in_notes(
            NOTES,
            {"topic": "Test"},
            llm,
            diagrams_dir=tmp_path,
            session_id="s1",
        )

        assert "```diagram-json" in out
        assert "![Intro Flow](./diagrams/" in out
        assert list(tmp_path.glob("*.svg"))

    def test_batch_failure_falls_back_to_single(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        llm = MagicMock()
        single = BATCH_RESPONSE["diagrams"][0]
        llm.complete_json.side_effect = [
            {"diagrams": []},
            {"diagrams": []},
            {"diagrams": []},
            single,
        ]

        out = render_diagrams_in_notes(
            NOTES,
            {"topic": "Test"},
            llm,
            diagrams_dir=tmp_path,
        )
        assert "```diagram-json" in out
