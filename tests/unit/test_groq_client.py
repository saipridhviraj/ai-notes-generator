"""Tests for GroqClient — rate-limit retry and JSON parsing."""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestStripJsonFences:
    def test_strips_markdown_fences(self):
        from services.groq_client import _strip_json_fences

        raw = '```json\n{"a": 1}\n```'
        assert _strip_json_fences(raw) == '{"a": 1}'


class TestGroqClient:
    def test_init_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        from services.groq_client import GroqClient

        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            GroqClient()

    def test_complete_returns_content(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from services.groq_client import GroqClient

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="hello world"))]

        with patch("services.llm_client.Groq") as mock_groq_cls:
            mock_groq_cls.return_value.chat.completions.create.return_value = mock_response
            client = GroqClient()
            result = client.complete("prompt", system="sys")

        assert result == "hello world"
        mock_groq_cls.return_value.chat.completions.create.assert_called_once()

    def test_complete_retries_on_rate_limit(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from services.groq_client import GroqClient

        rate_err = Exception("Error 429: rate_limit_exceeded — try again in 0.1s")
        ok_response = MagicMock()
        ok_response.choices = [MagicMock(message=MagicMock(content="ok"))]

        with (
            patch("services.llm_client.Groq") as mock_groq_cls,
            patch("services.llm_client.time.sleep") as mock_sleep,
        ):
            mock_groq_cls.return_value.chat.completions.create.side_effect = [
                rate_err,
                ok_response,
            ]
            client = GroqClient()
            result = client.complete("prompt")

        assert result == "ok"
        mock_sleep.assert_called_once()

    def test_complete_raises_after_max_retries(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from services.groq_client import GroqClient

        rate_err = Exception("429 rate_limit_exceeded")

        with (
            patch("services.llm_client.Groq") as mock_groq_cls,
            patch("services.llm_client.time.sleep"),
        ):
            mock_groq_cls.return_value.chat.completions.create.side_effect = rate_err
            client = GroqClient()
            with pytest.raises(Exception, match="429"):
                client.complete("prompt")

    def test_complete_json_parses_response(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from services.groq_client import GroqClient

        payload = {"passed": True, "student_notes_score": 90}
        with patch.object(GroqClient, "complete", return_value=json.dumps(payload)):
            client = GroqClient()
            result = client.complete_json("prompt")

        assert result == payload

    def test_complete_json_invalid_raises(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        from services.groq_client import GroqClient

        with patch.object(GroqClient, "complete", return_value="not json"):
            client = GroqClient()
            with pytest.raises(ValueError, match="not valid JSON"):
                client.complete_json("prompt")
