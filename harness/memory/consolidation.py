"""Memory Consolidation (Short-Term -> Long-Term + Vector Store with CEO Approval Gate)."""

from __future__ import annotations

import json
from typing import Any

from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory
from harness.memory.vector_store import VectorMemoryBackend


def _summarize_steps(steps_dict: dict[str, Any], *, max_chars: int = 400) -> str:
    if not steps_dict:
        return "0 steps"
    parts: list[str] = []
    for key in sorted(steps_dict.keys()):
        val = steps_dict[key]
        if isinstance(val, dict):
            compact = {
                k: v
                for k, v in val.items()
                if k in {"found", "passed", "approved", "runner", "issues", "matches", "status"}
            }
            snippet = json.dumps(compact or val, ensure_ascii=False)
        else:
            snippet = str(val)
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        parts.append(f"step {key}: {snippet}")
    joined = "; ".join(parts)
    return joined[:max_chars] + ("..." if len(joined) > max_chars else "")


def consolidate_session_to_long_term(
    stm: ShortTermMemory,
    ltm: LongTermMemory,
    *,
    topic: str,
    ceo_approved: bool = False,
    vector_store: VectorMemoryBackend | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    if not ceo_approved:
        raise PermissionError("Memory Consolidation Blocked: CEO approval required.")
    steps_dict = stm.get_all().get("steps", {})
    steps = sorted(steps_dict.keys())
    detail = _summarize_steps(steps_dict)
    summary = f"Consolidated {stm.session_id} ({len(steps)} steps): {detail}"
    ep = ltm.add_episode(
        topic=topic,
        summary=summary,
        tags=["consolidated"],
        workspace=workspace,
    )
    if vector_store is not None:
        vector_store.upsert(
            doc_id=f"consolidated:{stm.session_id}",
            text=f"{topic}\n{summary}",
            metadata={
                "topic": topic,
                "session_id": stm.session_id,
                "timestamp": ep.get("timestamp", ""),
                "workspace": workspace or "",
                "tags": ["consolidated"],
            },
        )
    return {
        "consolidated": True,
        "session_id": stm.session_id,
        "steps_count": len(steps),
        "summary": summary,
    }
