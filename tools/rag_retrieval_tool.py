"""Researcher Tool: Path-Contained Markdown Keyword RAG."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
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
