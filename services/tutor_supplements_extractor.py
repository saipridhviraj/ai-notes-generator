"""Extract structured tutor supplements from tutor markdown for note.ready events."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from models.tutor_supplements import (
    AssignmentItem,
    PacingItem,
    QuizItem,
    TeachingTipItem,
    TutorSupplements,
)

_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_NUMBERED_LINE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)
_TIME_CHECK_RE = re.compile(
    r"TIME CHECK:\*\*\s*(.+?)(?:\n|$)|⏱️\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)
_QUIZ_ARROW_RE = re.compile(r'^[\s\d\."]*(.+?)\?\s*"?\s*→\s*(.+)$')


def _slug_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:02d}"


def _current_section(text: str, pos: int) -> Optional[str]:
    """Nearest heading before position pos."""
    section: Optional[str] = None
    for match in _HEADING_RE.finditer(text):
        if match.start() > pos:
            break
        section = match.group(2).strip()
    return section


def _extract_blockquote_blocks(text: str) -> List[tuple[str, int]]:
    """Return (combined blockquote text, start pos) for each contiguous block."""
    blocks: List[tuple[str, int]] = []
    lines = text.splitlines()
    current: List[str] = []
    start = 0
    in_block = False

    for i, line in enumerate(lines):
        if line.startswith(">"):
            if not in_block:
                start = sum(len(ln) + 1 for ln in lines[:i])
                in_block = True
            current.append(line.lstrip(">").strip())
        else:
            if in_block and current:
                blocks.append(("\n".join(current), start))
                current = []
                in_block = False
    if current:
        blocks.append(("\n".join(current), start))
    return blocks


def _parse_quiz_lines(body: str, section: Optional[str], kind: str, start_index: int) -> List[QuizItem]:
    items: List[QuizItem] = []
    idx = start_index
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        arrow = _QUIZ_ARROW_RE.match(line)
        if arrow:
            items.append(
                QuizItem(
                    id=_slug_id("quiz", idx),
                    kind=kind,  # type: ignore[arg-type]
                    question=arrow.group(1).strip().strip('"'),
                    answer=arrow.group(2).strip(),
                    section=section,
                )
            )
            idx += 1
            continue
        num = _NUMBERED_LINE_RE.match(line)
        if num:
            content = num.group(2).strip()
            if "→" in content:
                q, a = content.split("→", 1)
                items.append(
                    QuizItem(
                        id=_slug_id("quiz", idx),
                        kind=kind,  # type: ignore[arg-type]
                        question=q.strip().strip('"').rstrip("?") + "?",
                        answer=a.strip(),
                        section=section,
                    )
                )
            else:
                items.append(
                    QuizItem(
                        id=_slug_id("quiz", idx),
                        kind=kind,  # type: ignore[arg-type]
                        question=content.strip('"'),
                        answer=None,
                        section=section,
                    )
                )
            idx += 1
    return items


def _extract_quizzes(text: str) -> List[QuizItem]:
    quizzes: List[QuizItem] = []
    idx = 1
    for block, pos in _extract_blockquote_blocks(text):
        upper = block.upper()
        section = _current_section(text, pos)
        if "RAPID-FIRE QUIZ" in upper or "RAPID FIRE QUIZ" in upper:
            quizzes.extend(_parse_quiz_lines(block, section, "rapid_fire", idx))
            idx += len(quizzes)
        elif "EXPECTED ANSWERS" in upper:
            # Revision / end-of-lesson answers
            for line in block.splitlines():
                if "EXPECTED ANSWERS" in line.upper():
                    continue
                num = _NUMBERED_LINE_RE.match(line.strip())
                if num:
                    quizzes.append(
                        QuizItem(
                            id=_slug_id("quiz", idx),
                            kind="revision",
                            question=f"Revision question {num.group(1)}",
                            answer=num.group(2).strip(),
                            section=section,
                        )
                    )
                    idx += 1
    return quizzes


def _extract_pacing(text: str) -> List[PacingItem]:
    pacing: List[PacingItem] = []
    idx = 1
    for block, pos in _extract_blockquote_blocks(text):
        if "TIME CHECK" not in block.upper() and "⏱️" not in block:
            continue
        section = _current_section(text, pos)
        marker = None
        for m in _TIME_CHECK_RE.finditer(block):
            marker = (m.group(1) or m.group(2) or "").strip()
            break
        pacing.append(
            PacingItem(
                id=_slug_id("pacing", idx),
                section=section,
                minutes_marker=marker,
                teaching_tip=block.strip(),
            )
        )
        idx += 1
    return pacing


def _extract_teaching_tips(text: str) -> List[TeachingTipItem]:
    tips: List[TeachingTipItem] = []
    idx = 1
    for block, pos in _extract_blockquote_blocks(text):
        upper = block.upper()
        if not any(k in upper for k in ("TEACHING NOTE", "TEACHING TIP", "TEACHING STRATEGY", "SAY THIS")):
            continue
        if "TIME CHECK" in upper or "RAPID-FIRE QUIZ" in upper or "ASSIGNMENT DELIVERY" in upper:
            continue
        tips.append(
            TeachingTipItem(
                id=_slug_id("tip", idx),
                section=_current_section(text, pos),
                tip=block.strip(),
            )
        )
        idx += 1
    return tips


def _extract_homework_section(text: str) -> Optional[str]:
    match = re.search(r"^##\s+.*Homework.*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    rest = text[start:]
    end_match = re.search(r"^##\s+", rest, re.MULTILINE)
    section_body = rest[: end_match.start()] if end_match else rest
    return section_body.strip()


def _extract_assignments(text: str) -> List[AssignmentItem]:
    homework = _extract_homework_section(text)
    if not homework:
        return []

    title = "Homework"
    description_parts: List[str] = []
    rubric_notes: Optional[str] = None

    for block, _ in _extract_blockquote_blocks(homework):
        upper = block.upper()
        if "ASSIGNMENT DELIVERY" in upper:
            rubric_notes = (rubric_notes or "") + block.strip() + "\n"
        elif "WHY THIS HOMEWORK" in upper or "GIVE THEM A PROMPT" in upper:
            rubric_notes = (rubric_notes or "") + block.strip() + "\n"
        else:
            description_parts.append(block)

    # Non-blockquote body (tables, headings)
    stripped = homework
    for block, _ in _extract_blockquote_blocks(homework):
        stripped = stripped.replace("> " + block.replace("\n", "\n> "), "")
    stripped = re.sub(r"^>\s.*$", "", stripped, flags=re.MULTILINE).strip()
    if stripped:
        description_parts.insert(0, stripped)

    description = "\n\n".join(p for p in description_parts if p).strip()
    if not description and not rubric_notes:
        return []

    return [
        AssignmentItem(
            id="assignment-01",
            title=title,
            description=description or rubric_notes or "See homework section in tutor guide.",
            rubric_notes=rubric_notes.strip() if rubric_notes else None,
            section="Homework",
        )
    ]


def extract_supplements(tutor_markdown: str) -> TutorSupplements:
    """Parse tutor markdown into structured tutor-only RAG items."""
    if not tutor_markdown or not tutor_markdown.strip():
        return TutorSupplements()

    return TutorSupplements(
        quizzes=_extract_quizzes(tutor_markdown),
        assignments=_extract_assignments(tutor_markdown),
        pacing=_extract_pacing(tutor_markdown),
        teaching_tips=_extract_teaching_tips(tutor_markdown),
    )


def supplements_filename(student_filename: str) -> str:
    if student_filename.endswith("_student.md"):
        return student_filename.replace("_student.md", "_supplements.json")
    stem = Path(student_filename).stem
    return f"{stem}_supplements.json"


def write_supplements_json(supplements: TutorSupplements, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(supplements.model_dump_json(indent=2), encoding="utf-8")
    return path.resolve()
