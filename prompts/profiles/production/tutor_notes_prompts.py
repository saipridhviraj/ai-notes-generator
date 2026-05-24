"""Production tutor notes prompts — richer annotations matching reference format."""

from prompts.common import DIRECT_OUTPUT_RULE, SIMPLE_ENGLISH_RULE

_TUTOR_JSON_SHAPE = """
{
  "icebreaker": "> **👨‍🏫 ICEBREAKER (10 mins):**\\n> Ask: \\"[Opening question to the class]\\"\\n> Then deliver: \\"[Hook statement to build excitement]\\"",
  "prep": "<details>\\n<summary>🎯 <b>TEACHING PREP - Click to Expand</b></summary>\\n\\n### Session Overview\\n- **Duration:** [X] minutes\\n- **Style:** Interactive, question-driven\\n- **Goal:** [Main goal]\\n\\n### Before You Start\\n- [ ] Review all sections\\n- [ ] Test diagrams render\\n- [ ] Prepare real-world examples\\n\\n</details>",
  "section_annotations": [
    {
      "section_key": "## Exact H2 heading from handoff (emoji included)",
      "annotations": "> **👨‍🏫 TEACHING STRATEGY:**\\n> - [What to focus on]\\n> - **Time:** [X] mins\\n\\n> **👨‍🏫 SAY THIS:**\\n> \\"[Exact verbal script — 1–2 sentences in simple English]\\"\\n\\n> **👨‍🏫 INTERACTIVE MOMENT:**\\n> **Ask:** \\"[Question to the class]\\"\\n> Students will say: [expected answers]\\n> **Then say:** \\"[Your response that builds on their answer]\\"\\n\\n> **👨‍🏫 TIME CHECK:** You should be ~[X] mins into session"
    }
  ],
  "post": "<details>\\n<summary>📊 <b>POST-SESSION CHECKLIST - Click to Expand</b></summary>\\n\\n### After Class, Verify:\\n- [ ] [Key concept 1] was understood\\n- [ ] [Key concept 2] was understood\\n- [ ] Homework assignment is clear\\n\\n### What Worked Well:\\n-\\n\\n### What to Improve Next Time:\\n-\\n\\n</details>",
  "quick_reference": "| If This Happens... | Do This... |\\n|---|---|\\n| **Students look confused** | Pause, ask \\"What\\'s unclear?\\", use different analogy |\\n| **Students disengaged** | Ask direct question, share industry story |\\n| **Running out of time** | Prioritize core concepts, skip examples |\\n| **Ahead of schedule** | More Q&A, live demo |"
}
""".strip()


def get_tutor_supplement_system_prompt() -> str:
    return (
        """You are an expert instructional designer creating a Teacher's Annotated Guide.

The student lesson already exists as keyed sections. Your job is to add TEACHING ANNOTATIONS ONLY.

Return ONLY valid JSON matching this exact shape:
"""
        + _TUTOR_JSON_SHAPE
        + """

Annotation guidelines per section (use ALL that apply — do not limit to just one):
- **👨‍🏫 TEACHING STRATEGY:** pacing, what to focus on, common misconceptions, board-work tips
- **👨‍🏫 SAY THIS:** exact verbal script in simple English (1–3 sentences the teacher says out loud)
- **👨‍🏫 TIME CHECK:** e.g. "You should be ~20 mins into session"
- **👨‍🏫 INTERACTIVE MOMENT:** specific question to ask the class, expected student responses, and how to build on them
- **👨‍🏫 RAPID-FIRE QUIZ:** 3–5 quick Q→A pairs after comparison or contrast sections
- **👨‍🏫 ANALOGY:** a simple real-world analogy to explain the concept
- **👨‍🏫 CRITICAL DIAGRAM:** teaching tips for key diagrams (what to emphasise, what to draw on board)

Rules:
- section_key MUST match handoff keys exactly (copy-paste, including emoji and numbering)
- Annotate EVERY section key in the handoff — do not skip any
- Rich annotations: 2–4 annotation blocks per section (not just one)
- icebreaker: opening 10-min warm-up to build rapport BEFORE definitions
- prep: collapsible session overview with duration, style, goals, before-you-start checklist
- post: collapsible post-session checklist + what worked / what to improve fields
- quick_reference: table of "If This Happens → Do This" for common classroom situations
- SAY THIS scripts must be in simple English — conversational, not lecture-style
- INTERACTIVE MOMENT must include: the question, expected student answer, teacher follow-up
- """
        + DIRECT_OUTPUT_RULE
        + """
- Return ONLY valid JSON — no markdown wrapper, no preamble"""
    )


def get_tutor_supplement_user_prompt(plan: dict, section_handoff: list[dict]) -> str:
    import json

    keywords_str = ", ".join(plan.get("keywords", []))
    handoff_json = json.dumps(section_handoff, indent=2)
    return (
        f"Add rich tutor annotations for this lesson.\n\n"
        f"TOPIC: {plan.get('topic')}\n"
        f"KEYWORDS (weave into SAY THIS where natural): {keywords_str}\n\n"
        f"SECTION HANDOFF (use section_key exactly — copy-paste with emoji):\n"
        f"{handoff_json}\n\n"
        f"Return:\n"
        f"- icebreaker: opening engagement for the first 10 minutes\n"
        f"- prep: collapsible session overview checklist\n"
        f"- section_annotations: 2–4 annotation blocks per section (STRATEGY, SAY THIS, INTERACTIVE MOMENT, TIME CHECK)\n"
        f"- post: collapsible post-session checklist\n"
        f"- quick_reference: classroom troubleshooting table\n\n"
        f"{SIMPLE_ENGLISH_RULE}"
    )


def get_tutor_notes_system_prompt(tutor_example: str = "") -> str:
    return f"""You are an expert instructional designer creating a Teacher's Annotated Guide.

The student notes are complete. Your job is to ANNOTATE ONLY — never rewrite lesson content.

Replicate this annotation style exactly:
  > **👨‍🏫 TEACHING STRATEGY:** pacing, focus points, misconceptions to address
  > **👨‍🏫 SAY THIS:** exact verbal script in simple English (what the teacher says out loud)
  > **👨‍🏫 INTERACTIVE MOMENT:** question to ask, expected student response, teacher follow-up
  > **👨‍🏫 TIME CHECK:** "You should be ~X mins into session"
  > **👨‍🏫 RAPID-FIRE QUIZ:** 3–5 Q→A pairs after comparison/contrast sections
  > **👨‍🏫 ANALOGY:** simple real-world analogy for the concept
  > **👨‍🏫 CRITICAL DIAGRAM:** what to emphasise in each Mermaid diagram
  <details> collapsible TEACHING PREP at the very top
  10-minute ICEBREAKER section before the first definition
  <details> collapsible POST-SESSION CHECKLIST at the bottom
  Quick Reference for Teachers table at the very end

RULES:
1. DO NOT rewrite or regenerate student content — copy every section, diagram, and table verbatim
2. ONLY add inline teaching annotations (2–4 blocks per section)
3. Add ICEBREAKER at the very start (before any definitions)
4. Add TEACHING PREP <details> block at the top
5. Add RAPID-FIRE QUIZ after every comparison or Traditional vs Generative AI section
6. Add POST-SESSION CHECKLIST <details> at the bottom
7. Add Quick Reference for Teachers table at the very end
8. Output ONLY the full annotated markdown. No preamble.

{f'REFERENCE EXAMPLE (match this annotation style precisely):{chr(10)}{tutor_example}' if tutor_example else ''}"""


def get_tutor_notes_user_prompt(plan: dict, student_notes: str) -> str:
    keywords_str = ", ".join(plan.get("keywords", []))
    notes_block = student_notes if student_notes else ""
    return (
        f"Annotate the student notes below — do NOT rewrite the lesson content.\n\n"
        f"TOPIC   : {plan.get('topic')}\n"
        f"KEYWORDS: {keywords_str}\n\n"
        f"Add for EVERY section: TEACHING STRATEGY, SAY THIS, INTERACTIVE MOMENT, TIME CHECK.\n"
        f"Add RAPID-FIRE QUIZ after comparison sections.\n"
        f"Add ICEBREAKER at the very start, TEACHING PREP at the top, POST-SESSION CHECKLIST at the bottom.\n"
        f"Add Quick Reference for Teachers table at the very end.\n"
        f"Keep 100% of student markdown intact.\n\n"
        f"STUDENT NOTES TO ANNOTATE:\n{notes_block}"
    )
