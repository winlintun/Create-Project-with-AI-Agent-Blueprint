"""SecurityAuditorAgent — Tier 2 Budget Staff Agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from harness.observability.tracer import ObservabilityTracer
from llm.client import LLMClient
from tools.registry import ToolRegistry


class SecurityAuditorAgent(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_client: LLMClient | None = None,
        tracer: ObservabilityTracer | None = None,
    ) -> None:
        super().__init__(
            "security_auditor",
            "Security Auditor",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
            tracer=tracer,
        )

    def audit_snippet(self, session_id: str, code_text: str) -> dict[str, Any]:
        return dict(self.use_tool(session_id, "code_review", code_text=code_text))
