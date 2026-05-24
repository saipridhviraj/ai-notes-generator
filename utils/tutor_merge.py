"""Merge tutor annotation supplements into student notes."""
from __future__ import annotations

import re

from utils.notes_sections import merge_annotations_by_section

_SECTION_MARKER = re.compile(
    r"<!--\s*after:\s*(.+?)\s*-->\s*\n(.*?)(?=<!--\s*after:|$)",
    re.DOTALL | re.IGNORECASE,
)


def merge_tutor_supplements(student_notes: str, supplement: str) -> str:
    """Legacy markdown-marker merge (fallback if JSON handoff fails)."""
    if not supplement or not supplement.strip():
        return student_notes

    blocks = list(_SECTION_MARKER.finditer(supplement))
    if not blocks:
        return student_notes.rstrip() + "\n\n" + supplement.strip() + "\n"

    lines = student_notes.splitlines(keepends=True)
    insertions: list[tuple[int, str]] = []

    for match in blocks:
        heading = match.group(1).strip()
        content = match.group(2).strip()
        if not content:
            continue
        idx = _find_heading_line(lines, heading)
        if idx is None:
            continue
        insert_at = idx + 1
        while insert_at < len(lines) and not lines[insert_at].strip().startswith("#"):
            insert_at += 1
        insertions.append((insert_at, content + "\n\n"))

    insertions.sort(key=lambda x: x[0], reverse=True)
    result_lines = list(lines)
    for pos, block in insertions:
        result_lines.insert(pos, block)

    merged = "".join(result_lines).rstrip() + "\n"
    unmatched = _unmatched_blocks(blocks, lines)
    if unmatched:
        merged = merged.rstrip() + "\n\n" + unmatched + "\n"
    return merged


def merge_tutor_json_handoff(student_notes: str, tutor_json: dict) -> str:
    """Preferred path: section_key → annotations from structured tutor JSON."""
    from utils.notes_sections import annotations_from_tutor_json

    annotations, prep, post = annotations_from_tutor_json(tutor_json)
    return merge_annotations_by_section(student_notes, annotations, prep=prep, post=post)


def _find_heading_line(lines: list[str], heading: str) -> int | None:
    target = heading.lstrip("#").strip().lower()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        text = stripped.lstrip("#").strip().lower()
        if text == target or target in text or text in target:
            return i
    if heading.upper() == "TOP":
        return 0
    return None


def _unmatched_blocks(blocks, lines: list[str]) -> str:
    orphan: list[str] = []
    for match in blocks:
        heading = match.group(1).strip()
        content = match.group(2).strip()
        if not content:
            continue
        if _find_heading_line(lines, heading) is None and heading.upper() != "TOP":
            orphan.append(content)
    return "\n\n".join(orphan)
