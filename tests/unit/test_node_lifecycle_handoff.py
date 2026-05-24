"""Tests for node handoff lifecycle."""

from utils.helpers import create_session, get_session
from utils.node_lifecycle import advance_after_node_complete, mark_node_started


def test_mark_node_started_sets_phase():
    create_session("lc-1", {"status": "running", "errors": [], "output_files": [], "retry_count": 0})
    mark_node_started("lc-1", "research")
    session = get_session("lc-1")
    assert session["current_node"] == "research"
    assert session["node_phase"] == "starting"
    assert "Starting" in (session.get("status_detail") or "")


def test_advance_after_research_completes():
    create_session(
        "lc-2",
        {
            "status": "running",
            "research_data": "## brief",
            "errors": [],
            "output_files": [],
            "retry_count": 0,
        },
    )
    session = get_session("lc-2")
    session["current_node"] = "research"
    advance_after_node_complete("lc-2", "research", session["state"])
    session = get_session("lc-2")
    assert session["current_node"] == "student_notes"
    assert session["node_phase"] == "starting"
