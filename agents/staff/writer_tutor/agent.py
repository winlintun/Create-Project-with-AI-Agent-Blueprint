"""WriterTutorAgent — Tier 2 Budget Staff Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from llm.client import LLMClient
from tools.registry import ToolRegistry


class WriterTutorAgent(BaseAgent):
    def __init__(
        self, tool_registry: ToolRegistry, llm_client: LLMClient | None = None
    ) -> None:
        super().__init__(
            "writer_tutor",
            "Writer & Bilingual CS Tutor",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
        )

    def recall_context(self, session_id: str, keyword: str) -> dict[str, Any]:
        return dict(self.use_tool(session_id, 'memory_read', keyword=keyword))
