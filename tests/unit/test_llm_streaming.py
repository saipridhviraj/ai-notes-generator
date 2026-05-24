"""Tests for LLM streaming complete()."""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestOllamaStreaming:
    def test_iter_complete_yields_tokens(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        from services.llm_client import OllamaClient

        lines = [
            json.dumps({"message": {"content": "Hel"}, "done": False}),
            json.dumps({"message": {"content": "lo"}, "done": True}),
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines = MagicMock(return_value=iter(lines))

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_response)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_stream_ctx

        with patch("services.llm_client.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value = mock_client
            client = OllamaClient()
            tokens = list(client.iter_complete("prompt"))

        assert tokens == ["Hel", "lo"]

    def test_complete_with_stream_publishes_tokens(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        monkeypatch.setenv("LLM_STREAMING", "true")
        from services.llm_client import OllamaClient

        with (
            patch.object(OllamaClient, "iter_complete", return_value=iter(["A", "B"])),
            patch("utils.stream_bus.start_node") as mock_start,
            patch("utils.stream_bus.publish_token") as mock_pub,
            patch("utils.stream_bus.end_node") as mock_end,
        ):
            client = OllamaClient()
            result = client.complete(
                "prompt",
                session_id="s1",
                stream_node="student_notes",
            )

        assert result == "AB"
        mock_start.assert_called_once_with("s1", "student_notes")
        assert mock_pub.call_count == 2
        mock_end.assert_called_once_with("s1", "student_notes")
