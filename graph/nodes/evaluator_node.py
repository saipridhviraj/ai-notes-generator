import logging
import os
from graph.state import GraphState, EvaluationResult
from services.groq_client import groq_client
from prompts.evaluator_prompts import (
    get_evaluator_system_prompt,
    get_evaluator_user_prompt,
    get_light_evaluator_system_prompt,
    get_light_evaluator_user_prompt,
    python_pre_check,
)
from services.prompt_config import (
    get_eval_max_tokens,
    get_eval_mode,
    get_eval_snippet_chars,
    get_min_mermaid_diagrams,
    use_diagram_pipeline,
    use_tutor_supplement_mode,
)
from utils.eval_summary import build_eval_summary, compute_alignment_issues
from utils.fast_eval import heuristic_evaluate
from utils.helpers import validate_all_mermaid_in_notes, validate_diagrams_in_notes

logger = logging.getLogger(__name__)


def _merge_python_mermaid_issues(result: EvaluationResult, mermaid_issues: list[str]) -> EvaluationResult:
    if not mermaid_issues:
        return result
    merged = list(dict.fromkeys([*(result.diagram_issues or []), *mermaid_issues]))
    if merged != result.diagram_issues:
        return result.model_copy(update={"diagram_issues": merged})
    return result


def _merge_python_alignment_issues(
    result: EvaluationResult, alignment_issues: list[str]
) -> EvaluationResult:
    if not alignment_issues:
        return result
    merged = list(dict.fromkeys([*(result.alignment_issues or []), *alignment_issues]))
    if merged != result.alignment_issues:
        return result.model_copy(update={"alignment_issues": merged})
    return result


def _finalize_eval_result(
    result: EvaluationResult,
    mermaid_issues: list[str],
    alignment_issues: list[str],
) -> EvaluationResult:
    merged = _merge_python_alignment_issues(
        _merge_python_mermaid_issues(result, mermaid_issues),
        alignment_issues,
    )
    if mermaid_issues or alignment_issues:
        merged = merged.model_copy(update={"passed": False})
    return merged


def evaluator_node(state: GraphState) -> dict:
    plan = state["planner_output"]
    student_notes = state["student_notes"]
    tutor_notes = state["tutor_notes"]
    repair_count = state.get("retry_count", 0)
    errors = list(state.get("errors", []))
    max_retries = int(os.getenv("MAX_EVAL_RETRIES", "2"))

    if use_diagram_pipeline():
        mermaid_issues = validate_diagrams_in_notes(student_notes or "")
    else:
        mermaid_issues = validate_all_mermaid_in_notes(student_notes or "")
    if mermaid_issues:
        logger.warning(f"[evaluator_node] {len(mermaid_issues)} diagram issue(s) detected")

    alignment_issues = compute_alignment_issues(student_notes or "", tutor_notes or "")
    if alignment_issues:
        logger.warning(f"[evaluator_node] {len(alignment_issues)} alignment issue(s) detected")

    supplement_mode = use_tutor_supplement_mode()
    session_id = state.get("session_id")
    eval_mode = get_eval_mode()

    if session_id:
        from utils.node_lifecycle import set_status_detail

        detail = (
            "Quick structural check…"
            if eval_mode == "heuristic"
            else "Structural quality check (sections + diagrams)…"
        )
        set_status_detail(session_id, detail)

    if eval_mode == "heuristic":
        result = heuristic_evaluate(
            student_notes, tutor_notes, plan.keywords, mermaid_issues, alignment_issues
        )
        logger.info(
            "[evaluator_node] heuristic | student=%s tutor=%s passed=%s",
            result.student_notes_score,
            result.tutor_notes_score,
            result.passed,
        )
    else:
        pre = python_pre_check(
            student_notes or "",
            tutor_notes or "",
            plan.model_dump(),
            min_diagrams=get_min_mermaid_diagrams(),
        )
        if not pre["passed"]:
            pre_payload = {k: v for k, v in pre.items() if k != "pre_check_only"}
            result = _finalize_eval_result(
                EvaluationResult(**pre_payload), mermaid_issues, alignment_issues
            )
            logger.info(
                "[evaluator_node] python_pre_check failed — skipped LLM | student=%s tutor=%s",
                result.student_notes_score,
                result.tutor_notes_score,
            )
        else:
            try:
                if eval_mode == "light":
                    summary = build_eval_summary(
                        plan=plan.model_dump(),
                        student_notes=student_notes or "",
                        tutor_notes=tutor_notes or "",
                        mermaid_issues=mermaid_issues,
                        supplement_mode=supplement_mode,
                    )
                    raw = groq_client.complete_json(
                        prompt=get_light_evaluator_user_prompt(summary),
                        size="small",
                        system=get_light_evaluator_system_prompt(supplement_mode=supplement_mode),
                        temperature=0.1,
                        max_tokens=get_eval_max_tokens(),
                    )
                else:
                    mermaid_context = ""
                    if mermaid_issues:
                        mermaid_context = "\n\nMermaid syntax issues found:\n" + "\n".join(
                            f"- {issue}" for issue in mermaid_issues
                        )
                    raw = groq_client.complete_json(
                        prompt=get_evaluator_user_prompt(
                            student_notes,
                            tutor_notes,
                            plan.keywords,
                            max_chars=get_eval_snippet_chars(),
                            supplement_mode=supplement_mode,
                        )
                        + mermaid_context,
                        size="reasoning",
                        system=get_evaluator_system_prompt(supplement_mode=supplement_mode),
                        temperature=0.1,
                        max_tokens=get_eval_max_tokens(),
                    )
                result = _finalize_eval_result(EvaluationResult(**raw), mermaid_issues, alignment_issues)
                logger.info(
                    "[evaluator_node] %s LLM | student=%s tutor=%s passed=%s",
                    eval_mode,
                    result.student_notes_score,
                    result.tutor_notes_score,
                    result.passed,
                )
            except Exception as e:
                logger.warning(
                    "[evaluator_node] %s LLM eval failed — falling back to heuristic | error=%s",
                    eval_mode,
                    e,
                )
                errors.append(
                    f"EvaluatorNode: {eval_mode} LLM scoring unavailable ({e}) — used fast checks instead."
                )
                result = heuristic_evaluate(
                    student_notes, tutor_notes, plan.keywords, mermaid_issues, alignment_issues
                )

    status = state.get("status", "running")
    if not result.passed and repair_count >= max_retries:
        errors.append(f"Max retries ({max_retries}) reached. Saving best attempt.")
        status = "max_retries_reached"

    logger.info(
        f"[evaluator_node] scored | student={result.student_notes_score} "
        f"tutor={result.tutor_notes_score} passed={result.passed} repairs={repair_count}"
    )
    return {
        "evaluation_result": result,
        "errors": errors,
        "status": status,
    }
