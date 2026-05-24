"""Tests for gap_bridger_node — BUG-RT-007 JSON fallback."""
from unittest.mock import patch
from graph.nodes.gap_bridger_node import gap_bridger_node
from graph.state import EvaluationResult
from prompts.gap_bridger_prompts import split_gap_content
from utils.gap_patch import _merge_sections, _resolve_insertions


class TestSplitGapContent:
    def test_splits_tutor_marker(self):
        raw = "## Student\n\nPatch.\n\n===TUTOR_PATCHES===\n\n## Intro\n\n> **👨‍🏫 TEACHING NOTE:** Hi."
        student, tutor = split_gap_content(raw)
        assert "## Student" in student
        assert "===TUTOR_PATCHES===" not in student
        assert "## Intro" in tutor

    def test_no_marker_returns_all_student(self):
        raw = "## Only student patch"
        student, tutor = split_gap_content(raw)
        assert student == "## Only student patch"
        assert tutor == ""


class TestResolveInsertions:
    def test_valid_json_returns_insertions(self):
        errors = []
        with patch("utils.gap_patch.groq_client") as mock:
            mock.complete_json.return_value = [
                {"insert_after": "## Topic", "content": "## New\nMore content"}
            ]
            result = _resolve_insertions("# Notes\n## Topic\n", "gap", errors)
        assert len(result) == 1
        assert not errors

    def test_invalid_json_falls_back_to_append(self):
        errors = []
        with patch("utils.gap_patch.groq_client") as mock:
            mock.complete_json.side_effect = ValueError("Unterminated string")
            result = _resolve_insertions("# Notes\n", "gap content here", errors)
        assert result == [{"insert_after": "", "content": "gap content here"}]
        assert any("append" in e.lower() or "JSON" in e for e in errors)


class TestMergeSections:
    def test_append_when_insert_after_empty(self):
        notes = "# Hello\n"
        result = _merge_sections(notes, [{"insert_after": "", "content": "## Gap\nNew section"}])
        assert "## Gap" in result
        assert result.startswith("# Hello")

    def test_safe_when_no_newline_after_heading(self):
        notes = "## Only heading"
        result = _merge_sections(notes, [{"insert_after": "## Only heading", "content": "added"}])
        assert "added" in result


class TestGapBridgerAlignment:
    def test_runs_when_only_alignment_issues(self):
        state = {
            "evaluation_result": EvaluationResult(
                student_notes_score=70,
                tutor_notes_score=70,
                missing_topics=[],
                diagram_issues=[],
                alignment_issues=["Missing tutor annotation on section: Intro"],
                passed=False,
            ),
            "student_notes": "## Intro\n\nBody.\n",
            "tutor_notes": "## Intro\n\nNo annotation.\n",
            "research_data": "",
            "errors": [],
            "session_id": None,
        }
        with patch("utils.gap_patch.groq_client") as mock:
            mock.complete.return_value = (
                "===TUTOR_PATCHES===\n\n## Intro\n\n> **👨‍🏫 TEACHING NOTE:** Review intro.\n"
            )
            mock.complete_json.return_value = [
                {"insert_after": "## Intro", "content": "> **👨‍🏫 TEACHING NOTE:** Review intro.\n"}
            ]
            result = gap_bridger_node(state)
        assert "TEACHING NOTE" in result["tutor_notes"]
        assert result.get("retry_count") == 1
        mock.complete.assert_called_once()
        prompt = mock.complete.call_args.kwargs["prompt"]
        assert "Missing tutor annotation" in prompt
