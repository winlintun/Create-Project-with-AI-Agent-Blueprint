"""Comprehensive Unit Tests for Personal AI Workforce v8."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from api.dashboard import (
    read_jsonl_for_session,
    summarize_session_costs,
    verify_dashboard_token,
)
from demo import build_demo_workforce
from harness.circuit_breaker import ManagerCircuitBreaker
from harness.context_payload import StructuredContextPayload
from harness.hitl.approval_adapter import request_cli_approval
from harness.memory.auto_consolidation import AutoConsolidator
from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory
from harness.memory.vector_store import InMemoryCosineVectorStore
from harness.observability.tracer import ObservabilityTracer
from harness.persistence.audit_logger import AuditLogger
from launcher import AGENT_PROFILES, launch_agent, prepare_context_injection, prepare_filtered_env
from llm.client import LLMClient, LLMResponse, ProviderSpec
from tools.code_review_tool import code_review
from tools.docker_python_runner_tool import build_docker_sandbox_cmd
from tools.hybrid_rag_tool import make_hybrid_rag_tool
from tools.log_reader_tool import make_log_reader_tool
from tools.registry import ToolRegistry


class TestPersonalAIWorkforceV8(unittest.TestCase):
    def test_anthropic_and_gemini_header_auth_without_url_key(self) -> None:
        captured: list[tuple[str, dict[str, str]]] = []

        def fake_post(
            url: str, headers: dict[str, str], payload: dict[str, Any], **_kw: Any
        ) -> dict[str, Any]:
            captured.append((url, headers))
            if "anthropic" in url:
                return {
                    "content": [{"text": "Hello from Claude"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                }
            return {
                "candidates": [{"content": {"parts": [{"text": "Hello from Gemini"}]}}],
                "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4},
            }

        os.environ["ANTHROPIC_API_KEY"] = "ant-test-key"
        os.environ["GEMINI_API_KEY"] = "gem-test-key"
        try:
            ant_spec = ProviderSpec("anthropic", "claude-sonnet-4-5")
            c_ant = LLMClient([ant_spec], http_post_fn=fake_post)
            r_ant = c_ant.complete("sys", "hi")
            self.assertEqual(r_ant.content, "Hello from Claude")
            self.assertEqual(captured[0][1]["x-api-key"], "ant-test-key")
            self.assertEqual(captured[0][1]["anthropic-version"], "2023-06-01")

            c_gem = LLMClient([ProviderSpec("gemini", "gemini-2.5-pro")], http_post_fn=fake_post)
            r_gem = c_gem.complete("sys", "hi")
            self.assertEqual(r_gem.content, "Hello from Gemini")
            self.assertNotIn("key=", captured[1][0])
            self.assertEqual(captured[1][1]["x-goog-api-key"], "gem-test-key")
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)

    def test_dynamic_yaml_tier_loading_and_fallback(self) -> None:
        cfg_path = Path(__file__).parent.parent / "config" / "model_tiers.yaml"
        client = LLMClient.from_config(cfg_path)
        self.assertEqual(client.for_agent("assistant_ai").providers[0].provider, "anthropic")
        self.assertEqual(client.for_agent("researcher").providers[0].model, "gemini-3.5-flash-lite")

        fb_client = LLMClient(
            providers=[ProviderSpec("anthropic", "claude"), ProviderSpec("ollama", "qwen2.5:7b")],
            custom_handlers={
                "anthropic": lambda _s, _sys, _u: (_ for _ in ()).throw(ConnectionError("down")),
                "ollama": lambda s, _sys, u: LLMResponse(s.provider, s.model, f"OK:{u}"),
            },
        )
        self.assertEqual(fb_client.complete("sys", "ping").provider, "ollama")

    def test_ast_code_review_catches_bypasses_and_open_write(self) -> None:
        self.assertFalse(code_review("__import__('os').system('id')")["approved"])
        self.assertFalse(code_review("getattr(__builtins__, 'ev' + 'al')('1+1')")["approved"])
        self.assertFalse(code_review("import subprocess\nsubprocess.run(['ls'])")["approved"])
        self.assertFalse(code_review("open('/etc/passwd', 'w').write('x')")["approved"])
        self.assertFalse(code_review("builtins.open('/tmp/x', 'w')")["approved"])
        self.assertFalse(code_review("io.open('/tmp/x', 'a')")["approved"])
        self.assertFalse(code_review("().__class__.__bases__[0].__subclasses__()")["approved"])
        self.assertFalse(code_review("__builtins__['eval']('1+1')")["approved"])
        clean = "def add(a: int, b: int) -> int:\n    return a + b\n"
        self.assertTrue(code_review(clean)["approved"])

    def test_dotenv_loader_and_automatic_cost_logging(self) -> None:
        from harness.env_loader import load_dotenv_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_file.write_text('TEST_WF_KEY="hello_v8"\n# comment\n', encoding="utf-8")
            os.environ.pop("TEST_WF_KEY", None)
            try:
                self.assertEqual(load_dotenv_file(env_file), 1)
                self.assertEqual(os.environ.get("TEST_WF_KEY"), "hello_v8")
            finally:
                os.environ.pop("TEST_WF_KEY", None)

            assistant, _manager, _tracer = build_demo_workforce(root)
            payload = assistant.draft_directive("Auto cost log test")
            summary = summarize_session_costs(payload.session_id, logs_root=root / "logs")
            self.assertEqual(summary["call_count"], 1)
            self.assertGreater(summary["total_tokens"], 0)

    def test_docker_sandbox_cmd_has_cap_drop_tmpfs_and_name(self) -> None:
        cname, cmd = build_docker_sandbox_cmd("print(1)", runtime="runsc")
        self.assertTrue(cname.startswith("wf_sbx_"))
        self.assertIn("--cap-drop=ALL", cmd)
        self.assertIn("--tmpfs", cmd)
        self.assertIn("/tmp:size=16m,noexec,nosuid,nodev", cmd)
        self.assertIn("--name", cmd)
        self.assertIn("--runtime=runsc", cmd)

    def test_async_workflow_stops_and_escalates_when_researcher_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "logs").mkdir(parents=True, exist_ok=True)
            assistant, manager, _ = build_demo_workforce(root)
            payload = assistant.draft_directive("Missing log test")
            assistant.record_ceo_approval(
                payload, approved=True, approval_source="demo_auto_approve"
            )

            # Missing log file -> researcher must fail quality gate & escalate (NOT run coder!)
            missing = str(root / "logs" / "missing.log")
            res = asyncio.run(manager.run_workflow_async(payload, missing))
            self.assertEqual(res["status"], "ESCALATED_TO_CEO")
            self.assertIn("Step 1", res["plan_markdown"])
            self.assertIn("[!]", res["plan_markdown"])

    def test_async_workflow_succeeds_with_valid_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "logs").mkdir(parents=True, exist_ok=True)
            sample_log = root / "logs" / "app.log"
            sample_log.write_text("ERROR 500 timeout\n", encoding="utf-8")
            assistant, manager, _ = build_demo_workforce(root)
            payload = assistant.draft_directive("Async valid test")
            assistant.record_ceo_approval(
                payload, approved=True, approval_source="demo_auto_approve"
            )

            res = asyncio.run(manager.run_workflow_async(payload, str(sample_log)))
            self.assertEqual(res["status"], "COMPLETED_ASYNC")
            trace_file = root / "logs" / "trace_logs" / f"{payload.session_id}.jsonl"
            self.assertTrue(trace_file.exists())

    def test_dashboard_cost_summary_and_token_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tracer = ObservabilityTracer(root / "logs")
            tracer.record_token_cost(
                trace_id="t1", session_id="sess_c1", agent="assistant_ai",
                provider="anthropic",
                model="claude",
                input_tokens=100,
                output_tokens=50,
                estimated_cost_usd=0.001,
            )
            tracer.record_token_cost(
                trace_id="t1", session_id="sess_c1", agent="researcher",
                provider="gemini",
                model="flash",
                input_tokens=200,
                output_tokens=100,
                estimated_cost_usd=0.0002,
            )
            summary = summarize_session_costs("sess_c1", logs_root=root / "logs")
            self.assertEqual(summary["total_tokens"], 450)
            self.assertEqual(summary["total_cost_usd"], 0.0012)
            cost_rows = read_jsonl_for_session("cost_logs", "sess_c1", logs_root=root / "logs")
            self.assertEqual(len(cost_rows), 2)

            os.environ["WORKFORCE_DASHBOARD_TOKEN"] = "secret-dash-token"
            try:
                self.assertFalse(verify_dashboard_token(None))
                self.assertFalse(verify_dashboard_token("Bearer wrong"))
                self.assertTrue(verify_dashboard_token("Bearer secret-dash-token"))
            finally:
                os.environ.pop("WORKFORCE_DASHBOARD_TOKEN", None)

    def test_vector_memory_and_auto_consolidator(self) -> None:
        vs = InMemoryCosineVectorStore()
        vs.upsert("d1", "Stripe checkout timeout retry policy")
        vs.upsert("d2", "Mohinga soup recipe")
        hits = vs.query("Stripe timeout")
        self.assertEqual(hits[0]["id"], "d1")

        with tempfile.TemporaryDirectory() as tmp:
            ltm = LongTermMemory(Path(tmp) / "ltm.json")
            consolidator = AutoConsolidator(ltm, interval_seconds=60)
            stm = ShortTermMemory("sess_a1")
            stm.set_step_output("1", {"ok": True})
            with self.assertRaises(PermissionError):
                consolidator.enqueue_session(stm, topic="x", ceo_approved=False)
            consolidator.enqueue_session(stm, topic="approved", ceo_approved=True)
            self.assertEqual(consolidator.run_once(), 1)

    def test_launcher_cli_injection_and_env_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Rules", encoding="utf-8")
            (root / "config").mkdir()
            lp = root / "config" / "language_profile.yaml"
            lp.write_text("primary_language: Burmese", encoding="utf-8")
            mt = root / "config" / "model_tiers.yaml"
            mt.write_text("tier_1_orchestrators: {}", encoding="utf-8")

            ctx = prepare_context_injection(AGENT_PROFILES["agy"], root)
            self.assertTrue(ctx["injected_context_path"].endswith(".agy_context.md"))
            env = prepare_filtered_env(
                AGENT_PROFILES["agy"], root, ctx,
                source_env={
                    "PATH": "/usr/bin",
                    "GEMINI_API_KEY": "g",
                    "AWS_SECRET_ACCESS_KEY": "LEAK",
                },
            )
            self.assertIn("GEMINI_API_KEY", env)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
            self.assertEqual(launch_agent(AGENT_PROFILES["opencode"], root, dry_run=True), 0)

    def test_security_core_and_project_files(self) -> None:
        project_root = Path(__file__).parent.parent
        self.assertTrue((project_root / ".gitignore").exists())
        self.assertTrue((project_root / "project_book" / "05_project_calendar.md").exists())

        payload = StructuredContextPayload("Fix bug", "Check logs")
        with self.assertRaises(PermissionError):
            payload.validate_for_handoff()
        payload.approve()
        payload.approved_directive = "Tampered"
        with self.assertRaises(PermissionError):
            payload.validate_for_handoff()

        with self.assertRaises(ValueError):
            ManagerCircuitBreaker(max_retries=-1)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logger = AuditLogger(root / "logs")
            reg = ToolRegistry(logger, permissions={})
            reg.register("web_search", lambda query: {})
            with self.assertRaises(PermissionError):
                reg.invoke("sess_1", "researcher", "web_search", query="x")

            (root / "secret.txt").write_text("SECRET", encoding="utf-8")
            with self.assertRaises(PermissionError):
                make_log_reader_tool(root / "logs")(str(root / "logs" / ".." / "secret.txt"))

            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("Stripe timeout guide", encoding="utf-8")
            rag_res = make_hybrid_rag_tool(root)("docs", "Stripe")
            self.assertTrue(rag_res["results"][0]["file"].endswith("a.md"))

        p2 = StructuredContextPayload("Fix", "Logs")
        ans = iter(["y"])
        self.assertTrue(request_cli_approval(p2, input_fn=lambda _p: next(ans)).approved)


if __name__ == "__main__":
    unittest.main()
