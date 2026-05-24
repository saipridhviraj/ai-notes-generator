"""Parse suggested diagram brief from research writer instructions."""

from __future__ import annotations

import re

_SUGGESTED_HEADING = re.compile(r"^##\s+Suggested Diagrams\s*$", re.MULTILINE | re.IGNORECASE)
_NEXT_H2 = re.compile(r"^##\s+", re.MULTILINE)
_BULLET = re.compile(r"^[-*•]\s+")
_NUMBERED = re.compile(r"^\d+\.\s+")


def parse_suggested_diagrams(research_markdown: str) -> list[str]:
    """Return bullet items under ## Suggested Diagrams (plain-text specs only)."""
    if not research_markdown:
        return []

    match = _SUGGESTED_HEADING.search(research_markdown)
    if not match:
        return []

    rest = research_markdown[match.end() :]
    next_heading = _NEXT_H2.search(rest)
    section = rest[: next_heading.start()] if next_heading else rest

    items: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _BULLET.match(line):
            items.append(_BULLET.sub("", line).strip())
        elif _NUMBERED.match(line):
            items.append(_NUMBERED.sub("", line).strip())

    return [item for item in items if item]
