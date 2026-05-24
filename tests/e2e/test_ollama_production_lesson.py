"""
Production Ollama E2E — one full single lesson against a LIVE backend.

Run explicitly (not in default CI):
  pytest tests/e2e/test_ollama_production_lesson.py -m e2e -v --no-cov

Requires:
  - uvicorn running with USE_OLLAMA=true, USE_PRODUCTION_PROMPTS=true
  - Ollama reachable at OLLAMA_BASE_URL
  - APP_API_KEY set in environment (or .env loaded by server)
"""
from __future__ import annotations

import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("APP_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
POLL_INTERVAL = 5
MAX_WAIT_SECONDS = int(os.getenv("OLLAMA_E2E_TIMEOUT", "1200"))
TOPIC = os.getenv("OLLAMA_E2E_TOPIC", "Python list comprehensions")


def _skip_if_not_ready():
    if not API_KEY:
        pytest.skip("APP_API_KEY not set — required for live E2E")
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        pytest.skip(f"Live backend not reachable at {BASE_URL}: {exc}")
    if data.get("llm_provider") != "ollama":
        pytest.skip(f"Backend not on Ollama (provider={data.get('llm_provider')})")
    if data.get("prompt_profile") != "production":
        pytest.skip(f"Backend not on production profile ({data.get('prompt_profile')})")
    if data.get("ollama_reachable") is False:
        pytest.skip("Ollama not reachable per /health")


@pytest.mark.e2e
def test_production_ollama_single_lesson_completes():
    """Generate one lesson end-to-end on Ollama + production prompts."""
    _skip_if_not_ready()

    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=60) as client:
        gen = client.post("/generate", json={"topic": TOPIC})
        assert gen.status_code == 200, gen.text
        session_id = gen.json()["session_id"]

        deadline = time.time() + MAX_WAIT_SECONDS
        terminal = {"completed", "failed", "max_retries_reached", "cancelled", "rejected"}
        last_status = "running"

        while time.time() < deadline:
            st = client.get(f"/status/{session_id}")
            assert st.status_code == 200, st.text
            body = st.json()
            last_status = body["status"]

            if body.get("interrupted") and not body.get("job_alive"):
                pytest.fail(
                    f"Generation job died (interrupted, node={body.get('current_node')})"
                )

            if body["status"] == "awaiting_tutor" and body.get("tutor_question"):
                resp = client.post(
                    f"/tutor/respond/{session_id}",
                    json={"approved": True, "feedback": "", "response_to": "plan_verification"},
                )
                assert resp.status_code == 200, resp.text
                time.sleep(POLL_INTERVAL)
                continue

            if last_status in terminal:
                break
            time.sleep(POLL_INTERVAL)

        assert last_status in terminal, f"Timed out after {MAX_WAIT_SECONDS}s (last={last_status})"
        assert last_status in ("completed", "max_retries_reached"), (
            f"Lesson did not succeed: status={last_status}"
        )

        result = client.get(f"/result/{session_id}")
        assert result.status_code == 200, result.text
        data = result.json()
        assert data.get("student_markdown"), "Missing student markdown"
        assert data.get("tutor_markdown"), "Missing tutor markdown"
        assert len(data.get("student_markdown", "")) > 500
