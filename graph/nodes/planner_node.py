import sys
from graph.state import GraphState, KeywordPlan
from services.groq_client import groq_client
from prompts.planner_prompts import (
    get_planner_system_prompt,
    get_planner_user_prompt,
    get_tutor_verification_question,
)


def planner_node(state: GraphState) -> dict:
    try:
        raw = groq_client.complete_json(
            prompt=get_planner_user_prompt(state["user_input"]),
            size="small",
            system=get_planner_system_prompt(),
            temperature=0.1,
        )
        plan = KeywordPlan(**raw)
        tutor_question = get_tutor_verification_question(
            plan.model_dump(), state["session_id"]
        )
        return {
            "planner_output": plan,
            "planner_verified": False,
            "awaiting_tutor": True,
            "tutor_question": tutor_question,
            "status": "awaiting_tutor",
        }
    except Exception as e:
        print(f"[PlannerNode] Error: {e}", file=sys.stderr)
        errors = list(state.get("errors", []))
        errors.append(f"PlannerNode failed: {e}")
        return {"errors": errors, "status": "failed"}
