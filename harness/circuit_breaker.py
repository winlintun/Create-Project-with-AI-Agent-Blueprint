"""Manager Circuit Breaker (Quality Gate — Max 2 Retries + Exception Safety)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ValidationResult:
    passed: bool
    feedback: str = ""


@dataclass
class CircuitBreakerOutcome:
    success: bool
    attempts: int
    result: Any = None
    escalated_to_ceo: bool = False
    escalation_reason: str = ""


class ManagerCircuitBreaker:
    def __init__(self, max_retries: int = 2) -> None:
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative int.")
        self.max_retries = max_retries

    def execute_with_gate(
        self,
        task_fn: Callable[[str | None], Any],
        validator_fn: Callable[[Any], ValidationResult],
    ) -> CircuitBreakerOutcome:
        feedback: str | None = None
        total_attempts = 1 + self.max_retries
        for attempt in range(1, total_attempts + 1):
            try:
                output = task_fn(feedback)
                check = validator_fn(output)
            except Exception as exc:
                feedback = f"Unhandled exception ({type(exc).__name__}): {exc}"
                continue
            if check.passed:
                return CircuitBreakerOutcome(True, attempt, output, False)
            feedback = check.feedback
        reason = f"Quality Gate failed after {total_attempts} attempts: {feedback}"
        return CircuitBreakerOutcome(False, total_attempts, None, True, reason)
