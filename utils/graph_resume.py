"""Resume pipeline from a specific node without re-running earlier steps."""

from __future__ import annotations

from typing import Literal

ResumeNode = Literal[
    "research",
    "student_notes",
    "tutor_notes",
    "evaluator",
    "gap_bridger",
    "mermaid_repair",
]

# (as_node for checkpoint, goto target)
RESUME_FROM_NODE: dict[str, tuple[str, str]] = {
    "research": ("consult_tutor", "research"),
    "student_notes": ("research", "student_notes"),
    "tutor_notes": ("student_notes", "tutor_notes"),
    "evaluator": ("tutor_notes", "evaluator"),
    "gap_bridger": ("evaluator", "gap_bridger"),
    "mermaid_repair": ("tutor_notes", "mermaid_repair"),
}

RESUMABLE_STATUSES = frozenset(
    {"completed", "max_retries_reached", "failed", "running", "cancelled"}
)

# Fields cleared when resuming from a node (that node and everything after re-runs)
_DOWNSTREAM_FIELDS: dict[str, list[str]] = {
    "research": [
        "research_data",
        "student_notes",
        "student_filename",
        "tutor_notes",
        "tutor_filename",
        "evaluation_result",
        "output_files",
        "final_summary",
    ],
    "student_notes": [
        "student_notes",
        "student_filename",
        "tutor_notes",
        "tutor_filename",
        "evaluation_result",
        "output_files",
        "final_summary",
    ],
    "tutor_notes": [
        "tutor_notes",
        "tutor_filename",
        "evaluation_result",
        "output_files",
        "final_summary",
    ],
    "evaluator": [
        "evaluation_result",
        "output_files",
        "final_summary",
    ],
    "mermaid_repair": [
        "evaluation_result",
        "output_files",
        "final_summary",
    ],
    "gap_bridger": [
        "output_files",
        "final_summary",
    ],
}

_ERROR_PREFIXES_BY_NODE: dict[str, tuple[str, ...]] = {
    "research": ("ResearchNode", "StudentNotes", "TutorNotes", "Evaluator", "GapBridger", "Max retries"),
    "student_notes": ("StudentNotes", "TutorNotes", "Evaluator", "GapBridger", "Max retries"),
    "tutor_notes": ("TutorNotes", "Evaluator", "GapBridger", "Max retries"),
    "evaluator": ("Evaluator", "GapBridger", "Max retries"),
    "mermaid_repair": ("StudentNotes", "Evaluator", "GapBridger", "Max retries"),
    "gap_bridger": ("GapBridger", "Max retries"),
}


def validate_resume_request(state: dict, from_node: str) -> str | None:
    """Return error message if resume is not allowed, else None."""
    status = state.get("status", "")
    if status not in RESUMABLE_STATUSES:
        return f"Cannot resume session with status '{status}'"
    if status in ("rejected", "awaiting_tutor"):
        return f"Cannot resume session with status '{status}'"

    plan = state.get("planner_output")
    if plan is None:
        return "Missing planner output — start a new generation instead."

    if from_node == "research":
        if not state.get("planner_verified"):
            return "Plan was not approved — approve the plan first or start fresh."
        return None

    if from_node in ("student_notes", "tutor_notes", "evaluator", "gap_bridger", "mermaid_repair"):
        if not state.get("research_data") and from_node == "student_notes":
            return "Missing research_data — resume from 'research' or start fresh."

    if from_node in ("tutor_notes", "evaluator", "gap_bridger", "mermaid_repair"):
        notes = state.get("student_notes") or ""
        if len(notes.strip()) < 100:
            return "Missing student_notes — resume from 'student_notes' or start fresh."

    if from_node in ("evaluator", "gap_bridger", "mermaid_repair"):
        tutor = state.get("tutor_notes") or ""
        if len(tutor.strip()) < 50 and from_node == "evaluator":
            return "Missing tutor_notes — resume from 'tutor_notes' first."

    if from_node == "gap_bridger":
        if state.get("evaluation_result") is None:
            return "Missing evaluation_result — resume from 'evaluator' first."

    return None


def _filter_errors(errors: list[str], from_node: str) -> list[str]:
    prefixes = _ERROR_PREFIXES_BY_NODE.get(from_node, ())
    if not prefixes:
        return list(errors)
    return [e for e in errors if not any(p in e for p in prefixes)]


def build_resume_state_patch(state: dict, from_node: str) -> dict:
    """Merge session state with fields cleared for a partial re-run."""
    patch: dict = {
        "status": "running",
        "errors": _filter_errors(list(state.get("errors") or []), from_node),
    }
    if from_node in ("research", "student_notes", "tutor_notes", "evaluator", "gap_bridger", "mermaid_repair"):
        patch["retry_count"] = 0

    for field in _DOWNSTREAM_FIELDS.get(from_node, []):
        patch[field] = None if field != "output_files" else []

    if from_node == "research":
        patch["used_web_search"] = state.get("used_web_search", False)

    return patch


def get_resume_goto(from_node: str) -> tuple[str, str]:
    if from_node not in RESUME_FROM_NODE:
        raise ValueError(f"Unknown resume node: {from_node}")
    return RESUME_FROM_NODE[from_node]
