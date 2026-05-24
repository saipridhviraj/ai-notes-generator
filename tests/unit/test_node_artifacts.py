"""Tests for per-node artifact builders."""

import json

from graph.state import EvaluationResult, KeywordPlan
from utils.node_artifacts import (
    artifact_node_ids,
    build_node_artifacts,
    get_node_artifact_content,
)
from utils.pipeline_progress import get_pipeline_progress


def _plan():
    return KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators", "closure"],
        subtopics=["syntax", "use cases"],
        needs_web_search=False,
    )


def _pipeline(state):
    return get_pipeline_progress("student_notes", state.get("status", "running"), 0)[
        "pipeline_steps"
    ]


class TestNodeArtifacts:
    def test_build_metadata_for_partial_state(self):
        state = {
            "status": "running",
            "planner_output": _plan(),
            "research_data": "## Writing Goals\nCover decorators.",
            "student_notes": None,
        }
        progress = _pipeline(state)
        items = build_node_artifacts(state, progress)
        assert len(items) == len(artifact_node_ids())

        planner = next(i for i in items if i["node_id"] == "planner")
        research = next(i for i in items if i["node_id"] == "research")
        student = next(i for i in items if i["node_id"] == "student_notes")

        assert planner["available"] is True
        assert planner["format"] == "json"
        assert research["available"] is True
        assert student["available"] is False

    def test_get_full_planner_content(self):
        state = {"planner_output": _plan()}
        payload = get_node_artifact_content(state, "planner")
        assert payload is not None
        parsed = json.loads(payload["content"])
        assert parsed["topic"] == "Python Decorators"

    def test_get_research_markdown(self):
        state = {"research_data": "## Instructions\nNo code here."}
        payload = get_node_artifact_content(state, "research")
        assert payload["format"] == "markdown"
        assert "No code here" in payload["content"]

    def test_research_includes_suggested_diagrams(self):
        state = {
            "research_data": (
                "## Suggested Diagrams\n"
                "- After Classes: flowchart class → object\n"
                "- After Inheritance: hierarchy Animal → Dog\n"
            )
        }
        payload = get_node_artifact_content(state, "research")
        assert payload["suggested_diagrams"] == [
            "After Classes: flowchart class → object",
            "After Inheritance: hierarchy Animal → Dog",
        ]

    def test_build_research_diagram_count_metadata(self):
        state = {
            "status": "running",
            "research_data": "## Suggested Diagrams\n- A\n- B\n- C\n",
        }
        items = build_node_artifacts(state, _pipeline(state))
        research = next(i for i in items if i["node_id"] == "research")
        assert research["suggested_diagram_count"] == 3

    def test_evaluator_json(self):
        state = {
            "evaluation_result": EvaluationResult(
                student_notes_score=85,
                tutor_notes_score=90,
                missing_topics=[],
                diagram_issues=[],
                alignment_issues=[],
                passed=True,
            )
        }
        payload = get_node_artifact_content(state, "evaluator")
        assert payload is not None
        assert payload["format"] == "json"
        assert "student_notes_score" in payload["content"]

    def test_unknown_node_returns_none(self):
        assert get_node_artifact_content({}, "unknown") is None
