"""Researcher Tool: Path-Contained Log Reader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

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
