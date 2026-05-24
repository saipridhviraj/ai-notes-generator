"""Tests for server-side SVG rendering from diagram JSON."""

from models.diagram_spec import DiagramSpec
from utils.diagram_svg import render_diagram_svg

SPEC = {
    "title": "Pipeline",
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


class TestDiagramSvg:
    def test_renders_svg_markup(self):
        svg = render_diagram_svg(DiagramSpec.model_validate(SPEC))
        assert svg.startswith("<svg")
        assert "User Input" in svg
        assert "</svg>" in svg

    def test_accepts_dict(self):
        svg = render_diagram_svg(SPEC)
        assert "Pipeline" in svg
