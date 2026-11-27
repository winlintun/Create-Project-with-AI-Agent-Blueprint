"""Memory Read (Hybrid Keyword + Semantic Vector) & CEO-Approved Write Tools."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from harness.memory.long_term import LongTermMemory
from harness.memory.vector_store import VectorMemoryBackend


def make_memory_read_tool(
    ltm: LongTermMemory,
    vector_store: VectorMemoryBackend | None = None,
    *,
    workspace: str | None = None,
) -> Callable[..., dict[str, Any]]:
    def memory_read(keyword: str = "", top_k: int = 5) -> dict[str, Any]:
        kw = keyword.strip()
        if not kw:
            episodes = ltm.list_episodes(limit=max(1, top_k), workspace=workspace)
            return {
                "preferences": ltm.get_preferences(),
                "episodes": episodes,
                "semantic_hits": [],
                "mode": "recent",
            }
        keyword_hits = ltm.search_episodes(kw, workspace=workspace)
        semantic_hits = vector_store.query(kw, top_k=top_k) if vector_store is not None else []
        return {
            "preferences": ltm.get_preferences(),
            "episodes": keyword_hits,
            "semantic_hits": semantic_hits,
            "mode": "hybrid" if vector_store is not None else "keyword",
        }

    return memory_read


def make_memory_write_tool(
    ltm: LongTermMemory,
    vector_store: VectorMemoryBackend | None = None,
    *,
    workspace: str | None = None,
) -> Callable[..., dict[str, Any]]:
    def memory_write(
        topic: str, summary: str, tags: list[str] | None = None, *, ceo_approved: bool = False
    ) -> dict[str, Any]:
        if not ceo_approved:
            raise PermissionError("Memory Write Blocked: ceo_approved=True required.")
        ep = ltm.add_episode(topic=topic, summary=summary, tags=tags or [], workspace=workspace)
        doc_id = f"ep:{uuid.uuid4().hex[:12]}"
        if vector_store is not None:
            vector_store.upsert(
                doc_id=doc_id,
                text=f"{topic}\n{summary}\n{' '.join(tags or [])}",
                metadata={
                    "topic": topic,
                    "timestamp": ep.get("timestamp", ""),
                    "tags": list(tags or []),
                    "workspace": workspace or "",
                },
            )
        return {
            "saved": True,
            "topic": topic,
            "indexed": vector_store is not None,
            "doc_id": doc_id,
        }

    return memory_write
