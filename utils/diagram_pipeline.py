"""Full diagram pipeline: placeholders → batched JSON LLM → Pydantic → SVG embed."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from models.diagram_spec import BatchDiagramResponse, DiagramSpec
from prompts.diagram_json_prompts import (
    get_diagram_batch_system_prompt,
    get_diagram_batch_user_prompt,
)
from services.prompt_config import (
    get_mermaid_llm_temperature,
    get_mermaid_supplement_max_tokens,
    get_min_diagrams,
)
from utils.diagram_placeholders import (
    DiagramPlaceholder,
    build_embed_block,
    convert_mermaid_blocks_to_placeholders,
    ensure_min_placeholders,
    find_placeholders,
    replace_placeholder,
    section_context_for_anchor,
)
from utils.diagram_svg import render_diagram_svg

logger = logging.getLogger(__name__)


def _slug_for_filename(text: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "diagram").lower()).strip("-")
    slug = slug[:40] or "diagram"
    return f"fig-{index:02d}-{slug}.svg"


def _fetch_batch_specs(
    llm_client,
    *,
    topic: str,
    anchors: list[tuple[str, str]],
    issues: list[str] | None,
    session_id: str | None,
    stream_node: str,
) -> dict[str, DiagramSpec]:
    """One LLM call for all diagrams; returns anchor → validated spec."""
    last_errors: list[str] = []
    for attempt in range(3):
        raw = llm_client.complete_json(
            prompt=get_diagram_batch_user_prompt(
                topic=topic,
                anchors=anchors,
                issues=last_errors or issues,
            ),
            system=get_diagram_batch_system_prompt(),
            size="small",
            temperature=get_mermaid_llm_temperature(),
            max_tokens=max(get_mermaid_supplement_max_tokens(), 2048),
            session_id=session_id,
            stream_node=stream_node,
        )
        try:
            if isinstance(raw, dict) and "diagrams" in raw:
                batch = BatchDiagramResponse.model_validate(raw)
            elif isinstance(raw, list):
                batch = BatchDiagramResponse.model_validate({"diagrams": raw})
            else:
                raise ValueError("Response must include a diagrams array")

            by_anchor: dict[str, DiagramSpec] = {}
            for item in batch.diagrams:
                spec = DiagramSpec.model_validate(item.model_dump(exclude={"anchor"}))
                key = item.anchor.strip()
                by_anchor[key] = spec
                if not key.startswith("##"):
                    by_anchor[f"## {key.lstrip('#').strip()}"] = spec
            if by_anchor:
                return by_anchor
            last_errors = ["No valid diagrams in batch response"]
        except Exception as exc:
            last_errors = [str(exc)]
            logger.info("[diagram_pipeline] batch validation failed attempt %s: %s", attempt + 1, exc)

    raise ValueError(f"Diagram batch invalid after retries: {'; '.join(last_errors[:4])}")


def _match_spec(
    placeholder: DiagramPlaceholder,
    specs_by_anchor: dict[str, DiagramSpec],
) -> DiagramSpec | None:
    anchor = placeholder.anchor
    candidates = [
        anchor,
        anchor.strip(),
        anchor.lower(),
        anchor.replace("## ", "").strip(),
    ]
    for key in candidates:
        if key in specs_by_anchor:
            return specs_by_anchor[key]
    for key, spec in specs_by_anchor.items():
        if key.lower() == anchor.lower():
            return spec
        h = key.replace("## ", "").strip().lower()
        a = anchor.replace("## ", "").strip().lower()
        if h == a or h in a or a in h:
            return spec
    return None


def _fetch_single_spec(
    llm_client,
    *,
    topic: str,
    anchor: str,
    context: str,
    session_id: str | None,
    stream_node: str,
) -> DiagramSpec:
    from prompts.diagram_json_prompts import get_diagram_json_system_prompt, get_diagram_json_user_prompt

    last_errors: list[str] = []
    for attempt in range(3):
        raw = llm_client.complete_json(
            prompt=get_diagram_json_user_prompt(topic=topic, context=f"{anchor}. {context}"),
            system=get_diagram_json_system_prompt(),
            size="small",
            temperature=get_mermaid_llm_temperature(),
            max_tokens=get_mermaid_supplement_max_tokens(),
            session_id=session_id,
            stream_node=stream_node,
        )
        try:
            return DiagramSpec.model_validate(raw)
        except Exception as exc:
            last_errors = [str(exc)]
    raise ValueError(f"Single diagram invalid: {'; '.join(last_errors[:3])}")


def render_diagrams_in_notes(
    notes: str,
    plan: dict,
    llm_client,
    *,
    diagrams_dir: Path,
    session_id: str | None = None,
    stream_node: str = "diagram_generator",
    errors: list | None = None,
    repair_only: bool = False,
) -> str:
    """
    Fill diagram placeholders with diagram-json fences + SVG images.
    Creates diagrams_dir and writes *.svg files.
    """
    errors = errors if errors is not None else []
    topic = plan.get("topic") or "Lesson"
    markdown = notes or ""

    if not repair_only:
        markdown = convert_mermaid_blocks_to_placeholders(markdown)
        markdown = ensure_min_placeholders(markdown, get_min_diagrams())

    placeholders = find_placeholders(markdown)
    if not placeholders:
        return markdown

    targets: list[DiagramPlaceholder] = []
    for ph in placeholders:
        tail = markdown[ph.end : ph.end + 600]
        if "```diagram-json" not in tail:
            targets.append(ph)

    if repair_only and not targets:
        return markdown

    if not targets:
        targets = list(placeholders)

    diagrams_dir.mkdir(parents=True, exist_ok=True)

    anchor_contexts: list[tuple[str, str]] = [
        (ph.anchor, section_context_for_anchor(markdown, ph.anchor)) for ph in targets
    ]

    specs_by_anchor: dict[str, DiagramSpec] = {}
    try:
        if targets:
            specs_by_anchor = _fetch_batch_specs(
                llm_client,
                topic=topic,
                anchors=anchor_contexts,
                issues=None,
                session_id=session_id,
                stream_node=stream_node,
            )
    except Exception as exc:
        logger.warning("[diagram_pipeline] batch failed, falling back to sequential: %s", exc)
        errors.append(f"Diagram batch fallback: {exc}")

    updated = markdown
    for fig_index, ph in enumerate(targets, start=1):
        current_ph = next(
            (p for p in find_placeholders(updated) if p.anchor == ph.anchor),
            None,
        )
        if current_ph is None:
            continue
        tail = updated[current_ph.end : current_ph.end + 600]
        if "```diagram-json" in tail:
            continue

        spec = _match_spec(ph, specs_by_anchor)
        if spec is None:
            ctx = section_context_for_anchor(updated, ph.anchor)
            try:
                spec = _fetch_single_spec(
                    llm_client,
                    topic=topic,
                    anchor=ph.anchor,
                    context=ctx,
                    session_id=session_id,
                    stream_node=stream_node,
                )
            except Exception as exc:
                errors.append(f"Diagram for {ph.anchor}: {exc}")
                continue

        svg_name = _slug_for_filename(ph.anchor, fig_index)
        svg_path = diagrams_dir / svg_name
        svg_path.write_text(render_diagram_svg(spec), encoding="utf-8")
        embed = build_embed_block(spec.to_dict(), f"./diagrams/{svg_name}")
        updated = replace_placeholder(updated, current_ph, embed)

    return updated


def strip_mermaid_from_notes(notes: str) -> str:
    """Remove legacy mermaid blocks when using JSON pipeline."""
    return re.sub(r"```mermaid\s*\n.*?\n```\s*", "", notes or "", flags=re.DOTALL)
