"""Researcher Tool: Path-Contained Hybrid RAG (Keyword + Cosine Similarity)."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from harness.validators import ensure_path_within_root

TOKEN_RE = re.compile(r"[\w\u1000-\u109F\u4e00-\u9fff]+", re.UNICODE)


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
        q_vec, q_low, scored, scanned = _tokenize(query), query.lower(), [], 0
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
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {
            "query": query,
            "mode": "hybrid_keyword_cosine",
            "scanned_files": scanned,
            "results": scored[:top_k],
        }

    return hybrid_rag
