"""Dev/free-tier tutor notes prompts — trimmed for low TPM but still rich annotations."""

import json

_TUTOR_JSON_SHAPE = """
{
  "icebreaker": "> **👨‍🏫 ICEBREAKER (10 mins):**\\n> Ask: \\"[Opening question to the class]\\"\\n> Then say: \\"[Hook to build excitement]\\"",
  "prep": "<details>\\n<summary>🎯 <b>TEACHING PREP</b></summary>\\n\\n### Session Overview\\n- **Duration:** [X] minutes\\n- **Goal:** [Main goal]\\n\\n### Before You Start\\n- [ ] Review all sections\\n- [ ] Test diagrams render\\n\\n</details>",
  "section_annotations": [
    {
      "section_key": "## Exact H2 heading from handoff (emoji included)",
      "annotations": "> **👨‍🏫 TEACHING STRATEGY:**\\n> - [What to focus on]\\n> - **Time:** [X] mins\\n\\n> **👨‍🏫 SAY THIS:**\\n> \\"[Verbal script in simple English]\\"\\n\\n> **👨‍🏫 INTERACTIVE MOMENT:**\\n> **Ask:** \\"[Question to the class]\\"\\n> Students will say: [expected answers]\\n> **Then say:** \\"[Your follow-up]\\"\\n\\n> **👨‍🏫 TIME CHECK:** You should be ~[X] mins into session"
    }
  ],
  "post": "<details>\\n<summary>📊 <b>POST-SESSION CHECKLIST</b></summary>\\n\\n### After Class:\\n- [ ] [Key concept 1] was understood\\n- [ ] Homework assignment is clear\\n\\n</details>",
  "quick_reference": "| If This Happens... | Do This... |\\n|---|---|\\n| **Students look confused** | Pause, ask \\"What\\'s unclear?\\", use different analogy |\\n| **Students disengaged** | Ask direct question, share real-world story |\\n| **Running out of time** | Skip examples, cover core concepts only |"
}
""".strip()


def get_tutor_supplement_system_prompt() -> str:
    return (
        """You are an expert instructional designer creating a Teacher's Annotated Guide.

The student lesson already exists. Your job is to add TEACHING ANNOTATIONS ONLY.

Return ONLY valid JSON matching this exact shape:
"""
        + _TUTOR_JSON_SHAPE
        + """

Annotation guidelines (use 2–3 per section):
- **👨‍🏫 TEACHING STRATEGY:** pacing, what to focus on, common misconceptions
- **👨‍🏫 SAY THIS:** exact verbal script in simple English (1–2 sentences the teacher says out loud)
- **👨‍🏫 TIME CHECK:** e.g. "You should be ~20 mins into session"
- **👨‍🏫 INTERACTIVE MOMENT:** question to ask + expected student response + teacher follow-up
- **👨‍🏫 ANALOGY:** simple real-world analogy for the concept

Rules:
- section_key MUST match handoff keys exactly (copy-paste, including emoji and numbering)
- Annotate EVERY section key in the handoff — do not skip any
- icebreaker: 10-min warm-up BEFORE definitions to build rapport
- prep: collapsible session overview with duration, goals, before-you-start checklist
- post: collapsible post-session checklist
- quick_reference: "If This Happens → Do This" table for classroom situations
- SAY THIS must be conversational, not lecture-style
- Return ONLY valid JSON — no markdown wrapper, no preamble"""
    )


def get_tutor_supplement_user_prompt(plan: dict, section_handoff: list[dict]) -> str:
    keywords_str = ", ".join(plan.get("keywords", []))
    handoff_json = json.dumps(section_handoff, indent=2)
    return (
        f"Add tutor annotations for this lesson.\n\n"
        f"TOPIC: {plan.get('topic')}\n"
        f"KEYWORDS (weave into SAY THIS where natural): {keywords_str}\n\n"
        f"SECTION HANDOFF (use section_key exactly — copy-paste with emoji):\n"
        f"{handoff_json}\n\n"
        f"Return:\n"
        f"- icebreaker: opening engagement for the first 10 minutes\n"
        f"- prep: collapsible session overview\n"
        f"- section_annotations: 2–3 annotation blocks per section\n"
        f"- post: collapsible post-session checklist\n"
        f"- quick_reference: classroom troubleshooting table"
    )


def get_tutor_notes_system_prompt(tutor_example: str = "") -> str:  # noqa: ARG001
    return """You are an expert instructional designer creating a Teacher's Annotated Guide.

The student notes are complete. Your job is to ANNOTATE ONLY — never rewrite lesson content.

Add these annotations:
  > **👨‍🏫 TEACHING STRATEGY:** pacing, what to focus on, misconceptions to address
  > **👨‍🏫 SAY THIS:** exact verbal script in simple English (what the teacher says out loud)
  > **👨‍🏫 INTERACTIVE MOMENT:** question to ask + expected student response + teacher follow-up
  > **👨‍🏫 TIME CHECK:** "You should be ~X mins into session"
  <details> TEACHING PREP collapsible at the very top
  10-minute ICEBREAKER before the first definition
  <details> POST-SESSION CHECKLIST at the bottom
  Quick Reference for Teachers table at the very end

RULES:
1. DO NOT rewrite or regenerate student content — copy every section, diagram, and table verbatim
2. ONLY add inline teaching annotations (2–3 blocks per section)
3. Add ICEBREAKER at the very start (before any definitions)
4. Add TEACHING PREP <details> block at the top
5. Add POST-SESSION CHECKLIST <details> at the bottom
6. Add Quick Reference for Teachers table at the very end
7. Output ONLY the full annotated markdown. No preamble."""


def get_tutor_notes_user_prompt(plan: dict, student_notes: str) -> str:
    keywords_str = ", ".join(plan.get("keywords", []))
    notes_block = student_notes if student_notes else ""
    return (
        f"Annotate the student notes below — do NOT rewrite the lesson content.\n\n"
        f"TOPIC   : {plan.get('topic')}\n"
        f"KEYWORDS: {keywords_str}\n\n"
        f"Add for EVERY section: TEACHING STRATEGY, SAY THIS, INTERACTIVE MOMENT, TIME CHECK.\n"
        f"Add ICEBREAKER at the very start, TEACHING PREP at the top, POST-SESSION CHECKLIST at the bottom.\n"
        f"Add Quick Reference for Teachers table at the very end.\n"
        f"Keep 100% of student markdown intact.\n\n"
        f"STUDENT NOTES TO ANNOTATE:\n{notes_block}"
    )
