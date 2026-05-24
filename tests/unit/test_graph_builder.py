"""Tests for graph routing functions — BUG-2 regression: rejected route must exist."""
import pytest
from unittest.mock import MagicMock


class TestRouteAfterTutor:
    def test_rejected_status_routes_to_rejected(self):
        from graph.graph_builder import route_after_tutor
        state = {"status": "rejected", "awaiting_tutor": False}
        assert route_after_tutor(state) == "rejected"

    def test_awaiting_tutor_routes_to_consult_tutor(self):
        from graph.graph_builder import route_after_tutor
        state = {"status": "running", "awaiting_tutor": True}
        assert route_after_tutor(state) == "consult_tutor"

    def test_approved_routes_to_research(self):
        from graph.graph_builder import route_after_tutor
        state = {"status": "running", "awaiting_tutor": False}
        assert route_after_tutor(state) == "research"


class TestRouteAfterEvaluation:
    def test_passed_routes_to_final_response(self):
        from graph.graph_builder import route_after_evaluation
        result = MagicMock()
        result.passed = True
        state = {"evaluation_result": result, "retry_count": 0}
        assert route_after_evaluation(state) == "final_response"

    def test_failed_under_max_routes_to_gap_bridger(self):
        from graph.graph_builder import route_after_evaluation
        result = MagicMock()
        result.passed = False
        state = {"evaluation_result": result, "retry_count": 0}
        assert route_after_evaluation(state) == "gap_bridger"

    def test_failed_at_max_routes_to_final_response(self, monkeypatch):
        from graph.graph_builder import route_after_evaluation
        monkeypatch.setenv("MAX_EVAL_RETRIES", "2")
        result = MagicMock()
        result.passed = False
        state = {"evaluation_result": result, "retry_count": 2}
        assert route_after_evaluation(state) == "final_response_max_retries"

    def test_none_result_routes_to_final_response_max_retries(self):
        from graph.graph_builder import route_after_evaluation
        state = {"evaluation_result": None, "retry_count": 0}
        assert route_after_evaluation(state) == "final_response_max_retries"
