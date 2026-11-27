"""BaseAgent — Agent-Aware Tiered Model Selection (`tier=1` Premium vs `tier=2` Budget)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.observability.tracer import ObservabilityTracer
from llm.client import LLMClient, LLMResponse
from tools.registry import ToolRegistry


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        prompt_path: Path,
        tool_registry: ToolRegistry,
        *,
        tier: int = 2,
        llm_client: LLMClient | None = None,
        tracer: ObservabilityTracer | None = None,
    ) -> None:
        self.name = name
        self.role = role
        self.tier = tier
        self.prompt_path = prompt_path
        self.tool_registry = tool_registry
        self.llm_client = llm_client.for_agent(name) if llm_client is not None else None
        self.tracer = tracer

    def load_system_prompt(self) -> str:
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return f"You are {self.name}."

    def ask_llm(
        self,
        user_message: str,
        *,
        trace_id: str | None = None,
        session_id: str | None = None,
    ) -> LLMResponse:
        if self.llm_client is None:
            raise RuntimeError(f"LLMClient not configured for '{self.name}'.")
        resp = self.llm_client.complete(self.load_system_prompt(), user_message)
        if self.tracer is not None and session_id:
            self.tracer.record_token_cost(
                trace_id=trace_id or "trace_unassigned",
                session_id=session_id,
                agent=self.name,
                provider=resp.provider,
                model=resp.model,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                estimated_cost_usd=resp.estimated_cost_usd,
            )
        return resp

    def use_tool(self, session_id: str, tool_name: str, **kwargs: Any) -> Any:
        return self.tool_registry.invoke(session_id, self.name, tool_name, **kwargs)
