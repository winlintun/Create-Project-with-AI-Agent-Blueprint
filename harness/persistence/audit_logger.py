"""Persistence & Audit Logger (Recursive Secret Redaction + Session ID Validation + 0600)."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id

SENSITIVE_KEY_TOKENS = (
    "token", "password", "passwd", "secret", "api_key",
    "apikey", "authorization", "cookie", "credential", "private_key",
)
SECRET_VALUE_REGEX = re.compile(
    r"(Bearer\s+[A-Za-z0-9._-]+|sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,})",
    re.IGNORECASE,
)


def redact_sensitive_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: (
                "***REDACTED***"
                if any(t in str(k).lower() for t in SENSITIVE_KEY_TOKENS)
                else redact_sensitive_data(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_sensitive_data(i) for i in obj]
    if isinstance(obj, str):
        return SECRET_VALUE_REGEX.sub("***REDACTED***", obj)
    return obj


class AuditLogger:
    def __init__(self, logs_root: Path) -> None:
        self.action_dir = logs_root / "action_logs"
        self.decision_dir = logs_root / "decision_logs"
        self.action_dir.mkdir(parents=True, exist_ok=True)
        self.decision_dir.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, directory: Path, session_id: str, entry: dict[str, Any]) -> None:
        safe_id = validate_session_id(session_id)
        log_file = ensure_path_within_root(directory / f"{safe_id}.jsonl", directory)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        try:
            os.chmod(log_file, 0o600)
        except OSError:
            pass

    def log_action(
        self, session_id: str, agent_name: str, tool_name: str, status: str, details: Any
    ) -> dict[str, Any]:
        safe_id = validate_session_id(session_id)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": safe_id,
            "agent": agent_name,
            "tool": tool_name,
            "status": status,
            "details": redact_sensitive_data(details),
        }
        self._append_jsonl(self.action_dir, safe_id, entry)
        return entry

    def log_decision(
        self, session_id: str, actor: str, decision: str, notes: str = ""
    ) -> dict[str, Any]:
        safe_id = validate_session_id(session_id)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": safe_id,
            "actor": actor,
            "decision": decision,
            "notes": redact_sensitive_data(notes),
        }
        self._append_jsonl(self.decision_dir, safe_id, entry)
        return entry
