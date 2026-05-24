"""Tests for Pydantic diagram spec models."""

import pytest

from models.diagram_spec import DiagramSpec, BatchDiagramResponse

VALID = {
    "title": "Test",
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


class TestDiagramSpec:
    def test_valid_spec(self):
        spec = DiagramSpec.model_validate(VALID)
        assert spec.title == "Test"
        assert len(spec.nodes) == 4

    def test_rejects_colon_in_label(self):
        bad = {**VALID, "nodes": [{**VALID["nodes"][0], "label": "Bad: label"}, *VALID["nodes"][1:]]}
        with pytest.raises(Exception):
            DiagramSpec.model_validate(bad)

    def test_batch_response(self):
        batch = BatchDiagramResponse.model_validate(
            {"diagrams": [{**VALID, "anchor": "## Intro"}]}
        )
        assert batch.diagrams[0].anchor == "## Intro"
