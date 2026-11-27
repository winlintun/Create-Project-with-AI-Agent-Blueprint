"""Workspace-Aware Memory Resolver (`harness/memory/workspace_memory.py`).

Resolves memory and log paths consistently for BOTH:
- Current project (`workforce_root`) -> `workforce_root/memory_store/` & `workforce_root/logs/`
- External project (`--workspace` / `--workforce`) -> Zero-Pollution isolation under
  `workforce_root/workspaces/<slug>/memory_store/` & `workforce_root/workspaces/<slug>/logs/`,
  inheriting global user preferences from `workforce_root/memory_store/long_term/user_preferences.json`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.memory.long_term import LongTermMemory
from harness.memory.vector_store import InMemoryCosineVectorStore
from harness.workspace_guard import make_workspace_slug


@dataclass(frozen=True)
class WorkspaceMemoryContext:
    workforce_root: Path
    workspace_root: Path
    is_external: bool
    workspace_slug: str
    state_dir: Path
    memory_root: Path
    long_term_path: Path
    short_term_dir: Path
    vector_index_path: Path
    logs_dir: Path


def resolve_workspace_memory(
    workforce_root: Path,
    workspace_root: Path | None = None,
) -> WorkspaceMemoryContext:
    wf_root = workforce_root.resolve()
    ws_root = workspace_root.resolve() if workspace_root is not None else wf_root
    is_external = ws_root != wf_root
    slug = make_workspace_slug(ws_root) if is_external else "default"

    if is_external:
        state_dir = wf_root / "workspaces" / slug
        memory_root = state_dir / "memory_store"
        logs_dir = state_dir / "logs"
    else:
        state_dir = wf_root
        memory_root = wf_root / "memory_store"
        logs_dir = wf_root / "logs"

    return WorkspaceMemoryContext(
        workforce_root=wf_root,
        workspace_root=ws_root,
        is_external=is_external,
        workspace_slug=slug,
        state_dir=state_dir,
        memory_root=memory_root,
        long_term_path=memory_root / "long_term" / "user_preferences.json",
        short_term_dir=memory_root / "short_term",
        vector_index_path=memory_root / "long_term" / "vector_index.json",
        logs_dir=logs_dir,
    )


def open_workspace_memory(
    workforce_root: Path,
    workspace_root: Path | None = None,
) -> tuple[WorkspaceMemoryContext, LongTermMemory, InMemoryCosineVectorStore]:
    ctx = resolve_workspace_memory(workforce_root, workspace_root)
    global_ltm_path = ctx.workforce_root / "memory_store" / "long_term" / "user_preferences.json"
    ltm = LongTermMemory(
        ctx.long_term_path,
        fallback_preferences_path=global_ltm_path if ctx.is_external else None,
    )
    vec = InMemoryCosineVectorStore(persist_path=ctx.vector_index_path)

    # Backfill vector store from existing LTM episodes if vector index is empty
    if vec.count() == 0:
        for idx, ep in enumerate(ltm.list_episodes(limit=0)):
            topic = str(ep.get("topic", ""))
            summary = str(ep.get("summary", ""))
            ts = str(ep.get("timestamp", idx))
            vec.upsert(
                doc_id=f"ep:{ts}:{idx}",
                text=f"{topic}\n{summary}\n{' '.join(ep.get('tags', []))}",
                metadata={
                    "topic": topic,
                    "timestamp": ts,
                    "tags": ep.get("tags", []),
                    "workspace": ep.get("workspace", ctx.workspace_slug),
                },
            )
    return ctx, ltm, vec


def format_memory_snapshot_markdown(
    workforce_root: Path,
    workspace_root: Path | None = None,
    *,
    recent_limit: int = 8,
) -> str:
    """Render a compact Markdown snapshot of LTM preferences + recent episodes for CLI context."""
    ctx, ltm, _vec = open_workspace_memory(workforce_root, workspace_root)
    prefs: dict[str, Any] = ltm.get_preferences()
    episodes = ltm.list_episodes(limit=recent_limit)

    lines = [
        "## Persistent Memory Context (Auto-Injected)",
        f"- Workspace Scope: `{ctx.workspace_slug}` (`{ctx.workspace_root}`)",
        f"- Memory Store   : `{ctx.long_term_path}`",
        f"- Vector Index   : `{ctx.vector_index_path}`",
        "- To query memory: `python3 main.py --memory-read \"<query>\"` "
        + (f"`--workspace \"{ctx.workspace_root}\"`" if ctx.is_external else ""),
        "- To save memory (CEO approved): `python3 main.py --memory-write \"<topic>\" \"<summary>\" --approve` "
        + (f"`--workspace \"{ctx.workspace_root}\"`" if ctx.is_external else ""),
        "",
        "### User Preferences",
    ]
    for k, v in prefs.items():
        lines.append(f"- **{k}**: {v}")

    lines.append("")
    lines.append(f"### Recent Episodes ({len(episodes)})")
    if not episodes:
        lines.append("- _(No episodes recorded yet for this workspace.)_")
    else:
        for ep in episodes:
            ts = str(ep.get("timestamp", ""))[:19]
            topic = ep.get("topic", "")
            summary = ep.get("summary", "")
            tags = ", ".join(ep.get("tags", []))
            tag_str = f" [{tags}]" if tags else ""
            lines.append(f"- `{ts}` **{topic}**{tag_str}: {summary}")
    return "\n".join(lines)
