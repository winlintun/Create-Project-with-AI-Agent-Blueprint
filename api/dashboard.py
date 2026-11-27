"""
Observability Web Dashboard (`api/dashboard.py`)
- Binds strictly to `127.0.0.1` by default.
- Supports optional `WORKFORCE_DASHBOARD_TOKEN` Bearer auth header.
- Exposes `/api/sessions`, `/api/memory`, `/api/traces`, `/api/costs`, and `/api/costs/summary`
  for BOTH current project and external `--workspace` slugs (`?workspace=<slug>`).
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.memory.long_term import LongTermMemory
from harness.memory.vector_store import InMemoryCosineVectorStore
from harness.validators import ensure_path_within_root, validate_session_id
from tools.memory_access_tool import make_memory_read_tool

LOGS_ROOT = PROJECT_ROOT / "logs"


def resolve_dashboard_roots(
    workspace: str | None = None, *, project_root: Path = PROJECT_ROOT
) -> tuple[Path, Path]:
    """Return `(logs_root, memory_root)` safely for default or named `--workspace` slug."""
    root = project_root.resolve()
    if not workspace or workspace == "default":
        return root / "logs", root / "memory_store"
    safe_slug = validate_session_id(workspace)
    ws_base = root / "workspaces"
    ws_dir = ensure_path_within_root(ws_base / safe_slug, ws_base)
    return ws_dir / "logs", ws_dir / "memory_store"


def list_sessions(logs_root: Path = LOGS_ROOT) -> list[str]:
    sessions: set[str] = set()
    for subdir in ("trace_logs", "cost_logs", "action_logs"):
        folder = logs_root / subdir
        if folder.is_dir():
            for fp in folder.glob("*.jsonl"):
                sessions.add(fp.stem)
    return sorted(sessions)


def list_workspaces(project_root: Path = PROJECT_ROOT) -> list[str]:
    ws_dir = project_root.resolve() / "workspaces"
    names = ["default"]
    if ws_dir.is_dir():
        for child in sorted(ws_dir.iterdir()):
            if child.is_dir():
                names.append(child.name)
    return names


def read_memory_for_dashboard(
    query: str = "",
    *,
    workspace: str | None = None,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    _logs_root, mem_root = resolve_dashboard_roots(workspace, project_root=project_root)
    ltm_path = mem_root / "long_term" / "user_preferences.json"
    vec_path = mem_root / "long_term" / "vector_index.json"
    if not ltm_path.is_file():
        return {"workspace": workspace or "default", "preferences": {}, "episodes": [], "semantic_hits": []}
    ltm = LongTermMemory(ltm_path)
    vec = InMemoryCosineVectorStore(persist_path=vec_path)
    reader = make_memory_read_tool(ltm, vector_store=vec)
    return {"workspace": workspace or "default", **reader(keyword=query)}


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
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="Personal AI Workforce Observability Dashboard")

    def _require_auth(authorization: str | None) -> None:
        if not verify_dashboard_token(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(
        workspace: str | None = None, authorization: str | None = Header(default=None)
    ) -> str:
        _require_auth(authorization)
        try:
            logs_root, _mem_root = resolve_dashboard_roots(workspace)
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        sessions = list_sessions(logs_root)
        workspaces = list_workspaces()
        ws_label = workspace or "default"
        sess_items = "".join(
            f"<li><code>{s}</code> — "
            f"<a href='/api/traces?session_id={s}&workspace={ws_label}'>traces</a> | "
            f"<a href='/api/costs/summary?session_id={s}&workspace={ws_label}'>costs</a></li>"
            for s in sessions
        ) or "<li>No sessions recorded yet.</li>"
        ws_links = " | ".join(
            f"<a href='/dashboard?workspace={w}'>{w}</a>" for w in workspaces
        )
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>AI Workforce Dashboard</title></head>"
            "<body style='font-family:sans-serif;max-width:900px;margin:2rem auto;'>"
            "<h1>Personal AI Workforce — Observability & Memory Dashboard</h1>"
            f"<p><strong>Workspaces:</strong> {ws_links}</p>"
            f"<p><strong>Active Scope:</strong> <code>{ws_label}</code> — "
            f"<a href='/api/memory?workspace={ws_label}'>View Memory JSON</a></p>"
            f"<h2>Sessions ({len(sessions)})</h2><ul>{sess_items}</ul>"
            "<p>Endpoints: <code>/api/sessions</code>, <code>/api/memory</code>, "
            "<code>/api/traces</code>, <code>/api/costs</code>, "
            "<code>/api/costs/summary</code></p></body></html>"
        )

    @app.get("/api/sessions")
    async def get_sessions(
        workspace: str | None = None, authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            logs_root, _ = resolve_dashboard_roots(workspace)
            return {
                "workspace": workspace or "default",
                "workspaces": list_workspaces(),
                "sessions": list_sessions(logs_root),
            }
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/memory")
    async def get_memory(
        query: str = "",
        workspace: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            return read_memory_for_dashboard(query=query, workspace=workspace)
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/traces")
    async def get_traces(
        session_id: str,
        workspace: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            logs_root, _ = resolve_dashboard_roots(workspace)
            traces = read_jsonl_for_session("trace_logs", session_id, logs_root=logs_root)
            return {"workspace": workspace or "default", "session_id": session_id, "traces": traces}
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs")
    async def get_costs(
        session_id: str,
        workspace: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            logs_root, _ = resolve_dashboard_roots(workspace)
            costs = read_jsonl_for_session("cost_logs", session_id, logs_root=logs_root)
            return {"workspace": workspace or "default", "session_id": session_id, "costs": costs}
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/costs/summary")
    async def get_cost_summary(
        session_id: str,
        workspace: str | None = None,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _require_auth(authorization)
        try:
            logs_root, _ = resolve_dashboard_roots(workspace)
            return summarize_session_costs(session_id, logs_root=logs_root)
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=400, detail=str(exc))
except ImportError:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
