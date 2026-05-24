"""Parse student markdown into keyed sections for tutor handoff."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NoteSection:
    """One heading block in student notes."""

    key: str  # exact heading line, e.g. "## 🔧 Decorators"
    level: int
    content: str
    start_line: int
    end_line: int  # exclusive — line index after section body


def parse_markdown_sections(markdown: str) -> list[NoteSection]:
    """Split markdown into sections keyed by heading line."""
    if not markdown or not markdown.strip():
        return []

    lines = markdown.splitlines()
    headings: list[tuple[int, str, int]] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        headings.append((i, stripped, level))

    if not headings:
        return [
            NoteSection(
                key="_document",
                level=0,
                content=markdown.strip(),
                start_line=0,
                end_line=len(lines),
            )
        ]

    sections: list[NoteSection] = []
    for idx, (start, key, level) in enumerate(headings):
        body_start = start + 1
        if idx + 1 < len(headings):
            end_line = headings[idx + 1][0]
        else:
            end_line = len(lines)
        content = "\n".join(lines[body_start:end_line]).strip()
        sections.append(
            NoteSection(
                key=key,
                level=level,
                content=content,
                start_line=start,
                end_line=end_line,
            )
        )
    return sections


def build_tutor_handoff(
    sections: list[NoteSection],
    preview_chars: int = 320,
    max_sections: int = 10,
) -> list[dict]:
    """
    H2 sections only for tutor JSON — keeps output small and avoids H3/code-heading noise.
    Falls back to level-1 title sections if no H2 exists.
    """
    h2 = [s for s in sections if s.level == 2]
    if not h2:
        h2 = [s for s in sections if s.level == 1]
    if len(h2) > max_sections:
        h2 = h2[:max_sections]
    return build_section_handoff(h2, preview_chars=preview_chars)


def build_section_handoff(sections: list[NoteSection], preview_chars: int = 320) -> list[dict]:
    """Summary for tutor LLM — keys + short preview, not full student text."""
    handoff: list[dict] = []
    for sec in sections:
        preview = sec.content
        if len(preview) > preview_chars:
            preview = preview[:preview_chars].rstrip() + "..."
        handoff.append(
            {
                "section_key": sec.key,
                "preview": preview,
                "char_count": len(sec.content),
            }
        )
    return handoff


def _lookup_annotation(annotations: dict[str, str], section_key: str) -> str | None:
    if section_key in annotations:
        return annotations[section_key]
    normalized = section_key.strip()
    if normalized in annotations:
        return annotations[normalized]
    target = _heading_text(normalized)
    for key, value in annotations.items():
        if _heading_text(key) == target:
            return value
    return None


def _heading_text(heading: str) -> str:
    text = heading.lstrip("#").strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).lower()


def merge_annotations_by_section(
    student_notes: str,
    annotations: dict[str, str],
    *,
    prep: str | None = None,
    post: str | None = None,
) -> str:
    """Insert tutor annotations after each section body; preserve original markdown."""
    sections = parse_markdown_sections(student_notes)
    if not sections:
        base = student_notes.rstrip()
        if post and post.strip():
            base = base + "\n\n" + post.strip()
        return base + "\n"

    lines = student_notes.splitlines(keepends=True)
    insertions: list[tuple[int, str]] = []

    if prep and prep.strip():
        insertions.append((0, prep.strip() + "\n\n"))

    for sec in sections:
        ann = _lookup_annotation(annotations, sec.key)
        if not ann or not ann.strip():
            continue
        insertions.append((sec.end_line, ann.strip() + "\n\n"))

    insertions.sort(key=lambda x: x[0], reverse=True)
    for line_no, block in insertions:
        lines.insert(line_no, block)

    merged = "".join(lines).rstrip()
    if post and post.strip():
        merged = merged + "\n\n" + post.strip()
    return merged + "\n"


def annotations_from_tutor_json(raw: dict) -> tuple[dict[str, str], str | None, str | None]:
    """Normalize tutor JSON response into section_key → annotations map."""
    result: dict[str, str] = {}
    prep = raw.get("prep") or raw.get("prep_checklist")
    if isinstance(prep, str) and prep.strip():
        prep = prep.strip()
    else:
        prep = None

    post = raw.get("post") or raw.get("post_checklist")
    if isinstance(post, str) and post.strip():
        post = post.strip()
    else:
        post = None

    items = raw.get("section_annotations") or raw.get("sections") or []
    if isinstance(items, dict):
        for key, value in items.items():
            if value and str(value).strip():
                result[str(key)] = str(value).strip()
        return result, prep, post

    if isinstance(items, list):
        for row in items:
            if not isinstance(row, dict):
                continue
            key = row.get("section_key") or row.get("key") or row.get("heading")
            ann = row.get("annotations") or row.get("content") or row.get("tutor_notes")
            if key and ann and str(ann).strip():
                result[str(key)] = str(ann).strip()
    return result, prep, post
