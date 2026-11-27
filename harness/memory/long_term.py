"""Long-Term Memory (Runtime Auto-Seeded JSON Store)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    "primary_language": "Burmese (မြန်မာစာ)",
    "academic_language": "Traditional Chinese (繁體中文, TOCFL B1)",
    "english_level": "Basic (explain tech keywords in Burmese)",
    "preferred_stack": ["Python", "FastAPI", "Docker", "PostgreSQL"],
}


class LongTermMemory:
    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save_raw({"preferences": dict(DEFAULT_USER_PREFERENCES), "episodes": []})

    def _load_raw(self) -> dict[str, Any]:
        return dict(json.loads(self.store_path.read_text(encoding="utf-8")))

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_preferences(self) -> dict[str, Any]:
        return dict(self._load_raw().get("preferences", {}))

    def add_episode(self, topic: str, summary: str, tags: list[str] | None = None) -> None:
        data = self._load_raw()
        data.setdefault("episodes", []).append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "topic": topic,
                "summary": summary,
                "tags": tags or [],
            }
        )
        self._save_raw(data)

    def search_episodes(self, keyword: str) -> list[dict[str, Any]]:
        kw = keyword.lower()
        return [
            ep
            for ep in self._load_raw().get("episodes", [])
            if kw in ep.get("topic", "").lower()
            or kw in ep.get("summary", "").lower()
            or any(kw in t.lower() for t in ep.get("tags", []))
        ]
