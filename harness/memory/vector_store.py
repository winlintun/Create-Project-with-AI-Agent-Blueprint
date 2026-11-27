"""
Optional VectorMemory Interface (`harness/memory/vector_store.py`)
- Default: `InMemoryCosineVectorStore` (zero external dependencies).
- Production option: implement `VectorMemoryBackend` with PostgreSQL + `pgvector` or ChromaDB.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Protocol

TOKEN_RE = re.compile(r"[\w\u1000-\u109F\u4e00-\u9fff]+", re.UNICODE)


class VectorMemoryBackend(Protocol):
    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...
    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]: ...


class InMemoryCosineVectorStore:
    """Stdlib TF-cosine vector store for local semantic memory retrieval."""

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
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
