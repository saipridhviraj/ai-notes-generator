"""Tests for Ollama LLM provider."""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestLLMConfig:
    def test_use_ollama_true_flag(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from services.llm_config import use_ollama

        assert use_ollama() is True

    def test_llm_provider_ollama(self, monkeypatch):
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        from services.llm_config import use_ollama

        assert use_ollama() is True

    def test_defaults_to_groq(self, monkeypatch):
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from services.llm_config import use_ollama

        assert use_ollama() is False


class TestOllamaClient:
    def test_complete_returns_content(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        from services.llm_client import OllamaClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"message": {"content": "hello local"}}

        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            client = OllamaClient()
            result = client.complete("prompt", system="sys")

        assert result == "hello local"

    def test_build_payload_disables_thinking_by_default(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:9b-q4_K_M")
        monkeypatch.delenv("OLLAMA_THINK", raising=False)
        from services.llm_client import OllamaClient

        client = OllamaClient()
        payload = client._build_payload("hi", "", 0.7, 100, stream=False)

        assert payload["think"] is False

    def test_build_payload_enables_think_when_requested(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "qwen3.5:9b-q4_K_M")
        from services.llm_client import OllamaClient

        client = OllamaClient()
        payload = client._build_payload("hi", "", 0.7, 100, stream=False, think=True)

        assert payload["think"] is True

    def test_strips_thinking_blocks_from_content(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        from services.llm_client import OllamaClient

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        think_block = "<think" + ">hidden reasoning<" + "/think>\n\nFinal answer"
        mock_response.json.return_value = {
            "message": {"content": think_block},
        }

        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            client = OllamaClient()
            result = client.complete("prompt")

        assert result == "Final answer"

    def test_complete_json_parses_response(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        from services.llm_client import OllamaClient

        payload = {"topic": "Python", "keywords": ["loops"]}
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps(payload)},
        }

        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            client = OllamaClient()
            result = client.complete_json("plan this topic")

        assert result == payload

    def test_connect_error_raises_helpful_message(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:99999")
        from services.llm_client import OllamaClient

        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.side_effect = (
                httpx.ConnectError("connection refused")
            )
            client = OllamaClient()
            with pytest.raises(ConnectionError, match="Is Ollama running"):
                client.complete("prompt")


class TestLazyRouting:
    def test_routes_to_ollama_when_enabled(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        from services import groq_client as gc_module

        gc_module.groq_client._instance = None
        gc_module.groq_client._provider = None

        with patch.object(gc_module.OllamaClient, "complete", return_value="local") as mock_complete:
            result = gc_module.groq_client.complete("hi")

        assert result == "local"
        mock_complete.assert_called_once()
        gc_module.groq_client._instance = None
        gc_module.groq_client._provider = None
