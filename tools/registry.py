"""Tool Registry & Permission Enforcer (`permissions={}` = Deny All)."""

from __future__ import annotations

from typing import Any, Callable

from harness.persistence.audit_logger import AuditLogger, redact_sensitive_data

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
