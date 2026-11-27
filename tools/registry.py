"""Tool Registry & Permission Enforcer (`permissions={}` = Deny All, supports YAML config)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.persistence.audit_logger import AuditLogger, redact_sensitive_data

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

DEFAULT_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "assistant_ai": {"memory_read"},
    "manager_ai": {"memory_read", "memory_write"},
    "researcher": {"web_search", "log_reader", "rag_retrieval", "hybrid_rag"},
    "coder": {"docker_python_runner"},
    "reviewer": {"code_review"},
    "writer_tutor": {"memory_read", "memory_write"},
    "devops": {"docker_python_runner", "log_reader"},
    "security_auditor": {"code_review", "log_reader"},
}


def load_tool_permissions(config_path: Path | None = None) -> dict[str, set[str]]:
    """Load `tool_permissions` from YAML (PyYAML or stdlib fallback); defaults on missing file."""
    if config_path is None or not config_path.is_file():
        return {k: set(v) for k, v in DEFAULT_TOOL_PERMISSIONS.items()}

    raw = config_path.read_text(encoding="utf-8")
    if HAS_YAML:
        loaded = yaml.safe_load(raw)
        if isinstance(loaded, dict) and isinstance(loaded.get("tool_permissions"), dict):
            return {
                str(agent): {str(t) for t in tools}
                for agent, tools in loaded["tool_permissions"].items()
                if isinstance(tools, list)
            }
        return {k: set(v) for k, v in DEFAULT_TOOL_PERMISSIONS.items()}

    perms: dict[str, set[str]] = {}
    in_section = False
    for line in raw.splitlines():
        clean = line.split("#", 1)[0].rstrip()
        if not clean.strip():
            continue
        if clean.strip() == "tool_permissions:":
            in_section = True
            continue
        if in_section:
            if not clean.startswith(" "):
                break
            stripped = clean.strip()
            if ":" in stripped:
                agent, rest = stripped.split(":", 1)
                rest = rest.strip()
                if rest.startswith("[") and rest.endswith("]"):
                    items = [
                        item.strip().strip('"').strip("'")
                        for item in rest[1:-1].split(",")
                        if item.strip()
                    ]
                    perms[agent.strip()] = set(items)
    return perms if perms else {k: set(v) for k, v in DEFAULT_TOOL_PERMISSIONS.items()}


class ToolRegistry:
    def __init__(
        self,
        audit_logger: AuditLogger,
        permissions: dict[str, set[str]] | None = None,
    ) -> None:
        self.audit_logger = audit_logger
        src = DEFAULT_TOOL_PERMISSIONS if permissions is None else permissions
        self.permissions = {k: set(v) for k, v in src.items()}
        self._tools: dict[str, Callable[..., Any]] = {}

    @classmethod
    def from_config(
        cls,
        audit_logger: AuditLogger,
        config_path: Path = Path("config/tool_permissions.yaml"),
        *,
        overrides: dict[str, set[str]] | None = None,
    ) -> ToolRegistry:
        perms = load_tool_permissions(config_path)
        if overrides:
            for agent, tools in overrides.items():
                perms[agent] = set(tools)
        return cls(audit_logger=audit_logger, permissions=perms)

    def register(self, tool_name: str, fn: Callable[..., Any]) -> None:
        self._tools[tool_name] = fn

    def invoke(self, session_id: str, agent_name: str, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self.permissions.get(agent_name, set()):
            self.audit_logger.log_action(
                session_id, agent_name, tool_name, "DENIED", {"reason": "Toolbelt violation"}
            )
            raise PermissionError(
                f"Toolbelt Violation: Agent '{agent_name}' cannot use '{tool_name}'."
            )
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered.")

        safe_args = redact_sensitive_data({
            k: (f"<str len={len(v)}>" if isinstance(v, str) and len(v) > 80 else v)
            for k, v in kwargs.items()
        })
        try:
            res = self._tools[tool_name](**kwargs)
            self.audit_logger.log_action(
                session_id,
                agent_name,
                tool_name,
                "SUCCESS",
                {"args": safe_args, "result_type": type(res).__name__},
            )
            return res
        except Exception as exc:
            self.audit_logger.log_action(
                session_id,
                agent_name,
                tool_name,
                "FAIL",
                {"args": safe_args, "error": f"{type(exc).__name__}: {exc}"},
            )
            raise
