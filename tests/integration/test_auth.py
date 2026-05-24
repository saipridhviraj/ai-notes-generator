"""Tests for API key authentication."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_auth():
    with (
        patch("services.groq_client.groq_client", new=MagicMock()),
        patch("graph.graph_builder.build_graph", return_value=MagicMock()),
        patch.dict("os.environ", {"APP_API_KEY": "test-secret-key"}),
    ):
        import importlib
        import api.auth
        importlib.reload(api.auth)
        from main import app
        yield TestClient(app, raise_server_exceptions=False)


class TestAPIKeyAuth:
    def test_generate_without_key_returns_401(self, client_with_auth):
        response = client_with_auth.post("/generate", json={"topic": "Python loops"})
        assert response.status_code == 401

    def test_generate_with_wrong_key_returns_401(self, client_with_auth):
        response = client_with_auth.post(
            "/generate",
            json={"topic": "Python loops"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_generate_with_correct_key_passes_auth(self, client_with_auth):
        with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
            response = client_with_auth.post(
                "/generate",
                json={"topic": "Python loops"},
                headers={"X-API-Key": "test-secret-key"},
            )
        assert response.status_code == 200

    def test_health_does_not_require_auth(self, client_with_auth):
        """Health check must be accessible without credentials."""
        response = client_with_auth.get("/health")
        assert response.status_code == 200

    def test_status_requires_auth_when_key_set(self, client_with_auth):
        response = client_with_auth.get("/status/nonexistent")
        assert response.status_code == 401

    def test_status_with_auth_returns_404(self, client_with_auth):
        response = client_with_auth.get("/status/nonexistent", headers={"X-API-Key": "test-secret-key"})
        assert response.status_code == 404

    def test_dev_mode_no_key_set_allows_all(self):
        """When APP_API_KEY is not set, all requests pass through."""
        with (
            patch("services.groq_client.groq_client", new=MagicMock()),
            patch("graph.graph_builder.build_graph", return_value=MagicMock()),
            patch.dict("os.environ", {"APP_API_KEY": ""}),
        ):
            import importlib
            import api.auth
            importlib.reload(api.auth)
            from main import app
            client = TestClient(app, raise_server_exceptions=False)
            with patch("api.routes.asyncio.create_task", return_value=MagicMock()):
                response = client.post("/generate", json={"topic": "Python loops"})
            assert response.status_code == 200
