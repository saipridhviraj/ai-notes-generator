"""Unit tests for graph nodes — planner, research, final_response."""
from unittest.mock import MagicMock, patch

import pytest

from graph.state import KeywordPlan


@pytest.fixture
def keyword_plan():
    return KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators", "wrappers"],
        subtopics=["syntax", "use cases"],
        needs_web_search=True,
    )


@pytest.fixture
def keyword_plan_no_web():
    return KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators", "wrappers"],
        subtopics=["syntax", "use cases"],
        needs_web_search=False,
    )


class TestPlannerNode:
    def test_planner_success(self, keyword_plan, monkeypatch):
        from graph.nodes.planner_node import planner_node

        raw = keyword_plan.model_dump()
        with patch("graph.nodes.planner_node.groq_client") as mock_groq:
            mock_groq.complete_json.return_value = raw
            result = planner_node({"user_input": "Decorators", "session_id": "s1", "errors": []})

        assert result["status"] == "awaiting_tutor"
        assert result["planner_output"].topic == "Python Decorators"
        assert result["tutor_question"]

    def test_planner_failure(self):
        from graph.nodes.planner_node import planner_node

        with patch("graph.nodes.planner_node.groq_client") as mock_groq:
            mock_groq.complete_json.side_effect = RuntimeError("llm down")
            result = planner_node({"user_input": "x", "session_id": "s1", "errors": []})

        assert result["status"] == "failed"
        assert any("PlannerNode" in e for e in result["errors"])


class TestResearchNode:
    def test_research_without_web(self, keyword_plan_no_web):
        from graph.nodes.research_node import research_node

        state = {
            "planner_output": keyword_plan_no_web,
            "errors": [],
        }
        with patch("graph.nodes.research_node.groq_client") as mock_groq:
            mock_groq.complete.return_value = "synthesized research"
            result = research_node(state)

        assert result["research_data"] == "synthesized research"
        assert result["used_web_search"] is False
        mock_groq.complete.assert_called_once()

    def test_research_with_web(self, keyword_plan):
        from graph.nodes.research_node import research_node

        state = {"planner_output": keyword_plan, "errors": []}
        with (
            patch("graph.nodes.research_node.groq_client") as mock_groq,
            patch("graph.nodes.research_node.tavily_client") as mock_tavily,
        ):
            mock_groq.complete.return_value = "web-augmented research"
            mock_tavily.search_keywords.return_value = "## Web Research Results"
            result = research_node(state)

        assert result["used_web_search"] is True
        assert "web-augmented" in result["research_data"]
        mock_groq.complete.assert_called_once()

    def test_research_forced_by_genai_domain(self):
        from graph.nodes.research_node import research_node

        plan = KeywordPlan(
            topic="Transformers",
            domain="genai",
            intent="comprehensive_notes",
            keywords=["attention"],
            subtopics=["self-attention"],
            needs_web_search=False,
        )
        state = {"planner_output": plan, "errors": []}
        with (
            patch("graph.nodes.research_node.groq_client") as mock_groq,
            patch("graph.nodes.research_node.tavily_client") as mock_tavily,
        ):
            mock_groq.complete.return_value = "genai brief"
            mock_tavily.search_keywords.return_value = "## Web"
            result = research_node(state)

        assert result["used_web_search"] is True
        mock_groq.complete.assert_called_once()
        mock_tavily.search_keywords.assert_called_once()

    def test_research_tavily_failure_continues(self, keyword_plan):
        from graph.nodes.research_node import research_node

        state = {"planner_output": keyword_plan, "errors": []}
        with (
            patch("graph.nodes.research_node.groq_client") as mock_groq,
            patch("graph.nodes.research_node.tavily_client") as mock_tavily,
        ):
            mock_groq.complete.return_value = "fallback research"
            mock_tavily.search_keywords.side_effect = RuntimeError("tavily down")
            result = research_node(state)

        assert result["used_web_search"] is False
        assert "fallback research" in result["research_data"]
        assert any("Tavily" in e for e in result["errors"])

    def test_research_failure(self, keyword_plan):
        from graph.nodes.research_node import research_node

        with patch("graph.nodes.research_node.groq_client") as mock_groq:
            mock_groq.complete.side_effect = RuntimeError("boom")
            result = research_node({"planner_output": keyword_plan, "errors": []})

        assert result["status"] == "failed"


class TestStudentNotesCreator:
    def test_student_notes_success(self, keyword_plan, base_state):
        from graph.nodes.student_notes_creator import student_notes_creator

        state = {**base_state, "planner_output": keyword_plan}
        with (
            patch("graph.nodes.student_notes_creator.groq_client") as mock_groq,
            patch(
                "graph.nodes.student_notes_creator.ensure_mermaid_diagrams",
                side_effect=lambda notes, *args, **kwargs: notes,
            ),
        ):
            mock_groq.complete.return_value = "# Student Notes"
            result = student_notes_creator(state)

        assert result["student_notes"].strip() == "# Student Notes"
        assert result["student_filename"].endswith("_student.md")

    def test_student_notes_strips_mermaid_when_diagram_pipeline(self, keyword_plan, base_state, monkeypatch):
        monkeypatch.setenv("DIAGRAM_PIPELINE", "true")
        from graph.nodes.student_notes_creator import student_notes_creator

        md = """## AI Basics

Intro.

```mermaid
graph TD
A --> B
```
"""
        state = {**base_state, "planner_output": keyword_plan}
        with patch("graph.nodes.student_notes_creator.groq_client") as mock_groq:
            mock_groq.complete.return_value = md
            result = student_notes_creator(state)

        out = result["student_notes"]
        assert "```mermaid" not in out
        assert "<!-- diagram: ## AI Basics -->" in out


class TestFinalResponseNode:
    def test_final_response_success(self, keyword_plan, base_state, tmp_path, monkeypatch):
        monkeypatch.setattr("services.file_service.NOTES_DIR", tmp_path)
        state = {
            **base_state,
            "planner_output": keyword_plan,
            "student_filename": "decorators_student.md",
            "tutor_filename": "decorators_tutor.md",
        }
        with patch("services.note_ready_publisher.publish_note_ready"):
            from graph.nodes.final_response_node import final_response_node

            result = final_response_node(state)

        assert result["status"] == "completed"
        assert len(result["output_files"]) == 2
        assert result["final_summary"] == (
            "Generated decorators_student.md and decorators_tutor.md for topic: Python Decorators"
        )

    def test_final_response_short_notes_warning(self, keyword_plan, base_state, tmp_path, monkeypatch):
        monkeypatch.setattr("services.file_service.NOTES_DIR", tmp_path)
        state = {
            **base_state,
            "planner_output": keyword_plan,
            "student_notes": "# Short",
            "tutor_notes": "# Also short",
            "student_filename": "s.md",
            "tutor_filename": "t.md",
        }
        with patch("services.note_ready_publisher.publish_note_ready"):
            from graph.nodes.final_response_node import final_response_node

            result = final_response_node(state)

        assert result["status"] == "completed"
        assert any("suspiciously short" in e for e in result["errors"])

    def test_final_response_save_failure(self, keyword_plan, base_state):
        state = {
            **base_state,
            "planner_output": keyword_plan,
            "student_filename": "bad.md",
            "tutor_filename": "bad_tutor.md",
        }
        with patch("graph.nodes.final_response_node.save_markdown", side_effect=OSError("disk full")):
            from graph.nodes.final_response_node import final_response_node

            result = final_response_node(state)

        assert result["status"] == "failed"

    def test_final_response_summary_fallback(self, keyword_plan, base_state, tmp_path, monkeypatch):
        monkeypatch.setattr("services.file_service.NOTES_DIR", tmp_path)
        monkeypatch.setenv("FINAL_SUMMARY_LLM", "true")
        state = {
            **base_state,
            "planner_output": keyword_plan,
            "student_filename": "s.md",
            "tutor_filename": "t.md",
        }
        with patch("services.groq_client.groq_client") as mock_groq, patch(
            "services.note_ready_publisher.publish_note_ready"
        ):
            mock_groq.complete.side_effect = RuntimeError("rate limit")
            from graph.nodes.final_response_node import final_response_node

            result = final_response_node(state)

        assert result["status"] == "completed"
        assert "s.md" in result["final_summary"]
