"""Route tutor notes prompts to dev or production profile."""

from services.prompt_config import get_prompt_profile, use_tutor_supplement_mode
from prompts.profiles.dev import tutor_notes_prompts as dev
from prompts.profiles.production import tutor_notes_prompts as production


def _module():
    return production if get_prompt_profile() == "production" else dev


def get_tutor_notes_system_prompt(tutor_example: str = "") -> str:
    if use_tutor_supplement_mode():
        return _module().get_tutor_supplement_system_prompt()
    return _module().get_tutor_notes_system_prompt(tutor_example)


def get_tutor_notes_user_prompt(plan: dict, student_notes: str) -> str:
    if use_tutor_supplement_mode():
        raise ValueError("Use get_tutor_section_handoff_prompt for supplement mode")
    return _module().get_tutor_notes_user_prompt(plan, student_notes)


def get_tutor_section_handoff_prompt(plan: dict, section_handoff: list[dict]) -> str:
    return _module().get_tutor_supplement_user_prompt(plan, section_handoff)
