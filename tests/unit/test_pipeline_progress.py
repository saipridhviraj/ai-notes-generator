"""Tests for pipeline progress with output-based step completion."""

from utils.pipeline_progress import get_pipeline_progress, pipeline_node_has_output


class TestPipelineOutputAware:
    def test_research_done_while_handoff_to_student(self):
        state = {
            "status": "running",
            "research_data": "## Instructions\nDone.",
            "retry_count": 0,
        }
        progress = get_pipeline_progress("research", "running", 0, state=state, node_phase="starting")
        research = next(s for s in progress["pipeline_steps"] if s["id"] == "research")
        student = next(s for s in progress["pipeline_steps"] if s["id"] == "student_notes")
        assert research["state"] == "done"
        assert student["state"] == "active"

    def test_pipeline_node_has_output_research(self):
        assert pipeline_node_has_output("research", {"research_data": "x"}) is True
        assert pipeline_node_has_output("research", {}) is False

    def test_running_at_student_notes(self):
        state = {"status": "running", "student_notes": None, "retry_count": 0}
        p = get_pipeline_progress("student_notes", "running", 0, state=state)
        active = [s for s in p["pipeline_steps"] if s["state"] == "active"]
        assert len(active) == 1
        assert active[0]["id"] == "student_notes"
