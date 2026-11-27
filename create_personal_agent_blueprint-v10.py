#!/usr/bin/env python3
"""
Personal AI Workforce — Hardened Production-Grade Blueprint Generator (v10 — Pattern B+ Native CLI Assets)
==========================================================================
v7 Fixes (Audit-Driven):
1. `llm/client.py`: Anthropic Messages API (`x-api-key` + `anthropic-version`),
   Gemini `x-goog-api-key` header (no `?key=` in URL), `httpx` with stdlib fallback,
   and exponential backoff retry on HTTP 429 / 5xx.
2. `.gitignore`: Protects `.env`, `logs/`, `memory_store/`, `.workforce_runtime.json`, caches.
3. Strict Ruff & Mypy Cleanliness: `agents/protocols.py` (`Protocol` types for Staff),
   zero unused imports, line length <= 100.
4. `ManagerAI.run_workflow_async()`: Full Planner, Short-Term Memory, Tracer & Circuit Breaker;
   stops and escalates to CEO immediately if Researcher fails (never runs Coder on failed research).
5. `tools/docker_python_runner_tool.py`: Adds `--name`, `--cap-drop=ALL`,
   `--tmpfs /tmp:size=16m,noexec,nosuid,nodev`, and runs `docker kill` on timeout.
6. `tools/code_review_tool.py`: Real Python `ast` analyzer catching `__import__`, `getattr`,
   `eval`, `exec`, `compile`, dangerous imports/calls + SQL/shell patterns.
7. `harness/memory/vector_store.py`: `VectorMemoryBackend` Protocol + `InMemoryCosineVectorStore`
   + `PgVectorMemoryStub` (aligned accurately with `AGENTS.md`).
8. `api/dashboard.py`: Adds `/api/costs/summary`, optional `WORKFORCE_DASHBOARD_TOKEN` Bearer auth,
   and `127.0.0.1` localhost binding.
9. Built-in `--self-test` flag verifying file generation, `compileall`, and unit tests.

Usage:
    python3 create_personal_agent_blueprint.py
    python3 create_personal_agent_blueprint.py ./my-ai-workforce --dry-run
    python3 create_personal_agent_blueprint.py ./my-ai-workforce --overwrite
    python3 create_personal_agent_blueprint.py --self-test
"""

from __future__ import annotations

import argparse
import compileall
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GenerationReport:
    created: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def write_file(
    base_dir: Path,
    relative_path: str,
    content: str,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
    report: GenerationReport | None = None,
) -> str:
    target = base_dir / relative_path
    exists = target.exists()

    if exists and not overwrite:
        if report is not None:
            report.skipped.append(relative_path)
        return "skipped"

    status = "overwritten" if exists else "created"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        body = content.lstrip("\n")
        target.write_text(body, encoding="utf-8")
        if body.startswith("#!"):
            target.chmod(0o755)

    if report is not None:
        if status == "overwritten":
            report.overwritten.append(relative_path)
        else:
            report.created.append(relative_path)
    return status


def build_files_map() -> dict[str, str]:
    files: dict[str, str] = {}

    # -------------------------------------------------------------------------
    # 1. Root Docs, .gitignore & Packaging
    # -------------------------------------------------------------------------
    files[".gitignore"] = """
# Secrets & Runtime Environment
.env
.env.*
!.env.example
.workforce_runtime.json

# CLI-Injected Runtime Contexts
.qwen_context.md
.agy_context.md
.agent_runtime_context.md

# Runtime Logs & Memory Stores
logs/*.log
logs/action_logs/*.jsonl
logs/decision_logs/*.jsonl
logs/trace_logs/*.jsonl
logs/cost_logs/*.jsonl
memory_store/short_term/*.json
memory_store/long_term/*.json
workspaces/*
!workspaces/.gitkeep

# Python & Tooling Caches
__pycache__/
*.py[cod]
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
"""

    files["README.md"] = """
# Personal AI Workforce Blueprint (v10 — Hardened Production-Grade)

4-Tier AI Workforce (`CEO → Assistant AI → Manager AI → Staff AI`) with:
- **Multi-Agent CLI Launcher** (`main.py` + `launcher.py`) for OpenCode / Claude / Qwen / Agy
- **Dynamic YAML Tiered LLM Client** (`llm/client.py`): Anthropic Messages API, Gemini (`x-goog-api-key` header), Groq, OpenAI, Ollama, `httpx` + retry/backoff (429/5xx)
- **Hardened Docker Sandbox** (`--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec`, `--name` + `docker kill` on timeout)
- **AST Code Review** (`tools/code_review_tool.py`) + Bandit in CI
- **Full Async Quality Gate** (`ManagerAI.run_workflow_async`) with Planner, STM, Tracer & Circuit Breaker
- **VectorMemory Protocol** (`harness/memory/vector_store.py`) + **Localhost/Token-Protected Observability Dashboard** (`api/dashboard.py`)

## Quick Start
```bash
cp .env.example .env
python3 main.py                                  # Interactive CLI Launcher
python3 demo.py                                  # Offline Workflow Demo
python3 -m unittest discover -s tests -v         # Run All Unit Tests
python3 api/dashboard.py                         # Dashboard (127.0.0.1:8080)
```
"""

    agents_context = """
# Project Context & Agent Instructions (Personal AI Workforce v10)

## 1. User Language & Communication Profile (Mandatory)
- **Primary Language:** Burmese (မြန်မာစာ) — ရိုးရှင်းနားလည်လွယ်အောင် ရှင်းပြရမည်။
- **Academic / CS Terms:** Traditional Chinese (`繁體中文`, TOCFL B1) တွဲဖော်ပြရမည် (ဥပမာ — Derivative `導數`, Matrix `矩陣`, Integration `積分`, Algorithm `演算法`, Vector Database `向量資料庫`)။
- **English Level:** Basic — Coding/Tech keyword များကို မြန်မာလို အမြဲတွဲရှင်းပြရမည်။

## 2. Tech Stack & Storage Architecture
- **Languages & Frameworks:** Python 3.11+, FastAPI, Docker, httpx, Bash
- **Memory & RAG:** JSON Long-Term Memory + `InMemoryCosineVectorStore` by default; optional PostgreSQL + `pgvector` interface defined in `harness/memory/vector_store.py` (`VectorMemoryBackend`).
- **CLI Agents Supported:** OpenCode (`opencode`), Claude (`claude`), Qwen (`qwen`), Antigravity (`agy`)
- **PRD Workflow:** `docs/PRDs/active/` & `docs/PRDs/active/phases/` using `skills/create-prd/feature-template.md`
- **Testing:** `python3 -m unittest discover -s tests -v`

## 3. Hard Safety Rules
- **Gatekeeper & Tamper Check:** CEO Approval မပါဘဲ သို့မဟုတ် Approve ပြီးနောက် Directive ပြောင်းသွားပါက Manager AI မလုပ်ဆောင်ရ။
- **Execution Isolation:** Production code execution တွင် `docker_python_runner` (`--network=none --read-only --cap-drop=ALL --pids-limit=64`) ကိုသာ သုံးပါ။
- **Path Containment & Secret Redaction:** File tools များသည် `allowed_root` အတွင်းသာ ဖတ်ရမည်။ Audit log များတွင် Secret များကို Redact လုပ်ရမည်။

## 4. Sub-Agent Model Policy (Mandatory — 分層預算模型)
- **Tier 1 (Assistant AI, Manager AI):** Premium reasoning model (configured in `config/model_tiers.yaml`).
- **Tier 2 (Staff Agents):** Budget high-speed model (configured in `config/model_tiers.yaml`).
"""
    files["AGENTS.md"] = agents_context
    files["CLAUDE.md"] = agents_context

    files["opencode.json"] = """
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": [
    "AGENTS.md",
    "config/language_profile.yaml",
    "config/model_tiers.yaml"
  ]
}
"""

    files[".env.example"] = """
# Copy to `.env` and fill in your real keys. NEVER commit `.env` to Git!

# Agent CLI Launcher
DEFAULT_AGENT=opencode
AUTO_LAUNCH=false

# LLM Provider API Keys
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Execution Security
DOCKER_SANDBOX_IMAGE=python:3.12-slim
DOCKER_SANDBOX_RUNTIME=

# Observability Dashboard Auth (recommended if exposed beyond localhost)
WORKFORCE_DASHBOARD_TOKEN=
"""

    files["requirements.txt"] = """
rich>=13.7.0
PyYAML>=6.0.1
httpx>=0.27.0
fastapi>=0.115.0
uvicorn>=0.30.0
pydantic-settings>=2.2.0
"""

    files["pyproject.toml"] = """
[project]
name = "personal-ai-workforce"
version = "10.0.0"
description = "Hardened 4-Tier Personal AI Workforce with CLI Launcher & Tiered Models"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_unused_ignores = true
"""

    # -------------------------------------------------------------------------
    # 2. Config Files (YAML)
    # -------------------------------------------------------------------------
    files["config/language_profile.yaml"] = """
primary_language: "Burmese (မြန်မာစာ)"
academic_terminology_language: "Traditional Chinese (繁體中文 - TOCFL B1)"
english_level: "Basic"

rules:
  - "အဓိက ရှင်းပြချက်အားလုံးကို မြန်မာစာဖြင့် ရိုးရှင်းနားလည်လွယ်အောင် ရေးသားရမည်။"
  - "ကျောင်းစာနှင့် CS/Math ဝေါဟာရများကို Traditional Chinese (繁體中文) တွဲဖော်ပြရမည်။"
  - "Coding/Tech keyword များကို ခက်ခဲသော English မသုံးဘဲ မြန်မာလို တွဲရှင်းပြရမည်။"
"""

    files["config/model_tiers.yaml"] = """
# config/model_tiers.yaml — Runtime Dynamic Model Tier Configuration
# Verify latest model IDs against official provider docs before production use.
tier_1_orchestrators:
  description: "Assistant AI & Manager AI — Complex reasoning, planning, refinement"
  agents:
    - "assistant_ai"
    - "manager_ai"
  models:
    - provider: "anthropic"
      model: "claude-sonnet-4-5"
      api_key_env: "ANTHROPIC_API_KEY"
      cost_per_1k_input_usd: 0.003
      cost_per_1k_output_usd: 0.015
    - provider: "gemini"
      model: "gemini-2.5-pro"
      api_key_env: "GEMINI_API_KEY"
      cost_per_1k_input_usd: 0.00125
      cost_per_1k_output_usd: 0.01

tier_2_staff_executors:
  description: "Staff Agents — Focused single-purpose tasks, budget-optimized"
  agents:
    - "researcher"
    - "coder"
    - "reviewer"
    - "writer_tutor"
    - "devops"
    - "security_auditor"
  models:
    - provider: "gemini"
      model: "gemini-3.5-flash-lite"
      api_key_env: "GEMINI_API_KEY"
      cost_per_1k_input_usd: 0.0001
      cost_per_1k_output_usd: 0.0004
    - provider: "groq"
      model: "llama-3.3-70b-versatile"
      api_key_env: "GROQ_API_KEY"
      cost_per_1k_input_usd: 0.00059
      cost_per_1k_output_usd: 0.00079
    - provider: "ollama"
      model: "qwen2.5:7b"
      base_url_env: "OLLAMA_BASE_URL"
      cost_per_1k_input_usd: 0.0
      cost_per_1k_output_usd: 0.0
"""

    files["config/hierarchy_config.yaml"] = """
hierarchy:
  tier_1_ceo:
    role: "Visionary, Decision-Maker, Final Approver"
    hitl_modes: ["cli", "web_ui"]
  tier_2_assistant_ai:
    role: "Chief of Staff / Prompt Refiner / Gatekeeper"
    model_tier: 1
    auto_forward_allowed: false
    invalidate_approval_on_mutation: true
  tier_3_manager_ai:
    role: "Orchestrator / Project Manager"
    model_tier: 1
    direct_staff_to_ceo_reporting: false
    require_ceo_approval_for_memory_write: true
    max_concurrent_staff: 4
    circuit_breaker:
      max_retries_per_step: 2
      escalate_to_ceo_on_failure: true
  tier_4_staff_ai:
    role: "Specialized Executors"
    model_tier: 2
    agents: ["researcher", "coder", "reviewer", "writer_tutor", "devops", "security_auditor"]
"""


    files["config/safety_policy.yaml"] = """
# Protected Data Paths Policy (Pattern B — Existing Project Safety)
# Agents MUST NEVER delete, overwrite, or truncate files matching these patterns.
protected_patterns:
  - "data/**"
  - "backups/**"
  - "migrations/**"
  - "*.db"
  - "*.sqlite"
  - "*.sqlite3"
  - "*.sql"
  - ".env"
  - ".env.*"

git_guard:
  warn_on_dirty_tree: true
  warn_on_protected_branches: ["main", "master"]
  recommended_branch_prefix: "ai-workforce/"
"""

    files["config/tool_permissions.yaml"] = """
tool_permissions:
  assistant_ai: ["memory_read"]
  manager_ai: ["memory_read", "memory_write"]
  researcher: ["web_search", "log_reader", "rag_retrieval", "hybrid_rag"]
  coder: ["docker_python_runner"]
  reviewer: ["code_review"]
  writer_tutor: ["memory_read", "memory_write"]
  devops: ["docker_python_runner", "log_reader"]
  security_auditor: ["code_review", "log_reader"]
"""

    # -------------------------------------------------------------------------
    # 3. Launcher (`launcher.py`), `main.py`, & `demo.py`
    # -------------------------------------------------------------------------
    files["launcher.py"] = """
\"\"\"
Multi-Agent CLI Launcher — Pattern B+ Native Asset & Argv/Env Wiring (`launcher.py`)
- Renders native skills, tiered subagents, and enforced deny permissions into
  `workforce_root/workspaces/<slug>/` without polluting `workspace_root` data or code.
- Provides `build_launch_plan()` for `--doctor` diagnostics and `--print-launch`.
\"\"\"

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 — only runs whitelisted CLI commands from AGENT_PROFILES
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.agent_assets import render_claude_assets, render_opencode_assets
from harness.env_loader import load_dotenv_file
from harness.workspace_guard import (
    check_git_preflight,
    load_protected_patterns,
    make_workspace_slug,
    validate_branch_name,
)

BASE_OS_ENV_KEYS = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM",
    "LANG", "LC_ALL", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
})

SAFE_API_ENV_KEYS = frozenset({
    "GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY", "OLLAMA_BASE_URL",
})


@dataclass(frozen=True)
class AgentProfile:
    name: str
    display_name: str
    command: tuple[str, ...]
    install_hint: str
    context_files: tuple[str, ...]
    env_keys: tuple[str, ...]


AGENT_PROFILES: dict[str, AgentProfile] = {
    "opencode": AgentProfile(
        name="opencode",
        display_name="OpenCode CLI",
        command=("opencode",),
        install_hint="npm i -g opencode-ai",
        context_files=("AGENTS.md", "config/language_profile.yaml", "config/model_tiers.yaml"),
        env_keys=("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
    ),
    "claude": AgentProfile(
        name="claude",
        display_name="Claude CLI",
        command=("claude",),
        install_hint="npm i -g @anthropic-ai/claude-code",
        context_files=("CLAUDE.md", "config/language_profile.yaml", "config/model_tiers.yaml"),
        env_keys=("ANTHROPIC_API_KEY",),
    ),
    "qwen": AgentProfile(
        name="qwen",
        display_name="Qwen-CLI",
        command=("qwen",),
        install_hint="npm i -g @qwen-code/qwen-code",
        context_files=("AGENTS.md", "config/language_profile.yaml", "config/model_tiers.yaml"),
        env_keys=("OPENAI_API_KEY", "OLLAMA_BASE_URL", "GEMINI_API_KEY"),
    ),
    "agy": AgentProfile(
        name="agy",
        display_name="Antigravity CLI (agy)",
        command=("agy",),
        install_hint="Install Antigravity CLI (agy) on your Linux Dev PC",
        context_files=("AGENTS.md", "config/language_profile.yaml", "config/model_tiers.yaml"),
        env_keys=("GEMINI_API_KEY", "GROQ_API_KEY"),
    ),
}


def validate_agent_available(profile: AgentProfile) -> bool:
    return shutil.which(profile.command[0]) is not None


def _build_combined_context(
    profile: AgentProfile,
    workforce_root: Path,
    workspace_root: Path,
    present_files: list[str],
    protected: tuple[str, ...],
) -> str:
    sections = [
        f"# Active Runtime Context for {profile.display_name}",
        f"# Target Workspace (Existing Project): {workspace_root}",
        "# ZERO-OVERWRITE & DATA PROTECTION POLICY:",
        "# - NEVER delete, truncate, or overwrite existing data files:",
        "#   " + ", ".join(protected),
        "# - Prefer minimal targeted patches; review diffs with CEO before merging.\\n",
    ]
    for rel in present_files:
        body = (workforce_root / rel).read_text(encoding="utf-8")
        sections.append(f"\\n---\\n## Workforce Rule: `{rel}`\\n\\n{body}")

    if workspace_root != workforce_root:
        for local_doc in ("AGENTS.md", "CLAUDE.md"):
            lp = workspace_root / local_doc
            if lp.is_file():
                local_body = lp.read_text(encoding="utf-8", errors="replace")
                sections.append(
                    f"\\n---\\n## Existing Project Context: `{local_doc}` (Read-Only)\\n\\n"
                    f"{local_body}"
                )
    return "\\n".join(sections)


def prepare_context_injection(
    profile: AgentProfile,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    is_external = ws_root != wf_root

    present_files = [rel for rel in profile.context_files if (wf_root / rel).is_file()]
    missing_files = [rel for rel in profile.context_files if rel not in present_files]
    protected = load_protected_patterns(wf_root / "config" / "safety_policy.yaml")

    if is_external:
        state_dir = wf_root / "workspaces" / make_workspace_slug(ws_root)
        state_dir.mkdir(parents=True, exist_ok=True)
    else:
        state_dir = wf_root

    combined = _build_combined_context(profile, wf_root, ws_root, present_files, protected)
    assets_info: dict[str, Any] = {}

    if profile.name == "claude":
        assets_info = render_claude_assets(wf_root, state_dir, protected)
        target_path = Path(assets_info["config_dir"]) / "CLAUDE.md"
        if is_external:
            target_path.write_text(combined, encoding="utf-8")
    elif profile.name == "opencode":
        ctx_md = state_dir / ".opencode_context.md"
        ctx_md.write_text(combined, encoding="utf-8")
        assets_info = render_opencode_assets(wf_root, state_dir, ctx_md)
        target_path = Path(assets_info["opencode_config"])
    elif profile.name == "qwen":
        target_path = state_dir / ".qwen_context.md"
        target_path.write_text(combined, encoding="utf-8")
    elif profile.name == "agy":
        target_path = state_dir / ".agy_context.md"
        target_path.write_text(combined, encoding="utf-8")
    else:
        target_path = state_dir / ".agent_runtime_context.md"
        target_path.write_text(combined, encoding="utf-8")

    return {
        "agent": profile.name,
        "workforce_root": str(wf_root),
        "workspace_root": str(ws_root),
        "state_dir": str(state_dir),
        "is_external_workspace": is_external,
        "present_files": present_files,
        "missing_files": missing_files,
        "protected_patterns_count": len(protected),
        "injected_context_path": str(target_path),
        "assets": assets_info,
    }


def prepare_filtered_env(
    profile: AgentProfile,
    project_root: Path,
    ctx_info: dict[str, Any],
    *,
    source_env: dict[str, str] | None = None,
) -> dict[str, str]:
    src = dict(os.environ) if source_env is None else source_env
    filtered: dict[str, str] = {}

    for k in BASE_OS_ENV_KEYS:
        if k in src:
            filtered[k] = src[k]

    for k in profile.env_keys:
        if k in SAFE_API_ENV_KEYS and k in src:
            filtered[k] = src[k]

    assets = ctx_info.get("assets", {})
    if profile.name == "claude" and "config_dir" in assets:
        filtered["CLAUDE_CONFIG_DIR"] = str(assets["config_dir"])
    elif profile.name == "opencode":
        if "opencode_config" in assets:
            filtered["OPENCODE_CONFIG"] = str(assets["opencode_config"])
        if "xdg_config_home" in assets:
            filtered["XDG_CONFIG_HOME"] = str(assets["xdg_config_home"])

    state_dir = Path(ctx_info.get("state_dir", str(project_root.resolve())))
    state_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = state_dir / ".workforce_runtime.json"
    metadata = {
        "agent": profile.name,
        "workspace_root": ctx_info.get("workspace_root", str(project_root.resolve())),
        "context_file": ctx_info["injected_context_path"],
        "present_rules": ctx_info["present_files"],
        "assets": assets,
    }
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\\n", encoding="utf-8")
    try:
        os.chmod(metadata_file, 0o600)
    except OSError:
        pass

    filtered["WORKFORCE_METADATA_FILE"] = str(metadata_file)
    return filtered


def build_cli_argv(
    profile: AgentProfile, wf_root: Path, ctx_info: dict[str, Any]
) -> list[str]:
    argv = list(profile.command)
    assets = ctx_info.get("assets", {})
    if profile.name == "claude":
        argv.extend(["--add-dir", str(wf_root)])
        if "settings_path" in assets:
            argv.extend(["--settings", str(assets["settings_path"])])
    elif profile.name == "qwen":
        argv.extend(["--include-directories", str(wf_root)])
    return argv


def build_launch_plan(
    profile: AgentProfile,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    load_dotenv_file(wf_root / ".env")
    ctx_info = prepare_context_injection(profile, wf_root, workspace_root=ws_root)
    env = prepare_filtered_env(profile, wf_root, ctx_info)
    argv = build_cli_argv(profile, wf_root, ctx_info)
    git_status = check_git_preflight(ws_root)
    return {
        "profile": profile.name,
        "cli_installed": validate_agent_available(profile),
        "argv": argv,
        "cwd": str(ws_root),
        "ctx_info": ctx_info,
        "env": env,
        "git_status": git_status,
    }


def run_doctor(
    project_root: Path, *, workspace_root: Path | None = None
) -> int:
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    expected_skills = len(list((wf_root / "skills").glob("*/SKILL.md")))
    print("=== Personal AI Workforce Doctor (Pattern B+) ===")
    print(f"Workforce Root  : {wf_root}")
    print(f"Target Workspace: {ws_root}")
    print(f"Expected Skills : {expected_skills}")
    for name, prof in AGENT_PROFILES.items():
        plan = build_launch_plan(prof, wf_root, workspace_root=ws_root)
        assets = plan["ctx_info"].get("assets", {})
        status = "OK" if plan["cli_installed"] else "NOT INSTALLED"
        s_cnt = assets.get("skills_count", "n/a")
        a_cnt = assets.get("agents_count", "n/a")
        d_cnt = assets.get("deny_rules_count", "n/a")
        print(
            f"  [{name:<8}] CLI={status:<13} | skills={s_cnt}/{expected_skills} "
            f"| subagents={a_cnt} | deny_rules={d_cnt}"
        )
        print(f"             argv: {' '.join(plan['argv'])}")
        print(f"             ctx : {plan['ctx_info']['injected_context_path']}")
    return 0


def launch_agent(
    profile: AgentProfile,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
    create_branch: str | None = None,
    dry_run: bool = False,
    print_launch: bool = False,
) -> int:
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    if not ws_root.exists() or not ws_root.is_dir():
        print(f"[X] Workspace directory မတွေ့ပါ: {ws_root}")
        return 1

    plan = build_launch_plan(profile, wf_root, workspace_root=ws_root)
    git_status = plan["git_status"]

    if create_branch:
        safe_branch = validate_branch_name(create_branch)
        if not (dry_run or print_launch) and git_status.is_git_repo:
            subprocess.run(  # nosec B603, B607 — validated branch name, fixed git argv
                ["git", "checkout", "-b", safe_branch], cwd=ws_root, check=False
            )

    if not (dry_run or print_launch) and not plan["cli_installed"]:
        print(f"[X] '{profile.command[0]}' CLI ကို system ထဲမှာ မတွေ့ပါ။")
        print(f"    Install လုပ်ရန်: {profile.install_hint}")
        return 1

    env = plan["env"]
    ctx_info = plan["ctx_info"]
    configured = [k for k in profile.env_keys if k in env]

    print(f"\\n>>> [{profile.display_name}] (Pattern B+)")
    print(f"    Target Workspace: {ws_root}")
    print(f"    State Dir       : {ctx_info['state_dir']} (Zero Data Pollution)")
    print(f"    Injected File   : {ctx_info['injected_context_path']}")
    print(f"    Command Argv    : {' '.join(plan['argv'])}")
    print(f"    Active API Env  : {len(configured)}/{len(profile.env_keys)} configured")
    for w in git_status.warnings:
        print(f"    [Git Guard] {w}")

    if dry_run or print_launch:
        return 0

    try:
        proc = subprocess.run(plan["argv"], cwd=ws_root, env=env, check=False)  # nosec B603
        return proc.returncode
    except KeyboardInterrupt:
        print("\\n[!] User interrupted. Exiting gracefully.")
        return 130
"""

    files["main.py"] = """
#!/usr/bin/env python3
\"\"\"Personal AI Workforce v10 — Interactive Agent CLI Launcher Entrypoint.\"\"\"

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from demo import run_demo_simulation
from harness.env_loader import load_dotenv_file
from launcher import AGENT_PROFILES, launch_agent, run_doctor, validate_agent_available

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

    print("\\n=== Personal AI Workforce v10 — Agent CLI Launcher ===")
    for key, slug, label, desc in MENU_ROWS:
        if slug in AGENT_PROFILES:
            status = "Installed" if validate_agent_available(AGENT_PROFILES[slug]) else "Not Found"
        else:
            status = "Built-in"
        print(f"  [{key}] {label:<18} ({status:<9}) — {desc}")
    return input("ရွေးချယ်ပါ (1-5/q): ").strip().lower()


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
    args = parser.parse_args(argv)

    root = Path(__file__).parent.resolve()
    load_dotenv_file(root / ".env")
    ws_root = args.workspace.resolve() if args.workspace else None

    if args.doctor:
        return run_doctor(root, workspace_root=ws_root)
    if args.demo:
        return run_demo_simulation(root)
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
            return run_demo_simulation(root)
        print("[!] မမှန်ကန်သော ရွေးချယ်မှု။ 1 မှ 5 သို့မဟုတ် q ကို ရွေးပါ။")


if __name__ == "__main__":
    sys.exit(main())
"""

    files["demo.py"] = """
#!/usr/bin/env python3
\"\"\"Personal AI Workforce v10 — Offline Demo Simulation (`demo_python_runner` isolated).\"\"\"

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
    \"\"\"DEMO/TEST ONLY — NOT isolated. Never use for untrusted code.\"\"\"
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
        "2026-11-27 10:01:02 INFO Checkout started\\n"
        "2026-11-27 10:01:08 ERROR 500 Checkout timeout: Stripe API latency spiked 300%\\n",
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
    print("\\n--- Manager AI Final Report to CEO ---")
    print(result["ceo_summary"])
    print("\\n" + result["plan_markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(run_demo_simulation(Path(__file__).parent.resolve()))
"""

    # -------------------------------------------------------------------------
    # 4. LLM Client (Anthropic Messages + Gemini Header + httpx/Retry + YAML)
    # -------------------------------------------------------------------------
    files["llm/__init__.py"] = '"""Provider-Agnostic LLM Integration Layer (v7)."""\n'

    files["llm/client.py"] = """
\"\"\"
Provider-Agnostic LLM Adapter (`llm/client.py`)
- Supports Anthropic Messages API (`x-api-key`, `anthropic-version: 2023-06-01`),
  Gemini (`x-goog-api-key` header — NEVER `?key=` in URL), OpenAI, Groq, Ollama, Mock.
- Uses `httpx` when installed (graceful `urllib.request` fallback for zero-dep envs).
- Includes exponential backoff retry for HTTP 429 / 5xx rate limits & transient errors.
\"\"\"

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

DEFAULT_TIER_1_AGENTS = {"assistant_ai", "manager_ai"}
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


@dataclass
class LLMResponse:
    provider: str
    model: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class ProviderSpec:
    provider: str
    model: str
    api_key_env: str = ""
    base_url_env: str = ""
    base_url: str = ""
    cost_per_1k_input_usd: float = 0.0
    cost_per_1k_output_usd: float = 0.0


def _parse_scalar(val: str) -> Any:
    v = val.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


def _stdlib_parse_model_tiers_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_tier: str | None = None
    current_section: str | None = None
    current_model: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":"):
            current_tier = stripped[:-1]
            data[current_tier] = {"agents": [], "models": []}
            current_section = None
            current_model = None
        elif current_tier and indent == 2 and ":" in stripped:
            k, v = stripped.split(":", 1)
            k = k.strip()
            if k in {"agents", "models"}:
                current_section = k
                current_model = None
            else:
                data[current_tier][k] = _parse_scalar(v)
                current_section = None
        elif current_tier and current_section == "agents" and stripped.startswith("- "):
            data[current_tier]["agents"].append(_parse_scalar(stripped[2:]))
        elif current_tier and current_section == "models":
            if stripped.startswith("- "):
                current_model = {}
                data[current_tier]["models"].append(current_model)
                rest = stripped[2:].strip()
                if ":" in rest:
                    mk, mv = rest.split(":", 1)
                    current_model[mk.strip()] = _parse_scalar(mv)
            elif current_model is not None and ":" in stripped:
                mk, mv = stripped.split(":", 1)
                current_model[mk.strip()] = _parse_scalar(mv)
    return data


def load_tier_config(config_path: Path = Path("config/model_tiers.yaml")) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Tier config not found: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    if HAS_YAML:
        loaded = yaml.safe_load(text)
        return dict(loaded) if isinstance(loaded, dict) else {}
    return _stdlib_parse_model_tiers_yaml(text)


def _spec_from_dict(m: dict[str, Any]) -> ProviderSpec:
    base_url_env = str(m.get("base_url_env", ""))
    resolved_base_url = os.getenv(base_url_env, "") if base_url_env else str(m.get("base_url", ""))
    return ProviderSpec(
        provider=str(m["provider"]),
        model=str(m["model"]),
        api_key_env=str(m.get("api_key_env", "")),
        base_url_env=base_url_env,
        base_url=resolved_base_url,
        cost_per_1k_input_usd=float(m.get("cost_per_1k_input_usd", 0.0)),
        cost_per_1k_output_usd=float(m.get("cost_per_1k_output_usd", 0.0)),
    )


def _retry_delay(retry_after: str | None, attempt: int, backoff_base: float) -> float:
    if retry_after:
        try:
            return min(30.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return backoff_base * (2**attempt)


def _post_json_with_retry(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    timeout_seconds: int = 30,
    max_retries: int = 2,
    backoff_base: float = 0.5,
) -> dict[str, Any]:
    \"\"\"POST JSON via httpx/urllib with Retry-After support and fail-fast on 4xx.\"\"\"
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                        ra = resp.headers.get("Retry-After")
                        time.sleep(_retry_delay(ra, attempt, backoff_base))
                        continue
                    if 400 <= resp.status_code < 500:
                        raise RuntimeError(f"Non-retryable HTTP {resp.status_code} from {url}")
                    resp.raise_for_status()
                    return dict(resp.json())
            raw = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=raw, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout_seconds) as uresp:  # nosec B310
                return dict(json.loads(uresp.read().decode("utf-8")))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                ra = exc.headers.get("Retry-After") if exc.headers else None
                time.sleep(_retry_delay(ra, attempt, backoff_base))
                continue
            raise RuntimeError(f"HTTP {exc.code} from {url}") from None
        except RuntimeError:
            raise
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(backoff_base * (2**attempt))
                continue
            raise
    raise RuntimeError(f"HTTP request failed after retries: {last_err}")


def _calc_cost(spec: ProviderSpec, in_tok: int, out_tok: int) -> float:
    in_cost = (in_tok / 1000.0) * spec.cost_per_1k_input_usd
    out_cost = (out_tok / 1000.0) * spec.cost_per_1k_output_usd
    return round(in_cost + out_cost, 6)


class LLMClient:
    def __init__(
        self,
        providers: list[ProviderSpec] | None = None,
        *,
        tier1_providers: list[ProviderSpec] | None = None,
        tier2_providers: list[ProviderSpec] | None = None,
        tier1_agents: set[str] | None = None,
        timeout_seconds: int = 30,
        http_post_fn: Callable[..., dict[str, Any]] | None = None,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> None:
        self.providers = providers or [ProviderSpec(provider="mock", model="mock-local")]
        self.tier1_providers = tier1_providers or list(self.providers)
        self.tier2_providers = tier2_providers or list(self.providers)
        self.tier1_agents = set(DEFAULT_TIER_1_AGENTS if tier1_agents is None else tier1_agents)
        self.timeout_seconds = timeout_seconds
        self._http_post = http_post_fn or _post_json_with_retry
        self.custom_handlers = custom_handlers or {}

    @classmethod
    def from_config(
        cls,
        config_path: Path = Path("config/model_tiers.yaml"),
        *,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> LLMClient:
        cfg = load_tier_config(config_path)
        t1 = [_spec_from_dict(m) for m in cfg["tier_1_orchestrators"]["models"]]
        t2 = [_spec_from_dict(m) for m in cfg["tier_2_staff_executors"]["models"]]
        t1_agents = set(cfg["tier_1_orchestrators"]["agents"])
        return cls(
            providers=t1,
            tier1_providers=t1,
            tier2_providers=t2,
            tier1_agents=t1_agents,
            custom_handlers=custom_handlers,
        )

    @classmethod
    def with_tier_specs(
        cls,
        *,
        tier1_providers: list[ProviderSpec],
        tier2_providers: list[ProviderSpec],
        tier1_agents: set[str] | None = None,
        custom_handlers: dict[str, Callable[[ProviderSpec, str, str], LLMResponse]] | None = None,
    ) -> LLMClient:
        return cls(
            providers=tier1_providers,
            tier1_providers=tier1_providers,
            tier2_providers=tier2_providers,
            tier1_agents=tier1_agents,
            custom_handlers=custom_handlers,
        )

    def for_agent(self, agent_name: str) -> LLMClient:
        chosen = self.tier1_providers if agent_name in self.tier1_agents else self.tier2_providers
        return LLMClient(
            providers=list(chosen),
            tier1_providers=list(self.tier1_providers),
            tier2_providers=list(self.tier2_providers),
            tier1_agents=set(self.tier1_agents),
            timeout_seconds=self.timeout_seconds,
            http_post_fn=self._http_post,
            custom_handlers=self.custom_handlers,
        )

    def complete(self, system_prompt: str, user_message: str) -> LLMResponse:
        errors: list[str] = []
        for spec in self.providers:
            try:
                return self._call_provider(spec, system_prompt, user_message)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{spec.provider}({spec.model}): {type(exc).__name__}: {exc}")
        raise RuntimeError("LLM Fallback Chain failed -> " + " | ".join(errors))

    def _call_provider(
        self, spec: ProviderSpec, system_prompt: str, user_message: str
    ) -> LLMResponse:
        if spec.provider in self.custom_handlers:
            return self.custom_handlers[spec.provider](spec, system_prompt, user_message)

        if spec.provider == "mock":
            in_tok = max(1, (len(system_prompt) + len(user_message)) // 4)
            text = f"[Mock:{spec.model}] {user_message[:120]}"
            out_tok = max(1, len(text) // 4)
            return LLMResponse("mock", spec.model, text, in_tok, out_tok, 0.0)

        if spec.provider == "anthropic":
            api_key = os.getenv(spec.api_key_env or "ANTHROPIC_API_KEY", "")
            if not api_key:
                raise OSError("Missing ANTHROPIC_API_KEY")
            data = self._http_post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                payload={
                    "model": spec.model,
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usage", {})
            in_tok = int(usage.get("input_tokens", 0))
            out_tok = int(usage.get("output_tokens", 0))
            text = data["content"][0]["text"]
            return LLMResponse(
                "anthropic", spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider == "gemini":
            api_key = os.getenv(spec.api_key_env or "GEMINI_API_KEY", "")
            if not api_key:
                raise OSError("Missing GEMINI_API_KEY")
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{spec.model}:generateContent"
            )
            data = self._http_post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                payload={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_message}]}],
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usageMetadata", {})
            in_tok = int(usage.get("promptTokenCount", 0))
            out_tok = int(usage.get("candidatesTokenCount", 0))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return LLMResponse(
                "gemini", spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider in {"openai", "groq"}:
            env_key = spec.api_key_env or (
                "GROQ_API_KEY" if spec.provider == "groq" else "OPENAI_API_KEY"
            )
            api_key = os.getenv(env_key, "")
            if not api_key:
                raise OSError(f"Missing {env_key}")
            url = (
                "https://api.groq.com/openai/v1/chat/completions"
                if spec.provider == "groq"
                else "https://api.openai.com/v1/chat/completions"
            )
            data = self._http_post(
                url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                payload={
                    "model": spec.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                },
                timeout_seconds=self.timeout_seconds,
            )
            usage = data.get("usage", {})
            in_tok = int(usage.get("prompt_tokens", 0))
            out_tok = int(usage.get("completion_tokens", 0))
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(
                spec.provider, spec.model, text, in_tok, out_tok, _calc_cost(spec, in_tok, out_tok)
            )

        if spec.provider == "ollama":
            url_env = spec.base_url_env or "OLLAMA_BASE_URL"
            default_url = os.getenv(url_env, "http://127.0.0.1:11434")
            base = (spec.base_url or default_url).rstrip("/")
            data = self._http_post(
                f"{base}/api/chat",
                headers={"Content-Type": "application/json"},
                payload={
                    "model": spec.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                },
                timeout_seconds=self.timeout_seconds,
            )
            return LLMResponse("ollama", spec.model, data.get("message", {}).get("content", ""))

        raise ValueError(f"Unsupported LLM provider: {spec.provider}")
"""

    # -------------------------------------------------------------------------
    # 5. Harness (Validators, Payload, Circuit Breaker, Planner, Async, HITL, Tracer, Memory + VectorStore, Audit)
    # -------------------------------------------------------------------------
    files["harness/__init__.py"] = '"""Harness System (v7)."""\n'

    files["harness/validators.py"] = """
\"\"\"Shared Security Validators (Session ID & Path Containment).\"\"\"

from __future__ import annotations

import re
from pathlib import Path

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(f"Invalid session_id '{session_id}'.")
    return session_id


def ensure_path_within_root(
    target_path: Path, allowed_root: Path, *, allow_symlinks: bool = False
) -> Path:
    root_resolved = allowed_root.resolve()
    if not allow_symlinks and target_path.is_symlink():
        raise PermissionError(f"Symlink access denied: {target_path}")
    resolved = target_path.resolve(strict=False)
    if not resolved.is_relative_to(root_resolved):
        raise PermissionError(f"Path Traversal Blocked: '{target_path}' outside '{root_resolved}'.")
    return resolved
"""




    files["harness/agent_assets.py"] = """
\"\"\"
CLI-Native Agent & Skill Asset Renderer (`harness/agent_assets.py`) — Pattern B+
- Renders Workforce `skills/*/SKILL.md` + `CLAUDE.md` + Tiered Subagent `.md` files
  into CLI-native discovery layouts inside `state_dir` (Zero Data Pollution).
- Converts `config/safety_policy.yaml` protected patterns into enforced Claude `settings.json`
  `permissions.deny` rules (`Edit(./...)`, `Write(./...)`, and `Read(./.env*)`).
\"\"\"

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm.client import load_tier_config

SUBAGENT_SPECS: tuple[tuple[str, str, int, str, str], ...] = (
    (
        "wf-manager",
        "Orchestrator & Dynamic Planner. Breaks approved directives into gated Staff steps.",
        1,
        "Read, Grep, Glob, Bash",
        "Verify CEO approval, maintain Dynamic Plan, enforce max 2 retries Circuit Breaker.",
    ),
    (
        "wf-researcher",
        "Log analysis & root-cause research. Use when investigating errors or reading docs.",
        2,
        "Read, Grep, Glob",
        "Inspect logs/docs safely and return evidence-backed root-cause findings.",
    ),
    (
        "wf-coder",
        "Minimal code fixes & sandboxed test verification. Never touch protected data paths.",
        2,
        "Read, Edit, Write, Bash",
        "Write minimal targeted patches and run unit tests without mutating protected data.",
    ),
    (
        "wf-reviewer",
        "Security & AST code quality critic. Reviews diffs before completion.",
        2,
        "Read, Grep, Glob",
        "Audit code changes for security risks, path traversal, and quality issues.",
    ),
    (
        "wf-tutor",
        "Bilingual CS & Math tutor (Burmese primary + Traditional Chinese academic terms).",
        2,
        "Read, Grep",
        "Explain concepts simply in Burmese paired with Traditional Chinese (TOCFL B1) terms.",
    ),
)


def _pick_tier_model(wf_root: Path, tier: int) -> str:
    cfg_path = wf_root / "config" / "model_tiers.yaml"
    if not cfg_path.is_file():
        return "claude-sonnet-4-5" if tier == 1 else "gemini-3.5-flash-lite"
    cfg = load_tier_config(cfg_path)
    key = "tier_1_orchestrators" if tier == 1 else "tier_2_staff_executors"
    models = cfg.get(key, {}).get("models", [])
    if models and isinstance(models[0], dict):
        return str(models[0].get("model", "gemini-3.5-flash-lite"))
    return "claude-sonnet-4-5" if tier == 1 else "gemini-3.5-flash-lite"


def build_claude_settings(protected: tuple[str, ...]) -> dict[str, Any]:
    \"\"\"Convert protected data patterns into enforced Claude `permissions.deny` rules.\"\"\"
    deny: list[str] = []
    for pat in protected:
        clean = pat[2:] if pat.startswith("./") else pat.lstrip("/")
        ops = ("Read", "Edit", "Write") if clean.startswith(".env") else ("Edit", "Write")
        for op in ops:
            deny.append(f"{op}(./{clean})")
    return {
        "permissions": {
            "deny": deny,
            "allow": ["Read(./**)"],
        }
    }


def _render_subagent_md(
    name: str, desc: str, model: str, tools: str, guidance: str
) -> str:
    return (
        f"---\\n"
        f"name: {name}\\n"
        f"description: {desc}\\n"
        f"model: {model}\\n"
        f"tools: {tools}\\n"
        f"---\\n"
        f"# {name}\\n\\n"
        f"{guidance}\\n\\n"
        "Language Profile (Mandatory): Primary Burmese (မြန်မာစာ), "
        "pair CS/Math terms with Traditional Chinese (繁體中文, TOCFL B1), "
        "keep English simple.\\n"
    )


def _copy_skills_and_subagents(
    wf_root: Path, skills_dst: Path, agents_dst: Path
) -> tuple[int, int]:
    skills_dst.mkdir(parents=True, exist_ok=True)
    agents_dst.mkdir(parents=True, exist_ok=True)
    skill_count = 0
    for skill_md in sorted((wf_root / "skills").glob("*/SKILL.md")):
        dst_dir = skills_dst / skill_md.parent.name
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "SKILL.md").write_text(
            skill_md.read_text(encoding="utf-8"), encoding="utf-8"
        )
        skill_count += 1
    tpl = wf_root / "skills" / "create-prd" / "feature-template.md"
    if tpl.is_file():
        (skills_dst / "create-prd" / "feature-template.md").write_text(
            tpl.read_text(encoding="utf-8"), encoding="utf-8"
        )

    t1_model = _pick_tier_model(wf_root, 1)
    t2_model = _pick_tier_model(wf_root, 2)
    agent_count = 0
    for name, desc, tier, tools, guidance in SUBAGENT_SPECS:
        model = t1_model if tier == 1 else t2_model
        body = _render_subagent_md(name, desc, model, tools, guidance)
        (agents_dst / f"{name}.md").write_text(body, encoding="utf-8")
        agent_count += 1
    return skill_count, agent_count


def render_claude_assets(
    wf_root: Path, state_dir: Path, protected: tuple[str, ...]
) -> dict[str, Any]:
    home = state_dir / "claude"
    home.mkdir(parents=True, exist_ok=True)
    claude_md = wf_root / "CLAUDE.md"
    if claude_md.is_file():
        (home / "CLAUDE.md").write_text(
            claude_md.read_text(encoding="utf-8"), encoding="utf-8"
        )
    s_cnt, a_cnt = _copy_skills_and_subagents(
        wf_root, home / "skills", home / "agents"
    )
    settings_path = home / "settings.json"
    settings_obj = build_claude_settings(protected)
    settings_path.write_text(json.dumps(settings_obj, indent=2) + "\\n", encoding="utf-8")
    return {
        "config_dir": str(home),
        "settings_path": str(settings_path),
        "skills_count": s_cnt,
        "agents_count": a_cnt,
        "deny_rules_count": len(settings_obj["permissions"]["deny"]),
    }


def render_opencode_assets(
    wf_root: Path, state_dir: Path, context_md_path: Path
) -> dict[str, Any]:
    xdg_home = state_dir / "xdg"
    oc_dir = xdg_home / "opencode"
    s_cnt, a_cnt = _copy_skills_and_subagents(
        wf_root, oc_dir / "skills", oc_dir / "agent"
    )
    oc_cfg = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": [str(context_md_path)],
    }
    cfg_path = state_dir / "opencode.json"
    cfg_path.write_text(json.dumps(oc_cfg, indent=2) + "\\n", encoding="utf-8")
    return {
        "xdg_config_home": str(xdg_home),
        "opencode_config": str(cfg_path),
        "skills_count": s_cnt,
        "agents_count": a_cnt,
    }
"""

    files["harness/workspace_guard.py"] = """
\"\"\"
Workspace Safety Guard (`harness/workspace_guard.py`) — Pattern B Protection
- Dynamically loads `config/safety_policy.yaml` at runtime (PyYAML or stdlib fallback).
- Supports true recursive `**` glob matching via `PurePosixPath.match` + path-part checks.
- Checks Git working tree status & validates branch names strictly.
\"\"\"

from __future__ import annotations

import fnmatch
import re
import subprocess  # nosec B404 — runs fixed, hardcoded git subcommands only
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFAULT_PROTECTED_PATTERNS: tuple[str, ...] = (
    "data/**",
    "backups/**",
    "migrations/**",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.sql",
    ".env",
    ".env.*",
)
PROTECTED_PATTERNS = DEFAULT_PROTECTED_PATTERNS

BRANCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_.-]{0,63}$")
SAFE_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


@dataclass(frozen=True)
class GitGuardStatus:
    is_git_repo: bool
    branch: str
    is_dirty: bool
    changed_files_count: int
    warnings: tuple[str, ...]


def load_protected_patterns(policy_path: Path | None = None) -> tuple[str, ...]:
    \"\"\"Dynamically loads `protected_patterns` from `config/safety_policy.yaml`.\"\"\"
    if policy_path is None or not policy_path.is_file():
        return DEFAULT_PROTECTED_PATTERNS
    raw = policy_path.read_text(encoding="utf-8")
    if HAS_YAML:
        data = yaml.safe_load(raw)
        if isinstance(data, dict) and isinstance(data.get("protected_patterns"), list):
            return tuple(str(p) for p in data["protected_patterns"])
        return DEFAULT_PROTECTED_PATTERNS

    patterns: list[str] = []
    in_section = False
    for line in raw.splitlines():
        clean = line.split("#", 1)[0].rstrip()
        if not clean.strip():
            continue
        if clean.strip() == "protected_patterns:":
            in_section = True
            continue
        if in_section:
            if not clean.startswith(" "):
                break
            stripped = clean.strip()
            if stripped.startswith("- "):
                val = stripped[2:].strip().strip('"').strip("'")
                if val:
                    patterns.append(val)
    return tuple(patterns) if patterns else DEFAULT_PROTECTED_PATTERNS


def make_workspace_slug(workspace_root: Path) -> str:
    raw = workspace_root.resolve().name or "workspace"
    slug = SAFE_SLUG_RE.sub("_", raw).strip("_")
    return (slug or "workspace")[:48]


def validate_branch_name(branch_name: str) -> str:
    if (
        not isinstance(branch_name, str)
        or not BRANCH_NAME_RE.fullmatch(branch_name)
        or ".." in branch_name
        or branch_name.endswith(".lock")
    ):
        raise ValueError(f"Invalid git branch name: '{branch_name}'")
    return branch_name


def _matches_recursive_pattern(rel_posix: str, pattern: str) -> bool:
    rel_path = PurePosixPath(rel_posix)
    parts = rel_path.parts
    if pattern.endswith("/**"):
        prefix = pattern[:-3].strip("/")
        if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
            return True
    if pattern.startswith("**/") and pattern.endswith("/**"):
        mid = pattern[3:-3].strip("/")
        if mid in parts:
            return True
    if rel_path.match(pattern):
        return True
    return fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(parts[-1], pattern)


def is_protected_path(
    target_path: Path,
    workspace_root: Path,
    *,
    policy_path: Path | None = None,
) -> bool:
    root = workspace_root.resolve()
    resolved = target_path.resolve(strict=False)
    try:
        rel = resolved.relative_to(root).as_posix()
    except ValueError:
        return True
    patterns = load_protected_patterns(policy_path)
    return any(_matches_recursive_pattern(rel, pat) for pat in patterns)


def check_git_preflight(workspace_root: Path) -> GitGuardStatus:
    root = workspace_root.resolve()
    warnings: list[str] = []
    probe = subprocess.run(  # nosec B603, B607
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        warnings.append("Workspace is not a Git repository; create a backup before editing.")
        return GitGuardStatus(False, "", False, 0, tuple(warnings))

    branch_proc = subprocess.run(  # nosec B603, B607
        ["git", "branch", "--show-current"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = branch_proc.stdout.strip() or "HEAD"
    if branch in {"main", "master"}:
        warnings.append(
            f"Currently on '{branch}'. Consider `--create-branch ai-workforce/<task>`."
        )

    status_proc = subprocess.run(  # nosec B603, B607
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = [ln for ln in status_proc.stdout.splitlines() if ln.strip()]
    if changed:
        warnings.append(
            f"Working tree has {len(changed)} uncommitted change(s). Commit or stash first."
        )

    return GitGuardStatus(True, branch, bool(changed), len(changed), tuple(warnings))
"""

    files["harness/env_loader.py"] = """
\"\"\"Zero-dependency `.env` file loader (does not overwrite existing OS env vars).\"\"\"

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(env_path: Path, *, override: bool = False) -> int:
    if not env_path.exists() or not env_path.is_file():
        return 0
    loaded = 0
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        if key and (override or key not in os.environ):
            os.environ[key] = val
            loaded += 1
    return loaded
"""

    files["harness/context_payload.py"] = """
\"\"\"Structured Context Payload (Tamper-Evident SHA-256 CEO Approval).\"\"\"

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from harness.validators import validate_session_id


@dataclass
class StructuredContextPayload:
    original_ceo_intent: str
    approved_directive: str
    constraints: list[str] = field(default_factory=list)
    context_notes: dict[str, Any] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    ceo_approved: bool = False
    approved_at: str | None = None
    approval_digest: str | None = None
    approval_source: str = "unapproved"

    def __post_init__(self) -> None:
        validate_session_id(self.session_id)

    def _compute_digest(self) -> str:
        canonical = json.dumps(
            {
                "original_ceo_intent": self.original_ceo_intent,
                "approved_directive": self.approved_directive,
                "constraints": list(self.constraints),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def approve(
        self,
        extra_constraints: list[str] | None = None,
        *,
        approval_source: str = "explicit_ceo",
    ) -> None:
        if extra_constraints:
            self.constraints.extend(extra_constraints)
        self.ceo_approved = True
        self.approved_at = datetime.now(timezone.utc).isoformat()
        self.approval_source = approval_source
        self.approval_digest = self._compute_digest()

    def revoke_approval(self) -> None:
        self.ceo_approved = False
        self.approved_at = None
        self.approval_digest = None
        self.approval_source = "revoked"

    def validate_for_handoff(self) -> None:
        validate_session_id(self.session_id)
        if not self.ceo_approved or not self.approval_digest:
            raise PermissionError("Gatekeeper Block: CEO approval required.")
        if self._compute_digest() != self.approval_digest:
            self.revoke_approval()
            raise PermissionError("Approval Invalidated: payload modified after CEO approval.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
"""

    files["harness/circuit_breaker.py"] = """
\"\"\"Manager Circuit Breaker (Quality Gate — Max 2 Retries + Exception Safety).\"\"\"

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    passed: bool
    feedback: str = ""


@dataclass
class CircuitBreakerOutcome:
    success: bool
    attempts: int
    result: Any = None
    escalated_to_ceo: bool = False
    escalation_reason: str = ""


class ManagerCircuitBreaker:
    def __init__(self, max_retries: int = 2) -> None:
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative int.")
        self.max_retries = max_retries

    def execute_with_gate(
        self,
        task_fn: Callable[[str | None], Any],
        validator_fn: Callable[[Any], ValidationResult],
    ) -> CircuitBreakerOutcome:
        feedback: str | None = None
        total_attempts = 1 + self.max_retries
        for attempt in range(1, total_attempts + 1):
            try:
                output = task_fn(feedback)
                check = validator_fn(output)
            except Exception as exc:  # noqa: BLE001
                feedback = f"Unhandled exception ({type(exc).__name__}): {exc}"
                continue
            if check.passed:
                return CircuitBreakerOutcome(True, attempt, output, False)
            feedback = check.feedback
        reason = f"Quality Gate failed after {total_attempts} attempts: {feedback}"
        return CircuitBreakerOutcome(False, total_attempts, None, True, reason)
"""

    files["harness/planner.py"] = """
\"\"\"Dynamic Planner (Manager AI Living Todo List).\"\"\"

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    step_id: str
    assigned_agent: str
    description: str
    status: str = "pending"
    output: Any = None
    notes: str = ""


@dataclass
class DynamicPlanner:
    session_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(self, step_id: str, assigned_agent: str, description: str) -> PlanStep:
        step = PlanStep(step_id, assigned_agent, description)
        self.steps.append(step)
        return step

    def mark_status(
        self, step_id: str, status: str, output: Any = None, notes: str = ""
    ) -> None:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = status
                if output is not None:
                    step.output = output
                if notes:
                    step.notes = notes
                return
        raise KeyError(f"Unknown step_id: {step_id}")

    def render_markdown(self) -> str:
        icons = {"pending": "[ ]", "in_progress": "[/]", "completed": "[x]", "failed": "[!]"}
        lines = [f"# Dynamic Plan ({self.session_id})", f"**Goal:** {self.goal}", ""]
        for s in self.steps:
            icon = icons.get(s.status, "[ ]")
            lines.append(f"- {icon} **Step {s.step_id}** (`{s.assigned_agent}`): {s.description}")
        return "\\n".join(lines)
"""

    files["harness/async_executor.py"] = """
\"\"\"Async Parallel Staff Executor (`asyncio.gather` + `Semaphore`).\"\"\"

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class AsyncStaffExecutor:
    def __init__(self, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.max_concurrency = max_concurrency

    async def run_parallel(
        self, tasks: list[tuple[str, Callable[[], Awaitable[Any]]]]
    ) -> dict[str, Any]:
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _guarded(
            name: str, factory: Callable[[], Awaitable[Any]]
        ) -> tuple[str, Any]:
            async with sem:
                return name, await factory()

        return dict(await asyncio.gather(*(_guarded(n, f) for n, f in tasks)))
"""

    files["harness/hitl/__init__.py"] = '"""Human-in-the-Loop Interactive CLI Approval Adapter."""\n'
    files["harness/hitl/approval_adapter.py"] = """
\"\"\"HITL Approval Adapter (Interactive CLI Only).\"\"\"

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from harness.context_payload import StructuredContextPayload


@dataclass
class ApprovalOutcome:
    approved: bool
    source: str
    extra_constraints: list[str]
    status: str


def request_cli_approval(
    payload: StructuredContextPayload, *, input_fn: Callable[[str], str] = input
) -> ApprovalOutcome:
    print("\\n=== [HITL CEO APPROVAL REQUIRED] ===")
    print(f"Intent     : {payload.original_ceo_intent}")
    print(f"Directive  : {payload.approved_directive}")
    print(f"Constraints: {payload.constraints}")
    prompt = "Approve? [y=Approve / n=Reject / e=Add Constraint & Approve]: "
    decision = input_fn(prompt).strip().lower()
    if decision == "y":
        return ApprovalOutcome(True, "interactive_cli", [], "APPROVED")
    if decision == "e":
        extra = input_fn("Extra constraint: ").strip()
        return ApprovalOutcome(True, "interactive_cli", [extra] if extra else [], "APPROVED")
    return ApprovalOutcome(False, "interactive_cli", [], "REJECTED")
"""

    files["harness/observability/__init__.py"] = '"""Observability Tracer & Cost Tracker."""\n'
    files["harness/observability/tracer.py"] = """
\"\"\"Observability Tracer (`trace_id`) & Token Cost Tracker (`logs/cost_logs/`).\"\"\"

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id


class ObservabilityTracer:
    def __init__(self, logs_root: Path) -> None:
        self.trace_dir = logs_root / "trace_logs"
        self.cost_dir = logs_root / "cost_logs"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.cost_dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, directory: Path, file_key: str, entry: dict[str, Any]) -> None:
        safe_key = validate_session_id(file_key)
        target = ensure_path_within_root(directory / f"{safe_key}.jsonl", directory)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\\n")
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass

    @contextmanager
    def span(
        self, trace_id: str, session_id: str, agent: str, operation: str
    ) -> Iterator[dict[str, Any]]:
        start = time.perf_counter()
        meta: dict[str, Any] = {"status": "OK"}
        try:
            yield meta
        except Exception as exc:
            meta["status"] = "ERROR"
            meta["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._append_jsonl(
                self.trace_dir,
                session_id,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "agent": agent,
                    "operation": operation,
                    "duration_ms": round((time.perf_counter() - start) * 1000.0, 2),
                    **meta,
                },
            )

    def record_token_cost(
        self,
        *,
        trace_id: str,
        session_id: str,
        agent: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "session_id": session_id,
            "agent": agent,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }
        self._append_jsonl(self.cost_dir, session_id, entry)
        return entry
"""

    files["harness/memory/__init__.py"] = '"""Dual Memory System + Optional VectorMemory Interface."""\n'

    files["harness/memory/short_term.py"] = """
\"\"\"Short-Term Memory (Working Memory) with Session ID & Path Containment.\"\"\"

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id


class ShortTermMemory:
    def __init__(self, session_id: str, storage_dir: Path | None = None) -> None:
        self.session_id = validate_session_id(session_id)
        self.state: dict[str, Any] = {"session_id": self.session_id, "steps": {}}
        self.storage_dir = storage_dir

    def set_step_output(self, step_id: str, data: Any) -> None:
        self.state["steps"][step_id] = data
        if self.storage_dir is not None:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            out = ensure_path_within_root(
                self.storage_dir / f"{self.session_id}.json", self.storage_dir
            )
            out.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_all(self) -> dict[str, Any]:
        return dict(self.state)
"""

    files["harness/memory/long_term.py"] = """
\"\"\"Long-Term Memory (Runtime Auto-Seeded JSON Store).\"\"\"

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    "primary_language": "Burmese (မြန်မာစာ)",
    "academic_language": "Traditional Chinese (繁體中文, TOCFL B1)",
    "english_level": "Basic (explain tech keywords in Burmese)",
    "preferred_stack": ["Python", "FastAPI", "Docker", "PostgreSQL"],
}


class LongTermMemory:
    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save_raw({"preferences": dict(DEFAULT_USER_PREFERENCES), "episodes": []})

    def _load_raw(self) -> dict[str, Any]:
        return dict(json.loads(self.store_path.read_text(encoding="utf-8")))

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_preferences(self) -> dict[str, Any]:
        return dict(self._load_raw().get("preferences", {}))

    def add_episode(self, topic: str, summary: str, tags: list[str] | None = None) -> None:
        data = self._load_raw()
        data.setdefault("episodes", []).append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "topic": topic,
                "summary": summary,
                "tags": tags or [],
            }
        )
        self._save_raw(data)

    def search_episodes(self, keyword: str) -> list[dict[str, Any]]:
        kw = keyword.lower()
        return [
            ep
            for ep in self._load_raw().get("episodes", [])
            if kw in ep.get("topic", "").lower()
            or kw in ep.get("summary", "").lower()
            or any(kw in t.lower() for t in ep.get("tags", []))
        ]
"""

    files["harness/memory/vector_store.py"] = """
\"\"\"
Optional VectorMemory Interface (`harness/memory/vector_store.py`)
- Default: `InMemoryCosineVectorStore` (zero external dependencies).
- Production option: implement `VectorMemoryBackend` with PostgreSQL + `pgvector` or ChromaDB.
\"\"\"

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Protocol

TOKEN_RE = re.compile(r"[\\w\\u1000-\\u109F\\u4e00-\\u9fff]+", re.UNICODE)


class VectorMemoryBackend(Protocol):
    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...
    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]: ...


class InMemoryCosineVectorStore:
    \"\"\"Stdlib TF-cosine vector store for local semantic memory retrieval.\"\"\"

    def __init__(self) -> None:
        self._docs: dict[str, tuple[str, Counter[str], dict[str, Any]]] = {}

    @staticmethod
    def _vec(text: str) -> Counter[str]:
        return Counter(t.lower() for t in TOKEN_RE.findall(text))

    @staticmethod
    def _cos(a: Counter[str], b: Counter[str]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a[k] * b[k] for k in (set(a) & set(b)))
        ma = math.sqrt(sum(v * v for v in a.values()))
        mb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (ma * mb) if ma and mb else 0.0

    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._docs[doc_id] = (text, self._vec(text), dict(metadata or {}))

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        qv = self._vec(query_text)
        scored: list[dict[str, Any]] = []
        for doc_id, (text, dv, meta) in self._docs.items():
            score = round(self._cos(qv, dv), 4)
            if score > 0:
                scored.append({"id": doc_id, "score": score, "text": text, "metadata": meta})
        scored.sort(key=lambda x: float(x["score"]), reverse=True)
        return scored[:top_k]
"""

    files["harness/memory/consolidation.py"] = """
\"\"\"Memory Consolidation (Short-Term -> Long-Term with CEO Approval Gate).\"\"\"

from __future__ import annotations

from typing import Any

from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory


def consolidate_session_to_long_term(
    stm: ShortTermMemory, ltm: LongTermMemory, *, topic: str, ceo_approved: bool = False
) -> dict[str, Any]:
    if not ceo_approved:
        raise PermissionError("Memory Consolidation Blocked: CEO approval required.")
    steps = sorted(stm.get_all().get("steps", {}).keys())
    ltm.add_episode(
        topic=topic,
        summary=f"Consolidated {stm.session_id}: {len(steps)} steps",
        tags=["consolidated"],
    )
    return {"consolidated": True, "session_id": stm.session_id, "steps_count": len(steps)}
"""

    files["harness/memory/auto_consolidation.py"] = """
\"\"\"Auto-Consolidation Background Worker (CEO-approved sessions only).\"\"\"

from __future__ import annotations

import threading

from harness.memory.consolidation import consolidate_session_to_long_term
from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory


class AutoConsolidator:
    def __init__(self, ltm: LongTermMemory, interval_seconds: float = 3600.0) -> None:
        self.ltm = ltm
        self.interval_seconds = interval_seconds
        self._queue: dict[str, tuple[ShortTermMemory, str, bool]] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def enqueue_session(self, stm: ShortTermMemory, *, topic: str, ceo_approved: bool) -> None:
        if not ceo_approved:
            raise PermissionError("AutoConsolidator only accepts CEO-approved sessions.")
        with self._lock:
            self._queue[stm.session_id] = (stm, topic, True)

    def run_once(self) -> int:
        with self._lock:
            snapshot = dict(self._queue)
            self._queue.clear()
        count = 0
        for stm, topic, approved in snapshot.values():
            consolidate_session_to_long_term(stm, self.ltm, topic=topic, ceo_approved=approved)
            count += 1
        return count

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.wait(self.interval_seconds):
                self.run_once()

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
"""

    files["harness/persistence/__init__.py"] = '"""Persistence Layer — Redacted Audit Logs."""\n'
    files["harness/persistence/audit_logger.py"] = """
\"\"\"Persistence & Audit Logger (Recursive Secret Redaction + Session ID Validation + 0600).\"\"\"

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id

SENSITIVE_KEY_TOKENS = (
    "token", "password", "passwd", "secret", "api_key",
    "apikey", "authorization", "cookie", "credential", "private_key",
)
SECRET_VALUE_REGEX = re.compile(
    r"(Bearer\\s+[A-Za-z0-9._-]+|sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,})",
    re.IGNORECASE,
)


def redact_sensitive_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: (
                "***REDACTED***"
                if any(t in str(k).lower() for t in SENSITIVE_KEY_TOKENS)
                else redact_sensitive_data(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_sensitive_data(i) for i in obj]
    if isinstance(obj, str):
        return SECRET_VALUE_REGEX.sub("***REDACTED***", obj)
    return obj


class AuditLogger:
    def __init__(self, logs_root: Path) -> None:
        self.action_dir = logs_root / "action_logs"
        self.decision_dir = logs_root / "decision_logs"
        self.action_dir.mkdir(parents=True, exist_ok=True)
        self.decision_dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, directory: Path, session_id: str, entry: dict[str, Any]) -> None:
        safe_id = validate_session_id(session_id)
        log_file = ensure_path_within_root(directory / f"{safe_id}.jsonl", directory)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\\n")
        try:
            os.chmod(log_file, 0o600)
        except OSError:
            pass

    def log_action(
        self, session_id: str, agent_name: str, tool_name: str, status: str, details: Any
    ) -> dict[str, Any]:
        safe_id = validate_session_id(session_id)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": safe_id,
            "agent": agent_name,
            "tool": tool_name,
            "status": status,
            "details": redact_sensitive_data(details),
        }
        self._append_jsonl(self.action_dir, safe_id, entry)
        return entry

    def log_decision(
        self, session_id: str, actor: str, decision: str, notes: str = ""
    ) -> dict[str, Any]:
        safe_id = validate_session_id(session_id)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": safe_id,
            "actor": actor,
            "decision": decision,
            "notes": redact_sensitive_data(notes),
        }
        self._append_jsonl(self.decision_dir, safe_id, entry)
        return entry
"""

    # -------------------------------------------------------------------------
    # 6. Observability Dashboard (Cost Summary + Token Auth + 127.0.0.1 Bind)
    # -------------------------------------------------------------------------
    files["api/__init__.py"] = '"""Observability Web Dashboard API."""\n'
    files["api/dashboard.py"] = """
\"\"\"
Observability Web Dashboard (`api/dashboard.py`)
- Binds strictly to `127.0.0.1` by default.
- Supports optional `WORKFORCE_DASHBOARD_TOKEN` Bearer auth header.
- Exposes `/api/traces`, `/api/costs`, and `/api/costs/summary`.
\"\"\"

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.validators import ensure_path_within_root, validate_session_id

LOGS_ROOT = PROJECT_ROOT / "logs"


def read_jsonl_for_session(
    subdir: str, session_id: str, logs_root: Path = LOGS_ROOT
) -> list[dict[str, Any]]:
    safe_id = validate_session_id(session_id)
    base = logs_root / subdir
    if not base.exists():
        return []
    target = ensure_path_within_root(base / f"{safe_id}.jsonl", base)
    if not target.exists():
        return []
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_session_costs(
    session_id: str, logs_root: Path = LOGS_ROOT
) -> dict[str, Any]:
    rows = read_jsonl_for_session("cost_logs", session_id, logs_root=logs_root)
    in_tok = sum(int(r.get("input_tokens", 0)) for r in rows)
    out_tok = sum(int(r.get("output_tokens", 0)) for r in rows)
    total_usd = round(sum(float(r.get("estimated_cost_usd", 0.0)) for r in rows), 6)
    return {
        "session_id": session_id,
        "call_count": len(rows),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "total_cost_usd": total_usd,
    }


def verify_dashboard_token(auth_header: str | None) -> bool:
    expected = os.getenv("WORKFORCE_DASHBOARD_TOKEN", "").strip()
    if not expected:
        return True
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    provided = auth_header.removeprefix("Bearer ").strip()
    return hmac.compare_digest(provided, expected)


app: Any = None
try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="Personal AI Workforce Observability Dashboard")

    def _require_auth(authorization: str | None) -> None:
        if not verify_dashboard_token(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(authorization: str | None = Header(default=None)) -> str:
        _require_auth(authorization)
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>AI Workforce Dashboard</title></head>"
            "<body style='font-family:sans-serif;max-width:900px;margin:2rem auto;'>"
            "<h1>Personal AI Workforce — Observability Dashboard</h1>"
            "<p>Endpoints: <code>/api/traces</code>, <code>/api/costs</code>, "
            "<code>/api/costs/summary</code></p></body></html>"
        )

    @app.get("/api/traces")
    async def get_traces(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            traces = read_jsonl_for_session("trace_logs", session_id)
            return {"session_id": session_id, "traces": traces}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs")
    async def get_costs(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            costs = read_jsonl_for_session("cost_logs", session_id)
            return {"session_id": session_id, "costs": costs}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs/summary")
    async def get_cost_summary(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            return summarize_session_costs(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
"""

    # -------------------------------------------------------------------------
    # 7. Production Tools (Hardened Docker + AST Code Review + Scoped RAG/Log)
    # -------------------------------------------------------------------------
    files["tools/__init__.py"] = '"""Strict Production Toolbelt."""\n'

    files["tools/registry.py"] = """
\"\"\"Tool Registry & Permission Enforcer (`permissions={}` = Deny All).\"\"\"

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness.persistence.audit_logger import AuditLogger, redact_sensitive_data

DEFAULT_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "assistant_ai": {"memory_read"},
    "manager_ai": {"memory_read", "memory_write"},
    "researcher": {"web_search", "log_reader", "rag_retrieval", "hybrid_rag"},
    "coder": {"docker_python_runner"},
    "reviewer": {"code_review"},
    "writer_tutor": {"memory_read", "memory_write"},
    "devops": {"docker_python_runner", "log_reader"},
    "security_auditor": {"code_review", "log_reader"},
}


class ToolRegistry:
    def __init__(
        self,
        audit_logger: AuditLogger,
        permissions: dict[str, set[str]] | None = None,
    ) -> None:
        self.audit_logger = audit_logger
        src = DEFAULT_TOOL_PERMISSIONS if permissions is None else permissions
        self.permissions = {k: set(v) for k, v in src.items()}
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, tool_name: str, fn: Callable[..., Any]) -> None:
        self._tools[tool_name] = fn

    def invoke(self, session_id: str, agent_name: str, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self.permissions.get(agent_name, set()):
            self.audit_logger.log_action(
                session_id, agent_name, tool_name, "DENIED", {"reason": "Toolbelt violation"}
            )
            raise PermissionError(
                f"Toolbelt Violation: Agent '{agent_name}' cannot use '{tool_name}'."
            )
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered.")

        safe_args = redact_sensitive_data({
            k: (f"<str len={len(v)}>" if isinstance(v, str) and len(v) > 80 else v)
            for k, v in kwargs.items()
        })
        try:
            res = self._tools[tool_name](**kwargs)
            self.audit_logger.log_action(
                session_id,
                agent_name,
                tool_name,
                "SUCCESS",
                {"args": safe_args, "result_type": type(res).__name__},
            )
            return res
        except Exception as exc:
            self.audit_logger.log_action(
                session_id,
                agent_name,
                tool_name,
                "FAIL",
                {"args": safe_args, "error": f"{type(exc).__name__}: {exc}"},
            )
            raise
"""

    files["tools/docker_python_runner_tool.py"] = """
\"\"\"
Hardened Docker Sandbox Runner (`tools/docker_python_runner_tool.py`)
- Adds `--name`, `--cap-drop=ALL`, `--tmpfs /tmp:size=16m,noexec,nosuid,nodev`.
- On timeout, explicitly runs `docker kill <container_name>` so no orphan container survives.
\"\"\"

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 — runs fixed docker CLI argv only
import uuid
from typing import Any

ALLOWED_DOCKER_CAPS = frozenset({"NET_BIND_SERVICE"})


def build_docker_sandbox_cmd(
    python_code: str,
    *,
    container_name: str | None = None,
    image: str = "python:3.12-slim",
    memory: str = "128m",
    cpus: str = "0.5",
    pids_limit: int = 64,
    runtime: str | None = None,
    cap_add: tuple[str, ...] = (),
) -> tuple[str, list[str]]:
    cname = container_name or f"wf_sbx_{uuid.uuid4().hex[:10]}"
    cmd = [
        "docker", "run", "--rm",
        "--name", cname,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--tmpfs", "/tmp:size=16m,noexec,nosuid,nodev",  # nosec B108 — container-internal tmpfs
        f"--memory={memory}",
        f"--cpus={cpus}",
        f"--pids-limit={pids_limit}",
        "--security-opt=no-new-privileges",
        "--user", "65534:65534",
    ]
    for cap in cap_add:
        if cap not in ALLOWED_DOCKER_CAPS:
            raise ValueError(f"Disallowed Docker capability: {cap}")
        cmd.extend(["--cap-add", cap])
    chosen = runtime or os.getenv("DOCKER_SANDBOX_RUNTIME", "").strip()
    if chosen:
        cmd.append(f"--runtime={chosen}")
    cmd.extend([image, "python", "-c", python_code])
    return cname, cmd


def docker_python_runner(
    python_code: str,
    timeout_seconds: int = 10,
    image: str = "python:3.12-slim",
    runtime: str | None = None,
) -> dict[str, Any]:
    if timeout_seconds < 1 or timeout_seconds > 60:
        raise ValueError("timeout_seconds must be between 1 and 60.")
    if shutil.which("docker") is None:
        return {
            "isolated": True,
            "available": False,
            "passed": False,
            "stderr": "Docker CLI not found.",
        }

    cname, cmd = build_docker_sandbox_cmd(python_code, image=image, runtime=runtime)
    try:
        proc = subprocess.run(  # nosec B603 — argv built internally, no shell
            cmd, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
        return {
            "isolated": True,
            "available": True,
            "container_name": cname,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "passed": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        # Actively kill the container so it does not keep running after CLI timeout
        subprocess.run(["docker", "kill", cname], capture_output=True, text=True, check=False)  # nosec B603, B607
        subprocess.run(["docker", "rm", "-f", cname], capture_output=True, text=True, check=False)  # nosec B603, B607
        return {
            "isolated": True,
            "available": True,
            "container_name": cname,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Docker Timeout ({timeout_seconds}s) — container killed",
            "passed": False,
        }
"""

    files["tools/code_review_tool.py"] = """
\"\"\"
AST-Based Static Code Reviewer (`tools/code_review_tool.py`)
- Uses Python `ast` to detect dangerous calls (`eval`, `exec`, `compile`, `__import__`, `getattr`),
  dangerous imports (`os`, `subprocess`, `shutil`, `socket`, `ctypes`, `pickle`, `importlib`),
  and case-insensitive SQL/shell patterns (`DROP TABLE`, `rm -rf`).
- Pair with `bandit` in CI for full SAST coverage.
\"\"\"

from __future__ import annotations

import ast
from typing import Any

DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "getattr", "setattr", "delattr"}
DANGEROUS_MODULES = {"os", "subprocess", "shutil", "socket", "ctypes", "pickle", "importlib"}
DANGEROUS_DUNDERS = {
    "__subclasses__", "__bases__", "__globals__",
    "__builtins__", "__class__", "__mro__", "__code__",
}
DANGEROUS_TEXT_PATTERNS = [
    ("drop table", "Database Safety: DROP TABLE detected."),
    ("rm -rf", "System Safety: destructive rm -rf detected."),
]


def _is_open_write_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Attribute) and node.func.attr in {"write_text", "write_bytes"}:
        return True
    is_open = (isinstance(node.func, ast.Name) and node.func.id == "open") or (
        isinstance(node.func, ast.Attribute) and node.func.attr == "open"
    )
    if not is_open:
        return False
    mode_arg: ast.expr | None = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "mode":
            mode_arg = kw.value
    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        return any(ch in mode_arg.value for ch in ("w", "a", "x", "+"))
    return False


def code_review(code_text: str) -> dict[str, Any]:
    issues: list[str] = []
    lowered = code_text.lower()
    for pat, msg in DANGEROUS_TEXT_PATTERNS:
        if pat in lowered:
            issues.append(msg)

    try:
        tree = ast.parse(code_text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in DANGEROUS_MODULES:
                        issues.append(f"AST Check: dangerous import '{alias.name}'.")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in DANGEROUS_MODULES:
                    issues.append(f"AST Check: dangerous from-import '{node.module}'.")
            elif isinstance(node, ast.Attribute) and node.attr in DANGEROUS_DUNDERS:
                issues.append(f"AST Check: dangerous dunder attribute '.{node.attr}'.")
            elif isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                    issues.append("AST Check: subscripting '__builtins__' is blocked.")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
                    issues.append(f"AST Check: dangerous call '{node.func.id}()'.")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in DANGEROUS_CALLS:
                    issues.append(f"AST Check: dangerous attribute call '.{node.func.attr}()'.")
                elif _is_open_write_call(node):
                    issues.append("AST Check: file write via open() is blocked.")
    except SyntaxError as exc:
        issues.append(f"AST SyntaxError: {exc.msg}")

    return {
        "review_type": "ast_static_and_pattern_check",
        "approved": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }
"""

    files["tools/hybrid_rag_tool.py"] = """
\"\"\"Researcher Tool: Path-Contained Hybrid RAG (Keyword + Cosine Similarity).\"\"\"

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root

TOKEN_RE = re.compile(r"[\\w\\u1000-\\u109F\\u4e00-\\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> Counter[str]:
    return Counter(tok.lower() for tok in TOKEN_RE.findall(text))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in (set(a) & set(b)))
    ma = math.sqrt(sum(v * v for v in a.values()))
    mb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (ma * mb) if ma and mb else 0.0


def make_hybrid_rag_tool(
    allowed_root: Path, *, max_files: int = 100, max_file_bytes: int = 524_288
) -> Callable[..., dict[str, Any]]:
    root = allowed_root.resolve()

    def hybrid_rag(docs_dir: str, query: str, top_k: int = 5) -> dict[str, Any]:
        raw_dir = Path(docs_dir)
        candidate = raw_dir if raw_dir.is_absolute() else (root / raw_dir)
        safe_dir = ensure_path_within_root(candidate, root)
        if not safe_dir.exists() or not safe_dir.is_dir():
            return {"query": query, "results": [], "error": "Directory not found."}
        q_vec = _tokenize(query)
        q_low = query.lower()
        scored: list[dict[str, Any]] = []
        scanned = 0
        for fp in sorted(safe_dir.rglob("*.md")):
            if scanned >= max_files or fp.is_symlink():
                continue
            try:
                sf = ensure_path_within_root(fp, root)
            except PermissionError:
                continue
            if sf.stat().st_size > max_file_bytes:
                continue
            scanned += 1
            text = sf.read_text(encoding="utf-8", errors="replace")
            sem = _cosine(q_vec, _tokenize(text))
            kw = 0.25 if q_low in text.lower() else 0.0
            total = round(sem + kw, 4)
            if total > 0:
                scored.append({
                    "file": str(sf),
                    "score": total,
                    "semantic_score": round(sem, 4),
                    "keyword_match": kw > 0,
                    "preview": text[:200],
                })
        scored.sort(key=lambda x: float(x["score"]), reverse=True)
        return {
            "query": query,
            "mode": "hybrid_keyword_cosine",
            "scanned_files": scanned,
            "results": scored[:top_k],
        }

    return hybrid_rag
"""

    files["tools/web_search_tool.py"] = """
\"\"\"Researcher Tool: Web Search Placeholder (connect Tavily/Brave/Google Search API).\"\"\"

from __future__ import annotations

from typing import Any


def web_search(query: str, max_results: int = 3) -> dict[str, Any]:
    return {
        "mode": "placeholder_demo",
        "query": query,
        "max_results": max_results,
        "results": [{"title": f"[Placeholder] {query}", "snippet": "Connect real search API."}],
    }
"""

    files["tools/log_reader_tool.py"] = """
\"\"\"Researcher Tool: Path-Contained Log Reader.\"\"\"

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import Any

from harness.validators import ensure_path_within_root


def make_log_reader_tool(
    allowed_root: Path, *, max_file_bytes: int = 1_048_576, max_tail_lines: int = 200
) -> Callable[..., dict[str, Any]]:
    root = allowed_root.resolve()

    def log_reader(log_path: str, keyword: str = "", tail_lines: int = 50) -> dict[str, Any]:
        if tail_lines < 1 or tail_lines > max_tail_lines:
            raise ValueError(f"tail_lines must be 1..{max_tail_lines}")
        raw = Path(log_path)
        safe = ensure_path_within_root(raw if raw.is_absolute() else (root / raw), root)
        if not safe.exists() or not safe.is_file():
            return {"found": False, "matches": []}
        if safe.stat().st_size > max_file_bytes:
            raise ValueError("Log file exceeds max size limit.")
        lines = safe.read_text(encoding="utf-8", errors="replace").splitlines()[-tail_lines:]
        matches = [ln for ln in lines if keyword.lower() in ln.lower()] if keyword else lines
        return {
            "found": True,
            "log_path": str(safe),
            "match_count": len(matches),
            "matches": matches,
        }

    return log_reader
"""

    files["tools/rag_retrieval_tool.py"] = """
\"\"\"Researcher Tool: Path-Contained Markdown Keyword RAG.\"\"\"

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import Any

from harness.validators import ensure_path_within_root


def make_rag_retrieval_tool(
    allowed_root: Path, *, max_files: int = 100, max_file_bytes: int = 524_288
) -> Callable[..., dict[str, Any]]:
    root = allowed_root.resolve()

    def rag_retrieval(docs_dir: str, query: str) -> dict[str, Any]:
        raw = Path(docs_dir)
        safe_dir = ensure_path_within_root(raw if raw.is_absolute() else (root / raw), root)
        if not safe_dir.exists() or not safe_dir.is_dir():
            return {"query": query, "hit_count": 0, "matches": []}
        kw, hits, scanned = query.lower(), [], 0
        for fp in sorted(safe_dir.rglob("*.md")):
            if scanned >= max_files or fp.is_symlink():
                continue
            try:
                sf = ensure_path_within_root(fp, root)
            except PermissionError:
                continue
            if sf.stat().st_size > max_file_bytes:
                continue
            scanned += 1
            text = sf.read_text(encoding="utf-8", errors="replace")
            if kw in text.lower():
                hits.append({"file": str(sf), "preview": text[:200]})
        return {"query": query, "scanned_files": scanned, "hit_count": len(hits), "matches": hits}

    return rag_retrieval
"""

    files["tools/memory_access_tool.py"] = """
\"\"\"Memory Read & CEO-Approved Write Tools.\"\"\"

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness.memory.long_term import LongTermMemory


def make_memory_read_tool(ltm: LongTermMemory) -> Callable[..., dict[str, Any]]:
    def memory_read(keyword: str = "") -> dict[str, Any]:
        return {
            "preferences": ltm.get_preferences(),
            "episodes": ltm.search_episodes(keyword) if keyword else [],
        }

    return memory_read


def make_memory_write_tool(ltm: LongTermMemory) -> Callable[..., dict[str, Any]]:
    def memory_write(
        topic: str, summary: str, tags: list[str] | None = None, *, ceo_approved: bool = False
    ) -> dict[str, Any]:
        if not ceo_approved:
            raise PermissionError("Memory Write Blocked: ceo_approved=True required.")
        ltm.add_episode(topic=topic, summary=summary, tags=tags or [])
        return {"saved": True, "topic": topic}

    return memory_write
"""

    # -------------------------------------------------------------------------
    # 8. Typed Protocols (`agents/protocols.py`) & Agents (Mypy-Clean!)
    # -------------------------------------------------------------------------
    files["agents/__init__.py"] = '"""Personal AI Workforce Agents."""\n'

    files["agents/protocols.py"] = """
\"\"\"Strict Typing Protocols & StaffRoster for Mypy-Clean Agent Orchestration.\"\"\"

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from llm.client import LLMClient


class ResearcherProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def investigate(
        self, session_id: str, log_path: str, keyword: str, feedback: str | None = None
    ) -> dict[str, Any]: ...


class CoderProtocol(Protocol):
    tier: int
    demo_mode: bool
    llm_client: LLMClient | None

    def draft_and_test_fix(
        self, session_id: str, findings: dict[str, Any], feedback: str | None = None
    ) -> dict[str, Any]: ...


class ReviewerProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def review_code(
        self, session_id: str, code_text: str, feedback: str | None = None
    ) -> dict[str, Any]: ...


class DevOpsProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def check_service_logs(
        self, session_id: str, log_path: str, keyword: str = "error"
    ) -> dict[str, Any]: ...


@dataclass
class StaffRoster:
    researcher: ResearcherProtocol
    coder: CoderProtocol
    reviewer: ReviewerProtocol
    writer_tutor: Any = None
    devops: DevOpsProtocol | None = None
    security_auditor: Any = None
"""

    files["agents/base_agent.py"] = """
\"\"\"BaseAgent — Agent-Aware Tiered Model Selection (`tier=1` Premium vs `tier=2` Budget).\"\"\"

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
"""

    files["agents/assistant_ai/__init__.py"] = ""
    files["agents/assistant_ai/system_prompt.md"] = "# Role: Assistant AI (Tier 1 Orchestrator / Gatekeeper)\n"
    files["agents/assistant_ai/agent.py"] = """
\"\"\"Assistant AI (Tier 1 Orchestrator / Gatekeeper).\"\"\"

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
"""

    files["agents/manager_ai/__init__.py"] = ""
    files["agents/manager_ai/system_prompt.md"] = "# Role: Manager AI (Tier 1 Orchestrator / Project Manager)\n"
    files["agents/manager_ai/agent.py"] = """
\"\"\"Manager AI — Both Sequential & Async Paths Enforce Planner, STM, Tracer & Circuit Breaker.\"\"\"

from __future__ import annotations

import asyncio
from pathlib import Path
from collections.abc import Awaitable, Callable
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
    ) -> None:
        super().__init__(
            "manager_ai",
            "Project Manager",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=1,
            llm_client=llm_client,
        )
        self.staff = staff
        self.short_term_dir = short_term_dir
        self.tracer = tracer
        self.circuit_breaker = ManagerCircuitBreaker(max_retries=max_retries)

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

        payload.validate_for_handoff()
        self.use_tool(
            payload.session_id,
            "memory_write",
            topic=payload.original_ceo_intent,
            summary=f"Verified '{payload.original_ceo_intent}' (trace={payload.trace_id})",
            tags=["ceo_approved"],
            ceo_approved=True,
        )
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
        \"\"\"
        Async Parallel Workflow enforcing ALL Doc 3 rules:
        - DynamicPlanner + ShortTermMemory + ObservabilityTracer + ManagerCircuitBreaker.
        - Stops & escalates immediately if Researcher fails (never runs Coder on failed research).
        \"\"\"
        payload.validate_for_handoff()
        planner = DynamicPlanner(payload.session_id, payload.approved_directive)
        stm = ShortTermMemory(payload.session_id, storage_dir=self.short_term_dir)
        executor = AsyncStaffExecutor(max_concurrency=4)

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

        payload.validate_for_handoff()
        self.use_tool(
            payload.session_id,
            "memory_write",
            topic=payload.original_ceo_intent,
            summary=f"Async verified '{payload.original_ceo_intent}' (trace={payload.trace_id})",
            tags=["ceo_approved", "async"],
            ceo_approved=True,
        )
        return {
            "status": "COMPLETED_ASYNC",
            "session_id": payload.session_id,
            "trace_id": payload.trace_id,
            "plan_markdown": planner.render_markdown(),
        }
"""

    files["agents/staff/__init__.py"] = ""

    # Staff Agents (strictly typed)
    files["agents/staff/coder/__init__.py"] = ""
    files["agents/staff/coder/system_prompt.md"] = "# Role: CoderAgent (Tier 2 Budget Staff AI)\n"
    files["agents/staff/coder/agent.py"] = """
\"\"\"CoderAgent — Production defaults to `docker_python_runner`; Demo uses `demo_python_runner`.\"\"\"

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from llm.client import LLMClient
from tools.registry import ToolRegistry


class CoderAgent(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_client: LLMClient | None = None,
        *,
        demo_mode: bool = False,
    ) -> None:
        super().__init__(
            "coder",
            "Specialized Coder",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
        )
        self.demo_mode = demo_mode

    def draft_and_test_fix(
        self, session_id: str, findings: dict[str, Any], feedback: str | None = None
    ) -> dict[str, Any]:
        code = (
            "def retry(): return {'status': 'ok'}\\n"
            "assert retry()['status'] == 'ok'\\nprint('OK')\\n"
        )
        runner_tool = "demo_python_runner" if self.demo_mode else "docker_python_runner"
        res = self.use_tool(session_id, runner_tool, python_code=code)
        return {"runner": runner_tool, "code": code, "test_result": res}
"""

    staff_defs = [
        (
            "researcher",
            "ResearcherAgent",
            "Researcher & Log Analyst",
            (
                "def investigate(\n"
                "        self, session_id: str, log_path: str, keyword: str, feedback: str | None = None\n"
                "    ) -> dict[str, Any]:\n"
                "        return dict(self.use_tool(session_id, 'log_reader', log_path=log_path, keyword=keyword))"
            ),
        ),
        (
            "reviewer",
            "ReviewerAgent",
            "Code Reviewer",
            (
                "def review_code(\n"
                "        self, session_id: str, code_text: str, feedback: str | None = None\n"
                "    ) -> dict[str, Any]:\n"
                "        return dict(self.use_tool(session_id, 'code_review', code_text=code_text))"
            ),
        ),
        (
            "writer_tutor",
            "WriterTutorAgent",
            "Writer & Bilingual CS Tutor",
            (
                "def recall_context(self, session_id: str, keyword: str) -> dict[str, Any]:\n"
                "        return dict(self.use_tool(session_id, 'memory_read', keyword=keyword))"
            ),
        ),
        (
            "devops",
            "DevOpsAgent",
            "DevOps Engineer",
            (
                "def check_service_logs(\n"
                "        self, session_id: str, log_path: str, keyword: str = 'error'\n"
                "    ) -> dict[str, Any]:\n"
                "        return dict(self.use_tool(session_id, 'log_reader', log_path=log_path, keyword=keyword))"
            ),
        ),
        (
            "security_auditor",
            "SecurityAuditorAgent",
            "Security Auditor",
            (
                "def audit_snippet(self, session_id: str, code_text: str) -> dict[str, Any]:\n"
                "        return dict(self.use_tool(session_id, 'code_review', code_text=code_text))"
            ),
        ),
    ]
    for folder, cls_name, role_desc, method_code in staff_defs:
        files[f"agents/staff/{folder}/__init__.py"] = ""
        files[f"agents/staff/{folder}/system_prompt.md"] = f"# Role: {cls_name} (Tier 2 Budget Staff AI)\n"
        files[f"agents/staff/{folder}/agent.py"] = (
            f'"""{cls_name} — Tier 2 Budget Staff Agent."""\n\n'
            "from __future__ import annotations\n\n"
            "from pathlib import Path\n"
            "from typing import Any\n\n"
            "from agents.base_agent import BaseAgent\n"
            "from llm.client import LLMClient\n"
            "from tools.registry import ToolRegistry\n\n\n"
            f"class {cls_name}(BaseAgent):\n"
            "    def __init__(\n"
            "        self, tool_registry: ToolRegistry, llm_client: LLMClient | None = None\n"
            "    ) -> None:\n"
            "        super().__init__(\n"
            f'            "{folder}",\n'
            f'            "{role_desc}",\n'
            '            Path(__file__).parent / "system_prompt.md",\n'
            "            tool_registry,\n"
            "            tier=2,\n"
            "            llm_client=llm_client,\n"
            "        )\n\n"
            f"    {method_code}\n"
        )

    # -------------------------------------------------------------------------
    # 9. Skills, CI/CD, Project Book (All 10 Templates) & Runtime Dirs
    # -------------------------------------------------------------------------
    files["skills/create-prd/feature-template.md"] = (
        "# PRD: {Feature Name}\n\n- **PRD ID:** {PRD_ID}\n- **Status:** Draft\n\n"
        "## Implementation Phases\n### Phase 1: Foundation\n- [ ] {task}\n"
    )
    for s_name, s_desc in [
        ("create-prd", "Generate a structured PRD using feature-template.md."),
        ("phase-prd", "Split an existing PRD in docs/PRDs/active/ into phase files."),
        ("language-communication", "Enforce Burmese primary, Traditional Chinese (繁體中文) terms, and Basic English."),
        ("prompt-refinement", "Refine CEO intent into tamper-evident StructuredContextPayload."),
        ("dynamic-planning", "Break an approved directive into gated sequential or async Staff steps."),
        ("quality-gate-review", "Validate Staff outputs via Manager Circuit Breaker (max 2 retries)."),
        ("research-and-log-analysis", "Scan path-contained logs and run Hybrid RAG search."),
        ("bilingual-cs-tutoring", "Explain CS/Math topics in Burmese paired with 繁體中文 terminology."),
    ]:
        files[f"skills/{s_name}/SKILL.md"] = f"---\nname: {s_name}\ndescription: {s_desc}\n---\n# {s_name}\n\n{s_desc}\n"

    files[".github/workflows/ci.yml"] = """
name: Personal AI Workforce CI
on: [push, pull_request]
jobs:
  quality-and-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff mypy bandit
      - run: ruff check .
      - run: mypy agents/ api/ harness/ llm/ tools/ launcher.py demo.py main.py
      - run: bandit -r agents/ api/ harness/ llm/ tools/ launcher.py
      - run: python3 -m unittest discover -s tests -v
      - run: bash tests/integration/docker_sandbox_test.sh
"""

    files["tests/integration/docker_sandbox_test.sh"] = """
#!/usr/bin/env bash
set -euo pipefail
command -v docker >/dev/null 2>&1 || { echo "Docker not installed — skipping."; exit 0; }
docker run --rm --network=none --read-only --cap-drop=ALL \
  --tmpfs /tmp:size=16m,noexec,nosuid,nodev \
  --memory=128m --cpus=0.5 --pids-limit=64 \
  --security-opt=no-new-privileges --user 65534:65534 \
  python:3.12-slim python -c "print('DOCKER_SANDBOX_OK')"
"""

    files["scripts/install_recommended_skills.sh"] = """
#!/usr/bin/env bash
set -euo pipefail
SKILLS_CLI_VERSION="${SKILLS_CLI_VERSION:-1.0.0}"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
SKILLS=(
  "vercel-labs/skills|find-skills|Skill discovery helper"
  "addyosmani/agent-skills|planning-and-task-breakdown|Manager AI planning helper"
  "addyosmani/agent-skills|code-review-and-quality|Reviewer Agent quality checklist"
  "mattpocock/skills|research|Researcher Agent workflow"
)
echo "=== Recommended skills.sh Packages (CLI: skills@${SKILLS_CLI_VERSION}) ==="
for entry in "${SKILLS[@]}"; do
  IFS="|" read -r repo skill purpose <<< "$entry"
  echo "  - ${repo} --skill ${skill} (${purpose})"
done
[[ "$DRY_RUN" == "true" ]] && { echo "[DRY-RUN] No packages installed."; exit 0; }
read -r -p "Install via npx skills@${SKILLS_CLI_VERSION}? [y/N]: " c
[[ "$c" =~ ^[Yy]$ ]] || exit 0
for entry in "${SKILLS[@]}"; do
  IFS="|" read -r repo skill _ <<< "$entry"
  npx "skills@${SKILLS_CLI_VERSION}" add "${repo}" --skill "${skill}"
done
"""

    for gk in [
        "docs/PRDs/active/.gitkeep",
        "docs/PRDs/active/phases/.gitkeep",
        "logs/action_logs/.gitkeep",
        "logs/decision_logs/.gitkeep",
        "logs/trace_logs/.gitkeep",
        "logs/cost_logs/.gitkeep",
        "memory_store/short_term/.gitkeep",
        "memory_store/long_term/.gitkeep",
        "workspaces/.gitkeep",
    ]:
        files[gk] = ""

    for pb_name, pb_title in [
        ("01_project_charter.md", "Project Charter & CSFs"),
        ("02_project_plan.md", "Project Plan (v10)"),
        ("03_key_action_planner.md", "Key Action Planner"),
        ("04_key_staffing_log.md", "Key Staffing Log"),
        ("05_project_calendar.md", "Project Calendar"),
        ("06_change_control_log.md", "Change Control Log"),
        ("07_risk_register.md", "Risk Register"),
        ("08_quality_log.md", "Quality Log"),
        ("09_communication_plan.md", "Communication Plan"),
        ("10_status_dashboard.md", "Project Status Dashboard"),
    ]:
        files[f"project_book/{pb_name}"] = f"# {pb_title}\n\n- **Lifecycle:** `Start → Plan → Do & Test → Monitor → Close`\n"

    # -------------------------------------------------------------------------
    # 10. Comprehensive Unit Tests (15 Tests covering every v7 fix!)
    # -------------------------------------------------------------------------
    files["tests/__init__.py"] = ""
    files["tests/test_harness.py"] = """
\"\"\"Comprehensive Unit Tests for Personal AI Workforce v10.\"\"\"

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
        self.assertFalse(code_review("import subprocess\\nsubprocess.run(['ls'])")["approved"])
        self.assertFalse(code_review("open('/etc/passwd', 'w').write('x')")["approved"])
        self.assertFalse(code_review("builtins.open('/tmp/x', 'w')")["approved"])
        self.assertFalse(code_review("io.open('/tmp/x', 'a')")["approved"])
        self.assertFalse(code_review("b.open('/tmp/x', mode='w')")["approved"])
        self.assertFalse(code_review("Path('/tmp/x').write_text('hi')")["approved"])
        self.assertFalse(code_review("().__class__.__bases__[0].__subclasses__()")["approved"])
        self.assertFalse(code_review("__builtins__['eval']('1+1')")["approved"])
        clean = "def add(a: int, b: int) -> int:\\n    return a + b\\n"
        self.assertTrue(code_review(clean)["approved"])

    def test_dotenv_loader_and_automatic_cost_logging(self) -> None:
        from harness.env_loader import load_dotenv_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_file.write_text('TEST_WF_KEY="hello_v8"\\n# comment\\n', encoding="utf-8")
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
            sample_log.write_text("ERROR 500 timeout\\n", encoding="utf-8")
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
            (existing / "main.py").write_text("print('EXISTING_APP')\\n", encoding="utf-8")
            (existing / "AGENTS.md").write_text("# Existing App Rules\\n", encoding="utf-8")
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
            self.assertEqual(main_txt, "print('EXISTING_APP')\\n")
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
                "protected_patterns:\\n  - data/**\\n  - secrets/**\\n  - .env\\n",
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
                "---\\nname: create-prd\\ndescription: PRD\\n---\\n", encoding="utf-8"
            )
            (wf_root / "AGENTS.md").write_text("# WF Agents", encoding="utf-8")
            (wf_root / "CLAUDE.md").write_text("# WF Claude", encoding="utf-8")
            (wf_root / "config" / "language_profile.yaml").write_text("lang: my", encoding="utf-8")
            (wf_root / "config" / "model_tiers.yaml").write_text(
                "tier_1_orchestrators:\\n  agents: [assistant_ai]\\n  models:\\n"
                "    - provider: anthropic\\n      model: claude-sonnet-4-5\\n"
                "tier_2_staff_executors:\\n  agents: [researcher]\\n  models:\\n"
                "    - provider: gemini\\n      model: gemini-3.5-flash-lite\\n",
                encoding="utf-8",
            )
            (wf_root / "config" / "safety_policy.yaml").write_text(
                "protected_patterns:\\n  - data/**\\n  - .env\\n", encoding="utf-8"
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


if __name__ == "__main__":
    unittest.main()
"""

    return files


def generate_project(
    target_dir: Path, *, overwrite: bool = False, dry_run: bool = False
) -> GenerationReport:
    files_map = build_files_map()
    report = GenerationReport()
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
    for rel_path, content in files_map.items():
        write_file(
            target_dir, rel_path, content, overwrite=overwrite, dry_run=dry_run, report=report
        )
    return report


def run_self_test() -> int:
    """Built-in self-test: generates into temp dir, verifies compileall & unit tests."""
    with tempfile.TemporaryDirectory(prefix="wf_selftest_") as tmp:
        target = Path(tmp) / "personal-ai-workforce"
        report = generate_project(target)
        expected = len(build_files_map())
        if len(report.created) != expected:
            print(f"[FAIL] Expected {expected} files, created {len(report.created)}")
            return 1
        if not compileall.compile_dir(str(target), quiet=1):
            print("[FAIL] compileall found syntax errors")
            return 1
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=target,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print(f"[SELF-TEST PASS] Generated {len(report.created)} files, compileall OK, unit tests OK.")
        return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Personal AI Workforce v10 Blueprint.")
    parser.add_argument("target", nargs="?", default="personal-ai-workforce")
    parser.add_argument("--overwrite", "--force", dest="overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true", help="Run generator self-test in temp dir")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()

    target = Path(args.target).resolve()
    report = generate_project(target, overwrite=args.overwrite, dry_run=args.dry_run)
    mode = "[DRY-RUN]" if args.dry_run else "[DONE]"
    print(
        f"{mode} Target: {target} | Created: {len(report.created)}, "
        f"Overwritten: {len(report.overwritten)}, Skipped: {len(report.skipped)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())