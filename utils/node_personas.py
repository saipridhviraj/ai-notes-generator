"""Friendly AI persona names for the notes-generation pipeline (tutor-facing UI)."""

from __future__ import annotations

# node_id → persona shown in StatusPanel / progress checklist
NODE_PERSONAS: dict[str, dict[str, str]] = {
    "planner": {
        "name": "Curriculum Planner",
        "icon": "📋",
        "task": "Plan curriculum",
        "blurb": "Designing the topic outline and learning path",
    },
    "consult_tutor": {
        "name": "Tutor Liaison",
        "icon": "🤝",
        "task": "Tutor review",
        "blurb": "Preparing the plan for your approval",
    },
    "research": {
        "name": "Research Analyst",
        "icon": "🔍",
        "task": "Writer instructions",
        "blurb": "Instructions for the student writer — topic, subtopics, and web facts",
    },
    "student_notes": {
        "name": "Student Notes Writer",
        "icon": "📘",
        "task": "Write student notes",
        "blurb": "Drafting clear notes for learners",
    },
    "diagram_generator": {
        "name": "Diagram Builder",
        "icon": "📊",
        "task": "Build diagrams",
        "blurb": "Generating JSON diagrams and SVG visuals",
    },
    "tutor_notes": {
        "name": "Tutor Guide Writer",
        "icon": "📗",
        "task": "Annotate tutor guide",
        "blurb": "Adding teaching notes on top of student content",
    },
    "evaluator": {
        "name": "Quality Evaluator",
        "icon": "⭐",
        "task": "Evaluate quality",
        "blurb": "Checking coverage, diagrams, and alignment",
    },
    "gap_bridger": {
        "name": "Content Specialist",
        "icon": "🔧",
        "task": "Fill content gaps",
        "blurb": "Improving notes based on quality feedback",
    },
    "final_response": {
        "name": "Publishing Assistant",
        "icon": "💾",
        "task": "Save & finish",
        "blurb": "Saving files and preparing your download",
    },
}

# Shown when pipeline pauses for human tutor input
TUTOR_REVIEW_PERSONA = {
    "name": "Your review",
    "icon": "🤚",
    "task": "Tutor review",
    "blurb": "Please approve or reject the generated plan",
}


def get_persona(node_id: str | None, *, awaiting_human: bool = False) -> dict[str, str] | None:
    if awaiting_human:
        return dict(TUTOR_REVIEW_PERSONA)
    if not node_id:
        return None
    data = NODE_PERSONAS.get(node_id)
    return dict(data) if data else None


def get_node_label(node_name: str | None, *, awaiting_human: bool = False) -> str | None:
    """Human-readable task label for the current pipeline step."""
    persona = get_persona(node_name, awaiting_human=awaiting_human)
    if persona:
        return persona["task"]
    if not node_name:
        return None
    return node_name.replace("_", " ").title()


def persona_for_step(node_id: str) -> dict[str, str]:
    """Persona fields for a pipeline checklist row."""
    data = NODE_PERSONAS.get(node_id, {})
    return {
        "persona": data.get("name", node_id.replace("_", " ").title()),
        "persona_icon": data.get("icon", "🤖"),
        "label": data.get("task", node_id.replace("_", " ").title()),
    }
