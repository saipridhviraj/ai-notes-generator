"""Route student notes prompts to dev or production profile."""

from services.prompt_config import get_prompt_profile
from prompts.profiles.dev import student_notes_prompts as dev
from prompts.profiles.production import student_notes_prompts as production


def _module():
    return production if get_prompt_profile() == "production" else dev


def get_student_notes_system_prompt(
    student_example: str = "",
    min_diagrams: int = 4,
    domain: str = "",
) -> str:
    if get_prompt_profile() == "production":
        return production.get_student_notes_system_prompt(
            student_example, min_diagrams, domain
        )
    return dev.get_student_notes_system_prompt(student_example)


def get_student_notes_user_prompt(plan: dict, research_data: str) -> str:
    return _module().get_student_notes_user_prompt(plan, research_data)
