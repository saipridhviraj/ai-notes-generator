"""Tests for Ollama → Groq fallback in llm_client."""
from unittest.mock import MagicMock, patch

import httpx
import pytest


class TestGroqFallback:
    def test_ollama_connect_error_falls_back_to_groq(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("LLM_FALLBACK_GROQ", "true")

        from services import llm_client as lc

        lc.llm_client._instance = None
        lc.llm_client._provider = None
        lc.llm_client._groq_fallback = None

        with (
            patch.object(lc.OllamaClient, "complete", side_effect=ConnectionError("down")),
            patch.object(lc.GroqClient, "complete", return_value="from groq") as mock_groq,
        ):
            result = lc.llm_client.complete("hello")

        assert result == "from groq"
        mock_groq.assert_called_once()
        lc.llm_client._instance = None
        lc.llm_client._provider = None
        lc.llm_client._groq_fallback = None

    def test_ollama_timeout_falls_back_when_enabled(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        from services import llm_client as lc

        lc.llm_client._instance = None
        lc.llm_client._provider = None
        lc.llm_client._groq_fallback = None

        with (
            patch.object(
                lc.OllamaClient,
                "complete",
                side_effect=httpx.TimeoutException("timeout"),
            ),
            patch.object(lc.GroqClient, "complete", return_value="fallback") as mock_groq,
        ):
            result = lc.llm_client.complete("prompt")

        assert result == "fallback"
        mock_groq.assert_called_once()
        lc.llm_client._instance = None
        lc.llm_client._provider = None
        lc.llm_client._groq_fallback = None

    def test_no_fallback_without_groq_key(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("LLM_FALLBACK_GROQ", "true")

        from services import llm_client as lc

        lc.llm_client._instance = None
        lc.llm_client._provider = None

        with patch.object(lc.OllamaClient, "complete", side_effect=ConnectionError("down")):
            with pytest.raises(ConnectionError):
                lc.llm_client.complete("hello")

        lc.llm_client._instance = None
        lc.llm_client._provider = None


class TestCheckOllamaReachable:
    def test_returns_none_when_not_ollama(self, monkeypatch):
        monkeypatch.delenv("USE_OLLAMA", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from services.llm_client import check_ollama_reachable

        assert check_ollama_reachable() is None

    def test_returns_true_when_tags_ok(self, monkeypatch):
        monkeypatch.setenv("USE_OLLAMA", "true")
        from services.llm_client import check_ollama_reachable

        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response
            assert check_ollama_reachable() is True
