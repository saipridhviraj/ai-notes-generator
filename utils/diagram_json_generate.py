"""Generate diagram patches via JSON LLM calls + deterministic Mermaid compile."""

from __future__ import annotations

import logging

from prompts.diagram_json_prompts import (
    get_diagram_json_system_prompt,
    get_diagram_json_user_prompt,
)
from prompts.mermaid_prompts import _extract_h2_headings, _section_context
from services.prompt_config import (
    get_mermaid_llm_temperature,
    get_mermaid_supplement_max_tokens,
)
from utils.diagram_compiler import compile_diagram_to_mermaid, validate_diagram_spec, wrap_after_heading, wrap_replace_index

logger = logging.getLogger(__name__)


def _fetch_spec(
    llm_client,
    *,
    topic: str,
    context: str,
    issues: list[str] | None,
    session_id: str | None,
    stream_node: str,
) -> dict:
    last_errors: list[str] = []
    for attempt in range(3):
        raw = llm_client.complete_json(
            prompt=get_diagram_json_user_prompt(
                topic=topic,
                context=context,
                issues=last_errors or issues,
            ),
            system=get_diagram_json_system_prompt(),
            size="small",
            temperature=get_mermaid_llm_temperature(),
            max_tokens=get_mermaid_supplement_max_tokens(),
            session_id=session_id,
            stream_node=stream_node,
        )
        if not isinstance(raw, dict):
            last_errors = ["Response must be a JSON object"]
            continue
        spec_issues = validate_diagram_spec(raw)
        if not spec_issues:
            return raw
        last_errors = spec_issues
        logger.info("[diagram_json] spec validation failed attempt %s: %s", attempt + 1, spec_issues[:2])
    raise ValueError(f"Diagram JSON invalid after retries: {'; '.join(last_errors[:4])}")


def generate_supplement_patch_json(
    llm_client,
    *,
    plan: dict,
    student_notes: str,
    needed: int,
    session_id: str | None = None,
    stream_node: str = "student_notes",
) -> str:
    topic = plan.get("topic") or "Lesson"
    headings = _extract_h2_headings(student_notes)
    if not headings:
        headings = ["Overview"]

    parts: list[str] = []
    for heading in headings[:needed]:
        ctx = _section_context(student_notes, heading) or heading
        spec = _fetch_spec(
            llm_client,
            topic=topic,
            context=f"Section: {heading}. {ctx}",
            issues=None,
            session_id=session_id,
            stream_node=stream_node,
        )
        parts.append(wrap_after_heading(f"## {heading}" if not heading.startswith("##") else heading, spec))

    return "\n\n".join(parts)


def generate_repair_patch_json(
    llm_client,
    *,
    plan: dict,
    student_notes: str,
    failed_diagrams: list[dict],
    issues: list[str] | None = None,
    session_id: str | None = None,
    stream_node: str = "student_notes",
) -> str:
    topic = plan.get("topic") or "Lesson"
    parts: list[str] = []

    for item in failed_diagrams:
        idx = item.get("index", 1)
        block = item.get("block") or ""
        block_issues = list(item.get("issues") or [])
        if issues:
            block_issues = block_issues + issues[:3]
        ctx = f"Replace broken diagram {idx}. Prior mermaid (broken):\n{block[:500]}"
        spec = _fetch_spec(
            llm_client,
            topic=topic,
            context=ctx,
            issues=block_issues,
            session_id=session_id,
            stream_node=stream_node,
        )
        # Verify compile before wrapping
        compile_diagram_to_mermaid(spec)
        parts.append(wrap_replace_index(int(idx), spec))

    return "\n\n".join(parts)
