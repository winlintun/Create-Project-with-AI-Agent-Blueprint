"""Researcher Tool: Web Search Placeholder (connect Tavily/Brave/Google Search API)."""

from __future__ import annotations

from typing import Any


def web_search(query: str, max_results: int = 3) -> dict[str, Any]:
    return {
        "mode": "placeholder_demo",
        "query": query,
        "max_results": max_results,
        "results": [{"title": f"[Placeholder] {query}", "snippet": "Connect real search API."}],
    }
