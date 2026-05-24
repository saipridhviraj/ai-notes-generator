"""Tests for tutor supplements extraction."""
from services.tutor_supplements_extractor import (
    extract_supplements,
    supplements_filename,
    write_supplements_json,
)

from tests.conftest import EXAMPLES_DIR

EXAMPLE_TUTOR = EXAMPLES_DIR / "day1_tutor_notes.md"


class TestSupplementsExtractor:
    def test_extracts_from_day1_example(self):
        text = EXAMPLE_TUTOR.read_text(encoding="utf-8")
        sup = extract_supplements(text)
        assert sup.total_items() > 0
        assert len(sup.quizzes) >= 5
        assert any(q.kind == "rapid_fire" for q in sup.quizzes)
        assert len(sup.pacing) >= 3
        assert len(sup.assignments) == 1
        assert sup.assignments[0].title == "Homework"
        assert sup.visibility == "tutor_only"

    def test_empty_tutor_markdown(self):
        sup = extract_supplements("")
        assert sup.is_empty()

    def test_supplements_filename(self):
        assert supplements_filename("day-01_topic_student.md") == "day-01_topic_supplements.json"

    def test_write_supplements_json(self, tmp_path):
        from models.tutor_supplements import AssignmentItem, TutorSupplements

        sup = TutorSupplements(
            assignments=[
                AssignmentItem(
                    id="assignment-01",
                    title="HW",
                    description="Do the reading",
                )
            ]
        )
        path = write_supplements_json(sup, tmp_path, "test_supplements.json")
        assert path.exists()
        assert "assignment-01" in path.read_text(encoding="utf-8")

    def test_rapid_fire_quiz_parses_arrow_answers(self):
        md = """
## Section A

> **👨‍🏫 RAPID-FIRE QUIZ:**
> 1. "Instagram recommendations?" → Traditional AI
> 2. "ChatGPT writing story?" → Generative AI
"""
        sup = extract_supplements(md)
        assert len(sup.quizzes) == 2
        assert sup.quizzes[0].answer == "Traditional AI"
        assert "Instagram" in sup.quizzes[0].question
