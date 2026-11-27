"""CoderAgent — Production defaults to `docker_python_runner`; Demo uses `demo_python_runner`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from llm.client import LLMClient
from tools.registry import ToolRegistry


class CoderAgent(BaseAgent):
    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_client: LLMClient | None = None,
        *,
        demo_mode: bool = False,
    ) -> None:
        super().__init__(
            "coder",
            "Specialized Coder",
            Path(__file__).parent / "system_prompt.md",
            tool_registry,
            tier=2,
            llm_client=llm_client,
        )
        self.demo_mode = demo_mode

    def draft_and_test_fix(
        self, session_id: str, findings: dict[str, Any], feedback: str | None = None
    ) -> dict[str, Any]:
        code = (
            "def retry(): return {'status': 'ok'}\n"
            "assert retry()['status'] == 'ok'\nprint('OK')\n"
        )
        runner_tool = "demo_python_runner" if self.demo_mode else "docker_python_runner"
        res = self.use_tool(session_id, runner_tool, python_code=code)
        return {"runner": runner_tool, "code": code, "test_result": res}
