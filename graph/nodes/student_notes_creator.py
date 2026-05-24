import sys
from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import (
    get_few_shot_max_chars,
    get_min_mermaid_diagrams,
    get_note_max_tokens,
    use_diagram_pipeline,
    use_production_prompts,
)
from services.file_service import load_example, slugify
from prompts.student_notes_prompts import (
    get_student_notes_system_prompt,
    get_student_notes_user_prompt,
)
from utils.mermaid_enforce import ensure_mermaid_diagrams
from utils.mermaid_sanitize import sanitize_markdown_mermaid
from utils.diagram_placeholders import convert_mermaid_blocks_to_placeholders
from utils.student_notes_clean import clean_student_notes
from utils.node_lifecycle import set_status_detail


def student_notes_creator(state: GraphState) -> dict:
    plan = state["planner_output"]
    research_data = state["research_data"]
    errors = list(state.get("errors", []))
    session_id = state.get("session_id")

    try:
        set_status_detail(session_id, "Building prompts…")
        domain = getattr(plan, "domain", "") or ""
        if use_production_prompts():
            system_prompt = get_student_notes_system_prompt(
                min_diagrams=get_min_mermaid_diagrams(),
                domain=domain,
            )
        else:
            set_status_detail(session_id, "Loading style reference…")
            example = load_example("day1_student_notes.md", max_chars=get_few_shot_max_chars())
            if use_diagram_pipeline():
                example = convert_mermaid_blocks_to_placeholders(example)
            system_prompt = get_student_notes_system_prompt(example, domain=domain)
        user_prompt = get_student_notes_user_prompt(plan.model_dump(), research_data)
        set_status_detail(session_id, "Writing student notes…")

        notes = groq_client.complete(
            prompt=user_prompt,
            size="large",
            system=system_prompt,
            temperature=0.5,
            max_tokens=get_note_max_tokens(),
            session_id=state.get("session_id"),
            stream_node="student_notes",
        )

        if use_diagram_pipeline():
            notes = convert_mermaid_blocks_to_placeholders(clean_student_notes(notes))
        else:
            notes = ensure_mermaid_diagrams(
                notes,
                plan.model_dump(),
                groq_client,
                session_id=state.get("session_id"),
                errors=errors,
            )
            notes = sanitize_markdown_mermaid(clean_student_notes(notes))

        day = state.get("course_day")
        base = slugify(plan.topic)
        prefix = f"day-{day:02d}_" if day else ""
        filename = prefix + base + "_student.md"

        return {
            "student_notes": notes,
            "student_filename": filename,
            "errors": errors,
        }

    except Exception as e:
        print(f"[StudentNotesCreator] Error: {e}", file=sys.stderr)
        errors.append(f"StudentNotesCreator failed: {e}")
        return {"errors": errors, "status": "failed"}
