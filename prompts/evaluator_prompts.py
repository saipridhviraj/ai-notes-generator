"""
Evaluator prompts — strict but fast for Qwen 3.5 9B via Ollama.

Stage 1: python_pre_check (no LLM)
Stage 2: compact LLM evaluator (diagram blocks + headings only)
Stage 3: repair guard via should_abort_repair / MAX_REPAIR_ATTEMPTS
"""

from __future__ import annotations

import re

from prompts.common import DIRECT_OUTPUT_RULE
from prompts.mermaid_colors import FILLS, FILLS_INLINE, TEXT_COLOR


def python_pre_check(
    student_notes: str,
    tutor_notes: str,
    plan: dict,
    min_diagrams: int = 4,
) -> dict:
    """
    Fast structural pre-check — no LLM.

    Returns evaluator-shaped dict with pre_check_only=True.
    If passed=False, callers may skip the LLM evaluator.
    """
    student_score = 100
    tutor_score = 100
    missing_topics: list[str] = []
    diagram_issues: list[str] = []
    alignment_issues: list[str] = []

    mermaid_blocks = re.findall(r"```mermaid", student_notes or "")
    diagram_count = len(mermaid_blocks)
    if diagram_count < min_diagrams:
        deficit = min_diagrams - diagram_count
        diagram_issues.append(
            f"Only {diagram_count} Mermaid diagram(s) found — need {min_diagrams} (missing {deficit})"
        )
        student_score -= 10 * deficit

    blocks = re.findall(r"```mermaid\s*(.*?)```", student_notes or "", re.DOTALL)
    for idx, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            diagram_issues.append(f"Diagram {idx}: empty block")
            student_score -= 5
            continue

        if lines[0] not in ("flowchart TD", "flowchart LR", "graph TD", "graph LR"):
            diagram_issues.append(
                f"Diagram {idx}: bad header '{lines[0]}' — must be 'flowchart TD' or 'flowchart LR'"
            )
            student_score -= 5

        if "<br" in block.lower():
            diagram_issues.append(
                f"Diagram {idx}: contains <br/> in label — replace with short text"
            )
            student_score -= 5

        node_lines = [line for line in lines if re.match(r"^[A-Za-z_]\w*\[", line)]
        for nl in node_lines:
            if not re.match(r'^[A-Za-z_]\w*\["', nl):
                diagram_issues.append(
                    f"Diagram {idx}: unquoted label '{nl[:40]}' — wrap in double quotes"
                )
                student_score -= 5
                break

        if not any(line.startswith("style ") for line in lines):
            diagram_issues.append(f"Diagram {idx}: no style lines — every node needs a style")
            student_score -= 5

        if not any(fill in block for fill in FILLS):
            diagram_issues.append(
                f"Diagram {idx}: no allowed fill color found — use one of: {FILLS_INLINE}"
            )
            student_score -= 5

        subgraph_names = re.findall(r"subgraph\s+(\w+)", block)
        for sg_name in subgraph_names:
            if re.search(rf"style\s+{sg_name}\b", block):
                diagram_issues.append(
                    f"Diagram {idx}: 'style {sg_name}' styles a subgraph ID — "
                    f"style only the nodes inside '{sg_name}', not the subgraph itself"
                )
                student_score -= 5

    subtopics = plan.get("subtopics") or []
    h2_headings = re.findall(r"^##\s+(.+)$", student_notes or "", re.MULTILINE)
    h2_lower = [h.lower() for h in h2_headings]

    for sub in subtopics:
        sub_lower = sub.lower()
        matched = any(
            sub_lower in h or any(word in h for word in sub_lower.split() if len(word) > 4)
            for h in h2_lower
        )
        if not matched:
            missing_topics.append(sub)
            student_score -= 15

    notes_lower = (student_notes or "").lower()
    if "revision" not in notes_lower and "quick revision" not in notes_lower:
        missing_topics.append("Revision / Quick Check section missing")
        student_score -= 10
    if "homework" not in notes_lower and "home work" not in notes_lower:
        missing_topics.append("Homework section missing")
        student_score -= 10

    if len(student_notes or "") < 400:
        missing_topics.append("Student notes too short — appears to be a stub")
        student_score -= 15

    tutor_h2 = set(re.findall(r"^##\s+(.+)$", tutor_notes or "", re.MULTILINE))
    student_h2 = set(h2_headings)

    for h in student_h2 - tutor_h2:
        alignment_issues.append(f"Section '## {h}' in student notes but missing from tutor notes")
        tutor_score -= 15
    for h in tutor_h2 - student_h2:
        alignment_issues.append(f"Section '## {h}' in tutor notes but missing from student notes")
        tutor_score -= 10

    teaching_note_count = len(re.findall(
        r"TEACHING NOTE|TEACHING STRATEGY|SAY THIS|INTERACTIVE MOMENT",
        tutor_notes or ""
    ))
    if len(student_h2) > 0 and teaching_note_count < len(student_h2) // 2:
        alignment_issues.append(
            f"Only {teaching_note_count} teaching annotation blocks "
            f"for {len(student_h2)} sections — add TEACHING STRATEGY / SAY THIS / INTERACTIVE MOMENT"
        )
        tutor_score -= 10

    student_score = max(0, student_score)
    tutor_score = max(0, tutor_score)

    critical_fail = bool(diagram_issues)
    passed = (
        student_score >= 80
        and tutor_score >= 80
        and not critical_fail
        and not missing_topics
    )

    return {
        "student_notes_score": student_score,
        "tutor_notes_score": tutor_score,
        "missing_topics": missing_topics,
        "diagram_issues": diagram_issues,
        "alignment_issues": alignment_issues,
        "passed": passed,
        "pre_check_only": True,
    }


def get_light_evaluator_system_prompt(*, supplement_mode: bool = False) -> str:
    tutor_check = (
        "Tutor (supplement mode): prep checklist, post checklist, TEACHING STRATEGY or SAY THIS or INTERACTIVE MOMENT on most H2 sections."
        if supplement_mode
        else "Tutor: TEACHING STRATEGY or SAY THIS or INTERACTIVE MOMENT on most H2 sections; prep and post checklists present."
    )
    return f"""You are a STRUCTURAL quality checker for AI-generated lesson notes.

You receive a SUMMARY — not the full notes. Do NOT ask for more content.

Scoring (start at 100 for student, 100 for tutor):
- Deduct 15 per plan subtopic with no matching H2 section (fuzzy match allowed)
- Deduct 10 per MISSING KEYWORD listed in the summary
- Deduct 10 if REVISION or HOMEWORK section is absent
- Deduct 10 if MERMAID COUNT is below minimum
- Deduct 5 per DIAGRAM ISSUE listed
- Deduct 15 if student notes length is under 400 chars
- {tutor_check}
- Deduct 10 per H2 section missing TEACHING STRATEGY / SAY THIS / INTERACTIVE MOMENT in tutor notes
- Deduct 15 per student H2 absent from tutor notes
- Deduct 10 per tutor-only H2 with no matching student section

PASS: student >= 80 AND tutor >= 80 AND no diagram issues listed.
If any DIAGRAM ISSUE is listed, set passed=false regardless of scores.

{DIRECT_OUTPUT_RULE}

Return ONLY valid JSON:
{{
  "student_notes_score": <int 0-100>,
  "tutor_notes_score": <int 0-100>,
  "missing_topics": ["subtopic or keyword gaps"],
  "diagram_issues": ["each issue exactly as listed"],
  "alignment_issues": ["heading mismatches, missing annotations"],
  "passed": <true|false>
}}"""


def get_light_evaluator_user_prompt(summary: str) -> str:
    return (
        "Evaluate STRUCTURE only using this summary. Do not request more text.\n\n"
        f"{summary}"
    )


def get_evaluator_system_prompt(*, supplement_mode: bool = False) -> str:
    student_rules = """\
STUDENT NOTES (100 pts):
- Start at 100
- Deduct 10 per keyword missing from notes
- Deduct 5 per broken or malformed Mermaid diagram
- Deduct 5 if revision questions section is missing
- Deduct 5 if homework section is missing
- Deduct 10 if notes are a stub (under 400 chars)"""

    if supplement_mode:
        tutor_rules = """\
TUTOR NOTES (100 pts) — merged student + annotations:
- 20 pts: prep checklist present (details block or TEACHING STRATEGY block at top)
- 30 pts: TEACHING STRATEGY or SAY THIS or INTERACTIVE MOMENT on most H2 sections
- 20 pts: at least one TIME CHECK or pacing marker
- 15 pts: post-session checklist at bottom
- 15 pts: student content preserved (not rewritten)"""
    else:
        tutor_rules = """\
TUTOR NOTES (100 pts):
- 25 pts: all diagrams from student notes present
- 25 pts: TEACHING STRATEGY / SAY THIS / INTERACTIVE MOMENT for each section
- 25 pts: collapsible prep checklist at top
- 25 pts: collapsible post-session checklist at bottom"""

    return f"""\
You are a strict quality evaluator for AI-generated lesson notes.

{student_rules}

{tutor_rules}

MERMAID CHECK — for each diagram block verify:
- First line: flowchart TD or flowchart LR
- Every node has a style line
- Fills from: {FILLS_INLINE}
- Text color: {TEXT_COLOR}
- At least one arrow (-->)
- No unquoted labels (labels must use double quotes)
- No <br/> inside labels
- Subgraph names are NOT styled directly

PASS: both scores >= 80. Any diagram issue = passed=false.

{DIRECT_OUTPUT_RULE}

Return ONLY valid JSON:
{{
  "student_notes_score": <int 0-100>,
  "tutor_notes_score": <int 0-100>,
  "missing_topics": ["topic1", ...],
  "diagram_issues": ["issue description", ...],
  "alignment_issues": ["description", ...],
  "passed": <true|false>
}}"""


def get_evaluator_user_prompt(
    student_notes: str,
    tutor_notes: str,
    keywords: list,
    max_chars: int | None = None,
    *,
    supplement_mode: bool = False,
) -> str:
    del max_chars  # compact diagram-only payload; kept for API compatibility
    keywords_str = ", ".join(keywords)

    student_diagrams = re.findall(r"```mermaid.*?```", student_notes or "", re.DOTALL)
    student_headings = re.findall(r"^##\s+.+$", student_notes or "", re.MULTILINE)
    tutor_headings = re.findall(r"^##\s+.+$", tutor_notes or "", re.MULTILINE)
    teaching_notes = re.findall(r"(?:TEACHING NOTE|TEACHING STRATEGY|SAY THIS|INTERACTIVE MOMENT).{0,80}", tutor_notes or "")

    diagram_section = (
        "\n\n".join(student_diagrams[:6])
        if student_diagrams
        else "(no diagrams found)"
    )

    mode_note = (
        "Tutor notes = merged student + annotations (supplement mode).\n"
        if supplement_mode
        else "Tutor notes should mirror all student sections plus inline annotations.\n"
    )

    return (
        f"Keywords that MUST appear in notes: {keywords_str}\n\n"
        f"{mode_note}\n"
        f"Student H2 sections:\n" + "\n".join(f"  {h}" for h in student_headings) + "\n\n"
        "Tutor H2 sections:\n" + "\n".join(f"  {h}" for h in tutor_headings[:20]) + "\n\n"
        f"Teaching annotation samples ({len(teaching_notes)} total):\n"
        + "\n".join(f"  {t[:80]}" for t in teaching_notes[:5]) + "\n\n"
        f"─── MERMAID DIAGRAMS TO EVALUATE ───\n"
        f"{diagram_section}"
    )


MAX_REPAIR_ATTEMPTS = 2


def should_abort_repair(attempt: int, diagram_issues: list[str]) -> tuple[bool, str]:
    """Returns (should_abort, reason). attempt is 1-based repair attempt count."""
    if attempt > MAX_REPAIR_ATTEMPTS:
        return True, (
            f"Repair aborted after {MAX_REPAIR_ATTEMPTS} attempts. "
            f"Remaining diagram issues accepted with warnings: {diagram_issues}"
        )
    return False, ""
