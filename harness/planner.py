"""Dynamic Planner (Manager AI Living Todo List)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanStep:
    step_id: str
    assigned_agent: str
    description: str
    status: str = "pending"
    output: Any = None
    notes: str = ""


@dataclass
class DynamicPlanner:
    session_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(self, step_id: str, assigned_agent: str, description: str) -> PlanStep:
        step = PlanStep(step_id, assigned_agent, description)
        self.steps.append(step)
        return step

    def mark_status(
        self, step_id: str, status: str, output: Any = None, notes: str = ""
    ) -> None:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = status
                if output is not None:
                    step.output = output
                if notes:
                    step.notes = notes
                return
        raise KeyError(f"Unknown step_id: {step_id}")

    def render_markdown(self) -> str:
        icons = {"pending": "[ ]", "in_progress": "[/]", "completed": "[x]", "failed": "[!]"}
        lines = [f"# Dynamic Plan ({self.session_id})", f"**Goal:** {self.goal}", ""]
        for s in self.steps:
            icon = icons.get(s.status, "[ ]")
            lines.append(f"- {icon} **Step {s.step_id}** (`{s.assigned_agent}`): {s.description}")
        return "\n".join(lines)
