"""Shared gap-bridger patch logic (pipeline + post-completion chat)."""

from __future__ import annotations

import logging
import re
from typing import Any

from services.groq_client import groq_client
from services.prompt_config import get_gap_max_tokens
from prompts.gap_bridger_prompts import (
    get_gap_content_prompt,
    split_gap_content,
)
from utils.mermaid_sanitize import sanitize_markdown_mermaid

# Trailing sections that should always stay at the end of the notes.
# Gap content is inserted BEFORE these sections.
_TRAILING_SECTION_KEYWORDS = (
    "key takeaways",
    "quick revision",
    "revision questions",
    "homework",
    "home work",
    "next class",
    "next session",
)

logger = logging.getLogger(__name__)


def apply_gap_patch(
    *,
    student_notes: str,
    tutor_notes: str,
    research_data: str,
    missing_topics: list[str],
    diagram_issues: list[str],
    alignment_issues: list[str],
    session_id: str | None = None,
    errors: list[str] | None = None,
    stream_node: str = "gap_bridger",
    prompt_builder=None,
) -> dict[str, Any]:
    """
    Patch student/tutor notes via gap-bridger LLM flow.
    Returns dict with student_notes, tutor_notes, errors (partial update).
    """
    errors = list(errors or [])
    if not missing_topics and not diagram_issues and not alignment_issues:
        return {"errors": errors}

    build_prompt = prompt_builder or get_gap_content_prompt
    logger.info(
        "[gap_patch] patching %s topics, %s diagram issues, %s alignment issues",
        len(missing_topics),
        len(diagram_issues),
        len(alignment_issues),
    )

    try:
        gap_content = groq_client.complete(
            prompt=build_prompt(
                missing_topics,
                diagram_issues,
                research_data,
                alignment_issues=alignment_issues,
            ),
            size="small",
            temperature=0.5,
            max_tokens=get_gap_max_tokens(),
            session_id=session_id,
            stream_node=stream_node,
        )

        student_patch, tutor_patch = split_gap_content(gap_content)
        updated_student = student_notes
        updated_tutor = tutor_notes

        if student_patch:
            insertions = _resolve_insertions(student_notes, student_patch, errors)
            updated_student = _merge_sections(student_notes, insertions)

        if tutor_patch:
            tutor_insertions = _resolve_tutor_insertions(tutor_notes, tutor_patch, errors)
            updated_tutor = _merge_sections(tutor_notes, tutor_insertions)
        elif student_patch:
            tutor_patch = (
                "\n\n> **👨‍🏫 TEACHING NOTE:** Content patched after quality review.\n\n"
                + student_patch
            )
            updated_tutor = tutor_notes.rstrip() + tutor_patch + "\n"

        return {
            "student_notes": sanitize_markdown_mermaid(updated_student),
            "tutor_notes": updated_tutor,
            "errors": errors,
        }
    except Exception as e:
        logger.error("[gap_patch] failed | error=%s", e, exc_info=True)
        errors.append(f"Gap patch failed: {e}")
        return {"errors": errors}


def _parse_gap_sections(gap_content: str) -> list[dict]:
    """
    Split gap_content into individual ## sections.
    Returns list of {"insert_after": <anchor>, "content": <section_text>}.
    This avoids an LLM call (and JSON-truncation bugs) for insertion point resolution.
    """
    # Split on ## boundaries, keeping the heading with its content
    parts = re.split(r"\n(?=## )", gap_content.strip())
    sections = [p.strip() for p in parts if p.strip()]
    if not sections:
        return [{"insert_after": "", "content": gap_content}]
    return [{"insert_after": "", "content": s} for s in sections]


def _find_last_content_anchor(notes: str) -> str:
    """
    Find the last ## heading in notes that is NOT a trailing section
    (Key Takeaways, Homework, Quick Revision, Next Class).
    Gap content should be inserted after this anchor.
    """
    headings = re.findall(r"^## .+$", notes, re.MULTILINE)
    anchor = ""
    for h in headings:
        h_lower = h.lower()
        if any(kw in h_lower for kw in _TRAILING_SECTION_KEYWORDS):
            break  # stop at first trailing section
        anchor = h
    return anchor


def _resolve_insertions(student_notes: str, gap_content: str, errors: list) -> list:  # noqa: ARG001
    """
    Resolve insertion points using pure Python heading matching.
    Previously used an LLM (which caused JSON-truncation failures when patch was large).
    """
    sections = _parse_gap_sections(gap_content)
    anchor = _find_last_content_anchor(student_notes)
    # Assign the same anchor to all patches — they get inserted after the last content section
    for s in sections:
        s["insert_after"] = anchor
    return sections


def _resolve_tutor_insertions(tutor_notes: str, tutor_patch: str, errors: list) -> list:  # noqa: ARG001
    """Resolve tutor insertion points using pure Python heading matching."""
    sections = _parse_gap_sections(tutor_patch)
    anchor = _find_last_content_anchor(tutor_notes)
    for s in sections:
        s["insert_after"] = anchor
    return sections


def _merge_sections(notes: str, insertions: list) -> str:
    for insertion in insertions:
        heading = insertion.get("insert_after", "")
        content = insertion.get("content", "")
        if not content:
            continue
        if not heading:
            notes = notes.rstrip() + "\n\n" + content + "\n"
            continue
        if heading not in notes:
            notes = notes.rstrip() + "\n\n" + content + "\n"
            continue
        idx = notes.index(heading)
        newline_idx = notes.find("\n", idx)
        if newline_idx == -1:
            notes = notes + "\n\n" + content + "\n"
        else:
            end_of_heading_line = newline_idx + 1
            notes = notes[:end_of_heading_line] + "\n" + content + "\n" + notes[end_of_heading_line:]
    return notes
