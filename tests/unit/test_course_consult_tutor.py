"""Course day auto-approve in consult_tutor_node."""
from unittest.mock import patch

from graph.nodes.consult_tutor_node import consult_tutor_node


class TestCourseAutoApprove:
    def test_skips_interrupt_when_auto_approve(self):
        state = {
            "session_id": "sess-course-1",
            "planner_output": None,
            "errors": [],
        }
        with patch("graph.nodes.consult_tutor_node.get_session") as mock_get:
            mock_get.return_value = {"auto_approve_tutor": True}
            result = consult_tutor_node(state)
        assert result["planner_verified"] is True
        assert result["status"] == "running"
