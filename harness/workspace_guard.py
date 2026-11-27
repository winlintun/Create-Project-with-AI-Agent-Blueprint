"""
Workspace Safety Guard (`harness/workspace_guard.py`) — Pattern B Protection
- Dynamically loads `config/safety_policy.yaml` at runtime (PyYAML or stdlib fallback).
- Supports true recursive `**` glob matching via `PurePosixPath.match` + path-part checks.
- Checks Git working tree status & validates branch names strictly.
"""

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
    """Dynamically loads `protected_patterns` from `config/safety_policy.yaml`."""
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
    probe = subprocess.run(  # nosec B603, B607 — fixed literal git argv, no user input
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        warnings.append("Workspace is not a Git repository; create a backup before editing.")
        return GitGuardStatus(False, "", False, 0, tuple(warnings))

    branch_proc = subprocess.run(  # nosec B603, B607 — fixed literal git argv
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

    status_proc = subprocess.run(  # nosec B603, B607 — fixed literal git argv
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
