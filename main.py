#!/usr/bin/env python3
"""Personal AI Workforce v10 — Interactive Agent CLI Launcher, Memory CLI & Workflow Entrypoint."""

from __future__ import annotations

import argparse
import json
import os
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
from demo import run_demo_simulation
from harness.env_loader import load_dotenv_file
from harness.hierarchy_loader import load_hierarchy_config
from harness.hitl.approval_adapter import request_cli_approval
from harness.memory.auto_consolidation import AutoConsolidator
from harness.memory.workspace_memory import open_workspace_memory
from harness.observability.tracer import ObservabilityTracer
from harness.persistence.audit_logger import AuditLogger
from harness.project_bootstrap import (
    DEFAULT_AGENT_FILES,
    analyze_project,
    decide_recommended_skills,
    install_selected_skills,
    sync_agent_instruction_files,
)
from launcher import AGENT_PROFILES, launch_agent, run_doctor, validate_agent_available
from llm.client import LLMClient
from tools.code_review_tool import code_review
from tools.docker_python_runner_tool import docker_python_runner
from tools.hybrid_rag_tool import make_hybrid_rag_tool
from tools.log_reader_tool import make_log_reader_tool
from tools.memory_access_tool import make_memory_read_tool, make_memory_write_tool
from tools.rag_retrieval_tool import make_rag_retrieval_tool
from tools.registry import ToolRegistry
from tools.web_search_tool import web_search

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

MENU_ROWS = [
    ("1", "opencode", "OpenCode CLI", "Open-source AI coding agent"),
    ("2", "claude", "Claude CLI", "Anthropic official CLI"),
    ("3", "qwen", "Qwen-CLI", "Alibaba Qwen coding agent"),
    ("4", "agy", "Agy (Antigravity)", "Antigravity CLI agent"),
    ("5", "demo", "Demo Simulation", "Local 4-Tier workflow demo"),
    ("q", "quit", "Quit", "Exit launcher"),
]


def show_menu() -> str:
    if HAS_RICH:
        console = Console()
        table = Table(title="Personal AI Workforce v10 — Agent CLI Launcher")
        table.add_column("#", style="bold cyan")
        table.add_column("Agent CLI", style="bold green")
        table.add_column("Status")
        table.add_column("Description")
        for key, slug, label, desc in MENU_ROWS:
            if slug in AGENT_PROFILES:
                ok = validate_agent_available(AGENT_PROFILES[slug])
                status = "[green]Installed[/]" if ok else "[yellow]Not Found[/]"
            else:
                status = "[cyan]Built-in[/]"
            table.add_row(key, label, status, desc)
        console.print(table)
        return console.input("[bold yellow]ရွေးချယ်ပါ (1-5/q): [/]").strip().lower()

    print("\n=== Personal AI Workforce v10 — Agent CLI Launcher ===")
    for key, slug, label, desc in MENU_ROWS:
        if slug in AGENT_PROFILES:
            status = "Installed" if validate_agent_available(AGENT_PROFILES[slug]) else "Not Found"
        else:
            status = "Built-in"
        print(f"  [{key}] {label:<18} ({status:<9}) — {desc}")
    return input("ရွေးချယ်ပါ (1-5/q): ").strip().lower()


def run_memory_read(
    workforce_root: Path,
    query: str,
    *,
    workspace_root: Path | None = None,
    top_k: int = 5,
) -> int:
    ctx, ltm, vec = open_workspace_memory(workforce_root, workspace_root)
    reader = make_memory_read_tool(ltm, vector_store=vec, workspace=ctx.workspace_slug)
    result = reader(keyword=query, top_k=top_k)
    output: dict[str, Any] = {
        "workspace_slug": ctx.workspace_slug,
        "workspace_root": str(ctx.workspace_root),
        "memory_store": str(ctx.long_term_path),
        "vector_index": str(ctx.vector_index_path),
        **result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def run_memory_write(
    workforce_root: Path,
    topic: str,
    summary: str,
    *,
    tags: list[str] | None = None,
    ceo_approved: bool = False,
    workspace_root: Path | None = None,
) -> int:
    ctx, ltm, vec = open_workspace_memory(workforce_root, workspace_root)
    writer = make_memory_write_tool(ltm, vector_store=vec, workspace=ctx.workspace_slug)
    try:
        res = writer(topic=topic, summary=summary, tags=tags or [], ceo_approved=ceo_approved)
    except PermissionError as exc:
        print(f"[X] {exc} (Add --approve to confirm CEO approval.)")
        return 1
    output = {
        "workspace_slug": ctx.workspace_slug,
        "memory_store": str(ctx.long_term_path),
        "vector_index": str(ctx.vector_index_path),
        **res,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def run_production_workflow(
    workforce_root: Path,
    intent: str,
    *,
    workspace_root: Path | None = None,
    log_path: str | None = None,
    auto_approve: bool = False,
) -> int:
    root = workforce_root.resolve()
    mem_ctx, ltm, vec = open_workspace_memory(root, workspace_root)
    audit_logger = AuditLogger(mem_ctx.logs_dir)
    tracer = ObservabilityTracer(mem_ctx.logs_dir)
    consolidator = AutoConsolidator(ltm, vector_store=vec, workspace=mem_ctx.workspace_slug)
    llm_router = LLMClient.from_config(root / "config" / "model_tiers.yaml")

    registry = ToolRegistry.from_config(
        audit_logger=audit_logger,
        config_path=root / "config" / "tool_permissions.yaml",
    )
    registry.register("web_search", web_search)
    registry.register("log_reader", make_log_reader_tool(allowed_root=mem_ctx.logs_dir))
    registry.register("rag_retrieval", make_rag_retrieval_tool(allowed_root=mem_ctx.workspace_root))
    registry.register("hybrid_rag", make_hybrid_rag_tool(allowed_root=mem_ctx.workspace_root))
    registry.register("docker_python_runner", docker_python_runner)
    registry.register("code_review", code_review)
    registry.register(
        "memory_read",
        make_memory_read_tool(ltm, vector_store=vec, workspace=mem_ctx.workspace_slug),
    )
    registry.register(
        "memory_write",
        make_memory_write_tool(ltm, vector_store=vec, workspace=mem_ctx.workspace_slug),
    )

    staff = StaffRoster(
        researcher=ResearcherAgent(registry, llm_client=llm_router, tracer=tracer),
        coder=CoderAgent(registry, llm_client=llm_router, tracer=tracer, demo_mode=False),
        reviewer=ReviewerAgent(registry, llm_client=llm_router, tracer=tracer),
        writer_tutor=WriterTutorAgent(registry, llm_client=llm_router, tracer=tracer),
        devops=DevOpsAgent(registry, llm_client=llm_router, tracer=tracer),
        security_auditor=SecurityAuditorAgent(registry, llm_client=llm_router, tracer=tracer),
    )
    assistant = AssistantAI(
        tool_registry=registry, audit_logger=audit_logger, llm_client=llm_router, tracer=tracer
    )
    hier = load_hierarchy_config(root / "config" / "hierarchy_config.yaml")
    manager = ManagerAI(
        tool_registry=registry,
        staff=staff,
        short_term_dir=mem_ctx.short_term_dir,
        tracer=tracer,
        llm_client=llm_router,
        max_retries=hier.max_retries_per_step,
        max_concurrency=hier.max_concurrent_staff,
        consolidator=consolidator,
    )

    try:
        payload = assistant.draft_directive(intent)
    except RuntimeError as exc:
        print(f"[X] LLM Provider failed: {exc}")
        print("    Configure API keys in .env (ANTHROPIC_API_KEY / GEMINI_API_KEY / GROQ_API_KEY) or run --demo.")
        return 1

    if auto_approve:
        assistant.record_ceo_approval(payload, approved=True, approval_source="cli_flag_approve")
    else:
        outcome = request_cli_approval(payload)
        assistant.record_ceo_approval(
            payload,
            approved=outcome.approved,
            extra_constraints=outcome.extra_constraints,
            approval_source=outcome.source,
        )
        if not outcome.approved:
            print("[!] CEO rejected directive. Workflow cancelled.")
            return 1

    target_log = log_path or str(mem_ctx.logs_dir / "app.log")
    result = manager.run_workflow(payload, log_path=target_log)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "ESCALATED_TO_CEO" else 1


def run_recommend_skills_cli(
    workforce_root: Path,
    *,
    workspace_root: Path | None = None,
    goal: str | None = None,
    dry_run: bool = False,
    auto_yes: bool = False,
) -> int:
    profile = analyze_project(workforce_root, workspace_root, explicit_goal=goal)
    recs = decide_recommended_skills(profile, extra_goal_text=goal or "")
    cli_ver = os.getenv("SKILLS_CLI_VERSION", "latest")
    print(f"=== AI Skill Decision Engine (skills.sh | CLI: skills@{cli_ver}) ===")
    print(f"Target Project : {profile.project_name} ({profile.workspace_root})")
    print(f"Detected Stack : {', '.join(profile.detected_stack) or 'general'}")
    print(f"Project Goal   : {profile.inferred_goal}")
    print(f"Reference Docs : {', '.join(profile.reference_docs_found) or 'none'}")
    print(f"\nRecommended Skills ({len(recs)}):")
    for rec in recs:
        print(f"  - [{rec.priority}] {rec.repo} --skill {rec.skill}")
        print(f"      Reason: {rec.reason}")
    res = install_selected_skills(
        recs,
        skills_cli_version=cli_ver,
        dry_run=dry_run,
        auto_yes=auto_yes,
        cwd=workforce_root,
    )
    if res.get("dry_run"):
        print("\n[DRY-RUN] No packages installed.")
    elif res.get("cancelled"):
        print("\n[!] Skill installation cancelled by user.")
    else:
        print(f"\n[OK] Installed {len(res.get('installed', []))} skill(s).")
        if res.get("failed"):
            print(f"[!] Failed ({len(res['failed'])}): {res['failed']}")
            return 1
    return 0


def run_bootstrap_cli(
    workforce_root: Path,
    *,
    workspace_root: Path | None = None,
    goal: str | None = None,
    agent_files: tuple[str, ...] = DEFAULT_AGENT_FILES,
    install_skills: bool = False,
    dry_run: bool = False,
    auto_yes: bool = False,
) -> int:
    ws_target = workspace_root.resolve() if workspace_root is not None else workforce_root.resolve()
    if not ws_target.exists() or not ws_target.is_dir():
        print(f"[X] Workspace directory မတွေ့ပါ: {ws_target}")
        return 1

    profile = analyze_project(
        workforce_root,
        ws_target,
        explicit_goal=goal,
        target_agent_files=agent_files,
    )
    print("=== Personal AI Workforce — Project Bootstrap ===")
    print(f"Project        : {profile.project_name} ({profile.workspace_root})")
    print(f"Detected Stack : {', '.join(profile.detected_stack) or 'general'}")
    print(f"Project Goal   : {profile.inferred_goal}")
    print(f"Reference Docs : {', '.join(profile.reference_docs_found) or 'none'}")
    print(f"Existing Files : {', '.join(profile.existing_agent_files) or 'none'}")
    print(f"Missing Files  : {', '.join(profile.missing_agent_files) or 'none'}")

    sync_res = sync_agent_instruction_files(
        profile,
        workforce_root,
        target_files=agent_files,
        dry_run=dry_run,
    )
    print("\n--- Agent Instruction Files Summary ---")
    print(json.dumps(sync_res, ensure_ascii=False, indent=2))

    if install_skills:
        print("")
        run_recommend_skills_cli(
            workforce_root,
            workspace_root=ws_target,
            goal=goal,
            dry_run=dry_run,
            auto_yes=auto_yes,
        )
    else:
        recs = decide_recommended_skills(profile, extra_goal_text=goal or "")
        print(
            f"\n[TIP] {len(recs)} skills.sh package(s) recommended for this project. "
            "Run with `--install-skills` or `bash scripts/install_recommended_skills.sh` to install."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Personal AI Workforce v10 CLI Launcher")
    parser.add_argument("--agent", choices=list(AGENT_PROFILES.keys()))
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Target existing project directory (Pattern B zero-pollution mode)",
    )
    parser.add_argument(
        "--create-branch",
        default=None,
        help="Optional new git branch to create in target workspace before launch",
    )
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--doctor", action="store_true", help="Diagnose CLI asset wiring")
    parser.add_argument(
        "--print-launch", action="store_true", help="Print launch argv without running"
    )
    parser.add_argument(
        "--memory-read",
        nargs="?",
        const="",
        default=None,
        metavar="QUERY",
        help="Read persistent memory (recent episodes if empty, or hybrid keyword+vector search)",
    )
    parser.add_argument(
        "--memory-write",
        nargs=2,
        metavar=("TOPIC", "SUMMARY"),
        default=None,
        help="Write an episode to persistent memory (requires --approve)",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags for --memory-write",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Explicit CEO approval flag for --memory-write or --run",
    )
    parser.add_argument(
        "--run",
        metavar="INTENT",
        default=None,
        help="Run production 4-tier workflow with real LLM & Docker sandbox",
    )
    parser.add_argument(
        "--log-path",
        default=None,
        help="Log file path inside workspace logs dir for --run",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Check/create AGENTS.md, CLAUDE.md, QWEN.md, GEMINI.md from project goals & 3 reference docs",
    )
    parser.add_argument(
        "--recommend-skills",
        action="store_true",
        help="AI-decide and optionally install needed skills.sh packages for this project",
    )
    parser.add_argument(
        "--goal",
        default=None,
        help="Explicit project goal for --bootstrap or --recommend-skills",
    )
    parser.add_argument(
        "--agent-files",
        default=",".join(DEFAULT_AGENT_FILES),
        help="Comma-separated agent files to sync during --bootstrap",
    )
    parser.add_argument(
        "--install-skills",
        action="store_true",
        help="Also run AI skill recommendation & installation during --bootstrap",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm skill installation prompt (non-interactive)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).parent.resolve()
    load_dotenv_file(root / ".env")
    ws_root = args.workspace.resolve() if args.workspace else None

    if args.bootstrap:
        chosen_files = tuple(f.strip() for f in args.agent_files.split(",") if f.strip())
        return run_bootstrap_cli(
            root,
            workspace_root=ws_root,
            goal=args.goal,
            agent_files=chosen_files or DEFAULT_AGENT_FILES,
            install_skills=args.install_skills,
            dry_run=args.dry_run,
            auto_yes=args.yes,
        )
    if args.recommend_skills:
        return run_recommend_skills_cli(
            root,
            workspace_root=ws_root,
            goal=args.goal,
            dry_run=args.dry_run,
            auto_yes=args.yes,
        )
    if args.memory_read is not None:
        return run_memory_read(root, args.memory_read, workspace_root=ws_root)
    if args.memory_write is not None:
        topic, summary = args.memory_write
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        return run_memory_write(
            root,
            topic,
            summary,
            tags=tags,
            ceo_approved=args.approve,
            workspace_root=ws_root,
        )
    if args.run is not None:
        return run_production_workflow(
            root,
            args.run,
            workspace_root=ws_root,
            log_path=args.log_path,
            auto_approve=args.approve,
        )
    if args.doctor:
        return run_doctor(root, workspace_root=ws_root)
    if args.demo:
        return run_demo_simulation(root, workspace_root=ws_root)
    if args.agent:
        return launch_agent(
            AGENT_PROFILES[args.agent],
            root,
            workspace_root=ws_root,
            create_branch=args.create_branch,
            dry_run=args.dry_run,
            print_launch=args.print_launch,
        )
    if os.getenv("AUTO_LAUNCH", "false").lower() == "true":
        default_agent = os.getenv("DEFAULT_AGENT", "opencode").lower()
        if default_agent in AGENT_PROFILES:
            return launch_agent(
                AGENT_PROFILES[default_agent],
                root,
                workspace_root=ws_root,
                create_branch=args.create_branch,
                dry_run=args.dry_run,
            )

    mapping = {"1": "opencode", "2": "claude", "3": "qwen", "4": "agy"}
    while True:
        choice = show_menu()
        if choice == "q":
            return 0
        if choice in mapping:
            return launch_agent(
                AGENT_PROFILES[mapping[choice]],
                root,
                workspace_root=ws_root,
                create_branch=args.create_branch,
                dry_run=args.dry_run,
            )
        if choice == "5":
            return run_demo_simulation(root, workspace_root=ws_root)
        print("[!] မမှန်ကန်သော ရွေးချယ်မှု။ 1 မှ 5 သို့မဟုတ် q ကို ရွေးပါ။")


if __name__ == "__main__":
    sys.exit(main())
