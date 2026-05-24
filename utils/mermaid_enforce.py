"""Ensure student notes contain valid, renderable Mermaid diagrams."""

from __future__ import annotations

import logging
import re

from prompts.mermaid_prompts import (
    get_mermaid_core_system_prompt,
    get_mermaid_repair_user_prompt,
    get_mermaid_supplement_user_prompt,
)
from services.prompt_config import (
    get_mermaid_generation_mode,
    get_mermaid_llm_ollama_options,
    get_mermaid_llm_temperature,
    get_mermaid_max_retries,
    get_mermaid_supplement_max_tokens,
    get_min_mermaid_diagrams,
)
from prompts.evaluator_prompts import should_abort_repair
from utils.diagram_json_generate import generate_repair_patch_json, generate_supplement_patch_json
from utils.helpers import (
    extract_mermaid_blocks,
    extract_mermaid_blocks_indexed,
    replace_mermaid_block_by_index,
    validate_all_mermaid_in_notes,
    validate_mermaid_block,
)
from utils.mermaid_patch_clean import clean_mermaid_llm_output
from utils.mermaid_metrics import get_mermaid_metrics
from utils.mermaid_sanitize import normalize_markdown_mermaid
from utils.node_lifecycle import set_status_detail
from utils.tutor_merge import merge_tutor_supplements

logger = logging.getLogger(__name__)

_REPLACE_MARKER = re.compile(
    r"<!--\s*replace:\s*(\d+)\s*-->\s*\n(.*?)(?=<!--\s*replace:|$)",
    re.DOTALL | re.IGNORECASE,
)


def count_mermaid_diagrams(markdown: str) -> int:
    return len(extract_mermaid_blocks(markdown or ""))


def merge_mermaid_supplements(student_notes: str, supplement: str) -> str:
    """Insert diagram blocks after headings; append at end if markers don't match."""
    supplement = clean_mermaid_llm_output(supplement or "")
    if not supplement.strip():
        return student_notes
    merged = merge_tutor_supplements(student_notes, supplement)
    if merged != student_notes:
        return merged
    return student_notes.rstrip() + "\n\n## 📊 Visual Summaries\n\n" + supplement.strip() + "\n"


def _mermaid_ok(notes: str) -> tuple[bool, list[str]]:
    issues = validate_all_mermaid_in_notes(notes)
    count = count_mermaid_diagrams(notes)
    min_required = get_min_mermaid_diagrams()
    if count < min_required:
        issues = list(issues) + [f"Only {count}/{min_required} Mermaid diagram(s) found"]
    return (not issues, issues)


def _issues_for_diagram(index: int, all_issues: list[str]) -> list[str]:
    prefix = f"Diagram {index}:"
    return [i[len(prefix) :].strip() for i in all_issues if i.startswith(prefix)]


def _collect_failed_diagrams(notes: str, issues: list[str]) -> list[dict]:
    """Build per-diagram failure records for targeted repair prompts."""
    failed: list[dict] = []
    for index, block in extract_mermaid_blocks_indexed(notes):
        block_issues = _issues_for_diagram(index, issues) or validate_mermaid_block(block)
        if block_issues:
            failed.append({"index": index, "block": block, "issues": block_issues})
    return failed


def _issue_fix_hints(issues: list[str]) -> list[str]:
    """Map validator messages to concrete fix instructions (boosting context)."""
    hints: list[str] = []
    joined = " ".join(issues).lower()

    if "unquoted" in joined or "':'" in joined or "colon" in joined:
        hints.append('Quote labels that contain colons: A["Step: example"] not A[Step: example]')
    if "subgraph" in joined and "style" in joined:
        hints.append("Never use `style SubgraphId` — apply style lines to node IDs inside the subgraph")
    if "no 'style'" in joined or "no style" in joined:
        hints.append("Add `style NodeId fill:#...,stroke:#...,color:#e2e8f0` for every node")
    if "#e2e8f0" in joined:
        hints.append("Every style line must include color:#e2e8f0 for readable text")
    if "no arrows" in joined:
        hints.append("Add --> connections between nodes so the graph is connected")
    if "invalid or missing graph type" in joined or "graph type" in joined:
        hints.append("First line must be graph TD, graph LR, or flowchart TD")
    if "unbalanced" in joined:
        hints.append("Balance all [ ] and ( ) brackets in node definitions")
    if "->" in joined and "sequence" in joined:
        hints.append("Remove sequenceDiagram/participant/->> syntax — use flowchart TD with A --> B only")

    if not hints:
        hints.append("Rewrite the broken block from scratch using graph TD with quoted labels and explicit styles")
    return hints


def _extract_mermaid_from_patch(patch: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"```mermaid\n(.*?)```", patch or "", re.DOTALL)]


def apply_mermaid_repair_patch(notes: str, patch: str, failed_diagrams: list[dict] | None = None) -> str:
    """
    Apply LLM repair output: prefer <!-- replace: N --> markers, then index-aligned
    replacement, then merge-by-heading fallback.
    """
    if not patch or not patch.strip():
        return notes

    patch = clean_mermaid_llm_output(patch)
    if not patch.strip():
        return notes

    updated = notes
    replace_blocks = list(_REPLACE_MARKER.finditer(patch))
    if replace_blocks:
        for match in replace_blocks:
            idx = int(match.group(1))
            content = match.group(2).strip()
            inner_blocks = _extract_mermaid_from_patch(content)
            if inner_blocks:
                updated = replace_mermaid_block_by_index(updated, idx, inner_blocks[0])
        return updated

    patch_blocks = _extract_mermaid_from_patch(patch)
    failed = failed_diagrams or _collect_failed_diagrams(notes, validate_all_mermaid_in_notes(notes))
    if patch_blocks and failed and len(patch_blocks) == len(failed):
        for item, new_inner in zip(failed, patch_blocks):
            updated = replace_mermaid_block_by_index(updated, item["index"], new_inner)
        return updated

    if patch_blocks and failed and len(patch_blocks) == 1 and len(failed) == 1:
        updated = replace_mermaid_block_by_index(updated, failed[0]["index"], patch_blocks[0])
        return updated

    return merge_mermaid_supplements(updated, patch)


def ensure_mermaid_diagrams(
    notes: str,
    plan: dict,
    llm_client,
    *,
    session_id: str | None = None,
    errors: list | None = None,
) -> str:
    """
    Sanitize, validate, and repair Mermaid blocks (up to MERMAID_MAX_RETRIES repair passes).
    Later attempts use targeted repair with error history (boosting-style context).

    Pipeline per block: generated → normalize → validate → repair_if_needed (LLM).
    """
    max_repairs = get_mermaid_max_retries()
    metrics = get_mermaid_metrics()
    ctx = session_id or "anonymous"

    notes = normalize_markdown_mermaid(notes or "")
    initial_count = count_mermaid_diagrams(notes)
    if initial_count:
        metrics.generated += initial_count

    ok, issues = _mermaid_ok(notes)
    if ok:
        metrics.passed_after_normalize += initial_count
        metrics.log_summary(context=f"session={ctx} normalize_only")
        return notes

    repair_history: list[dict] = []
    repair_attempt = 0

    for attempt in range(max_repairs + 1):
        if attempt > 0:
            logger.info("[mermaid_enforce] repair attempt %s/%s", attempt, max_repairs)

        min_required = get_min_mermaid_diagrams()
        existing = count_mermaid_diagrams(notes)
        needed = max(0, min_required - existing)
        failed_diagrams = _collect_failed_diagrams(notes, issues)
        fix_hints = _issue_fix_hints(issues)
        targeted_only = attempt >= 2 and bool(failed_diagrams)

        if attempt == 0 and needed > 0:
            set_status_detail(session_id, f"Adding {needed} Mermaid diagram(s)…")
            label = "supplement"
            prompt = get_mermaid_supplement_user_prompt(plan, notes, needed, existing)
        else:
            repair_attempt += 1
            abort, reason = should_abort_repair(repair_attempt, issues)
            if abort:
                logger.warning("[mermaid_enforce] %s", reason)
                if errors is not None:
                    errors.append(reason)
                break
            set_status_detail(
                session_id,
                f"Fixing Mermaid diagrams (attempt {attempt + 1}/{max_repairs + 1})…",
            )
            label = "repair"
            prompt = get_mermaid_repair_user_prompt(
                plan,
                notes,
                issues,
                failed_diagrams=failed_diagrams,
                repair_history=repair_history,
                fix_hints=fix_hints,
                targeted_only=targeted_only,
            )

        if get_mermaid_generation_mode() == "json":
            try:
                if label == "supplement":
                    patch = generate_supplement_patch_json(
                        llm_client,
                        plan=plan,
                        student_notes=notes,
                        needed=max(needed, 1),
                        session_id=session_id,
                    )
                else:
                    targets = failed_diagrams or _collect_failed_diagrams(notes, issues)
                    if not targets and issues:
                        targets = [{"index": 1, "block": "", "issues": issues}]
                    patch = generate_repair_patch_json(
                        llm_client,
                        plan=plan,
                        student_notes=notes,
                        failed_diagrams=targets,
                        issues=issues,
                        session_id=session_id,
                    )
            except Exception as e:
                logger.warning("[mermaid_enforce] JSON diagram gen failed, fallback to mermaid: %s", e)
                patch = llm_client.complete(
                    prompt=prompt,
                    system=get_mermaid_core_system_prompt(),
                    size="small",
                    temperature=get_mermaid_llm_temperature(),
                    max_tokens=get_mermaid_supplement_max_tokens(),
                    session_id=session_id,
                    stream_node="student_notes",
                    llm_options=get_mermaid_llm_ollama_options(),
                )
        else:
            patch = llm_client.complete(
                prompt=prompt,
                system=get_mermaid_core_system_prompt(),
                size="small",
                temperature=get_mermaid_llm_temperature(),
                max_tokens=get_mermaid_supplement_max_tokens(),
                session_id=session_id,
                stream_node="student_notes",
                llm_options=get_mermaid_llm_ollama_options(),
            )
        metrics.llm_repair_calls += 1

        issues_before = list(issues)
        if label == "repair":
            notes = normalize_markdown_mermaid(
                apply_mermaid_repair_patch(notes, patch, failed_diagrams)
            )
        else:
            notes = normalize_markdown_mermaid(merge_mermaid_supplements(notes, patch))

        ok, issues = _mermaid_ok(notes)
        repair_history.append(
            {
                "attempt": attempt + 1,
                "issues_before": issues_before[:6],
                "issues_after": issues[:6],
                "patch_preview": (patch or "")[:500],
            }
        )

        if ok:
            logger.info("[mermaid_enforce] diagrams OK after %s pass", label)
            metrics.log_summary(context=f"session={ctx} after_{label}")
            return notes

        if attempt >= max_repairs:
            break

    remaining = len(_collect_failed_diagrams(notes, issues))
    metrics.failed += max(remaining, 1)
    metrics.log_summary(context=f"session={ctx} exhausted")
    msg = (
        f"StudentNotesCreator: Mermaid quality check still failing after "
        f"{max_repairs} repair(s): {'; '.join(issues[:4])}"
    )
    logger.warning("[mermaid_enforce] %s", msg)
    if errors is not None:
        errors.append(msg)
    return notes
