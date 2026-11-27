"""Memory Read & CEO-Approved Write Tools."""

from __future__ import annotations

from typing import Any, Callable

from harness.memory.long_term import LongTermMemory


def make_memory_read_tool(ltm: LongTermMemory) -> Callable[..., dict[str, Any]]:
    def memory_read(keyword: str = "") -> dict[str, Any]:
        return {
            "preferences": ltm.get_preferences(),
            "episodes": ltm.search_episodes(keyword) if keyword else [],
        }

    return memory_read


def make_memory_write_tool(ltm: LongTermMemory) -> Callable[..., dict[str, Any]]:
    def memory_write(
        topic: str, summary: str, tags: list[str] | None = None, *, ceo_approved: bool = False
    ) -> dict[str, Any]:
        if not ceo_approved:
            raise PermissionError("Memory Write Blocked: ceo_approved=True required.")
        ltm.add_episode(topic=topic, summary=summary, tags=tags or [])
        return {"saved": True, "topic": topic}

    return memory_write
