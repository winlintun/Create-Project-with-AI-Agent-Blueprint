"""Observability Tracer (`trace_id`) & Token Cost Tracker (`logs/cost_logs/`)."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id


class ObservabilityTracer:
    def __init__(self, logs_root: Path) -> None:
        self.trace_dir = logs_root / "trace_logs"
        self.cost_dir = logs_root / "cost_logs"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.cost_dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, directory: Path, file_key: str, entry: dict[str, Any]) -> None:
        safe_key = validate_session_id(file_key)
        target = ensure_path_within_root(directory / f"{safe_key}.jsonl", directory)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass

    @contextmanager
    def span(
        self, trace_id: str, session_id: str, agent: str, operation: str
    ) -> Iterator[dict[str, Any]]:
        start = time.perf_counter()
        meta: dict[str, Any] = {"status": "OK"}
        try:
            yield meta
        except Exception as exc:
            meta["status"] = "ERROR"
            meta["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self._append_jsonl(
                self.trace_dir,
                session_id,
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "agent": agent,
                    "operation": operation,
                    "duration_ms": round((time.perf_counter() - start) * 1000.0, 2),
                    **meta,
                },
            )

    def record_token_cost(
        self,
        *,
        trace_id: str,
        session_id: str,
        agent: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": trace_id,
            "session_id": session_id,
            "agent": agent,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        }
        self._append_jsonl(self.cost_dir, session_id, entry)
        return entry
