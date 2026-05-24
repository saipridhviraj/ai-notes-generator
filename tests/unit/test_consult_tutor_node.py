"""P0 tests for consult_tutor_node — BUG-2 regression: rejection halts graph."""
import pytest
from unittest.mock import patch
from graph.nodes.consult_tutor_node import consult_tutor_node


@pytest.fixture
def approved_state(base_state):
    state = dict(base_state)
    state["awaiting_tutor"] = False
    return state


@pytest.fixture
def rejected_state(base_state):
    state = dict(base_state)
    state["awaiting_tutor"] = False
    return state


@pytest.fixture
def awaiting_state(base_state):
    state = dict(base_state)
    state["tutor_response"] = None
    state["awaiting_tutor"] = True
    return state


class TestTutorApproval:
    def test_approved_sets_planner_verified_true(self, approved_state):
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value="approved"),
        ):
            result = consult_tutor_node(approved_state)
        assert result["planner_verified"] is True
        assert result["awaiting_tutor"] is False
        assert result["status"] == "running"

    def test_approved_clears_tutor_response(self, approved_state):
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value="approved"),
        ):
            result = consult_tutor_node(approved_state)
        assert result["tutor_response"] is None


class TestTutorRejection:
    """BUG-2 regression — rejection must stop the pipeline."""

    def test_rejection_sets_verified_false(self, rejected_state):
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value="rejected: Topic is out of scope"),
        ):
            result = consult_tutor_node(rejected_state)
        assert result["planner_verified"] is False

    def test_rejection_sets_status_rejected(self, rejected_state):
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value="rejected: Topic is out of scope"),
        ):
            result = consult_tutor_node(rejected_state)
        assert result["status"] == "rejected"

    def test_rejection_clears_awaiting_tutor(self, rejected_state):
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value="rejected: Topic is out of scope"),
        ):
            result = consult_tutor_node(rejected_state)
        assert result["awaiting_tutor"] is False


class TestTutorTimeout:
    def test_timeout_auto_approves(self, awaiting_state):
        awaiting_state["errors"] = []
        with (
            patch("graph.nodes.consult_tutor_node.is_tutor_timed_out", return_value=True),
            patch("graph.nodes.consult_tutor_node.interrupt") as mock_interrupt,
        ):
            result = consult_tutor_node(awaiting_state)
        mock_interrupt.assert_not_called()
        assert result["planner_verified"] is True
        assert "auto-approved" in result["errors"][0]


class TestKeywordInjection:
    def test_add_keyword_pattern_injected(self, base_state):
        state = dict(base_state)
        state["awaiting_tutor"] = False
        feedback = "approved with feedback: add recursion and memoization"
        with (
            patch("utils.helpers.is_tutor_timed_out", return_value=False),
            patch("graph.nodes.consult_tutor_node.interrupt", return_value=feedback),
        ):
            result = consult_tutor_node(state)
        updated_plan = result["planner_output"]
        keyword_strings = [k.lower() for k in updated_plan.keywords]
        assert "recursion" in keyword_strings or "recursion and memoization" in keyword_strings
