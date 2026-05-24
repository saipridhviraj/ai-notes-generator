"""Tests for research web-search policy."""
from graph.state import KeywordPlan
from services.research_policy import WEB_SEARCH_DOMAINS, should_use_web_search


def _plan(**overrides):
    base = dict(
        topic="Test",
        domain="python",
        intent="comprehensive_notes",
        keywords=["a"],
        subtopics=["b"],
        needs_web_search=False,
    )
    base.update(overrides)
    return KeywordPlan(**base)


class TestShouldUseWebSearch:
    def test_planner_flag_forces_search(self):
        use, reason = should_use_web_search(_plan(needs_web_search=True))
        assert use is True
        assert reason == "planner_flag"

    def test_genai_domain_forces_search(self):
        for domain in WEB_SEARCH_DOMAINS:
            use, reason = should_use_web_search(_plan(domain=domain))
            assert use is True
            assert reason == f"domain:{domain}"

    def test_python_domain_skips_when_not_flagged(self):
        use, reason = should_use_web_search(_plan())
        assert use is False
        assert reason == "not_required"
