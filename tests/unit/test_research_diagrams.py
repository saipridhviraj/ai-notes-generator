"""Tests for suggested diagram parsing from research briefs."""

from utils.research_diagrams import parse_suggested_diagrams


class TestParseSuggestedDiagrams:
    def test_extracts_bullets_under_heading(self):
        text = """## Writing Goals
Cover OOP basics.

## Suggested Diagrams
- After Introduction: flowchart — class blueprint → object instance
- After Inheritance: hierarchy — Animal → Dog, Cat

## Must-Cover Keywords
- class
"""
        assert parse_suggested_diagrams(text) == [
            "After Introduction: flowchart — class blueprint → object instance",
            "After Inheritance: hierarchy — Animal → Dog, Cat",
        ]

    def test_case_insensitive_heading(self):
        text = "## suggested diagrams\n* Flow for decorators\n"
        assert parse_suggested_diagrams(text) == ["Flow for decorators"]

    def test_numbered_list(self):
        text = "## Suggested Diagrams\n1. Sequence: request → middleware → handler\n"
        assert parse_suggested_diagrams(text) == ["Sequence: request → middleware → handler"]

    def test_missing_section_returns_empty(self):
        assert parse_suggested_diagrams("## Writing Goals\nNo diagrams here.") == []

    def test_stops_at_next_h2(self):
        text = """## Suggested Diagrams
- Diagram A

## Key Concepts
- Should not include this
"""
        assert parse_suggested_diagrams(text) == ["Diagram A"]
