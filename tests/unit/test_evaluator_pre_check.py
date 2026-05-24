"""Tests for python_pre_check and repair abort guard."""

from prompts.evaluator_prompts import MAX_REPAIR_ATTEMPTS, python_pre_check, should_abort_repair


GOOD_BLOCK = """```mermaid
flowchart TD
A["Start"] --> B["End"]
style A fill:#1a1a2e,stroke:#7c3aed,stroke-width:2px,color:#e2e8f0
style B fill:#16213e,stroke:#2563eb,stroke-width:2px,color:#e2e8f0
```"""

PLAN = {
    "topic": "OOP",
    "subtopics": ["Introduction", "Core Concepts"],
    "keywords": ["class", "object"],
}


class TestPythonPreCheck:
    def test_passes_with_valid_structure(self):
        notes = (
            "# Topic\n\n## Introduction\n\nText.\n\n## Core Concepts\n\nMore.\n\n"
            "## Revision\n\nQ1\n\n## Homework\n\nDo reading.\n\n"
            + GOOD_BLOCK * 4
        )
        tutor = notes.replace("Text.", "> **👨‍🏫 TEACHING NOTE:** Intro.\n\nText.")
        result = python_pre_check(notes, tutor, PLAN, min_diagrams=4)
        assert result["pre_check_only"] is True
        assert result["diagram_issues"] == []
        assert result["passed"] is True

    def test_fails_on_br_in_diagram(self):
        bad = """```mermaid
flowchart TD
A["Line<br/>break"] --> B["End"]
style A fill:#1a1a2e,stroke:#7c3aed,stroke-width:2px,color:#e2e8f0
style B fill:#16213e,stroke:#2563eb,stroke-width:2px,color:#e2e8f0
```"""
        notes = "# T\n\n## Introduction\n\nx\n\n## Core Concepts\n\ny\n\n" + bad * 4
        result = python_pre_check(notes, notes, PLAN, min_diagrams=4)
        assert any("<br/>" in i for i in result["diagram_issues"])
        assert result["passed"] is False


class TestShouldAbortRepair:
    def test_allows_up_to_max_attempts(self):
        assert should_abort_repair(1, ["Diagram 1: bad"])[0] is False
        assert should_abort_repair(2, ["Diagram 1: bad"])[0] is False

    def test_aborts_after_max(self):
        abort, reason = should_abort_repair(MAX_REPAIR_ATTEMPTS + 1, ["Diagram 1: bad"])
        assert abort is True
        assert "Repair aborted" in reason
