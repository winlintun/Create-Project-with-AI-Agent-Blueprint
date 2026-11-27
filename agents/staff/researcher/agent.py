"""ResearcherAgent — Tier 2 Budget Staff Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from llm.client import LLMClient
from tools.registry import ToolRegistry


class ResearcherAgent(BaseAgent):
    def __init__(
        self, tool_registry: ToolRegistry, llm_client: LLMClient | None = None
    ) -> None:
        super().__init__(
            "researcher",
            "Researcher & Log Analyst",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
        )

    def investigate(
        self, session_id: str, log_path: str, keyword: str, feedback: str | None = None
    ) -> dict[str, Any]:
        return dict(self.use_tool(session_id, 'log_reader', log_path=log_path, keyword=keyword))
