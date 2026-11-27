"""
Observability Web Dashboard (`api/dashboard.py`)
- Binds strictly to `127.0.0.1` by default.
- Supports optional `WORKFORCE_DASHBOARD_TOKEN` Bearer auth header.
- Exposes `/api/traces`, `/api/costs`, and `/api/costs/summary`.
"""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id

LOGS_ROOT = Path(__file__).parent.parent / "logs"


def read_jsonl_for_session(
    subdir: str, session_id: str, logs_root: Path = LOGS_ROOT
) -> list[dict[str, Any]]:
    safe_id = validate_session_id(session_id)
    base = logs_root / subdir
    if not base.exists():
        return []
    target = ensure_path_within_root(base / f"{safe_id}.jsonl", base)
    if not target.exists():
        return []
    return [
        json.loads(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_session_costs(
    session_id: str, logs_root: Path = LOGS_ROOT
) -> dict[str, Any]:
    rows = read_jsonl_for_session("cost_logs", session_id, logs_root=logs_root)
    in_tok = sum(int(r.get("input_tokens", 0)) for r in rows)
    out_tok = sum(int(r.get("output_tokens", 0)) for r in rows)
    total_usd = round(sum(float(r.get("estimated_cost_usd", 0.0)) for r in rows), 6)
    return {
        "session_id": session_id,
        "call_count": len(rows),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "total_cost_usd": total_usd,
    }


def verify_dashboard_token(auth_header: str | None) -> bool:
    expected = os.getenv("WORKFORCE_DASHBOARD_TOKEN", "").strip()
    if not expected:
        return True
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    provided = auth_header.removeprefix("Bearer ").strip()
    return hmac.compare_digest(provided, expected)


app: Any = None
try:
    from fastapi import FastAPI, Header, HTTPException  # type: ignore[import-not-found]
    from fastapi.responses import HTMLResponse  # type: ignore[import-not-found]

    app = FastAPI(title="Personal AI Workforce Observability Dashboard")

    def _require_auth(authorization: str | None) -> None:
        if not verify_dashboard_token(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(authorization: str | None = Header(default=None)) -> str:
        _require_auth(authorization)
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>AI Workforce Dashboard</title></head>"
            "<body style='font-family:sans-serif;max-width:900px;margin:2rem auto;'>"
            "<h1>Personal AI Workforce — Observability Dashboard</h1>"
            "<p>Endpoints: <code>/api/traces</code>, <code>/api/costs</code>, "
            "<code>/api/costs/summary</code></p></body></html>"
        )

    @app.get("/api/traces")
    async def get_traces(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            traces = read_jsonl_for_session("trace_logs", session_id)
            return {"session_id": session_id, "traces": traces}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs")
    async def get_costs(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            costs = read_jsonl_for_session("cost_logs", session_id)
            return {"session_id": session_id, "costs": costs}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs/summary")
    async def get_cost_summary(
        session_id: str, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            return summarize_session_costs(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn  # type: ignore[import-not-found]

    uvicorn.run(app, host="127.0.0.1", port=8080)
