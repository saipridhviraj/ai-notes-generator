"""Build per-node artifact metadata and content from session graph state."""

from __future__ import annotations

import json
from typing import Any

from utils.node_personas import persona_for_step
from services.prompt_config import use_diagram_pipeline
from utils.research_diagrams import parse_suggested_diagrams

_BASE_ARTIFACT_NODE_IDS = (
    "planner",
    "consult_tutor",
    "research",
    "student_notes",
    "tutor_notes",
    "evaluator",
    "gap_bridger",
    "final_response",
)


def artifact_node_ids() -> tuple[str, ...]:
    if use_diagram_pipeline():
        return (
            "planner",
            "consult_tutor",
            "research",
            "student_notes",
            "diagram_generator",
            "tutor_notes",
            "evaluator",
            "gap_bridger",
            "final_response",
        )
    return _BASE_ARTIFACT_NODE_IDS


def _format_planner(plan) -> tuple[str, str]:
    if plan is None:
        return "", "json"
    payload = plan.model_dump() if hasattr(plan, "model_dump") else dict(plan)
    return json.dumps(payload, indent=2), "json"


def _format_evaluation(result) -> tuple[str, str]:
    if result is None:
        return "", "json"
    payload = result.model_dump() if hasattr(result, "model_dump") else dict(result)
    return json.dumps(payload, indent=2), "json"


def _content_for_node(node_id: str, state: dict) -> tuple[str, str]:
    """Return (content, format) for a node — empty string if not yet available."""
    if node_id == "planner":
        return _format_planner(state.get("planner_output"))

    if node_id == "consult_tutor":
        q = state.get("tutor_question") or ""
        feedback = state.get("planner_feedback") or ""
        parts = []
        if q:
            parts.append(q)
        if feedback and feedback not in ("approved", ""):
            parts.append(f"\n\n---\n\n**Tutor feedback:** {feedback}")
        return "\n".join(parts).strip(), "markdown"

    if node_id == "research":
        return (state.get("research_data") or "").strip(), "markdown"

    if node_id == "student_notes":
        return (state.get("student_notes") or "").strip(), "markdown"

    if node_id == "diagram_generator":
        notes = state.get("student_notes") or ""
        if "```diagram-json" in notes:
            import re

            blocks = re.findall(r"```diagram-json\s*\n(.*?)```", notes, re.DOTALL)
            summary = f"Generated {len(blocks)} diagram(s) with JSON + SVG embeds."
            if blocks:
                summary += f"\n\nFirst spec preview:\n```json\n{blocks[0][:400].strip()}\n```"
            return summary.strip(), "markdown"
        return "", "markdown"

    if node_id == "tutor_notes":
        return (state.get("tutor_notes") or "").strip(), "markdown"

    if node_id == "evaluator":
        return _format_evaluation(state.get("evaluation_result"))

    if node_id == "gap_bridger":
        errors = state.get("errors") or []
        gap_lines = [e for e in errors if "GapBridger" in e or "gap" in e.lower()]
        if gap_lines:
            return "\n".join(f"- {line}" for line in gap_lines), "markdown"
        eval_result = state.get("evaluation_result")
        if eval_result and not eval_result.passed:
            missing = eval_result.missing_topics or []
            diagrams = eval_result.diagram_issues or []
            alignment = eval_result.alignment_issues or []
            if missing or diagrams or alignment:
                lines = ["Gap bridger triggered by evaluation:"]
                for t in missing:
                    lines.append(f"- Missing: {t}")
                for d in diagrams:
                    lines.append(f"- Diagram: {d}")
                for a in alignment:
                    lines.append(f"- Alignment: {a}")
                return "\n".join(lines), "markdown"
        return "", "markdown"

    if node_id == "final_response":
        summary = state.get("final_summary") or ""
        files = state.get("output_files") or []
        if not summary and not files:
            return "", "markdown"
        lines = []
        if summary:
            lines.append(summary)
        if files:
            lines.append("\n**Saved files:**")
            lines.extend(f"- `{f}`" for f in files)
        return "\n".join(lines).strip(), "markdown"

    return "", "markdown"


def build_node_artifacts(state: dict, pipeline_steps: list[dict]) -> list[dict[str, Any]]:
    """
    Metadata + preview for each pipeline step (for /status polling).
    Full content via get_node_artifact_content().
    """
    step_by_id = {s["id"]: s for s in pipeline_steps}
    items: list[dict[str, Any]] = []

    for node_id in artifact_node_ids():
        step = step_by_id.get(node_id, {})
        persona = persona_for_step(node_id)
        content, fmt = _content_for_node(node_id, state)
        available = bool(content)
        preview = content[:280] + "…" if len(content) > 280 else content
        suggested_diagram_count: int | None = None
        if node_id == "research" and content:
            count = len(parse_suggested_diagrams(content))
            suggested_diagram_count = count if count else None

        item: dict[str, Any] = {
                "node_id": node_id,
                "label": step.get("label") or persona["label"],
                "persona_icon": step.get("persona_icon") or persona["persona_icon"],
                "state": step.get("state", "pending"),
                "format": fmt,
                "available": available,
                "char_count": len(content),
                "preview": preview if available else None,
            }
        if suggested_diagram_count is not None:
            item["suggested_diagram_count"] = suggested_diagram_count

        items.append(item)
    return items


def get_node_artifact_content(state: dict, node_id: str) -> dict[str, Any] | None:
    """Full artifact payload for GET /artifacts/{session_id}/{node_id}."""
    if node_id not in artifact_node_ids():
        return None
    content, fmt = _content_for_node(node_id, state)
    if not content:
        return None
    persona = persona_for_step(node_id)
    payload: dict[str, Any] = {
        "node_id": node_id,
        "label": persona["label"],
        "persona_icon": persona["persona_icon"],
        "format": fmt,
        "content": content,
        "char_count": len(content),
    }
    if node_id == "research":
        diagrams = parse_suggested_diagrams(content)
        if diagrams:
            payload["suggested_diagrams"] = diagrams
    return payload
