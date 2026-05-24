"""Tests for tutor-facing node personas."""
from utils.node_personas import get_node_label, get_persona, persona_for_step


class TestNodePersonas:
    def test_student_notes_persona(self):
        p = get_persona("student_notes")
        assert p["name"] == "Student Notes Writer"
        assert p["icon"] == "📘"

    def test_awaiting_human_persona(self):
        p = get_persona("planner", awaiting_human=True)
        assert p["name"] == "Your review"
        assert p["icon"] == "🤚"

    def test_pipeline_step_includes_persona(self):
        row = persona_for_step("evaluator")
        assert row["persona"] == "Quality Evaluator"
        assert row["label"] == "Evaluate quality"

    def test_node_label_from_persona(self):
        assert get_node_label("tutor_notes") == "Annotate tutor guide"
