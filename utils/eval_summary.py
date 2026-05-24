"""Build a compact structural summary for light LLM evaluation."""

from __future__ import annotations

import re
from typing import TypedDict

from services.prompt_config import get_min_mermaid_diagrams
from utils.helpers import extract_mermaid_blocks
from utils.notes_sections import parse_markdown_sections


class HeadingAlignment(TypedDict):
    matched: list[str]
    student_only: list[str]
    tutor_only: list[str]
    missing_annotations: list[str]


def _norm_h2(title: str) -> str:
    return re.sub(r"^#+\s*", "", title).strip().lower()


def _h2_titles(markdown: str) -> list[str]:
    sections = parse_markdown_sections(markdown or "")
    titles: list[str] = []
    for sec in sections:
        if sec.level != 2:
            continue
        title = re.sub(r"^#+\s*", "", sec.key).strip()
        if title:
            titles.append(title)
    return titles


def _has_section(markdown: str, *needles: str) -> bool:
    lower = (markdown or "").lower()
    return any(n.lower() in lower for n in needles)


def _has_tutor_annotation(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "teaching note" in lower
        or "say this" in lower
        or "time check" in lower
        or "👨‍🏫" in (text or "")
    )


def _missing_tutor_annotations(student_notes: str, tutor_notes: str) -> list[str]:
    student_secs = [s for s in parse_markdown_sections(student_notes) if s.level == 2]
    tutor_secs = parse_markdown_sections(tutor_notes or "")
    tutor_by_title = {
        _norm_h2(s.key): s.content for s in tutor_secs if s.level == 2
    }

    missing: list[str] = []
    for sec in student_secs:
        title = re.sub(r"^#+\s*", "", sec.key).strip()
        key = _norm_h2(title)
        tutor_body = tutor_by_title.get(key, "")
        if not tutor_body and tutor_notes:
            tutor_body = tutor_notes if _has_tutor_annotation(tutor_notes) else ""
        if not _has_tutor_annotation(tutor_body):
            missing.append(title)
    return missing


def compute_heading_alignment(student_notes: str, tutor_notes: str) -> HeadingAlignment:
    """Compare student vs tutor H2 headings and tutor annotation coverage."""
    student_h2 = _h2_titles(student_notes)
    tutor_h2 = _h2_titles(tutor_notes)
    student_by_norm = {_norm_h2(t): t for t in student_h2}
    tutor_by_norm = {_norm_h2(t): t for t in tutor_h2}

    matched_norm = set(student_by_norm) & set(tutor_by_norm)
    return {
        "matched": [student_by_norm[k] for k in sorted(matched_norm)],
        "student_only": [student_by_norm[k] for k in student_by_norm if k not in tutor_by_norm],
        "tutor_only": [tutor_by_norm[k] for k in tutor_by_norm if k not in student_by_norm],
        "missing_annotations": _missing_tutor_annotations(student_notes, tutor_notes),
    }


def compute_alignment_issues(student_notes: str, tutor_notes: str) -> list[str]:
    """Human-readable alignment gaps for evaluator + gap bridger."""
    align = compute_heading_alignment(student_notes, tutor_notes)
    issues: list[str] = []
    for title in align["student_only"]:
        issues.append(f"Tutor missing section heading: {title}")
    for title in align["tutor_only"]:
        issues.append(f"Tutor-only section (not in student notes): {title}")
    for title in align["missing_annotations"]:
        issues.append(f"Missing tutor annotation on section: {title}")
    return issues


def _tutor_coverage(student_notes: str, tutor_notes: str) -> list[str]:
    """One line per student H2: whether tutor block has an annotation."""
    align = compute_heading_alignment(student_notes, tutor_notes)
    missing = set(align["missing_annotations"])
    lines: list[str] = []
    for title in _h2_titles(student_notes):
        status = "missing" if title in missing else "yes"
        lines.append(f"  - {title}: TEACHING NOTE/SAY THIS {status}")
    return lines


def _mermaid_lines(markdown: str) -> list[str]:
    blocks = extract_mermaid_blocks(markdown or "")
    lines: list[str] = []
    for i, block in enumerate(blocks, start=1):
        first = (block.strip().splitlines() or ["?"])[0].strip()
        lines.append(f"  - Diagram {i}: {first}")
    return lines


def _heading_alignment_lines(align: HeadingAlignment) -> list[str]:
    lines = [
        f"MATCHED H2 HEADINGS ({len(align['matched'])}): "
        + (", ".join(align["matched"]) if align["matched"] else "(none)"),
        f"STUDENT-ONLY H2 ({len(align['student_only'])}): "
        + (", ".join(align["student_only"]) if align["student_only"] else "(none)"),
        f"TUTOR-ONLY H2 ({len(align['tutor_only'])}): "
        + (", ".join(align["tutor_only"]) if align["tutor_only"] else "(none)"),
        f"MISSING TUTOR ANNOTATIONS ({len(align['missing_annotations'])}): "
        + (
            ", ".join(align["missing_annotations"])
            if align["missing_annotations"]
            else "(none)"
        ),
    ]
    return lines


def build_eval_summary(
    *,
    plan: dict,
    student_notes: str,
    tutor_notes: str,
    mermaid_issues: list[str],
    supplement_mode: bool = False,
) -> str:
    """Structural checklist only — no full note bodies."""
    keywords = plan.get("keywords") or []
    subtopics = plan.get("subtopics") or []
    notes_lower = (student_notes or "").lower()
    missing_kw = [kw for kw in keywords if kw.lower() not in notes_lower]

    blocks = extract_mermaid_blocks(student_notes or "")
    min_diagrams = get_min_mermaid_diagrams()
    h2s = _h2_titles(student_notes)
    align = compute_heading_alignment(student_notes, tutor_notes)
    python_alignment = compute_alignment_issues(student_notes, tutor_notes)

    lines = [
        "STRUCTURAL EVALUATION SUMMARY (do not infer content quality — checklist only)",
        "",
        f"PLAN SUBTOPICS ({len(subtopics)}): " + ", ".join(subtopics),
        f"PLAN KEYWORDS ({len(keywords)}): " + ", ".join(keywords),
        "",
        f"STUDENT H2 SECTIONS ({len(h2s)}):",
    ]
    if h2s:
        lines.extend(f"  - {t}" for t in h2s)
    else:
        lines.append("  - (none)")
    lines.extend(
        [
            "",
            "HEADING ALIGNMENT (student vs tutor — trust these lists):",
        ]
    )
    lines.extend(f"  {line}" for line in _heading_alignment_lines(align))
    lines.extend(
        [
            "",
            f"STUDENT LENGTH: {len(student_notes or '')} chars",
            f"REVISION SECTION: {'yes' if _has_section(student_notes, 'revision', 'review question') else 'missing'}",
            f"HOMEWORK SECTION: {'yes' if _has_section(student_notes, 'homework', 'assignment') else 'missing'}",
            "",
            f"MERMAID COUNT: {len(blocks)} (minimum {min_diagrams})",
        ]
    )
    mermaid_detail = _mermaid_lines(student_notes)
    if mermaid_detail:
        lines.append("MERMAID TYPES:")
        lines.extend(mermaid_detail)
    lines.append(
        "PYTHON MERMAID ISSUES: "
        + ("none" if not mermaid_issues else "; ".join(mermaid_issues))
    )
    lines.extend(
        [
            "",
            "PYTHON MISSING KEYWORDS: "
            + ("none" if not missing_kw else ", ".join(missing_kw)),
            "PYTHON ALIGNMENT ISSUES: "
            + ("none" if not python_alignment else "; ".join(python_alignment)),
            "",
            "TUTOR MODE: "
            + ("supplement (annotations merged into student notes)" if supplement_mode else "full handoff"),
            f"TUTOR LENGTH: {len(tutor_notes or '')} chars",
            f"TUTOR PREP CHECKLIST: {'yes' if _has_section(tutor_notes, '<details>', 'prep', 'before class') else 'missing'}",
            f"TUTOR POST CHECKLIST: {'yes' if _has_section(tutor_notes, 'post-session', 'after class', 'wrap-up') else 'missing'}",
            "",
            "TUTOR ANNOTATIONS BY STUDENT H2:",
        ]
    )
    coverage = _tutor_coverage(student_notes, tutor_notes)
    lines.extend(coverage if coverage else ["  - (no H2 sections parsed)"])

    return "\n".join(lines)
