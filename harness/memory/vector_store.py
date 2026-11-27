"""
Optional VectorMemory Interface (`harness/memory/vector_store.py`)
- Default: `InMemoryCosineVectorStore` (zero external dependencies; supports optional JSON disk persistence).
- Production option: implement `VectorMemoryBackend` with PostgreSQL + `pgvector` or ChromaDB.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Protocol

TOKEN_RE = re.compile(r"[\w\u1000-\u109F\u4e00-\u9fff]+", re.UNICODE)


class VectorMemoryBackend(Protocol):
    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...
    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]: ...


class InMemoryCosineVectorStore:
    """Stdlib TF-cosine vector store for local semantic memory retrieval (optional JSON persistence)."""

    def __init__(self, persist_path: Path | None = None) -> None:
        self.persist_path = persist_path
        self._lock = threading.Lock()
        self._docs: dict[str, tuple[str, Counter[str], dict[str, Any]]] = {}
        if self.persist_path is not None and self.persist_path.is_file():
            self._load()

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

    def _load(self) -> None:
        if self.persist_path is None or not self.persist_path.is_file():
            return
        try:
            raw = json.loads(self.persist_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        for doc_id, item in raw.items():
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            meta = dict(item.get("metadata", {})) if isinstance(item.get("metadata"), dict) else {}
            self._docs[str(doc_id)] = (text, self._vec(text), meta)

    def _save(self) -> None:
        if self.persist_path is None:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = {
            doc_id: {"text": text, "metadata": meta}
            for doc_id, (text, _vec, meta) in self._docs.items()
        }
        payload = json.dumps(serialized, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.persist_path.parent),
            prefix=f".{self.persist_path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(payload)
            os.replace(tmp_name, self.persist_path)
            try:
                os.chmod(self.persist_path, 0o600)
            except OSError:
                pass
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def upsert(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._docs[doc_id] = (text, self._vec(text), dict(metadata or {}))
            self._save()

    def count(self) -> int:
        with self._lock:
            return len(self._docs)

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        qv = self._vec(query_text)
        with self._lock:
            items = list(self._docs.items())
        scored: list[dict[str, Any]] = []
        for doc_id, (text, dv, meta) in items:
            score = round(self._cos(qv, dv), 4)
            if score > 0:
                scored.append({"id": doc_id, "score": score, "text": text, "metadata": meta})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
