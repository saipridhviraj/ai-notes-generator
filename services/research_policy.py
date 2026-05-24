"""When to use Tavily web search during research."""

WEB_SEARCH_DOMAINS = frozenset({"genai", "genai_system_design", "dl", "ml"})


def should_use_web_search(plan) -> tuple[bool, str]:
    """
    Decide if Tavily runs for this plan.

    Returns:
        (use_web, reason) — reason is logged / useful for tests
    """
    domain = (plan.domain or "").lower()
    if plan.needs_web_search:
        return True, "planner_flag"
    if domain in WEB_SEARCH_DOMAINS:
        return True, f"domain:{domain}"
    return False, "not_required"
