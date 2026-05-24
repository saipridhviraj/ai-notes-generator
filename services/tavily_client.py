import os
import sys
from typing import List
from tavily import TavilyClient as _TavilyClient


class TavilyClient:
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set. Add it to your .env file."
            )
        self.client = _TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 3) -> List[dict]:
        try:
            response = self.client.search(query=query, max_results=max_results)
            results = response.get("results", [])
            return [
                {
                    "title":   r.get("title", ""),
                    "url":     r.get("url", ""),
                    "content": r.get("content", ""),
                }
                for r in results
            ]
        except Exception as e:
            print(f"[TavilyClient] Search failed for '{query}': {e}", file=sys.stderr)
            return []

    def search_keywords(
        self,
        keywords: List[str],
        max_results_per_keyword: int = 3,
    ) -> str:
        seen_urls: set = set()
        all_results: List[dict] = []

        for keyword in keywords[:3]:
            results = self.search(keyword, max_results=max_results_per_keyword)
            for r in results:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)

        if not all_results:
            return ""

        lines = ["## Web Research Results\n"]
        for r in all_results:
            lines.append(f"### [{r['title']}]({r['url']})")
            lines.append(r["content"])
            lines.append("\n---\n")

        return "\n".join(lines)


class _LazyTavilyClient:
    """Proxy that creates TavilyClient on first use, after .env has been loaded."""

    _instance: TavilyClient | None = None

    def _get(self) -> TavilyClient:
        if self._instance is None:
            self._instance = TavilyClient()
        return self._instance

    def search(self, *args, **kwargs) -> List[dict]:
        return self._get().search(*args, **kwargs)

    def search_keywords(self, *args, **kwargs) -> str:
        return self._get().search_keywords(*args, **kwargs)


tavily_client = _LazyTavilyClient()
