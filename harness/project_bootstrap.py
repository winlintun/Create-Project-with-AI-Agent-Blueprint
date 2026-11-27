"""
Project Bootstrapper & AI Skill Decision Engine (`harness/project_bootstrap.py`)
- Reads the 3 Workforce Reference Documents:
  1. `1.Personal-Agent-Documents.md` (Language profile, Project lifecycle, Charter/Book)
  2. `2.The-Personal-AI-Workforce-Company.md` (4-Tier Hierarchy: CEO -> Assistant -> Manager -> Staff)
  3. `3.Best-Practices-for-Managing-the-User-AI.md` (Gatekeeper, Context Payload, Circuit Breaker, Dual Memory)
- Inspects target project (current or `--workspace`) to detect tech stack & project goals.
- Decides which `skills.sh` packages are needed for THIS specific project.
- Checks for `AGENTS.md`, `CLAUDE.md`, `QWEN.md` (or `QWENS.md`), `GEMINI.md`:
  - If missing -> auto-creates tailored to the project goals + 3 reference docs.
  - If exists  -> asks the user: Keep (`k`), Update/Append (`u`), or Modify/Regenerate (`m`),
    then implements the chosen action safely.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 — runs fixed npx skills CLI argv only
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REFERENCE_DOCS: tuple[str, ...] = (
    "1.Personal-Agent-Documents.md",
    "2.The-Personal-AI-Workforce-Company.md",
    "3.Best-Practices-for-Managing-the-User-AI.md",
)

DEFAULT_AGENT_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    "QWEN.md",
    "GEMINI.md",
)

MANAGED_BLOCK_START = "<!-- WORKFORCE-MANAGED-START -->"
MANAGED_BLOCK_END = "<!-- WORKFORCE-MANAGED-END -->"


@dataclass(frozen=True)
class SkillRecommendation:
    repo: str
    skill: str
    reason: str
    priority: str = "recommended"


@dataclass(frozen=True)
class ProjectProfile:
    project_name: str
    workspace_root: Path
    detected_stack: tuple[str, ...]
    inferred_goal: str
    reference_docs_found: tuple[str, ...]
    existing_agent_files: tuple[str, ...]
    missing_agent_files: tuple[str, ...]


# Curated skills.sh catalog mapped to project traits & Workforce hierarchy needs
SKILL_CATALOG: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    (
        "vercel-labs/skills",
        "find-skills",
        ("always",),
        "Core skill discovery helper for finding additional skills.sh packages",
    ),
    (
        "addyosmani/agent-skills",
        "planning-and-task-breakdown",
        ("always",),
        "Manager AI Dynamic Planner & milestone breakdown (Ref Doc 1 & 3)",
    ),
    (
        "addyosmani/agent-skills",
        "code-review-and-quality",
        ("python", "javascript", "typescript", "go", "rust", "java"),
        "Reviewer & Security Auditor quality gate checklist (Ref Doc 2 & 3)",
    ),
    (
        "mattpocock/skills",
        "research",
        ("always",),
        "Researcher Agent log analysis, RAG & web research workflow (Ref Doc 2)",
    ),
    (
        "vercel-labs/agent-skills",
        "vercel-react-best-practices",
        ("react", "nextjs", "frontend"),
        "Frontend React/Next.js architecture & performance rules",
    ),
    (
        "anthropics/skills",
        "frontend-design",
        ("react", "nextjs", "frontend", "gui"),
        "UI/UX design quality for web or desktop GUI applications",
    ),
    (
        "wshobson/agents",
        "python-testing-patterns",
        ("python",),
        "Python unittest/pytest patterns for Staff Coder & Quality Gate",
    ),
    (
        "wshobson/agents",
        "fastapi-templates",
        ("fastapi",),
        "FastAPI API routing, validation, and async best practices",
    ),
    (
        "wshobson/agents",
        "docker-expert",
        ("docker",),
        "Hardened container & sandbox configuration best practices",
    ),
    (
        "wshobson/agents",
        "sql-optimization-patterns",
        ("sql", "postgres", "sqlite"),
        "Safe database query & migration hygiene (Protected Data Guard)",
    ),
)


def read_reference_summaries(workforce_root: Path) -> dict[str, Any]:
    """Read the 3 Personal AI Workforce reference documents and extract key directives."""
    wf_root = workforce_root.resolve()
    found: list[str] = []
    combined_text: list[str] = []
    for name in REFERENCE_DOCS:
        fp = wf_root / name
        if fp.is_file():
            found.append(name)
            combined_text.append(fp.read_text(encoding="utf-8", errors="replace"))
    full = "\n".join(combined_text)
    return {
        "found": tuple(found),
        "has_burmese_zh_profile": ("မြန်မာစာ" in full and "繁體中文" in full),
        "has_4tier_hierarchy": ("Assistant AI" in full and "Manager AI" in full),
        "has_harness_rules": ("Circuit Breaker" in full or "Circuit Breakers" in full),
    }


def detect_project_stack(workspace_root: Path) -> tuple[str, ...]:
    """Inspect files in `workspace_root` (read-only) to infer languages & frameworks."""
    root = workspace_root.resolve()
    traits: list[str] = []

    def _add(tag: str) -> None:
        if tag not in traits:
            traits.append(tag)

    # Check common manifest files
    py_manifests = [root / "pyproject.toml", root / "requirements.txt", root / "setup.py"]
    py_text = ""
    for mp in py_manifests:
        if mp.is_file():
            _add("python")
            py_text += "\n" + mp.read_text(encoding="utf-8", errors="replace").lower()
    if any(root.glob("*.py")) or (root / "src").is_dir() and any((root / "src").glob("*.py")):
        _add("python")
    if "fastapi" in py_text:
        _add("fastapi")
    if any(k in py_text for k in ("tkinter", "pyqt", "pyside", "customtkinter", "streamlit")):
        _add("gui")

    pkg_json = root / "package.json"
    if pkg_json.is_file():
        pkg_text = pkg_json.read_text(encoding="utf-8", errors="replace").lower()
        _add("javascript")
        if "typescript" in pkg_text or (root / "tsconfig.json").is_file():
            _add("typescript")
        if "react" in pkg_text:
            _add("react")
            _add("frontend")
        if "next" in pkg_text:
            _add("nextjs")
            _add("frontend")

    if (root / "Dockerfile").is_file() or (root / "docker-compose.yml").is_file():
        _add("docker")
    if "docker" in py_text:
        _add("docker")

    if any(root.glob("*.sql")) or any(root.glob("*.db")) or any(root.glob("*.sqlite*")):
        _add("sql")
    if "psycopg" in py_text or "postgres" in py_text or "pgvector" in py_text:
        _add("postgres")
        _add("sql")
    if "sqlite" in py_text:
        _add("sqlite")
        _add("sql")

    if (root / "go.mod").is_file():
        _add("go")
    if (root / "Cargo.toml").is_file():
        _add("rust")
    if (root / "pom.xml").is_file() or (root / "build.gradle").is_file():
        _add("java")

    if "gui" in root.name.lower():
        _add("gui")

    return tuple(traits)


def infer_project_goal(workspace_root: Path, explicit_goal: str | None = None) -> str:
    """Infer the project's goal from explicit `--goal` or its README.md / directory name."""
    if explicit_goal and explicit_goal.strip():
        return explicit_goal.strip()
    root = workspace_root.resolve()
    for readme_name in ("README.md", "readme.md"):
        rp = root / readme_name
        if rp.is_file():
            lines = [
                ln.strip()
                for ln in rp.read_text(encoding="utf-8", errors="replace").splitlines()
                if ln.strip() and not ln.strip().startswith("![")
            ]
            if lines:
                heading = re.sub(r"^#+\s*", "", lines[0])
                detail = lines[1] if len(lines) > 1 and not lines[1].startswith("#") else ""
                return f"{heading} — {detail}" if detail else heading
    return f"Develop, maintain, and safely improve `{root.name}` with CEO-approved AI workflows."


def analyze_project(
    workforce_root: Path,
    workspace_root: Path | None = None,
    *,
    explicit_goal: str | None = None,
    target_agent_files: tuple[str, ...] = DEFAULT_AGENT_FILES,
) -> ProjectProfile:
    wf_root = workforce_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    refs = read_reference_summaries(wf_root)
    stack = detect_project_stack(ws_root)
    goal = infer_project_goal(ws_root, explicit_goal=explicit_goal)

    existing: list[str] = []
    missing: list[str] = []
    for fname in target_agent_files:
        if (ws_root / fname).is_file():
            existing.append(fname)
        elif fname == "QWEN.md" and (ws_root / "QWENS.md").is_file():
            existing.append("QWENS.md")
        else:
            missing.append(fname)

    return ProjectProfile(
        project_name=ws_root.name,
        workspace_root=ws_root,
        detected_stack=stack,
        inferred_goal=goal,
        reference_docs_found=tuple(refs["found"]),
        existing_agent_files=tuple(existing),
        missing_agent_files=tuple(missing),
    )


def decide_recommended_skills(
    profile: ProjectProfile,
    *,
    extra_goal_text: str = "",
) -> list[SkillRecommendation]:
    """AI Decision Rule: select the exact skills.sh packages needed for this project."""
    traits = set(profile.detected_stack)
    goal_low = f"{profile.inferred_goal} {extra_goal_text}".lower()
    if any(k in goal_low for k in ("gui", "ui", "dashboard", "frontend")):
        traits.add("gui")
    if any(k in goal_low for k in ("api", "fastapi", "backend")):
        traits.add("fastapi")
    if any(k in goal_low for k in ("db", "database", "sql", "sqlite", "postgres")):
        traits.add("sql")
    if "docker" in goal_low or "sandbox" in goal_low:
        traits.add("docker")

    chosen: list[SkillRecommendation] = []
    seen: set[tuple[str, str]] = set()
    for repo, skill, triggers, reason in SKILL_CATALOG:
        matched = "always" in triggers or any(t in traits for t in triggers)
        if matched and (repo, skill) not in seen:
            seen.add((repo, skill))
            priority = "core" if "always" in triggers else "project-matched"
            chosen.append(SkillRecommendation(repo=repo, skill=skill, reason=reason, priority=priority))
    return chosen


def render_agent_instruction_markdown(
    filename: str,
    profile: ProjectProfile,
    workforce_root: Path,
    *,
    is_update_block: bool = False,
) -> str:
    """Generate tailored agent instructions grounded in the project goal & 3 reference docs."""
    stack_str = ", ".join(profile.detected_stack) if profile.detected_stack else "General Software Project"
    refs_str = ", ".join(profile.reference_docs_found) if profile.reference_docs_found else "Workforce Reference Docs"
    agent_label = Path(filename).stem.upper()
    is_external = profile.workspace_root != workforce_root.resolve()
    ws_flag = f' --workspace "{profile.workspace_root}"' if is_external else ""

    body = (
        f"# {profile.project_name} — Agent Instructions ({agent_label})\n\n"
        f"> Auto-generated from project goals and Workforce Reference Docs (`{refs_str}`).\n\n"
        f"## 1. Project Goal & Scope (Ref Doc 1 — Project Charter)\n"
        f"- **Project:** `{profile.project_name}`\n"
        f"- **Goal:** {profile.inferred_goal}\n"
        f"- **Detected Stack:** {stack_str}\n"
        f"- **Lifecycle:** `Start → Plan → Do & Test → Monitor → Close`\n\n"
        f"## 2. User Language & Communication Profile (Mandatory)\n"
        f"- **Primary Language:** Burmese (မြန်မာစာ) — ရိုးရှင်းနားလည်လွယ်အောင် ရှင်းပြရမည်။\n"
        f"- **Academic / CS Terms:** Pair with Traditional Chinese (`繁體中文`, TOCFL B1), "
        f"e.g. Algorithm (`演算法`), Matrix (`矩陣`), Vector Database (`向量資料庫`).\n"
        f"- **English Level:** Basic — Coding/Tech keywords များကို မြန်မာလို အမြဲတွဲရှင်းပြရမည်။\n\n"
        f"## 3. 4-Tier AI Workforce Hierarchy & Harness Rules (Ref Doc 2 & 3)\n"
        f"- **Gatekeeper:** Never execute major changes without CEO approval; invalidate on directive tamper.\n"
        f"- **Circuit Breaker:** Max 2 retries per step with corrective feedback; escalate to CEO if still blocked.\n"
        f"- **Protected Data Guard:** NEVER delete, truncate, or overwrite `data/**`, `backups/**`, "
        f"`migrations/**`, `*.db`, `*.sqlite*`, `*.sql`, `.env*`.\n"
        f"- **Persistent Memory CLI:**\n"
        f"  - Read: `python3 main.py --memory-read \"<query>\"`{ws_flag}\n"
        f"  - Save (CEO approved): `python3 main.py --memory-write \"<topic>\" \"<summary>\" --approve`{ws_flag}\n"
    )
    if is_update_block:
        return f"{MANAGED_BLOCK_START}\n{body.strip()}\n{MANAGED_BLOCK_END}\n"
    return body


def _apply_update_block(existing_text: str, new_block: str) -> str:
    """Idempotently replace existing managed block or append it cleanly to the end."""
    if MANAGED_BLOCK_START in existing_text and MANAGED_BLOCK_END in existing_text:
        pattern = re.compile(
            re.escape(MANAGED_BLOCK_START) + r".*?" + re.escape(MANAGED_BLOCK_END) + r"\n?",
            re.DOTALL,
        )
        return pattern.sub(new_block, existing_text, count=1)
    sep = "\n\n" if existing_text.endswith("\n") else "\n\n"
    return existing_text.rstrip() + sep + new_block


def sync_agent_instruction_files(
    profile: ProjectProfile,
    workforce_root: Path,
    *,
    target_files: tuple[str, ...] = DEFAULT_AGENT_FILES,
    input_fn: Callable[[str], str] = input,
    default_existing_action: str | None = None,
    dry_run: bool = False,
) -> dict[str, list[str]]:
    """
    Create missing agent files automatically; for existing files, ask user:
    `k` (Keep), `u` (Update/Append managed section), or `m` (Modify/Regenerate).
    """
    summary: dict[str, list[str]] = {
        "created": [],
        "updated": [],
        "modified": [],
        "kept": [],
    }
    ws_root = profile.workspace_root

    for fname in target_files:
        # Respect existing QWENS.md if user already named it QWENS.md
        actual_name = "QWENS.md" if (fname == "QWEN.md" and (ws_root / "QWENS.md").is_file()) else fname
        fp = ws_root / actual_name

        if not fp.is_file():
            content = render_agent_instruction_markdown(actual_name, profile, workforce_root)
            if not dry_run:
                fp.write_text(content, encoding="utf-8")
            summary["created"].append(actual_name)
            continue

        # Existing file -> MUST ask user before modifying or updating!
        if default_existing_action is not None:
            choice = default_existing_action.strip().lower()
        else:
            prompt = (
                f"[?] '{actual_name}' already exists in {ws_root.name}. "
                "Action? [k=Keep / u=Update (append Workforce rules) / m=Modify (regenerate)]: "
            )
            choice = input_fn(prompt).strip().lower()

        if choice in {"u", "update"}:
            existing_text = fp.read_text(encoding="utf-8", errors="replace")
            block = render_agent_instruction_markdown(
                actual_name, profile, workforce_root, is_update_block=True
            )
            merged = _apply_update_block(existing_text, block)
            if not dry_run:
                fp.write_text(merged, encoding="utf-8")
            summary["updated"].append(actual_name)
        elif choice in {"m", "modify"}:
            content = render_agent_instruction_markdown(actual_name, profile, workforce_root)
            if not dry_run:
                fp.write_text(content, encoding="utf-8")
            summary["modified"].append(actual_name)
        else:
            summary["kept"].append(actual_name)

    return summary


def install_selected_skills(
    recommendations: list[SkillRecommendation],
    *,
    skills_cli_version: str = "latest",
    dry_run: bool = False,
    auto_yes: bool = False,
    input_fn: Callable[[str], str] = input,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Install AI-selected skills from skills.sh via `npx -y skills@latest add`."""
    pkg = f"skills@{skills_cli_version}" if skills_cli_version else "skills"
    commands = [
        ["npx", "-y", pkg, "add", rec.repo, "--skill", rec.skill]
        for rec in recommendations
    ]
    if dry_run:
        return {"installed": [], "dry_run": True, "commands": commands}

    if not auto_yes:
        ans = input_fn(
            f"Install {len(recommendations)} AI-selected skills via npx {pkg}? [y/N]: "
        ).strip().lower()
        if ans not in {"y", "yes"}:
            return {"installed": [], "cancelled": True, "commands": commands}

    installed: list[str] = []
    failed: list[dict[str, Any]] = []
    for rec, cmd in zip(recommendations, commands):
        proc = subprocess.run(cmd, cwd=cwd, check=False)  # nosec B603
        if proc.returncode == 0:
            installed.append(f"{rec.repo}:{rec.skill}")
        else:
            failed.append({"skill": f"{rec.repo}:{rec.skill}", "returncode": proc.returncode})
    return {"installed": installed, "failed": failed, "commands": commands}
