"""Shared Security Validators (Session ID & Path Containment)."""

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
