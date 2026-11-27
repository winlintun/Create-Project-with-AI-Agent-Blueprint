"""Long-Term Memory (Thread/Process-Safe Runtime Auto-Seeded JSON Store)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    "primary_language": "Burmese (မြန်မာစာ)",
    "academic_language": "Traditional Chinese (繁體中文, TOCFL B1)",
    "english_level": "Basic (explain tech keywords in Burmese)",
    "preferred_stack": ["Python", "FastAPI", "Docker", "PostgreSQL"],
}


class LongTermMemory:
    def __init__(
        self,
        store_path: Path,
        *,
        fallback_preferences_path: Path | None = None,
    ) -> None:
        self.store_path = store_path
        self.fallback_preferences_path = fallback_preferences_path
        self._thread_lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            seed_prefs = self._load_seed_preferences()
            self._save_raw({"preferences": seed_prefs, "episodes": []})

    def _load_seed_preferences(self) -> dict[str, Any]:
        if (
            self.fallback_preferences_path is not None
            and self.fallback_preferences_path.is_file()
        ):
            try:
                raw = json.loads(self.fallback_preferences_path.read_text(encoding="utf-8"))
                prefs = raw.get("preferences")
                if isinstance(prefs, dict) and prefs:
                    return dict(prefs)
            except (OSError, ValueError):
                pass
        return dict(DEFAULT_USER_PREFERENCES)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        lock_path = self.store_path.with_suffix(self.store_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            if not HAS_FCNTL:
                yield
                return
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load_raw(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"preferences": self._load_seed_preferences(), "episodes": []}
        return dict(json.loads(self.store_path.read_text(encoding="utf-8")))

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.store_path.parent),
            prefix=f".{self.store_path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(payload)
            os.replace(tmp_name, self.store_path)
            try:
                os.chmod(self.store_path, 0o600)
            except OSError:
                pass
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def get_preferences(self) -> dict[str, Any]:
        with self._locked():
            return dict(self._load_raw().get("preferences", {}))

    def list_episodes(
        self, *, limit: int = 20, workspace: str | None = None
    ) -> list[dict[str, Any]]:
        with self._locked():
            episodes = list(self._load_raw().get("episodes", []))
        if workspace:
            episodes = [ep for ep in episodes if ep.get("workspace") == workspace]
        if limit > 0:
            return episodes[-limit:]
        return episodes

    def add_episode(
        self,
        topic: str,
        summary: str,
        tags: list[str] | None = None,
        *,
        workspace: str | None = None,
    ) -> dict[str, Any]:
        episode: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "topic": topic,
            "summary": summary,
            "tags": list(tags or []),
        }
        if workspace:
            episode["workspace"] = workspace
        with self._locked():
            data = self._load_raw()
            data.setdefault("episodes", []).append(episode)
            self._save_raw(data)
        return episode

    def search_episodes(
        self, keyword: str, *, workspace: str | None = None
    ) -> list[dict[str, Any]]:
        kw = keyword.strip().lower()
        with self._locked():
            episodes = list(self._load_raw().get("episodes", []))
        if workspace:
            episodes = [ep for ep in episodes if ep.get("workspace") == workspace]
        if not kw:
            return episodes
        return [
            ep
            for ep in episodes
            if kw in ep.get("topic", "").lower()
            or kw in ep.get("summary", "").lower()
            or any(kw in t.lower() for t in ep.get("tags", []))
        ]
