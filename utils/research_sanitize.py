"""Strip code from research briefs — research must be instructions only."""

import re

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_MULTI_BLANK = re.compile(r"\n{3,}")


def sanitize_research_output(text: str) -> str:
    """Remove fenced code blocks; research should not emit runnable examples."""
    if not text:
        return text
    cleaned = _CODE_FENCE.sub("", text)
    return _MULTI_BLANK.sub("\n\n", cleaned).strip()
