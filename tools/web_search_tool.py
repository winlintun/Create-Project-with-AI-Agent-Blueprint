"""Researcher Tool: Real Web Search (Tavily / Brave / DuckDuckGo with graceful offline fallback)."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def _default_get_json(
    url: str, headers: dict[str, str], timeout_seconds: int = 10
) -> dict[str, Any]:
    if HAS_HTTPX:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return dict(resp.json())
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as uresp:  # nosec B310
        return dict(json.loads(uresp.read().decode("utf-8")))


def _default_post_json(
    url: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: int = 10
) -> dict[str, Any]:
    if HAS_HTTPX:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return dict(resp.json())
    raw = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=raw, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_seconds) as uresp:  # nosec B310
        return dict(json.loads(uresp.read().decode("utf-8")))


def web_search(
    query: str,
    max_results: int = 3,
    *,
    timeout_seconds: int = 10,
    http_get_fn: Callable[[str, dict[str, str], int], dict[str, Any]] | None = None,
    http_post_fn: Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Search the web via Tavily, Brave, or DuckDuckGo Instant Answer API."""
    q = query.strip()
    if not q:
        return {"mode": "empty_query", "query": query, "max_results": max_results, "results": []}

    get_fn = http_get_fn or _default_get_json
    post_fn = http_post_fn or _default_post_json
    limit = max(1, min(10, int(max_results)))
    errors: list[str] = []

    # 1. Tavily Search API (if TAVILY_API_KEY is configured)
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        try:
            data = post_fn(
                "https://api.tavily.com/search",
                {"Content-Type": "application/json"},
                {"api_key": tavily_key, "query": q, "max_results": limit},
                timeout_seconds,
            )
            results = [
                {
                    "title": str(r.get("title", "")),
                    "url": str(r.get("url", "")),
                    "snippet": str(r.get("content", ""))[:300],
                }
                for r in data.get("results", [])[:limit]
            ]
            return {"mode": "tavily", "query": q, "max_results": limit, "results": results}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"tavily: {type(exc).__name__}: {exc}")

    # 2. Brave Search API (if BRAVE_API_KEY is configured)
    brave_key = os.getenv("BRAVE_API_KEY", "").strip()
    if brave_key:
        try:
            qs = urllib.parse.urlencode({"q": q, "count": limit})
            data = get_fn(
                f"https://api.search.brave.com/res/v1/web/search?{qs}",
                {"Accept": "application/json", "X-Subscription-Token": brave_key},
                timeout_seconds,
            )
            web_items = data.get("web", {}).get("results", [])[:limit]
            results = [
                {
                    "title": str(r.get("title", "")),
                    "url": str(r.get("url", "")),
                    "snippet": str(r.get("description", ""))[:300],
                }
                for r in web_items
            ]
            return {"mode": "brave", "query": q, "max_results": limit, "results": results}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"brave: {type(exc).__name__}: {exc}")

    # 3. Zero-key fallback: DuckDuckGo Instant Answer API
    try:
        qs = urllib.parse.urlencode({"q": q, "format": "json", "no_html": "1", "skip_disambig": "1"})
        data = get_fn(
            f"https://api.duckduckgo.com/?{qs}",
            {"Accept": "application/json", "User-Agent": "PersonalAIWorkforce/10"},
            timeout_seconds,
        )
        results: list[dict[str, str]] = []
        if data.get("AbstractText"):
            results.append({
                "title": str(data.get("Heading", q)),
                "url": str(data.get("AbstractURL", "")),
                "snippet": str(data.get("AbstractText", ""))[:300],
            })
        for topic in data.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": str(topic.get("Text", ""))[:80],
                    "url": str(topic.get("FirstURL", "")),
                    "snippet": str(topic.get("Text", ""))[:300],
                })
        return {"mode": "duckduckgo", "query": q, "max_results": limit, "results": results[:limit]}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"duckduckgo: {type(exc).__name__}: {exc}")

    return {
        "mode": "offline_fallback",
        "query": q,
        "max_results": limit,
        "results": [],
        "errors": errors,
    }
