"""Tests for layered Mermaid prompts."""

from prompts.mermaid_prompts import (
    get_mermaid_core_system_prompt,
    get_mermaid_repair_user_prompt,
    get_mermaid_student_notes_hard_rules,
    get_mermaid_supplement_user_prompt,
)
from prompts.mermaid_colors import FILLS_INLINE, TEXT_COLOR


SAMPLE_NOTES = """# Topic

## Introduction

Intro text here.

## Core Concepts

More text.
"""


class TestMermaidCorePrompt:
    def test_core_includes_flowchart_and_quotes(self):
        core = get_mermaid_core_system_prompt()
        assert "flowchart TD" in core
        assert "double-quoted" in core
        assert TEXT_COLOR in core
        assert FILLS_INLINE.split()[0] in core
        assert "NO <br/>" in core
        assert "Emojis are allowed" in core

    def test_hard_rules_for_student_notes(self):
        rules = get_mermaid_student_notes_hard_rules(min_diagrams=4)
        assert "flowchart TD" in rules
        assert "Minimum 4 Mermaid diagrams" in rules
        assert "NO <br/>" in rules
        assert "emoji is fine" in rules


class TestMermaidWrappers:
    def test_supplement_prompt_uses_after_marker(self):
        prompt = get_mermaid_supplement_user_prompt(
            {"topic": "OOP"}, SAMPLE_NOTES, needed=2, existing=0
        )
        assert '"## Introduction"' in prompt
        assert "<!-- after:" in prompt
        assert "EXACTLY this format" in prompt
        assert "add 2 missing" in prompt.lower()
        assert "Topic:" not in prompt or "Do NOT echo Topic" not in prompt
        assert "Return:" not in prompt

    def test_repair_prompt_uses_replace_marker(self):
        prompt = get_mermaid_repair_user_prompt(
            {"topic": "OOP"},
            SAMPLE_NOTES,
            ["Diagram 1: No arrows found"],
            failed_diagrams=[
                {"index": 1, "block": "graph TD\nA-->B", "issues": ["No style"]}
            ],
            targeted_only=True,
        )
        assert "<!-- replace: 1 -->" in prompt
        assert "DIAGRAM 1 — BROKEN" in prompt
        assert "CORRECT OUTPUT FORMAT" in prompt
        assert "Do NOT rewrite any lesson prose" in prompt
