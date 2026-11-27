#!/usr/bin/env python3
"""Personal AI Workforce v10 — Offline Demo Simulation (`demo_python_runner` isolated)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from agents.assistant_ai.agent import AssistantAI
from agents.manager_ai.agent import ManagerAI
from agents.protocols import StaffRoster
from agents.staff.coder.agent import CoderAgent
from agents.staff.devops.agent import DevOpsAgent
from agents.staff.researcher.agent import ResearcherAgent
from agents.staff.reviewer.agent import ReviewerAgent
from agents.staff.security_auditor.agent import SecurityAuditorAgent
from agents.staff.writer_tutor.agent import WriterTutorAgent
from harness.memory.long_term import LongTermMemory
from harness.observability.tracer import ObservabilityTracer
from harness.persistence.audit_logger import AuditLogger
from llm.client import LLMClient, ProviderSpec
from tools.code_review_tool import code_review
from tools.hybrid_rag_tool import make_hybrid_rag_tool
from tools.log_reader_tool import make_log_reader_tool
from tools.memory_access_tool import make_memory_read_tool, make_memory_write_tool
from tools.rag_retrieval_tool import make_rag_retrieval_tool
from tools.registry import DEFAULT_TOOL_PERMISSIONS, ToolRegistry
from tools.web_search_tool import web_search


def _demo_only_python_runner(python_code: str, timeout_seconds: int = 5) -> dict[str, Any]:
    """DEMO/TEST ONLY — NOT isolated. Never use for untrusted code."""
    proc = subprocess.run(
        [sys.executable, "-c", python_code],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "isolated": False,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "passed": proc.returncode == 0,
    }


def build_demo_workforce(
    project_root: Path,
) -> tuple[AssistantAI, ManagerAI, ObservabilityTracer]:
    root = project_root.resolve()
    audit_logger = AuditLogger(root / "logs")
    tracer = ObservabilityTracer(root / "logs")
    ltm = LongTermMemory(root / "memory_store" / "long_term" / "user_preferences.json")

    llm_router = LLMClient.with_tier_specs(
        tier1_providers=[ProviderSpec(provider="mock", model="tier1-premium-mock")],
        tier2_providers=[ProviderSpec(provider="mock", model="tier2-budget-mock")],
    )

    demo_perms = {k: set(v) for k, v in DEFAULT_TOOL_PERMISSIONS.items()}
    demo_perms["coder"] = {"demo_python_runner"}

    registry = ToolRegistry(audit_logger=audit_logger, permissions=demo_perms)
    registry.register("web_search", web_search)
    registry.register("log_reader", make_log_reader_tool(allowed_root=root / "logs"))
    registry.register("rag_retrieval", make_rag_retrieval_tool(allowed_root=root))
    registry.register("hybrid_rag", make_hybrid_rag_tool(allowed_root=root))
    registry.register("demo_python_runner", _demo_only_python_runner)
    registry.register("code_review", code_review)
    registry.register("memory_read", make_memory_read_tool(ltm))
    registry.register("memory_write", make_memory_write_tool(ltm))

    staff = StaffRoster(
        researcher=ResearcherAgent(registry, llm_client=llm_router),
        coder=CoderAgent(registry, llm_client=llm_router, demo_mode=True),
        reviewer=ReviewerAgent(registry, llm_client=llm_router),
        writer_tutor=WriterTutorAgent(registry, llm_client=llm_router),
        devops=DevOpsAgent(registry, llm_client=llm_router),
        security_auditor=SecurityAuditorAgent(registry, llm_client=llm_router),
    )
    assistant = AssistantAI(
        tool_registry=registry,
        audit_logger=audit_logger,
        llm_client=llm_router,
        tracer=tracer,
    )
    manager = ManagerAI(
        tool_registry=registry,
        staff=staff,
        short_term_dir=root / "memory_store" / "short_term",
        tracer=tracer,
        llm_client=llm_router,
        max_retries=2,
    )
    return assistant, manager, tracer


def run_demo_simulation(project_root: Path) -> int:
    assistant, manager, _tracer = build_demo_workforce(project_root)
    sample_log = project_root / "logs" / "sample_checkout.log"
    sample_log.parent.mkdir(parents=True, exist_ok=True)
    sample_log.write_text(
        "2026-11-27 10:01:02 INFO Checkout started\n"
        "2026-11-27 10:01:08 ERROR 500 Checkout timeout: Stripe API latency spiked 300%\n",
        encoding="utf-8",
    )

    print("=== [DEMO SIMULATION] Personal AI Workforce v10 ===")
    if assistant.llm_client is not None:
        print(f"Assistant Model Tier : {assistant.llm_client.providers[0].model}")
    if manager.staff.researcher.llm_client is not None:
        print(f"Researcher Model Tier: {manager.staff.researcher.llm_client.providers[0].model}")

    payload = assistant.draft_directive("Fix the checkout bug.")
    assistant.record_ceo_approval(
        payload,
        approved=True,
        extra_constraints=["Stripe API နှင့် ဆက်စပ်မှုရှိမရှိ စစ်ဆေးပါ။"],
        approval_source="demo_auto_approve",
    )
    result = manager.run_workflow(payload, log_path=str(sample_log))
    print("\n--- Manager AI Final Report to CEO ---")
    print(result["ceo_summary"])
    print("\n" + result["plan_markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(run_demo_simulation(Path(__file__).parent.resolve()))
