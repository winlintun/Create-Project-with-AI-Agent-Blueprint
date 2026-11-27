"""Structured Context Payload (Tamper-Evident SHA-256 CEO Approval)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from harness.validators import validate_session_id


@dataclass
class StructuredContextPayload:
    original_ceo_intent: str
    approved_directive: str
    constraints: list[str] = field(default_factory=list)
    context_notes: dict[str, Any] = field(default_factory=dict)
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    ceo_approved: bool = False
    approved_at: str | None = None
    approval_digest: str | None = None
    approval_source: str = "unapproved"

    def __post_init__(self) -> None:
        validate_session_id(self.session_id)

    def _compute_digest(self) -> str:
        canonical = json.dumps(
            {
                "original_ceo_intent": self.original_ceo_intent,
                "approved_directive": self.approved_directive,
                "constraints": list(self.constraints),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def approve(
        self,
        extra_constraints: list[str] | None = None,
        *,
        approval_source: str = "explicit_ceo",
    ) -> None:
        if extra_constraints:
            self.constraints.extend(extra_constraints)
        self.ceo_approved = True
        self.approved_at = datetime.now(UTC).isoformat()
        self.approval_source = approval_source
        self.approval_digest = self._compute_digest()

    def revoke_approval(self) -> None:
        self.ceo_approved = False
        self.approved_at = None
        self.approval_digest = None
        self.approval_source = "revoked"

    def validate_for_handoff(self) -> None:
        validate_session_id(self.session_id)
        if not self.ceo_approved or not self.approval_digest:
            raise PermissionError("Gatekeeper Block: CEO approval required.")
        if self._compute_digest() != self.approval_digest:
            self.revoke_approval()
            raise PermissionError("Approval Invalidated: payload modified after CEO approval.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
