"""
Mermaid prompt layer — optimized for Qwen 3.5 9B (Ollama).

- Unified color palette via prompts.mermaid_colors
- Emojis allowed in labels (matches teaching examples)
- <br/> banned — strict Mermaid v11 parsing
- Supplement/repair prompts avoid task-metadata echo traps
- Repair notes context capped at 1500 chars
"""

from __future__ import annotations

from prompts.common import DIRECT_OUTPUT_RULE
from prompts.mermaid_colors import FILLS_INLINE, STROKES_INLINE, TEXT_COLOR

MERMAID_CORE_SYSTEM_PROMPT = f"""You are a Mermaid diagram generator. Output ONLY a valid ```mermaid block.

RULES — follow every one:

1. HEADER — first line must be exactly:
   flowchart TD   (top-down)
   flowchart LR   (left-right)

2. NODE LABELS — always double-quoted. Emojis are allowed and encouraged.
   CORRECT:  A["🔍 Search Step"]   B["⚙️ Processing"]
   WRONG:    A[Search Step]        B[Validation: Check]

3. NODE SHAPE — rectangular only.
   CORRECT:  A["text"]
   WRONG:    A(("text"))   A{{"text"}}   A[/"text"/]

4. NO <br/> INSIDE LABELS — use short text instead. Never use <br/> or <br>.
   WRONG:  A["Step One<br/>details here"]
   CORRECT: A["Step One — details"]

5. COLORS — use ONLY these values:
   Fills  : {FILLS_INLINE}
   Strokes: {STROKES_INLINE}
   Text   : {TEXT_COLOR} (ALWAYS — mandatory on every style line)

6. EVERY NODE needs a style line WITH color:{TEXT_COLOR}:
   style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px,color:{TEXT_COLOR}
   style B fill:#312e81,stroke:#7c3aed,stroke-width:2px,color:{TEXT_COLOR}
   ← The ,color:{TEXT_COLOR} at the end is NOT OPTIONAL — include it every time

7. SUBGRAPHS — if used, NEVER style the subgraph name. Style only nodes inside.
   WRONG:  style MyGroup fill:#312e81,...
   CORRECT: style A fill:#312e81,...   (A is a node inside the subgraph)

8. ARROWS — only these two forms:
   A --> B
   A -->|"label text"| B

9. STRUCTURE — minimum 3 nodes, all connected, no isolated nodes.

Output ONLY the ```mermaid block. No explanation, no preamble."""


MERMAID_ONE_SHOT_SUPPLEMENT = f"""\
<!-- after: ## 🔍 How It Works -->

```mermaid
flowchart LR

A["🙋 User Query"]
B["⚙️ Processing"]
C["📤 Response"]

A --> B
B --> C

style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px,color:{TEXT_COLOR}
style B fill:#312e81,stroke:#7c3aed,stroke-width:2px,color:{TEXT_COLOR}
style C fill:#0f3460,stroke:#06b6d4,stroke-width:2px,color:{TEXT_COLOR}
```"""


MERMAID_ONE_SHOT_REPAIR = f"""\
<!-- replace: 2 -->

```mermaid
flowchart TD

A["📥 Input"]
B["🔄 Validation"]
C["✅ Output"]

A --> B
B --> C

style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px,color:{TEXT_COLOR}
style B fill:#312e81,stroke:#7c3aed,stroke-width:2px,color:{TEXT_COLOR}
style C fill:#0f3460,stroke:#10b981,stroke-width:2px,color:{TEXT_COLOR}
```"""


def get_mermaid_core_system_prompt() -> str:
    return MERMAID_CORE_SYSTEM_PROMPT


def get_mermaid_supplement_system_prompt() -> str:
    return MERMAID_CORE_SYSTEM_PROMPT


def get_mermaid_student_notes_hard_rules(min_diagrams: int = 4) -> str:
    return f"""\
MERMAID RULES (apply inside every ```mermaid block):
- First line MUST be exactly: flowchart TD  or  flowchart LR  (nothing else)
- Node labels: always double-quoted — A["Label text"]  — NO emojis inside labels
- Rectangular nodes only — no (( )), {{ }}, [/ /]
- NO <br/> inside labels — keep text short instead (max 5 words per label)
- EVERY node MUST have a style line — no exceptions
- Style line format: style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px,color:{TEXT_COLOR}
- CRITICAL: color:{TEXT_COLOR} is REQUIRED at the end of EVERY style line
- Fills   : {FILLS_INLINE}
- Strokes : {STROKES_INLINE}
- Text    : color:{TEXT_COLOR} — THIS IS MANDATORY on every single style line
- Subgraphs: NEVER use style on a subgraph name — only style node IDs inside
- Arrows: A --> B  or  A -->|"label"| B
- Minimum 3 nodes, all connected, no isolated nodes
- Minimum {min_diagrams} Mermaid diagrams in the full notes file
- ONLY use flowchart or hierarchy layouts — NO sequenceDiagram, classDiagram, mindmap
- Output simpler diagrams rather than complex broken ones

CORRECT style example (copy this pattern exactly):
style A fill:#1e3a5f,stroke:#2563eb,stroke-width:2px,color:{TEXT_COLOR}
style B fill:#312e81,stroke:#7c3aed,stroke-width:2px,color:{TEXT_COLOR}
style C fill:#4c1d95,stroke:#d946ef,stroke-width:2px,color:{TEXT_COLOR}"""


def _extract_h2_headings(markdown: str) -> list[str]:
    headings: list[str] = []
    for line in (markdown or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("###"):
            headings.append(stripped[3:].strip())
    return headings


def _section_context(notes: str, heading: str, max_chars: int = 300) -> str:
    lines = (notes or "").splitlines()
    target = heading.strip().lower()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and not line.strip().startswith("###"):
            text = line.strip()[3:].strip().lower()
            if text == target or target in text or text in target:
                start = i + 1
                break
    if start is None:
        return ""
    chunk: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("## ") and not line.strip().startswith("###"):
            break
        if line.strip():
            chunk.append(line.strip())
        if sum(len(s) for s in chunk) >= max_chars:
            break
    text = " ".join(chunk)
    return text[:max_chars] + "…" if len(text) > max_chars else text


def get_mermaid_supplement_user_prompt(
    plan: dict,
    student_notes: str,
    needed: int,
    existing: int,
) -> str:
    topic = plan.get("topic") or "Lesson topic"
    notes_snippet = student_notes[:5000] + "\n...(truncated)..." if len(student_notes) > 5000 else student_notes

    headings = _extract_h2_headings(student_notes)
    heading_lines: list[str] = []
    for h in headings[: max(needed + 2, 5)]:
        ctx = _section_context(student_notes, h, max_chars=120)
        heading_lines.append(f'  "## {h}" — {ctx or "(no context)"}')
    heading_block = "\n".join(heading_lines) or "  (pick from existing ## headings)"

    return (
        f"TASK: Add {needed} missing Mermaid diagram(s) to lesson notes.\n"
        f"Lesson: {topic}\n"
        f"Diagrams already in notes: {existing}. Need {needed} more.\n\n"
        f"Pick the {needed} most important section(s) from this list that have NO diagram yet:\n"
        f"{heading_block}\n\n"
        f"For each diagram output EXACTLY this format — nothing else:\n\n"
        f"{MERMAID_ONE_SHOT_SUPPLEMENT}\n\n"
        f"RULES:\n"
        f"- Output ONLY <!-- after: ## Heading --> followed by the ```mermaid block\n"
        f"- Copy the heading text EXACTLY as it appears in the list above (emoji included)\n"
        f"- Do NOT output any explanation, preamble, or extra text\n"
        f"- Do NOT rewrite or repeat the lesson prose\n\n"
        f"EXISTING NOTES (read headings and content — do not rewrite):\n"
        f"{notes_snippet}\n\n"
        f"{DIRECT_OUTPUT_RULE}"
    )


def _format_repair_history(repair_history: list[dict] | None) -> str:
    if not repair_history:
        return ""
    lines = ["PREVIOUS FAILED ATTEMPTS — do NOT repeat these mistakes:"]
    for entry in repair_history:
        attempt = entry.get("attempt", "?")
        issues_before = entry.get("issues_before") or []
        issues_after = entry.get("issues_after") or []
        patch_preview = (entry.get("patch_preview") or "")[:300]
        lines.append(f"\nAttempt {attempt}:")
        if issues_before:
            lines.append("  Errors before : " + "; ".join(issues_before[:3]))
        if issues_after:
            lines.append("  Still broken  : " + "; ".join(issues_after[:3]))
        if patch_preview:
            lines.append(f"  Patch sent (truncated):\n{patch_preview}")
    return "\n".join(lines)


def _format_fix_hints(fix_hints: list[str] | None) -> str:
    if not fix_hints:
        return ""
    return "FIX GUIDANCE:\n" + "\n".join(f"- {h}" for h in fix_hints)


def _format_broken_diagrams(failed_diagrams: list[dict] | None) -> str:
    if not failed_diagrams:
        return ""
    parts: list[str] = []
    for item in failed_diagrams:
        idx = item.get("index", "?")
        issues = item.get("issues") or []
        block = (item.get("block") or "").strip()
        issue_lines = "\n".join(f"  - {i}" for i in issues) or "  - (unknown error)"
        parts.append(
            f"DIAGRAM {idx} — BROKEN:\n"
            f"Errors:\n{issue_lines}\n\n"
            f"Broken code:\n```mermaid\n{block}\n```\n\n"
            f"Replace it with:\n<!-- replace: {idx} -->\n```mermaid\n...\n```"
        )
    return "\n\n---\n\n".join(parts)


def get_mermaid_repair_user_prompt(
    plan: dict,
    student_notes: str,
    issues: list[str],
    *,
    failed_diagrams: list[dict] | None = None,
    repair_history: list[dict] | None = None,
    fix_hints: list[str] | None = None,
    targeted_only: bool = False,
) -> str:
    del targeted_only  # unified repair prompt; kept for call-site compatibility
    topic = plan.get("topic") or "Lesson topic"
    issue_lines = "\n".join(f"- {i}" for i in issues) or "- (unknown)"
    history_block = _format_repair_history(repair_history)
    hints_block = _format_fix_hints(fix_hints)
    broken_block = _format_broken_diagrams(failed_diagrams)

    notes_snippet = (student_notes or "")[:1500]
    if len(student_notes or "") > 1500:
        notes_snippet += "\n...(truncated — fix only the broken diagram, do not rewrite notes)..."

    sections = [
        f"TASK: Fix broken Mermaid diagram(s) only. Do NOT rewrite any lesson prose.\n"
        f"Lesson: {topic}\n\n"
        f"ALL ERRORS:\n{issue_lines}",
    ]
    if hints_block:
        sections.append(hints_block)
    if broken_block:
        sections.append(broken_block)

    sections.append(f"CORRECT OUTPUT FORMAT:\n{MERMAID_ONE_SHOT_REPAIR}")

    if history_block:
        sections.append(history_block)

    sections.append(
        f"NOTES CONTEXT (headings only — do not rewrite):\n{notes_snippet}\n\n"
        f"Output ONLY <!-- replace: N --> + corrected ```mermaid block(s). Nothing else.\n"
        f"{DIRECT_OUTPUT_RULE}"
    )

    return "\n\n".join(sections)
