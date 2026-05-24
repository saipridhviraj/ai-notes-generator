"""Tests for tutor_notes_creator node."""
from unittest.mock import patch

import pytest

from graph.state import KeywordPlan


@pytest.fixture
def tutor_state(keyword_plan):
    return {
        "planner_output": keyword_plan,
        "student_notes": "# Python Decorators\n\nStudent content.\n",
        "errors": [],
        "status": "running",
    }


@pytest.fixture
def keyword_plan():
    return KeywordPlan(
        topic="Python Decorators",
        domain="python",
        intent="comprehensive_notes",
        keywords=["decorators"],
        subtopics=["syntax"],
        needs_web_search=False,
    )


class TestTutorNotesCreator:
    def test_success_returns_notes_and_filename(self, tutor_state):
        from graph.nodes.tutor_notes_creator import tutor_notes_creator

        with patch("graph.nodes.tutor_notes_creator.groq_client") as mock_groq:
            mock_groq.complete.return_value = "# Tutor Notes\n\nDetailed guide.\n"
            result = tutor_notes_creator(tutor_state)

        assert "Tutor Notes" in result["tutor_notes"]
        assert result["tutor_filename"] == "python_decorators_tutor.md"
        assert result["errors"] == []

    def test_llm_failure_sets_failed_status(self, tutor_state):
        from graph.nodes.tutor_notes_creator import tutor_notes_creator

        with patch("graph.nodes.tutor_notes_creator.groq_client") as mock_groq:
            mock_groq.complete.side_effect = RuntimeError("llm timeout")
            result = tutor_notes_creator(tutor_state)

        assert result["status"] == "failed"
        assert any("TutorNotesCreator" in e for e in result["errors"])

    def test_supplement_mode_merges_annotations(self, tutor_state, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("TUTOR_SUPPLEMENT_MODE", "true")
        monkeypatch.setenv("USE_PRODUCTION_PROMPTS", "true")
        from graph.nodes.tutor_notes_creator import tutor_notes_creator
        from prompts.profiles.production.tutor_notes_prompts import (
            get_tutor_supplement_system_prompt,
        )

        get_tutor_supplement_system_prompt()  # regression: must not raise ValueError

        tutor_json = {
            "section_annotations": [
                {
                    "section_key": "## Decorators",
                    "annotations": "> **👨‍🏫 TEACHING NOTE:** Explain wrappers first.",
                }
            ]
        }
        tutor_state["student_notes"] = "# Python Decorators\n\n## Decorators\n\nBody.\n"
        with patch("graph.nodes.tutor_notes_creator.groq_client") as mock_groq:
            mock_groq.complete_json.return_value = tutor_json
            result = tutor_notes_creator(tutor_state)

        assert "TEACHING NOTE" in result["tutor_notes"]
        assert "Body." in result["tutor_notes"]
        assert not any("Invalid format specifier" in e for e in result["errors"])
        mock_groq.complete_json.assert_called_once()

    def test_success_clears_prior_tutor_errors(self, tutor_state, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("TUTOR_SUPPLEMENT_MODE", "true")
        from graph.nodes.tutor_notes_creator import tutor_notes_creator

        tutor_state["errors"] = [
            "TutorNotesCreator failed: Invalid format specifier 'old bug'",
            "ResearchNode: Tavily search failed — timeout",
        ]
        tutor_state["student_notes"] = "# Topic\n\n## Section\n\nBody.\n"
        with patch("graph.nodes.tutor_notes_creator.groq_client") as mock_groq:
            mock_groq.complete_json.return_value = {
                "section_annotations": [
                    {
                        "section_key": "## Section",
                        "annotations": "> **👨‍🏫 TEACHING NOTE:** ok",
                    }
                ]
            }
            result = tutor_notes_creator(tutor_state)

        assert not any("TutorNotesCreator" in e for e in result["errors"])
        assert any("ResearchNode" in e for e in result["errors"])
