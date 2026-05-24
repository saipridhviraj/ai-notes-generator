import re
import logging
from langgraph.types import interrupt
from graph.state import GraphState
from utils.helpers import is_tutor_timed_out, get_session

logger = logging.getLogger(__name__)


def consult_tutor_node(state: GraphState) -> dict:
    session_id = state["session_id"]

    session = get_session(session_id)
    if session and session.get("auto_approve_tutor"):
        logger.info(f"[consult_tutor_node] auto-approved (course day) | session={session_id}")
        return {
            "planner_verified": True,
            "awaiting_tutor": False,
            "planner_feedback": "auto-approved: course day",
            "status": "running",
        }

    # Auto-approve on timeout
    if is_tutor_timed_out(session_id):
        errors = list(state.get("errors", []))
        errors.append("ConsultTutor: auto-approved after 5-minute timeout")
        logger.warning(f"[consult_tutor_node] auto-approved on timeout | session={session_id}")
        return {
            "planner_verified": True,
            "awaiting_tutor": False,
            "status": "running",
            "errors": errors,
        }

    # In LangGraph 1.x, interrupt() pauses the graph and returns the resume value
    # when the caller passes Command(resume=value) to the next astream call.
    feedback = interrupt("Waiting for tutor response via POST /tutor/respond/" + session_id)

    if not isinstance(feedback, str):
        feedback = str(feedback) if feedback else ""

    # BUG-2 FIX: rejection must halt the pipeline
    if feedback.startswith("rejected:"):
        logger.warning(f"[consult_tutor_node] tutor rejected plan | session={session_id}")
        return {
            "planner_verified": False,
            "awaiting_tutor": False,
            "tutor_response": None,
            "status": "rejected",
        }

    # Tutor approved — optionally inject keywords from feedback
    plan = state.get("planner_output")
    updated_plan = plan

    if plan and feedback and feedback not in ("approved", "approved with feedback: "):
        keywords = list(plan.keywords)
        lower_feedback = feedback.lower()

        add_matches = re.findall(r"add['\s]+(['\w\s]+?)(?:\.|,|$)", lower_feedback)
        for match in add_matches:
            keyword = match.strip().strip("'\"")
            if keyword and keyword not in [k.lower() for k in keywords]:
                keywords.append(keyword)

        if keywords != list(plan.keywords):
            updated_plan = plan.model_copy(update={"keywords": keywords})

    logger.info(f"[consult_tutor_node] tutor approved | session={session_id}")
    return {
        "planner_output": updated_plan,
        "planner_verified": True,
        "planner_feedback": feedback,
        "awaiting_tutor": False,
        "tutor_response": None,
        "status": "running",
    }
