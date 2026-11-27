"""Short-Term Memory (Working Memory) with Session ID & Path Containment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.validators import ensure_path_within_root, validate_session_id


class ShortTermMemory:
    def __init__(self, session_id: str, storage_dir: Path | None = None) -> None:
        self.session_id = validate_session_id(session_id)
        self.state: dict[str, Any] = {"session_id": self.session_id, "steps": {}}
        self.storage_dir = storage_dir

    def set_step_output(self, step_id: str, data: Any) -> None:
        self.state["steps"][step_id] = data
        if self.storage_dir is not None:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            out = ensure_path_within_root(
                self.storage_dir / f"{self.session_id}.json", self.storage_dir
            )
            out.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_all(self) -> dict[str, Any]:
        return dict(self.state)
