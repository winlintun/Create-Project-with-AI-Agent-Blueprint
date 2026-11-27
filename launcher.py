"""
Multi-Agent CLI Launcher — Pattern B+ Native Asset & Argv/Env Wiring (`launcher.py`)
- Renders native skills, tiered subagents, and enforced deny permissions into
  `workforce_root/workspaces/<slug>/` without polluting `workspace_root` data or code.
- Provides `build_launch_plan()` for `--doctor` diagnostics and `--print-launch`.
"""

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
from harness.memory.workspace_memory import (
    format_memory_snapshot_markdown,
    resolve_workspace_memory,
)
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
        "# - Prefer minimal targeted patches; review diffs with CEO before merging.\n",
    ]
    for rel in present_files:
        body = (workforce_root / rel).read_text(encoding="utf-8")
        sections.append(f"\n---\n## Workforce Rule: `{rel}`\n\n{body}")

    if workspace_root != workforce_root:
        for local_doc in ("AGENTS.md", "CLAUDE.md", "QWEN.md", "QWENS.md", "GEMINI.md"):
            lp = workspace_root / local_doc
            if lp.is_file():
                local_body = lp.read_text(encoding="utf-8", errors="replace")
                sections.append(
                    f"\n---\n## Existing Project Context: `{local_doc}` (Read-Only)\n\n"
                    f"{local_body}"
                )

    memory_md = format_memory_snapshot_markdown(workforce_root, workspace_root)
    sections.append(f"\n---\n{memory_md}")
    return "\n".join(sections)


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

    mem_ctx = resolve_workspace_memory(wf_root, ws_root)
    state_dir = mem_ctx.state_dir
    state_dir.mkdir(parents=True, exist_ok=True)

    combined = _build_combined_context(profile, wf_root, ws_root, present_files, protected)
    assets_info: dict[str, Any] = {}

    if profile.name == "claude":
        assets_info = render_claude_assets(wf_root, state_dir, protected)
        target_path = Path(assets_info["config_dir"]) / "CLAUDE.md"
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
        "workspace_slug": mem_ctx.workspace_slug,
        "state_dir": str(state_dir),
        "memory_root": str(mem_ctx.memory_root),
        "logs_dir": str(mem_ctx.logs_dir),
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
        "workforce_root": ctx_info.get("workforce_root", str(project_root.resolve())),
        "workspace_root": ctx_info.get("workspace_root", str(project_root.resolve())),
        "workspace_slug": ctx_info.get("workspace_slug", "default"),
        "memory_root": ctx_info.get("memory_root", str(project_root.resolve() / "memory_store")),
        "logs_dir": ctx_info.get("logs_dir", str(project_root.resolve() / "logs")),
        "context_file": ctx_info["injected_context_path"],
        "present_rules": ctx_info["present_files"],
        "assets": assets,
    }
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(metadata_file, 0o600)
    except OSError:
        pass

    filtered["WORKFORCE_METADATA_FILE"] = str(metadata_file)
    filtered["WORKFORCE_ROOT"] = str(metadata["workforce_root"])
    filtered["WORKFORCE_WORKSPACE_ROOT"] = str(metadata["workspace_root"])
    filtered["WORKFORCE_WORKSPACE_SLUG"] = str(metadata["workspace_slug"])
    filtered["WORKFORCE_MEMORY_DIR"] = str(metadata["memory_root"])
    filtered["WORKFORCE_LOGS_DIR"] = str(metadata["logs_dir"])
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
    if not ws_root.exists() or not ws_root.is_dir():
        print(f"[X] Workspace directory မတွေ့ပါ: {ws_root}")
        return 1
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

    print(f"\n>>> [{profile.display_name}] (Pattern B+)")
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
        print("\n[!] User interrupted. Exiting gracefully.")
        return 130
