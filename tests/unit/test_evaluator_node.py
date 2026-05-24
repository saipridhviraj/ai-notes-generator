"""Tests for evaluator_node — BUG-4 regression: diagram validation must be called."""
import importlib
import pytest
from unittest.mock import patch, MagicMock
from graph.state import EvaluationResult

_EVALUATOR_MOD = "graph.nodes.evaluator_node"


def _evaluator_module():
    return importlib.import_module(_EVALUATOR_MOD)


@pytest.fixture(autouse=True)
def legacy_mermaid_pipeline(monkeypatch):
    """Keep evaluator tests on Mermaid path unless explicitly testing diagram pipeline."""
    monkeypatch.setenv("DIAGRAM_PIPELINE", "false")


@pytest.fixture(autouse=True)
def passing_python_pre_check(monkeypatch):
    """LLM evaluator tests assume structural pre-check passed."""
    monkeypatch.setattr(
        _evaluator_module(),
        "python_pre_check",
        lambda *args, **kwargs: {
            "student_notes_score": 100,
            "tutor_notes_score": 100,
            "missing_topics": [],
            "diagram_issues": [],
            "alignment_issues": [],
            "passed": True,
            "pre_check_only": True,
        },
    )


@pytest.fixture
def passing_eval_result():
    return {
        "student_notes_score": 85,
        "tutor_notes_score": 90,
        "missing_topics": [],
        "diagram_issues": [],
        "alignment_issues": [],
        "passed": True,
    }


@pytest.fixture
def failing_eval_result():
    return {
        "student_notes_score": 60,
        "tutor_notes_score": 65,
        "missing_topics": ["generators"],
        "diagram_issues": ["Missing diagram for control flow"],
        "alignment_issues": [],
        "passed": False,
    }


class TestEvaluatorNode:
    def test_passed_evaluation_returns_correct_status(self, base_state, passing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.compute_alignment_issues", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="full"),
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            result = evaluator_node(base_state)

        assert result["evaluation_result"].passed is True
        assert result.get("retry_count", 0) == 0

    def test_failed_evaluation_increments_retry(self, base_state, failing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="full"),
        ):
            mock_groq.complete_json.return_value = failing_eval_result
            result = evaluator_node(base_state)

        assert result["evaluation_result"].passed is False
        assert result.get("retry_count", 0) == 0

    def test_mermaid_validator_is_called(self, base_state, passing_eval_result):
        """BUG-4 regression — validate_all_mermaid_in_notes must be invoked."""
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]) as mock_val,
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            evaluator_node(base_state)

        mock_val.assert_called_once_with(base_state["student_notes"])

    def test_mermaid_issues_appended_to_prompt(self, base_state, passing_eval_result):
        """Mermaid issues must be included in the LLM prompt."""
        from graph.nodes.evaluator_node import evaluator_node

        mermaid_issues = ["Diagram 1: No arrows found"]

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=mermaid_issues),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="full"),
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            evaluator_node(base_state)

        call_kwargs = mock_groq.complete_json.call_args
        prompt_arg = call_kwargs[1].get("prompt") or call_kwargs[0][0]
        assert "Mermaid syntax issues" in prompt_arg

    def test_max_retries_sets_max_retries_status(self, base_state, failing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        state = dict(base_state)
        state["retry_count"] = 3

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch.dict("os.environ", {"MAX_EVAL_RETRIES": "3"}),
        ):
            mock_groq.complete_json.return_value = failing_eval_result
            result = evaluator_node(state)

        assert result["status"] == "max_retries_reached"

    def test_groq_exception_falls_back_to_heuristic(self, base_state):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="full"),
        ):
            mock_groq.complete_json.side_effect = Exception("API timeout")
            result = evaluator_node(base_state)

        assert result["evaluation_result"] is not None
        assert any("LLM scoring unavailable" in e for e in result["errors"])

    def test_light_eval_uses_summary_not_full_notes(self, base_state, passing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="light"),
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            evaluator_node(base_state)

        prompt = mock_groq.complete_json.call_args[1].get("prompt") or mock_groq.complete_json.call_args[0][0]
        assert "STRUCTURAL EVALUATION SUMMARY" in prompt
        assert "Student content here" not in prompt
        assert mock_groq.complete_json.call_args[1].get("size") == "small"

    def test_python_alignment_issues_merged_into_result(self, base_state, passing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="light"),
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            result = evaluator_node(base_state)

        alignment = result["evaluation_result"].alignment_issues
        assert any("Missing tutor annotation" in issue for issue in alignment)

    def test_pre_check_failure_skips_llm(self, base_state, monkeypatch):
        from graph.nodes.evaluator_node import evaluator_node

        monkeypatch.setattr(
            _evaluator_module(),
            "python_pre_check",
            lambda *args, **kwargs: {
                "student_notes_score": 50,
                "tutor_notes_score": 90,
                "missing_topics": ["Homework section missing"],
                "diagram_issues": ["Only 0 Mermaid diagram(s) found"],
                "alignment_issues": [],
                "passed": False,
                "pre_check_only": True,
            },
        )

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch("graph.nodes.evaluator_node.validate_all_mermaid_in_notes", return_value=[]),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="light"),
        ):
            result = evaluator_node(base_state)

        mock_groq.complete_json.assert_not_called()
        assert result["evaluation_result"].passed is False
        assert "Homework" in result["evaluation_result"].missing_topics[0]

    def test_mermaid_issues_force_fail_even_if_llm_passed(self, base_state, passing_eval_result):
        from graph.nodes.evaluator_node import evaluator_node

        with (
            patch("graph.nodes.evaluator_node.groq_client") as mock_groq,
            patch(
                "graph.nodes.evaluator_node.validate_all_mermaid_in_notes",
                return_value=["Diagram 1: Unquoted node labels with ':'"],
            ),
            patch("graph.nodes.evaluator_node.get_eval_mode", return_value="light"),
        ):
            mock_groq.complete_json.return_value = passing_eval_result
            result = evaluator_node(base_state)

        assert result["evaluation_result"].passed is False
        assert result["evaluation_result"].diagram_issues
