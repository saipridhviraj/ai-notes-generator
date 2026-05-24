"""Tests for node lifecycle UI updates."""
from unittest.mock import patch

from utils.graph_node_wrapper import wrap_graph_node


def test_wrap_graph_node_marks_start_before_run():
    seen: list[str] = []

    def inner(state):
        seen.append("run")
        return {"ok": True}

    wrapped = wrap_graph_node("research", inner)
    with patch("utils.graph_node_wrapper.mark_node_started") as mock_mark:
        result = wrapped({"session_id": "s1"})

    mock_mark.assert_called_once_with("s1", "research")
    assert result == {"ok": True}
    assert seen == ["run"]
