"""Tests for partial pipeline resume."""

import pytest

from graph.state import KeywordPlan
from utils.graph_resume import (
    build_resume_state_patch,
    validate_resume_request,
)


def _plan():
    return KeywordPlan(
        topic="Python OOP",
        domain="python",
        intent="comprehensive_notes",
        keywords=["class"],
        subtopics=["syntax"],
        needs_web_search=False,
    )


def _rich_state(**overrides):
    base = {
        "status": "max_retries_reached",
        "planner_output": _plan(),
        "planner_verified": True,
        "research_data": "## Instructions",
        "student_notes": "# OOP\n\n" + ("x" * 200),
        "tutor_notes": "partial tutor",
        "errors": [
            "TutorNotesCreator: JSON handoff failed",
            "Max retries (1) reached. Saving best attempt.",
        ],
        "retry_count": 1,
    }
    base.update(overrides)
    return base


class TestValidateResume:
    def test_tutor_resume_ok(self):
        assert validate_resume_request(_rich_state(), "tutor_notes") is None

    def test_tutor_resume_missing_student(self):
        err = validate_resume_request(_rich_state(student_notes="short"), "tutor_notes")
        assert err is not None
        assert "student_notes" in err

    def test_rejected_session_blocked(self):
        err = validate_resume_request(_rich_state(status="rejected"), "tutor_notes")
        assert err is not None


class TestResumePatch:
    def test_clears_tutor_and_eval(self):
        patch = build_resume_state_patch(_rich_state(), "tutor_notes")
        assert patch["tutor_notes"] is None
        assert patch["evaluation_result"] is None
        assert patch["retry_count"] == 0
        assert patch["status"] == "running"
        assert not any("TutorNotes" in e for e in patch["errors"])
        assert not any("Max retries" in e for e in patch["errors"])

    def test_keeps_student_notes(self):
        state = _rich_state()
        merged = {**state, **build_resume_state_patch(state, "tutor_notes")}
        assert len(merged["student_notes"]) > 100

    def test_mermaid_repair_resume_ok(self):
        assert validate_resume_request(_rich_state(), "mermaid_repair") is None
        patch = build_resume_state_patch(_rich_state(), "mermaid_repair")
        assert patch["evaluation_result"] is None
        assert patch["retry_count"] == 0
