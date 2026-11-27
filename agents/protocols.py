"""Strict Typing Protocols & StaffRoster for Mypy-Clean Agent Orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from llm.client import LLMClient


class ResearcherProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def investigate(
        self, session_id: str, log_path: str, keyword: str, feedback: str | None = None
    ) -> dict[str, Any]: ...


class CoderProtocol(Protocol):
    tier: int
    demo_mode: bool
    llm_client: LLMClient | None

    def draft_and_test_fix(
        self, session_id: str, findings: dict[str, Any], feedback: str | None = None
    ) -> dict[str, Any]: ...


class ReviewerProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def review_code(
        self, session_id: str, code_text: str, feedback: str | None = None
    ) -> dict[str, Any]: ...


class DevOpsProtocol(Protocol):
    tier: int
    llm_client: LLMClient | None

    def check_service_logs(
        self, session_id: str, log_path: str, keyword: str = "error"
    ) -> dict[str, Any]: ...


@dataclass
class StaffRoster:
    researcher: ResearcherProtocol
    coder: CoderProtocol
    reviewer: ReviewerProtocol
    writer_tutor: Any = None
    devops: DevOpsProtocol | None = None
    security_auditor: Any = None
