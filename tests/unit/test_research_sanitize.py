"""Tests for research output sanitization."""

from utils.research_sanitize import sanitize_research_output


def test_strips_fenced_code_blocks():
    raw = (
        "## Instructions\n"
        "Cover decorators.\n\n"
        "```python\n"
        "def foo():\n"
        "    pass\n"
        "```\n\n"
        "More bullets."
    )
    cleaned = sanitize_research_output(raw)
    assert "```" not in cleaned
    assert "def foo" not in cleaned
    assert "Cover decorators." in cleaned
    assert "More bullets." in cleaned


def test_empty_and_none_safe():
    assert sanitize_research_output("") == ""
    assert sanitize_research_output("no code here") == "no code here"
