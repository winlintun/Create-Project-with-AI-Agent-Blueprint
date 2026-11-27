"""ResearcherAgent — Tier 2 Budget Staff Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from harness.observability.tracer import ObservabilityTracer
from llm.client import LLMClient
from tools.registry import ToolRegistry


class ResearcherAgent(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_client: LLMClient | None = None,
        tracer: ObservabilityTracer | None = None,
    ) -> None:
        super().__init__(
            "researcher",
            "Researcher & Log Analyst",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
            tracer=tracer,
        )

    def investigate(
        self, session_id: str, log_path: str, keyword: str, feedback: str | None = None
    ) -> dict[str, Any]:
        result = dict(self.use_tool(session_id, "log_reader", log_path=log_path, keyword=keyword))
        if (
            result.get("found")
            and self.llm_client is not None
            and self.llm_client.providers
            and self.llm_client.providers[0].provider != "mock"
        ):
            prompt = f"Analyze log matches for '{keyword}': {result.get('matches', [])}"
            if feedback:
                prompt += f"\nPrevious feedback: {feedback}"
            resp = self.ask_llm(prompt, session_id=session_id)
            result["llm_analysis"] = resp.content
        return result
