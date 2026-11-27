"""Comprehensive Unit Tests for Personal AI Workforce v10."""

from __future__ import annotations

import asyncio
import json
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


class TestPersonalAIWorkforceV10(unittest.TestCase):
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
        self.assertEqual(client.for_agent("researcher").providers[0].model, "gemini-2.5-flash-lite")

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
        self.assertFalse(code_review("b.open('/tmp/x', mode='w')")["approved"])
        self.assertFalse(code_review("Path('/tmp/x').write_text('hi')")["approved"])
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


    def test_pattern_b_workspace_zero_pollution_and_data_guard(self) -> None:
        from harness.workspace_guard import is_protected_path, validate_branch_name

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wf_root = base / "workforce"
            (wf_root / "config").mkdir(parents=True)
            (wf_root / "AGENTS.md").write_text("# WF Rules", encoding="utf-8")
            (wf_root / "config" / "language_profile.yaml").write_text("lang: my", encoding="utf-8")
            (wf_root / "config" / "model_tiers.yaml").write_text("t1: {}", encoding="utf-8")

            # Existing project with code, AGENTS.md, and production data
            existing = base / "IncomeTrackerv1"
            (existing / "data").mkdir(parents=True)
            (existing / "main.py").write_text("print('EXISTING_APP')\n", encoding="utf-8")
            (existing / "AGENTS.md").write_text("# Existing App Rules\n", encoding="utf-8")
            (existing / "data" / "prod.db").write_text("REAL_DB_BYTES", encoding="utf-8")
            before_files = sorted(str(p.relative_to(existing)) for p in existing.rglob("*"))

            rc = launch_agent(
                AGENT_PROFILES["opencode"], wf_root, workspace_root=existing, dry_run=True
            )
            self.assertEqual(rc, 0)

            # Verify ZERO files added/modified inside existing project!
            after_files = sorted(str(p.relative_to(existing)) for p in existing.rglob("*"))
            self.assertEqual(before_files, after_files)
            main_txt = (existing / "main.py").read_text(encoding="utf-8")
            self.assertEqual(main_txt, "print('EXISTING_APP')\n")
            db_txt = (existing / "data" / "prod.db").read_text(encoding="utf-8")
            self.assertEqual(db_txt, "REAL_DB_BYTES")

            # Verify all runtime state landed inside workforce/workspaces/IncomeTrackerv1/
            ws_state = wf_root / "workspaces" / "IncomeTrackerv1"
            self.assertTrue((ws_state / "opencode.json").exists())
            self.assertTrue((ws_state / ".workforce_runtime.json").exists())
            ctx_text = (ws_state / ".opencode_context.md").read_text(encoding="utf-8")
            self.assertIn("Existing App Rules", ctx_text)

            # Verify Protected Data Paths & Branch Name Validation
            policy_file = wf_root / "config" / "safety_policy.yaml"
            policy_file.write_text(
                "protected_patterns:\n  - data/**\n  - secrets/**\n  - .env\n",
                encoding="utf-8",
            )
            nested_db = existing / "data" / "sub" / "deep" / "prod.db"
            self.assertTrue(is_protected_path(nested_db, existing, policy_path=policy_file))
            secret_f = existing / "secrets" / "keys" / "api.key"
            self.assertTrue(is_protected_path(secret_f, existing, policy_path=policy_file))
            self.assertTrue(is_protected_path(existing / ".env", existing))
            self.assertFalse(is_protected_path(existing / "main.py", existing))
            self.assertEqual(validate_branch_name("ai-workforce/fix-1"), "ai-workforce/fix-1")
            with self.assertRaises(ValueError):
                validate_branch_name("--bad-flag")
            with self.assertRaises(ValueError):
                validate_branch_name("a..b")


    def test_pattern_b_plus_native_cli_assets_and_doctor(self) -> None:
        from launcher import build_launch_plan, run_doctor

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wf_root = base / "workforce"
            (wf_root / "config").mkdir(parents=True)
            (wf_root / "skills" / "create-prd").mkdir(parents=True)
            (wf_root / "skills" / "create-prd" / "SKILL.md").write_text(
                "---\nname: create-prd\ndescription: PRD\n---\n", encoding="utf-8"
            )
            (wf_root / "AGENTS.md").write_text("# WF Agents", encoding="utf-8")
            (wf_root / "CLAUDE.md").write_text("# WF Claude", encoding="utf-8")
            (wf_root / "config" / "language_profile.yaml").write_text("lang: my", encoding="utf-8")
            (wf_root / "config" / "model_tiers.yaml").write_text(
                "tier_1_orchestrators:\n  agents: [assistant_ai]\n  models:\n"
                "    - provider: anthropic\n      model: claude-sonnet-4-5\n"
                "tier_2_staff_executors:\n  agents: [researcher]\n  models:\n"
                "    - provider: gemini\n      model: gemini-3.5-flash-lite\n",
                encoding="utf-8",
            )
            (wf_root / "config" / "safety_policy.yaml").write_text(
                "protected_patterns:\n  - data/**\n  - .env\n", encoding="utf-8"
            )

            existing = base / "MyApp"
            existing.mkdir()

            c_plan = build_launch_plan(
                AGENT_PROFILES["claude"], wf_root, workspace_root=existing
            )
            self.assertIn("--add-dir", c_plan["argv"])
            self.assertIn("--settings", c_plan["argv"])
            c_dir = Path(c_plan["env"]["CLAUDE_CONFIG_DIR"])
            self.assertTrue((c_dir / "skills" / "create-prd" / "SKILL.md").exists())
            self.assertTrue((c_dir / "agents" / "wf-researcher.md").exists())
            settings_data = json.loads((c_dir / "settings.json").read_text(encoding="utf-8"))
            self.assertIn("Edit(./data/**)", settings_data["permissions"]["deny"])
            self.assertIn("Read(./.env)", settings_data["permissions"]["deny"])

            o_plan = build_launch_plan(
                AGENT_PROFILES["opencode"], wf_root, workspace_root=existing
            )
            xdg = Path(o_plan["env"]["XDG_CONFIG_HOME"])
            self.assertTrue((xdg / "opencode" / "skills" / "create-prd" / "SKILL.md").exists())
            self.assertTrue((xdg / "opencode" / "agent" / "wf-manager.md").exists())

            self.assertEqual(run_doctor(wf_root, workspace_root=existing), 0)

    def test_persistent_vector_memory_hybrid_read_and_workspace_isolation(self) -> None:
        from api.dashboard import list_sessions, read_memory_for_dashboard
        from harness.memory.workspace_memory import open_workspace_memory
        from main import run_memory_read, run_memory_write
        from tools.memory_access_tool import make_memory_read_tool, make_memory_write_tool

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            wf_root = base / "workforce"
            (wf_root / "config").mkdir(parents=True)
            (wf_root / "AGENTS.md").write_text("# WF Rules", encoding="utf-8")
            (wf_root / "CLAUDE.md").write_text("# WF Claude", encoding="utf-8")
            (wf_root / "config" / "language_profile.yaml").write_text("lang: my", encoding="utf-8")
            (wf_root / "config" / "model_tiers.yaml").write_text(
                "tier_1_orchestrators:\n  agents: [assistant_ai]\n  models:\n"
                "    - provider: anthropic\n      model: claude-sonnet-4-5\n"
                "tier_2_staff_executors:\n  agents: [researcher]\n  models:\n"
                "    - provider: gemini\n      model: gemini-3.5-flash-lite\n",
                encoding="utf-8",
            )
            (wf_root / "config" / "tool_permissions.yaml").write_text(
                "tool_permissions:\n"
                "  assistant_ai: [memory_read]\n"
                "  manager_ai: [memory_read, memory_write]\n"
                "  researcher: [log_reader]\n"
                "  coder: [docker_python_runner]\n"
                "  reviewer: [code_review]\n"
                "  security_auditor: [code_review, log_reader]\n",
                encoding="utf-8",
            )

            # 1. Current project memory write (requires approval) & persistent vector reload
            self.assertEqual(run_memory_write(wf_root, "Blocked", "No approval", ceo_approved=False), 1)
            self.assertEqual(
                run_memory_write(
                    wf_root, "Stripe Retry", "Added exponential backoff for Stripe checkout",
                    tags=["stripe", "checkout"], ceo_approved=True
                ),
                0,
            )
            _ctx0, ltm0, vec0 = open_workspace_memory(wf_root)
            self.assertGreater(vec0.count(), 0)
            reader0 = make_memory_read_tool(ltm0, vector_store=vec0, workspace="default")
            recent0 = reader0(keyword="")
            self.assertEqual(len(recent0["episodes"]), 1)
            hybrid0 = reader0(keyword="exponential backoff")
            self.assertEqual(hybrid0["mode"], "hybrid")
            self.assertGreaterEqual(len(hybrid0["semantic_hits"]), 1)

            # 2. External --workspace memory isolation (ZERO pollution in external project!)
            ext_proj = base / "ShopApp"
            ext_proj.mkdir()
            (ext_proj / "app.py").write_text("print('shop')\n", encoding="utf-8")
            before_ext = sorted(str(p.relative_to(ext_proj)) for p in ext_proj.rglob("*"))

            self.assertEqual(
                run_memory_write(
                    wf_root, "ShopApp Cache", "Fixed Redis TTL bug in ShopApp",
                    tags=["redis"], ceo_approved=True, workspace_root=ext_proj
                ),
                0,
            )
            self.assertEqual(run_memory_read(wf_root, "Redis", workspace_root=ext_proj), 0)

            # Verify ZERO files created inside external workspace
            after_ext = sorted(str(p.relative_to(ext_proj)) for p in ext_proj.rglob("*"))
            self.assertEqual(before_ext, after_ext)

            # Verify external memory is isolated from default memory
            ctx_ext, ltm_ext, vec_ext = open_workspace_memory(wf_root, ext_proj)
            self.assertEqual(ctx_ext.workspace_slug, "ShopApp")
            self.assertEqual(len(ltm_ext.search_episodes("Redis")), 1)
            self.assertEqual(len(ltm_ext.search_episodes("Stripe")), 0)
            self.assertEqual(len(vec_ext.query("Redis TTL")), 1)

            # 3. Launcher injects live memory snapshot & Claude subagent uses Claude-compatible model
            ctx_agy = prepare_context_injection(AGENT_PROFILES["agy"], wf_root, workspace_root=ext_proj)
            agy_text = Path(ctx_agy["injected_context_path"]).read_text(encoding="utf-8")
            self.assertIn("Persistent Memory Context", agy_text)
            self.assertIn("ShopApp Cache", agy_text)

            ctx_claude = prepare_context_injection(AGENT_PROFILES["claude"], wf_root, workspace_root=ext_proj)
            claude_researcher = (
                Path(ctx_claude["assets"]["config_dir"]) / "agents" / "wf-researcher.md"
            ).read_text(encoding="utf-8")
            self.assertIn("model: haiku", claude_researcher)
            self.assertNotIn("gemini-3.5-flash-lite", claude_researcher)

            # 4. Demo workflow on external --workspace consolidates STM -> LTM + Vector + Dashboard
            assistant, manager, _tracer = build_demo_workforce(wf_root, workspace_root=ext_proj)
            sample_log = ctx_ext.logs_dir / "shop.log"
            sample_log.parent.mkdir(parents=True, exist_ok=True)
            sample_log.write_text("ERROR 500 timeout\n", encoding="utf-8")
            payload = assistant.draft_directive("Fix ShopApp timeout")
            self.assertIn("memory_recall", payload.context_notes)
            assistant.record_ceo_approval(payload, approved=True, approval_source="test")
            res = manager.run_workflow(payload, log_path=str(sample_log))
            self.assertEqual(res["status"], "COMPLETED_SIMULATION")
            self.assertIn(payload.session_id, list_sessions(ctx_ext.logs_dir))

            dash_mem = read_memory_for_dashboard(
                query="ShopApp", workspace="ShopApp", project_root=wf_root
            )
            self.assertGreaterEqual(len(dash_mem["episodes"]), 2)

            # 5. ToolRegistry.from_config loads YAML permissions
            reg = ToolRegistry.from_config(
                AuditLogger(wf_root / "logs"), wf_root / "config" / "tool_permissions.yaml"
            )
            self.assertEqual(reg.permissions["researcher"], {"log_reader"})
            self.assertEqual(
                make_memory_write_tool(ltm_ext, vector_store=vec_ext)(
                    "Direct", "Saved & indexed", ceo_approved=True
                )["indexed"],
                True,
            )

    def test_web_search_providers_hierarchy_config_and_skills(self) -> None:
        from harness.hierarchy_loader import load_hierarchy_config
        from tools.web_search_tool import web_search

        # 1. DuckDuckGo fallback (no API keys)
        os.environ.pop("TAVILY_API_KEY", None)
        os.environ.pop("BRAVE_API_KEY", None)
        ddg = web_search(
            "FastAPI",
            max_results=2,
            http_get_fn=lambda _u, _h, _t: {
                "Heading": "FastAPI",
                "AbstractText": "Modern Python web framework",
                "AbstractURL": "https://fastapi.tiangolo.com",
            },
        )
        self.assertEqual(ddg["mode"], "duckduckgo")
        self.assertEqual(ddg["results"][0]["title"], "FastAPI")

        # 2. Tavily API when TAVILY_API_KEY is set
        os.environ["TAVILY_API_KEY"] = "tvly-test"
        try:
            tv = web_search(
                "Python AST",
                http_post_fn=lambda _u, _h, _p, _t: {
                    "results": [{"title": "AST Docs", "url": "https://docs.python.org", "content": "ast module"}]
                },
            )
            self.assertEqual(tv["mode"], "tavily")
            self.assertEqual(tv["results"][0]["title"], "AST Docs")
        finally:
            os.environ.pop("TAVILY_API_KEY", None)

        # 3. Offline graceful fallback when network fails
        off = web_search(
            "offline query",
            http_get_fn=lambda _u, _h, _t: (_ for _ in ()).throw(OSError("no net")),
        )
        self.assertEqual(off["mode"], "offline_fallback")
        self.assertEqual(off["results"], [])

        # 4. Hierarchy config loader & enriched skills check
        project_root = Path(__file__).parent.parent
        hier = load_hierarchy_config(project_root / "config" / "hierarchy_config.yaml")
        self.assertEqual(hier.max_retries_per_step, 2)
        self.assertEqual(hier.max_concurrent_staff, 4)
        self.assertTrue(hier.require_ceo_approval_for_memory_write)

        skill_files = list((project_root / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skill_files), 10)
        self.assertTrue((project_root / "skills" / "memory-management" / "SKILL.md").is_file())
        self.assertTrue((project_root / "skills" / "project-bootstrap" / "SKILL.md").is_file())

    def test_project_bootstrap_agent_files_and_ai_skill_selection(self) -> None:
        from harness.project_bootstrap import (
            analyze_project,
            decide_recommended_skills,
            sync_agent_instruction_files,
        )

        project_root = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # Project A: Fresh Python + FastAPI + Docker project (NO agent files yet -> auto-create all 4)
            proj_a = base / "FastAPIService"
            proj_a.mkdir()
            (proj_a / "README.md").write_text("# FastAPIService\nBuild a fast billing API.\n", encoding="utf-8")
            (proj_a / "requirements.txt").write_text("fastapi\npsycopg\n", encoding="utf-8")
            (proj_a / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

            prof_a = analyze_project(project_root, proj_a)
            self.assertEqual(len(prof_a.reference_docs_found), 3)
            self.assertIn("fastapi", prof_a.detected_stack)
            self.assertIn("docker", prof_a.detected_stack)
            self.assertIn("sql", prof_a.detected_stack)
            self.assertEqual(len(prof_a.missing_agent_files), 4)

            skills_a = {r.skill for r in decide_recommended_skills(prof_a)}
            self.assertIn("fastapi-templates", skills_a)
            self.assertIn("docker-expert", skills_a)
            self.assertIn("sql-optimization-patterns", skills_a)
            self.assertNotIn("vercel-react-best-practices", skills_a)

            sync_a = sync_agent_instruction_files(prof_a, project_root)
            self.assertEqual(set(sync_a["created"]), {"AGENTS.md", "CLAUDE.md", "QWEN.md", "GEMINI.md"})
            agents_txt = (proj_a / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Build a fast billing API.", agents_txt)
            self.assertIn("1.Personal-Agent-Documents.md", agents_txt)
            self.assertIn("မြန်မာစာ", agents_txt)

            # Re-running when files EXIST must ask user: test Keep (k), Update (u), Modify (m), Keep (k)
            (proj_a / "AGENTS.md").write_text("# Custom Existing Rules\n", encoding="utf-8")
            (proj_a / "CLAUDE.md").write_text("# Existing Claude Rules\n", encoding="utf-8")
            (proj_a / "QWEN.md").write_text("# Old Qwen Rules\n", encoding="utf-8")
            answers = iter(["k", "u", "m", "k"])
            sync_a2 = sync_agent_instruction_files(
                prof_a, project_root, input_fn=lambda _p: next(answers)
            )
            self.assertEqual(sync_a2["kept"], ["AGENTS.md", "GEMINI.md"])
            self.assertEqual(sync_a2["updated"], ["CLAUDE.md"])
            self.assertEqual(sync_a2["modified"], ["QWEN.md"])
            self.assertEqual((proj_a / "AGENTS.md").read_text(encoding="utf-8"), "# Custom Existing Rules\n")
            claude_updated = (proj_a / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("# Existing Claude Rules", claude_updated)
            self.assertIn("WORKFORCE-MANAGED-START", claude_updated)
            self.assertIn("FastAPIService", (proj_a / "QWEN.md").read_text(encoding="utf-8"))

            # Project B: React/Next.js frontend project -> selects React & frontend-design skills
            proj_b = base / "WebDashboard"
            proj_b.mkdir()
            (proj_b / "package.json").write_text('{"dependencies":{"react":"19","next":"15"}}', encoding="utf-8")
            prof_b = analyze_project(project_root, proj_b, explicit_goal="Build React admin dashboard")
            skills_b = {r.skill for r in decide_recommended_skills(prof_b)}
            self.assertIn("vercel-react-best-practices", skills_b)
            self.assertIn("frontend-design", skills_b)
            self.assertNotIn("fastapi-templates", skills_b)


if __name__ == "__main__":
    unittest.main()
