"""Tests for TavilyClient — search and keyword aggregation."""
from unittest.mock import patch

import pytest


class TestTavilyClient:
    def test_init_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        from services.tavily_client import TavilyClient

        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            TavilyClient()

    def test_search_returns_normalized_results(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        from services.tavily_client import TavilyClient

        with patch("services.tavily_client._TavilyClient") as mock_cls:
            mock_cls.return_value.search.return_value = {
                "results": [
                    {"title": "T1", "url": "https://a.com", "content": "body"},
                ]
            }
            client = TavilyClient()
            results = client.search("python decorators")

        assert len(results) == 1
        assert results[0]["title"] == "T1"
        assert results[0]["url"] == "https://a.com"

    def test_search_returns_empty_on_error(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        from services.tavily_client import TavilyClient

        with patch("services.tavily_client._TavilyClient") as mock_cls:
            mock_cls.return_value.search.side_effect = RuntimeError("network down")
            client = TavilyClient()
            results = client.search("query")

        assert results == []

    def test_search_keywords_deduplicates_urls(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        from services.tavily_client import TavilyClient

        shared = {"title": "Shared", "url": "https://dup.com", "content": "x"}

        with patch.object(TavilyClient, "search", return_value=[shared]):
            client = TavilyClient()
            text = client.search_keywords(["k1", "k2", "k3"])

        assert "Web Research Results" in text
        assert text.count("https://dup.com") == 1

    def test_search_keywords_empty_when_no_results(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        from services.tavily_client import TavilyClient

        with patch.object(TavilyClient, "search", return_value=[]):
            client = TavilyClient()
            assert client.search_keywords(["nothing"]) == ""
