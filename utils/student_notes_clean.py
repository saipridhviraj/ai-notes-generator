"""Remove tutor-only and pipeline wrapper leaks from student-facing notes."""

from __future__ import annotations

import re

_TUTOR_LINE = re.compile(
    r"^>\s*\*\*👨‍🏫\s*(TEACHING NOTE|SAY THIS|TIME CHECK|INTERACTIVE MOMENT|"
    r"RAPID-FIRE QUIZ|QUICK ACTIVITY):\*\*.*$",
    re.MULTILINE | re.IGNORECASE,
)
_WRAPPER_BLOCK = re.compile(
    r"^Topic:\s*.+?\n(?:Context:\s*\n)?.*?\nInsert after:\s*\n##[^\n]+\n\nReturn:\s*\n",
    re.MULTILINE | re.DOTALL,
)
_WRAPPER_LINE = re.compile(
    r"^\s*(Topic:|Context:|Insert after:|Return:)\s*.*$",
    re.MULTILINE | re.IGNORECASE,
)
_DETAILS_TUTOR = re.compile(
    r"<details>\s*<summary>.*?(Pre-Session|Post-Session).*?</details>",
    re.DOTALL | re.IGNORECASE,
)


def clean_student_notes(markdown: str) -> str:
    """Strip tutor annotations and Mermaid wrapper scaffolding from student notes."""
    if not markdown:
        return markdown

    text = markdown
    text = _WRAPPER_BLOCK.sub("", text)
    text = _WRAPPER_LINE.sub("", text)
    text = _TUTOR_LINE.sub("", text)
    text = _DETAILS_TUTOR.sub("", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"
