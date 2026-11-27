"""Assistant AI (Tier 1 Orchestrator / Gatekeeper)."""

from __future__ import annotations

from pathlib import Path

from agents.base_agent import BaseAgent
from harness.context_payload import StructuredContextPayload
from harness.observability.tracer import ObservabilityTracer
from harness.persistence.audit_logger import AuditLogger
from llm.client import LLMClient
from tools.registry import ToolRegistry


class AssistantAI(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        audit_logger: AuditLogger,
        llm_client: LLMClient | None = None,
        tracer: ObservabilityTracer | None = None,
    ) -> None:
        super().__init__(
            "assistant_ai",
            "Chief of Staff",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=1,
            llm_client=llm_client,
            tracer=tracer,
        )
        self.audit_logger = audit_logger

    def draft_directive(
        self, raw_ceo_intent: str, default_constraints: list[str] | None = None
    ) -> StructuredContextPayload:
        constraints = (
            list(default_constraints)
            if default_constraints is not None
            else ["Production Database Schema ကို မပြောင်းလဲရ။"]
        )
        payload = StructuredContextPayload(
            original_ceo_intent=raw_ceo_intent,
            approved_directive=f"Investigate '{raw_ceo_intent}'",
            constraints=constraints,
        )
        try:
            recalled = self.use_tool(payload.session_id, "memory_read", keyword=raw_ceo_intent)
            payload.context_notes["memory_recall"] = recalled
        except (KeyError, PermissionError):
            pass

        if self.llm_client is not None:
            resp = self.ask_llm(
                f"Refine CEO intent: {raw_ceo_intent}",
                trace_id=payload.trace_id,
                session_id=payload.session_id,
            )
            payload.approved_directive = resp.content
        return payload

    def record_ceo_approval(
        self,
        payload: StructuredContextPayload,
        approved: bool,
        extra_constraints: list[str] | None = None,
        *,
        approval_source: str = "explicit_ceo",
    ) -> StructuredContextPayload:
        if approved:
            payload.approve(extra_constraints=extra_constraints, approval_source=approval_source)
            self.audit_logger.log_decision(
                payload.session_id, "CEO", "APPROVED", f"source={approval_source}"
            )
        else:
            payload.revoke_approval()
            self.audit_logger.log_decision(
                payload.session_id, "CEO", "REJECTED", "CEO rejected directive"
            )
        return payload
