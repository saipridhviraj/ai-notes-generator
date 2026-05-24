"""Tests for slowapi rate limiting on protected endpoints."""
import os
import re
from unittest.mock import MagicMock, patch

import pytest


def _generate_limit_per_minute() -> int:
    raw = os.getenv("RATE_LIMIT_GENERATE", "5/minute")
    match = re.match(r"(\d+)", raw)
    return int(match.group(1)) if match else 5


@pytest.fixture
def rate_limited_client(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", "test-api-key")
    with (
        patch("services.groq_client.groq_client", new=MagicMock()),
        patch("services.tavily_client.tavily_client", new=MagicMock()),
        patch("graph.graph_builder.build_graph", return_value=MagicMock()),
    ):
        import importlib
        import api.auth
        importlib.reload(api.auth)
        from main import app
        from fastapi.testclient import TestClient

        yield TestClient(app)


class TestRateLimiting:
    def test_generate_returns_429_when_limit_exceeded(self, rate_limited_client):
        headers = {"X-API-Key": "test-api-key"}
        payload = {"topic": "Rate Limit Test"}
        limit = _generate_limit_per_minute()

        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            for _ in range(limit):
                resp = rate_limited_client.post("/generate", json=payload, headers=headers)
                assert resp.status_code == 200, resp.text

            resp = rate_limited_client.post("/generate", json=payload, headers=headers)
        assert resp.status_code == 429
