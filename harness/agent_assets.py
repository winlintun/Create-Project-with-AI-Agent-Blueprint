"""
CLI-Native Agent & Skill Asset Renderer (`harness/agent_assets.py`) — Pattern B+
- Renders Workforce `skills/*/SKILL.md` + `CLAUDE.md` + Tiered Subagent `.md` files
  into CLI-native discovery layouts inside `state_dir` (Zero Data Pollution).
- Converts `config/safety_policy.yaml` protected patterns into enforced Claude `settings.json`
  `permissions.deny` rules (`Edit(./...)`, `Write(./...)`, and `Read(./.env*)`).
"""

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


def _pick_tier_model(
    wf_root: Path, tier: int, *, provider_hint: str | None = None
) -> str:
    if provider_hint == "claude":
        cfg_path = wf_root / "config" / "model_tiers.yaml"
        if cfg_path.is_file():
            cfg = load_tier_config(cfg_path)
            key = "tier_1_orchestrators" if tier == 1 else "tier_2_staff_executors"
            for m in cfg.get(key, {}).get("models", []):
                if isinstance(m, dict) and str(m.get("provider", "")).lower() == "anthropic":
                    return str(m.get("model", "claude-sonnet-4-5"))
        return "claude-sonnet-4-5" if tier == 1 else "haiku"

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
    """Convert protected data patterns into enforced Claude `permissions.deny` rules."""
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
        f"---\n"
        f"name: {name}\n"
        f"description: {desc}\n"
        f"model: {model}\n"
        f"tools: {tools}\n"
        f"---\n"
        f"# {name}\n\n"
        f"{guidance}\n\n"
        "Language Profile (Mandatory): Primary Burmese (မြန်မာစာ), "
        "pair CS/Math terms with Traditional Chinese (繁體中文, TOCFL B1), "
        "keep English simple.\n"
    )


def _copy_skills_and_subagents(
    wf_root: Path,
    skills_dst: Path,
    agents_dst: Path,
    *,
    provider_hint: str | None = None,
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

    t1_model = _pick_tier_model(wf_root, 1, provider_hint=provider_hint)
    t2_model = _pick_tier_model(wf_root, 2, provider_hint=provider_hint)
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
        wf_root, home / "skills", home / "agents", provider_hint="claude"
    )
    settings_path = home / "settings.json"
    settings_obj = build_claude_settings(protected)
    settings_path.write_text(json.dumps(settings_obj, indent=2) + "\n", encoding="utf-8")
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
    cfg_path.write_text(json.dumps(oc_cfg, indent=2) + "\n", encoding="utf-8")
    return {
        "xdg_config_home": str(xdg_home),
        "opencode_config": str(cfg_path),
        "skills_count": s_cnt,
        "agents_count": a_cnt,
    }
