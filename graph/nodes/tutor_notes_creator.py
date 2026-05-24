import sys
from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import (
    get_few_shot_max_chars,
    get_section_preview_chars,
    get_tutor_handoff_max_sections,
    get_tutor_max_tokens,
    use_tutor_supplement_mode,
)
from services.file_service import load_example, slugify
from prompts.tutor_notes_prompts import (
    get_tutor_notes_system_prompt,
    get_tutor_notes_user_prompt,
    get_tutor_section_handoff_prompt,
)
from utils.notes_sections import build_tutor_handoff, parse_markdown_sections
from utils.tutor_merge import merge_tutor_json_handoff, merge_tutor_supplements


def tutor_notes_creator(state: GraphState) -> dict:
    plan = state["planner_output"]
    student_notes = state["student_notes"]
    errors = [
        e for e in list(state.get("errors", []))
        if "TutorNotesCreator" not in e
    ]

    try:
        if use_tutor_supplement_mode():
            system_prompt = get_tutor_notes_system_prompt()
            sections = parse_markdown_sections(student_notes)
            handoff = build_tutor_handoff(
                sections,
                preview_chars=get_section_preview_chars(),
                max_sections=get_tutor_handoff_max_sections(),
            )
            user_prompt = get_tutor_section_handoff_prompt(plan.model_dump(), handoff)

            try:
                tutor_json = groq_client.complete_json(
                    prompt=user_prompt,
                    size="large",
                    system=system_prompt,
                    temperature=0.3,
                    max_tokens=get_tutor_max_tokens(),
                    session_id=state.get("session_id"),
                    stream_node="tutor_notes",
                )
                notes = merge_tutor_json_handoff(student_notes, tutor_json)
            except Exception as json_err:
                errors.append(
                    f"TutorNotesCreator: JSON handoff failed, fallback to markdown — {json_err}"
                )
                fallback_prompt = (
                    f"Add <!-- after: HEADING --> annotation blocks for:\n{student_notes}"
                )
                supplement = groq_client.complete(
                    prompt=fallback_prompt,
                    size="large",
                    system=system_prompt,
                    temperature=0.4,
                    max_tokens=get_tutor_max_tokens(),
                    session_id=state.get("session_id"),
                    stream_node="tutor_notes",
                )
                notes = merge_tutor_supplements(student_notes, supplement)
        else:
            example = load_example("day1_tutor_notes.md", max_chars=get_few_shot_max_chars())
            system_prompt = get_tutor_notes_system_prompt(example)
            user_prompt = get_tutor_notes_user_prompt(plan.model_dump(), student_notes)
            notes = groq_client.complete(
                prompt=user_prompt,
                size="large",
                system=system_prompt,
                temperature=0.4,
                max_tokens=get_tutor_max_tokens(),
                session_id=state.get("session_id"),
                stream_node="tutor_notes",
            )

        day = state.get("course_day")
        base = slugify(plan.topic)
        prefix = f"day-{day:02d}_" if day else ""
        filename = prefix + base + "_tutor.md"

        return {
            "tutor_notes": notes,
            "tutor_filename": filename,
            "errors": errors,
        }

    except Exception as e:
        print(f"[TutorNotesCreator] Error: {e}", file=sys.stderr)
        errors.append(f"TutorNotesCreator failed: {e}")
        return {"errors": errors, "status": "failed"}
