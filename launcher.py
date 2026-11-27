"""
Multi-Agent CLI Launcher — Pattern B Zero-Pollution Workspace Mode (`launcher.py`)
- Launches OpenCode / Claude / Qwen / Agy with `cwd = workspace_root` (the existing project).
- Writes ZERO files into `workspace_root`; stores all injected contexts & runtime metadata
  inside `workforce_root/workspaces/<workspace_slug>/`.
- Runs Git pre-flight safety check and appends Protected Data Paths rules automatically.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 — only runs whitelisted CLI commands from AGENT_PROFILES
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
) -> str:
    sections = [
        f"# Active Runtime Context for {profile.display_name}",
        f"# Target Workspace (Existing Project): {workspace_root}",
        "# ZERO-OVERWRITE & DATA PROTECTION POLICY:",
        "# - NEVER delete, truncate, or overwrite existing data files:",
        "#   " + ", ".join(
            load_protected_patterns(workforce_root / "config" / "safety_policy.yaml")
        ),
        "# - Prefer minimal targeted patches; review diffs with CEO before merging.\n",
    ]
    for rel in present_files:
        body = (workforce_root / rel).read_text(encoding="utf-8")
        sections.append(f"\n---\n## Workforce Rule: `{rel}`\n\n{body}")

    # Read-only merge of existing project's own AGENTS.md / CLAUDE.md if present
    if workspace_root != workforce_root:
        for local_doc in ("AGENTS.md", "CLAUDE.md"):
            lp = workspace_root / local_doc
            if lp.is_file():
                local_body = lp.read_text(encoding="utf-8", errors="replace")
                sections.append(
                    f"\n---\n## Existing Project Context: `{local_doc}` (Read-Only)\n\n"
                    f"{local_body}"
                )
    return "\n".join(sections)


def prepare_context_injection(
    profile: AgentProfile,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    """
    Pattern B Zero-Pollution Context Injection:
    - Writes ZERO files inside `workspace_root`; stores all generated files in
      `project_root/workspaces/<slug>/`.
    """
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    is_external = ws_root != wf_root

    present_files = [rel for rel in profile.context_files if (wf_root / rel).is_file()]
    missing_files = [rel for rel in profile.context_files if rel not in present_files]

    if is_external:
        slug = make_workspace_slug(ws_root)
        state_dir = wf_root / "workspaces" / slug
        state_dir.mkdir(parents=True, exist_ok=True)
    else:
        state_dir = wf_root

    combined = _build_combined_context(profile, wf_root, ws_root, present_files)
    if profile.name == "opencode":
        ctx_md = state_dir / ".opencode_context.md"
        if is_external:
            ctx_md.write_text(combined, encoding="utf-8")
            instr = [str(ctx_md)]
        else:
            instr = present_files
        oc_cfg = {"$schema": "https://opencode.ai/config.json", "instructions": instr}
        target_path = state_dir / "opencode.json"
        target_path.write_text(json.dumps(oc_cfg, indent=2) + "\n", encoding="utf-8")
    elif profile.name == "claude":
        if is_external:
            target_path = state_dir / ".claude_context.md"
            target_path.write_text(combined, encoding="utf-8")
        else:
            target_path = wf_root / "CLAUDE.md"
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
        "injected_context_path": str(target_path),
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

    state_dir = Path(ctx_info.get("state_dir", str(project_root.resolve())))
    state_dir.mkdir(parents=True, exist_ok=True)
    metadata_file = state_dir / ".workforce_runtime.json"
    metadata = {
        "agent": profile.name,
        "workspace_root": ctx_info.get("workspace_root", str(project_root.resolve())),
        "context_file": ctx_info["injected_context_path"],
        "present_rules": ctx_info["present_files"],
    }
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(metadata_file, 0o600)
    except OSError:
        pass

    filtered["WORKFORCE_METADATA_FILE"] = str(metadata_file)
    if profile.name == "opencode" and ctx_info.get("is_external_workspace"):
        filtered["OPENCODE_CONFIG"] = ctx_info["injected_context_path"]
    return filtered


def launch_agent(
    profile: AgentProfile,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
    create_branch: str | None = None,
    dry_run: bool = False,
) -> int:
    wf_root = project_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    if not ws_root.exists() or not ws_root.is_dir():
        print(f"[X] Workspace directory မတွေ့ပါ: {ws_root}")
        return 1

    load_dotenv_file(wf_root / ".env")
    ctx_info = prepare_context_injection(profile, wf_root, workspace_root=ws_root)
    git_status = check_git_preflight(ws_root)

    if create_branch:
        safe_branch = validate_branch_name(create_branch)
        if not dry_run and git_status.is_git_repo:
            subprocess.run(  # nosec B603, B607 — fixed literal git argv, validated branch name
                ["git", "checkout", "-b", safe_branch], cwd=ws_root, check=False
            )

    if not dry_run and not validate_agent_available(profile):
        print(f"[X] '{profile.command[0]}' CLI ကို system ထဲမှာ မတွေ့ပါ။")
        print(f"    Install လုပ်ရန်: {profile.install_hint}")
        return 1

    env = prepare_filtered_env(profile, wf_root, ctx_info)
    configured = [k for k in profile.env_keys if k in env]

    print(f"\n>>> [{profile.display_name}] ကို စတင်ဖွင့်လှစ်နေပါပြီ...")
    print(f"    Target Workspace: {ws_root}")
    print(f"    State Dir       : {ctx_info['state_dir']} (Zero-Pollution)")
    print(f"    Injected File   : {ctx_info['injected_context_path']}")
    print(f"    Active API Env  : {len(configured)}/{len(profile.env_keys)} configured")
    for w in git_status.warnings:
        print(f"    [Git Guard] {w}")

    if dry_run:
        print(f"    [DRY-RUN] Command: {' '.join(profile.command)} (cwd={ws_root})")
        return 0

    try:
        proc = subprocess.run(list(profile.command), cwd=ws_root, env=env, check=False)  # nosec B603
        return proc.returncode
    except KeyboardInterrupt:
        print("\n[!] User interrupted. Exiting gracefully.")
        return 130
