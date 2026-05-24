"""Tests for diagram_generator graph node."""

from unittest.mock import patch

import pytest

from graph.state import KeywordPlan


@pytest.fixture
def diagram_state(base_state):
    plan = KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators"],
        subtopics=["syntax"],
        needs_web_search=False,
    )
    return {
        **base_state,
        "planner_output": plan,
        "student_notes": "## Intro\n\nText\n\n<!-- diagram: ## Intro -->\n",
    }


class TestDiagramGeneratorNode:
    def test_skips_when_pipeline_disabled(self, diagram_state, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "false")
        from graph.nodes.diagram_generator_node import diagram_generator_node

        assert diagram_generator_node(diagram_state) == {}

    def test_renders_when_pipeline_enabled(self, diagram_state, tmp_path, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "true")
        monkeypatch.setenv("MIN_MERMAID_DIAGRAMS", "1")
        from graph.nodes.diagram_generator_node import diagram_generator_node

        batch = {
            "diagrams": [
                {
                    "anchor": "## Intro",
                    "title": "Intro",
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

        with patch("graph.nodes.diagram_generator_node.groq_client") as mock_llm:
            mock_llm.complete_json.return_value = batch
            with patch(
                "graph.nodes.diagram_generator_node.diagrams_dir_for_state",
                return_value=tmp_path,
            ):
                result = diagram_generator_node(diagram_state)

        assert "```diagram-json" in result["student_notes"]
