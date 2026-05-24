from prompts.common import DIRECT_OUTPUT_RULE
from services.prompt_config import use_diagram_pipeline


_TUTOR_PATCH_MARKER = "===TUTOR_PATCHES==="


def _diagram_fix_line(diagram_issues: list) -> str:
    if use_diagram_pipeline():
        return (
            "DIAGRAM FIXES (add <!-- diagram: ## Heading --> placeholders or fix listed issues — "
            "NEVER output ```mermaid``` blocks):\n"
            + ("\n".join(f"- {d}" for d in diagram_issues) or "- (none)")
            + "\n\n"
        )
    return (
        f"DIAGRAM FIXES (output corrected ```mermaid blocks only for listed issues):\n"
        f"{chr(10).join(f'- {d}' for d in diagram_issues) or '- (none)'}\n\n"
    )


def get_gap_content_prompt(
    missing_topics: list,
    diagram_issues: list,
    research_data: str,
    alignment_issues: list | None = None,
) -> str:
    topic_count = len([t for t in missing_topics if t])
    missing_str = "\n".join(f"- {t}" for t in missing_topics) or "- (none)"
    alignment_str = "\n".join(f"- {a}" for a in (alignment_issues or [])) or "- (none)"
    research_snippet = (research_data or "")[:1500]
    diagram_block = _diagram_fix_line(diagram_issues) if diagram_issues else ""
    return (
        f"You are patching gaps in EXISTING lesson notes — do NOT write a full lesson.\n\n"
        f"OUTPUT EXACTLY {topic_count} SECTION(S) — one ## section per bullet below. No more, no less.\n\n"
        f"MISSING TOPICS ({topic_count} items — write ONE compact section for each):\n"
        f"{missing_str}\n\n"
        f"{diagram_block if diagram_issues else ''}"
        f"ALIGNMENT FIXES (tutor annotations only):\n"
        f"{alignment_str}\n\n"
        f"REFERENCE (for accuracy — do not copy verbatim):\n"
        f"{research_snippet}\n\n"
        f"STRICT RULES:\n"
        f"- Write EXACTLY {topic_count} ## section(s) — match each bullet above one-to-one\n"
        f"- Each section: max 120 words. Short, focused. No repetition.\n"
        f"- DO NOT duplicate any section. Each topic appears ONCE only.\n"
        f"- Match emoji + heading style of surrounding notes (e.g. ## ❓ Quick Revision Questions)\n"
        f"- Do NOT regenerate content that already exists in the notes\n"
        f"- Fix only the diagrams listed — "
        f"{'add <!-- diagram --> placeholders, never Mermaid' if use_diagram_pipeline() else 'use approved dark-theme colors and explicit node styles'}\n"
        f"- If alignment fixes listed, after student patches output EXACTLY:\n"
        f"  {_TUTOR_PATCH_MARKER}\n"
        f"  then add > **👨‍🏫 TEACHING NOTE:** for each affected heading. Do NOT rewrite student text.\n"
        f"- If no alignment fixes, omit {_TUTOR_PATCH_MARKER} entirely.\n"
        f"- {DIRECT_OUTPUT_RULE}\n"
        f"- Output ONLY the patch markdown. No preamble. STOP after {topic_count} section(s)."
    )


def split_gap_content(gap_content: str) -> tuple[str, str]:
    """Split student patches from tutor alignment patches."""
    marker = _TUTOR_PATCH_MARKER
    if marker not in gap_content:
        return gap_content.strip(), ""
    student_part, tutor_part = gap_content.split(marker, 1)
    return student_part.strip(), tutor_part.strip()


def get_chat_patch_prompt(
    missing_topics: list,
    diagram_issues: list,
    research_data: str,
    alignment_issues: list | None = None,
) -> str:
    """Prompt tuned for post-completion user chat (routes through gap patch)."""
    request = missing_topics[0] if missing_topics else "Improve the notes"
    if request.startswith("User edit request: "):
        request = request[len("User edit request: ") :]
    research_snippet = (research_data or "")[:1500]
    return (
        f"You are editing EXISTING lesson notes based on a tutor's chat request.\n\n"
        f"USER REQUEST:\n{request}\n\n"
        f"WRITER INSTRUCTIONS REFERENCE (for accuracy):\n{research_snippet}\n\n"
        f"Rules:\n"
        f"- Apply ONLY what the user asked — do not rewrite unrelated sections\n"
        f"- Output compact markdown patches (## sections, fixes, or tutor TEACHING NOTE blocks)\n"
        f"- Node labels with colons MUST be quoted in Mermaid: A[\"Label: text\"]\n"
        f"- Do NOT use style on subgraph IDs in Mermaid\n"
        f"- If tutor annotations are needed, after student patches output exactly:\n"
        f"  {_TUTOR_PATCH_MARKER}\n"
        f"  then tutor-only markdown with > **👨‍🏫 TEACHING NOTE:** blocks\n"
        f"- {DIRECT_OUTPUT_RULE}\n"
        f"- Output ONLY patch markdown. No preamble."
    )


def get_insertion_point_prompt(student_notes: str, gap_content: str) -> str:
    notes_snippet = student_notes[:4000] if len(student_notes) > 4000 else student_notes
    return (
        f"Insert the patch sections into existing notes at the best logical location.\n\n"
        f"EXISTING NOTES (truncated if long):\n{notes_snippet}\n\n"
        f"PATCH CONTENT:\n{gap_content}\n\n"
        f"Return ONLY a JSON array:\n"
        f'[{{"insert_after": "## exact heading from existing notes", "content": "## patch section..."}}]\n\n'
        f"{DIRECT_OUTPUT_RULE}\n"
        f"If no good anchor exists, use insert_after: \"\" to append at end."
    )
