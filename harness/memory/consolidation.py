"""Memory Consolidation (Short-Term -> Long-Term with CEO Approval Gate)."""

from __future__ import annotations

from typing import Any

from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory


def consolidate_session_to_long_term(
    stm: ShortTermMemory, ltm: LongTermMemory, *, topic: str, ceo_approved: bool = False
) -> dict[str, Any]:
    if not ceo_approved:
        raise PermissionError("Memory Consolidation Blocked: CEO approval required.")
    steps = sorted(stm.get_all().get("steps", {}).keys())
    ltm.add_episode(
        topic=topic,
        summary=f"Consolidated {stm.session_id}: {len(steps)} steps",
        tags=["consolidated"],
    )
    return {"consolidated": True, "session_id": stm.session_id, "steps_count": len(steps)}
