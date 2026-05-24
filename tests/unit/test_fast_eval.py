"""Tests for fast heuristic evaluator."""
from utils.fast_eval import heuristic_evaluate


class TestHeuristicEvaluate:
    def test_passes_when_keywords_present(self):
        body = "decorators and wrappers explained. " * 15
        student = (
            "# T\n\n## Decorators\n\n"
            f"{body}\n\n"
            "```mermaid\ngraph TD\nA-->B\n```\n\n"
            "```mermaid\ngraph LR\nC-->D\n```\n"
        )
        tutor = student + "\n> **👨‍🏫 TEACHING NOTE:** hi\n"
        result = heuristic_evaluate(
            student, tutor, ["decorators", "wrappers"], []
        )
        assert result.passed is True
        assert result.student_notes_score >= 80

    def test_fails_when_keyword_missing(self):
        student = "# T\n\n## X\n\nno keywords\n"
        tutor = student + "\n> **👨‍🏫 TEACHING NOTE:** hi\n"
        result = heuristic_evaluate(student, tutor, ["decorators"], [])
        assert "decorators" in result.missing_topics

    def test_fails_when_alignment_issues_present(self):
        student = "## Intro\n\nBody.\n"
        tutor = "## Intro\n\nPlain text.\n"
        alignment = ["Missing tutor annotation on section: Intro"]
        result = heuristic_evaluate(student, tutor, ["intro"], [], alignment)
        assert result.passed is False
        assert result.alignment_issues == alignment
