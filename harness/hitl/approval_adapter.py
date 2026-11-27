"""HITL Approval Adapter (Interactive CLI Only)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from harness.context_payload import StructuredContextPayload


@dataclass
class ApprovalOutcome:
    approved: bool
    source: str
    extra_constraints: list[str]
    status: str


def request_cli_approval(
    payload: StructuredContextPayload, *, input_fn: Callable[[str], str] = input
) -> ApprovalOutcome:
    print("\n=== [HITL CEO APPROVAL REQUIRED] ===")
    print(f"Intent     : {payload.original_ceo_intent}")
    print(f"Directive  : {payload.approved_directive}")
    print(f"Constraints: {payload.constraints}")
    prompt = "Approve? [y=Approve / n=Reject / e=Add Constraint & Approve]: "
    decision = input_fn(prompt).strip().lower()
    if decision == "y":
        return ApprovalOutcome(True, "interactive_cli", [], "APPROVED")
    if decision == "e":
        extra = input_fn("Extra constraint: ").strip()
        return ApprovalOutcome(True, "interactive_cli", [extra] if extra else [], "APPROVED")
    return ApprovalOutcome(False, "interactive_cli", [], "REJECTED")
