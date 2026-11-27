"""Manager AI — Both Sequential & Async Paths Enforce Planner, STM, Tracer & Circuit Breaker."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from agents.base_agent import BaseAgent
from agents.protocols import StaffRoster
from harness.async_executor import AsyncStaffExecutor
from harness.circuit_breaker import (
    CircuitBreakerOutcome,
    ManagerCircuitBreaker,
    ValidationResult,
)
from harness.context_payload import StructuredContextPayload
from harness.memory.auto_consolidation import AutoConsolidator
from harness.memory.short_term import ShortTermMemory
from harness.observability.tracer import ObservabilityTracer
from harness.planner import DynamicPlanner
from llm.client import LLMClient
from tools.registry import ToolRegistry

T = TypeVar("T")


class ManagerAI(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        staff: StaffRoster,
        short_term_dir: Path,
        tracer: ObservabilityTracer | None = None,
        llm_client: LLMClient | None = None,
        max_retries: int = 2,
        max_concurrency: int = 4,
        consolidator: AutoConsolidator | None = None,
    ) -> None:
        super().__init__(
            "manager_ai",
            "Project Manager",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=1,
            llm_client=llm_client,
            tracer=tracer,
        )
        self.staff = staff
        self.short_term_dir = short_term_dir
        self.tracer = tracer
        self.max_concurrency = max(1, int(max_concurrency))
        self.consolidator = consolidator
        self.circuit_breaker = ManagerCircuitBreaker(max_retries=max_retries)

    def _recall_prior_memory(self, payload: StructuredContextPayload) -> dict[str, Any]:
        try:
            recalled = dict(
                self.use_tool(payload.session_id, "memory_read", keyword=payload.original_ceo_intent)
            )
            payload.context_notes["manager_memory_recall"] = recalled
            return recalled
        except (KeyError, PermissionError):
            return {}

    def _consolidate_if_enabled(
        self, stm: ShortTermMemory, payload: StructuredContextPayload
    ) -> int:
        if self.consolidator is None:
            return 0
        self.consolidator.enqueue_session(
            stm, topic=payload.original_ceo_intent, ceo_approved=payload.ceo_approved
        )
        return self.consolidator.run_once()

    def _run_traced(
        self, payload: StructuredContextPayload, agent: str, op: str, fn: Callable[[], T]
    ) -> T:
        if self.tracer is None:
            return fn()
        with self.tracer.span(payload.trace_id, payload.session_id, agent, op):
            return fn()

    def _escalate(
        self, planner: DynamicPlanner, payload: StructuredContextPayload, step_id: str, reason: str
    ) -> dict[str, Any]:
        planner.mark_status(step_id, "failed", notes=reason)
        return {
            "status": "ESCALATED_TO_CEO",
            "trace_id": payload.trace_id,
            "reason": reason,
            "plan_markdown": planner.render_markdown(),
        }

    def run_workflow(self, payload: StructuredContextPayload, log_path: str) -> dict[str, Any]:
        payload.validate_for_handoff()
        planner = DynamicPlanner(payload.session_id, payload.approved_directive)
        stm = ShortTermMemory(payload.session_id, storage_dir=self.short_term_dir)
        self._recall_prior_memory(payload)

        planner.add_step("1", "researcher", "Log များစစ်ဆေးပြီး Root Cause ရှာရန်")
        planner.add_step("2", "coder", "Fix Snippet ကို စမ်းသပ် Run ရန်")
        planner.add_step("3", "reviewer", "Coder ၏ Snippet ကို AST Review စစ်ဆေးရန်")

        planner.mark_status("1", "in_progress")
        s1 = self._run_traced(
            payload,
            "researcher",
            "investigate",
            lambda: self.circuit_breaker.execute_with_gate(
                lambda fb: self.staff.researcher.investigate(
                    payload.session_id, log_path, "timeout", fb
                ),
                lambda out: ValidationResult(bool(out.get("found")), "Log not found"),
            ),
        )
        if not s1.success:
            return self._escalate(planner, payload, "1", s1.escalation_reason)
        planner.mark_status("1", "completed", output=s1.result)
        stm.set_step_output("1", s1.result)

        planner.mark_status("2", "in_progress")
        s2 = self._run_traced(
            payload,
            "coder",
            "draft_and_test",
            lambda: self.circuit_breaker.execute_with_gate(
                lambda fb: self.staff.coder.draft_and_test_fix(
                    payload.session_id, s1.result, fb
                ),
                lambda out: ValidationResult(
                    bool(out.get("test_result", {}).get("passed")), "Test failed"
                ),
            ),
        )
        if not s2.success:
            return self._escalate(planner, payload, "2", s2.escalation_reason)
        planner.mark_status("2", "completed", output=s2.result)
        stm.set_step_output("2", s2.result)

        planner.mark_status("3", "in_progress")
        s3 = self._run_traced(
            payload,
            "reviewer",
            "review_code",
            lambda: self.circuit_breaker.execute_with_gate(
                lambda fb: self.staff.reviewer.review_code(
                    payload.session_id, s2.result["code"], fb
                ),
                lambda out: ValidationResult(
                    bool(out.get("approved")), f"Issues: {out.get('issues')}"
                ),
            ),
        )
        if not s3.success:
            return self._escalate(planner, payload, "3", s3.escalation_reason)
        planner.mark_status("3", "completed", output=s3.result)
        stm.set_step_output("3", s3.result)

        if self.staff.security_auditor is not None:
            sec_auditor = self.staff.security_auditor
            planner.add_step("4", "security_auditor", "Final Security Audit စစ်ဆေးရန်")
            planner.mark_status("4", "in_progress")
            s4 = self._run_traced(
                payload,
                "security_auditor",
                "audit_snippet",
                lambda: self.circuit_breaker.execute_with_gate(
                    lambda _fb: sec_auditor.audit_snippet(payload.session_id, s2.result["code"]),
                    lambda out: ValidationResult(
                        bool(out.get("approved")), f"Security Issues: {out.get('issues')}"
                    ),
                ),
            )
            if not s4.success:
                return self._escalate(planner, payload, "4", s4.escalation_reason)
            planner.mark_status("4", "completed", output=s4.result)
            stm.set_step_output("4", s4.result)

        payload.validate_for_handoff()
        self.use_tool(
            payload.session_id,
            "memory_write",
            topic=payload.original_ceo_intent,
            summary=f"Verified '{payload.original_ceo_intent}' (trace={payload.trace_id})",
            tags=["ceo_approved"],
            ceo_approved=True,
        )
        self._consolidate_if_enabled(stm, payload)
        return {
            "status": "COMPLETED_SIMULATION",
            "session_id": payload.session_id,
            "trace_id": payload.trace_id,
            "ceo_summary": (
                f"[Workflow ပြီးစီးပါပြီ | Trace: {payload.trace_id}] "
                f"'{payload.original_ceo_intent}' အတွက် စစ်ဆေးမှုအားလုံး အောင်မြင်ပါသည်။ "
                f"(Constraints: {', '.join(payload.constraints)})"
            ),
            "plan_markdown": planner.render_markdown(),
        }

    async def run_workflow_async(
        self, payload: StructuredContextPayload, log_path: str
    ) -> dict[str, Any]:
        """
        Async Parallel Workflow enforcing ALL Doc 3 rules:
        - DynamicPlanner + ShortTermMemory + ObservabilityTracer + ManagerCircuitBreaker.
        - Stops & escalates immediately if Researcher fails (never runs Coder on failed research).
        """
        payload.validate_for_handoff()
        planner = DynamicPlanner(payload.session_id, payload.approved_directive)
        stm = ShortTermMemory(payload.session_id, storage_dir=self.short_term_dir)
        self._recall_prior_memory(payload)
        executor = AsyncStaffExecutor(max_concurrency=self.max_concurrency)

        planner.add_step("1", "researcher+devops", "Parallel log diagnostics (gated)")
        planner.add_step("2", "coder", "Draft & test fix")
        planner.add_step("3", "reviewer", "AST security review")

        # Step 1: Parallel diagnostics with Circuit Breaker & Tracer
        planner.mark_status("1", "in_progress")

        def _gated_researcher() -> CircuitBreakerOutcome:
            return self._run_traced(
                payload,
                "researcher",
                "investigate_async",
                lambda: self.circuit_breaker.execute_with_gate(
                    lambda fb: self.staff.researcher.investigate(
                        payload.session_id, log_path, "timeout", fb
                    ),
                    lambda out: ValidationResult(bool(out.get("found")), "Log not found"),
                ),
            )

        diag_tasks: list[tuple[str, Callable[[], Awaitable[Any]]]] = [
            ("researcher", lambda: asyncio.to_thread(_gated_researcher)),
        ]
        if self.staff.devops is not None:
            devops = self.staff.devops

            def _gated_devops() -> CircuitBreakerOutcome:
                return self._run_traced(
                    payload,
                    "devops",
                    "check_service_logs_async",
                    lambda: self.circuit_breaker.execute_with_gate(
                        lambda _fb: devops.check_service_logs(
                            payload.session_id, log_path, "error"
                        ),
                        lambda out: ValidationResult(
                            bool(out.get("found")), "Service log not found"
                        ),
                    ),
                )

            diag_tasks.append(("devops", lambda: asyncio.to_thread(_gated_devops)))

        diag_results = await executor.run_parallel(diag_tasks)
        res_outcome: CircuitBreakerOutcome = diag_results["researcher"]
        if not res_outcome.success:
            return self._escalate(planner, payload, "1", res_outcome.escalation_reason)
        planner.mark_status("1", "completed", output=res_outcome.result)
        stm.set_step_output("1", res_outcome.result)

        # Step 2: Coder (only runs if Step 1 passed Quality Gate)
        planner.mark_status("2", "in_progress")
        s2: CircuitBreakerOutcome = await asyncio.to_thread(
            lambda: self._run_traced(
                payload,
                "coder",
                "draft_and_test_async",
                lambda: self.circuit_breaker.execute_with_gate(
                    lambda fb: self.staff.coder.draft_and_test_fix(
                        payload.session_id, res_outcome.result, fb
                    ),
                    lambda out: ValidationResult(
                        bool(out.get("test_result", {}).get("passed")), "Test failed"
                    ),
                ),
            )
        )
        if not s2.success:
            return self._escalate(planner, payload, "2", s2.escalation_reason)
        planner.mark_status("2", "completed", output=s2.result)
        stm.set_step_output("2", s2.result)

        # Step 3: Reviewer
        planner.mark_status("3", "in_progress")
        s3: CircuitBreakerOutcome = await asyncio.to_thread(
            lambda: self._run_traced(
                payload,
                "reviewer",
                "review_code_async",
                lambda: self.circuit_breaker.execute_with_gate(
                    lambda fb: self.staff.reviewer.review_code(
                        payload.session_id, s2.result["code"], fb
                    ),
                    lambda out: ValidationResult(
                    bool(out.get("approved")), f"Issues: {out.get('issues')}"
                ),
                ),
            )
        )
        if not s3.success:
            return self._escalate(planner, payload, "3", s3.escalation_reason)
        planner.mark_status("3", "completed", output=s3.result)
        stm.set_step_output("3", s3.result)

        if self.staff.security_auditor is not None:
            sec_auditor = self.staff.security_auditor
            planner.add_step("4", "security_auditor", "Final Security Audit စစ်ဆေးရန်")
            planner.mark_status("4", "in_progress")
            s4 = self._run_traced(
                payload,
                "security_auditor",
                "audit_snippet",
                lambda: self.circuit_breaker.execute_with_gate(
                    lambda _fb: sec_auditor.audit_snippet(payload.session_id, s2.result["code"]),
                    lambda out: ValidationResult(
                        bool(out.get("approved")), f"Security Issues: {out.get('issues')}"
                    ),
                ),
            )
            if not s4.success:
                return self._escalate(planner, payload, "4", s4.escalation_reason)
            planner.mark_status("4", "completed", output=s4.result)
            stm.set_step_output("4", s4.result)

        payload.validate_for_handoff()
        self.use_tool(
            payload.session_id,
            "memory_write",
            topic=payload.original_ceo_intent,
            summary=f"Async verified '{payload.original_ceo_intent}' (trace={payload.trace_id})",
            tags=["ceo_approved", "async"],
            ceo_approved=True,
        )
        self._consolidate_if_enabled(stm, payload)
        return {
            "status": "COMPLETED_ASYNC",
            "session_id": payload.session_id,
            "trace_id": payload.trace_id,
            "plan_markdown": planner.render_markdown(),
        }
