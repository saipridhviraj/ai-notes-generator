"""Fast heuristic evaluation — no LLM call (saves ~20–40s on local Ollama)."""
from __future__ import annotations

import re

from graph.state import EvaluationResult
from services.prompt_config import get_min_mermaid_diagrams


def heuristic_evaluate(
    student_notes: str,
    tutor_notes: str,
    keywords: list[str],
    mermaid_issues: list[str],
    alignment_issues: list[str] | None = None,
) -> EvaluationResult:
    notes_lower = (student_notes or "").lower()
    tutor_lower = (tutor_notes or "").lower()
    alignment_issues = alignment_issues or []

    missing = [kw for kw in keywords if kw.lower() not in notes_lower]
    keyword_penalty = 10 * len(missing)
    student_score = max(0, 100 - keyword_penalty)

    min_len = 400
    if len(student_notes or "") < min_len:
        student_score = min(student_score, 70)

    min_mermaid = get_min_mermaid_diagrams()
    mermaid_count = len(re.findall(r"```mermaid", student_notes or "", re.I))
    if mermaid_count < min_mermaid:
        student_score = max(0, student_score - 10 * (min_mermaid - mermaid_count))

    if mermaid_issues:
        student_score = max(0, student_score - 5 * len(mermaid_issues))

    tutor_score = 100
    if "teaching note" not in tutor_lower and "👨‍🏫" not in tutor_notes:
        tutor_score -= 25
    if len(tutor_notes or "") < len(student_notes or "") * 0.5:
        tutor_score -= 15
    tutor_score = max(0, tutor_score - 10 * len(alignment_issues))

    passed = (
        student_score >= 80
        and tutor_score >= 80
        and not mermaid_issues
        and not alignment_issues
    )

    return EvaluationResult(
        student_notes_score=student_score,
        tutor_notes_score=tutor_score,
        missing_topics=missing,
        diagram_issues=mermaid_issues,
        alignment_issues=alignment_issues if alignment_issues else [],
        passed=passed,
    )
