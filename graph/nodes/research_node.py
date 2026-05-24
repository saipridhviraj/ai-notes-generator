import logging
import sys

from graph.state import GraphState
from services.groq_client import groq_client
from services.prompt_config import get_research_max_tokens
from services.research_policy import should_use_web_search
from services.tavily_client import tavily_client
from prompts.research_prompts import (
    get_research_synthesis_system_prompt,
    get_research_synthesis_user_prompt,
)
from utils.research_sanitize import sanitize_research_output

logger = logging.getLogger(__name__)


def research_node(state: GraphState) -> dict:
    plan = state["planner_output"]
    errors = list(state.get("errors", []))

    try:
        forced, reason = should_use_web_search(plan)
        use_web = forced
        web_results = ""

        if use_web:
            logger.info("[research_node] web search | reason=%s topic=%s", reason, plan.topic)
            try:
                web_results = tavily_client.search_keywords(plan.keywords)
            except Exception as e:
                errors.append(f"ResearchNode: Tavily search failed — {e}")
                use_web = False
                reason = "tavily_failed"

        research_raw = groq_client.complete(
            prompt=get_research_synthesis_user_prompt(plan.model_dump(), web_results),
            size="small",
            system=get_research_synthesis_system_prompt(plan.domain),
            temperature=0.3,
            max_tokens=get_research_max_tokens(),
            session_id=state.get("session_id"),
            stream_node="research",
        )
        research_data = sanitize_research_output(research_raw)
        if research_data != research_raw:
            logger.info("[research_node] stripped code fences from research brief")

        return {
            "research_data": research_data,
            "used_web_search": use_web,
            "errors": errors,
        }

    except Exception as e:
        print(f"[ResearchNode] Error: {e}", file=sys.stderr)
        errors.append(f"ResearchNode failed: {e}")
        return {"errors": errors, "status": "failed"}
