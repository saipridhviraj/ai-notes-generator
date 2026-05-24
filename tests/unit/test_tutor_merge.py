"""Tests for tutor supplement merge."""
from utils.tutor_merge import merge_tutor_supplements


class TestMergeTutorSupplements:
    def test_inserts_after_matching_heading(self):
        student = "# Title\n\n## Decorators\n\nBody here.\n"
        supplement = (
            "<!-- after: ## Decorators -->\n"
            "> **👨‍🏫 TEACHING NOTE:** Ask what a wrapper is.\n"
        )
        result = merge_tutor_supplements(student, supplement)
        assert "TEACHING NOTE" in result
        assert "Body here." in result
        assert result.index("TEACHING NOTE") > result.index("Body here.")

    def test_appends_orphan_blocks_at_end(self):
        student = "# Title\n\n## Only section\n"
        supplement = (
            "<!-- after: ## Missing section -->\n"
            "> **👨‍🏫 SAY THIS:** Hello\n"
        )
        result = merge_tutor_supplements(student, supplement)
        assert "SAY THIS" in result

    def test_empty_supplement_returns_student(self):
        student = "# Title\n"
        assert merge_tutor_supplements(student, "") == student
