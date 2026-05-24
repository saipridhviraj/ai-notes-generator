"""Shared test fixtures and configuration."""
from pathlib import Path

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture(autouse=True)
def _reset_rate_limiter_storage():
    """Prevent cross-test pollution on /generate rate limits (shared testclient IP)."""
    try:
        from api.rate_limit import limiter
        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "storage"):
            storage.storage.clear()
    except Exception:
        pass
    yield
    try:
        from api.rate_limit import limiter
        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "storage"):
            storage.storage.clear()
    except Exception:
        pass


# ── App client fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Return FastAPI app with real routes, mocked services."""
    with (
        patch("services.groq_client.groq_client", new=MagicMock()),
        patch("services.tavily_client.tavily_client", new=MagicMock()),
    ):
        from main import app as _app
        return _app


@pytest.fixture
def client(app):
    return TestClient(app)


# ── Mocked Groq client ────────────────────────────────────────────────────────

@pytest.fixture
def mock_groq():
    m = MagicMock()
    m.complete.return_value = "Mocked LLM response"
    m.complete_json.return_value = {
        "student_notes_score": 85,
        "tutor_notes_score": 88,
        "missing_topics": [],
        "diagram_issues": [],
        "alignment_issues": [],
        "passed": True,
    }
    return m


# ── Graph state fixture ───────────────────────────────────────────────────────

@pytest.fixture
def base_state():
    from graph.state import KeywordPlan
    plan = KeywordPlan(
        topic="Python Basics",
        domain="python",
        intent="comprehensive_notes",
        keywords=["variables", "loops", "functions"],
        subtopics=["syntax", "data types", "control flow"],
        needs_web_search=False,
    )
    return {
        "user_input": "Python Basics",
        "session_id": "test-session-001",
        "planner_output": plan,
        "planner_verified": False,
        "planner_feedback": None,
        "tutor_question": None,
        "tutor_response": None,
        "awaiting_tutor": False,
        "research_data": "Python is a high-level programming language.",
        "used_web_search": False,
        "student_notes": "# Python Basics\n\n## Variables\n\nContent here.\n",
        "tutor_notes": "# Python Basics — Tutor Notes\n\n## Variables\n\nAnnotated content.\n",
        "student_filename": "python_basics_student.md",
        "tutor_filename": "python_basics_tutor.md",
        "evaluation_result": None,
        "retry_count": 0,
        "output_files": [],
        "final_summary": None,
        "errors": [],
        "status": "running",
    }
