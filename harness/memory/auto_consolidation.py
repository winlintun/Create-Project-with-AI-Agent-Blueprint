"""Auto-Consolidation Background Worker (CEO-approved sessions only)."""

from __future__ import annotations

import threading

from harness.memory.consolidation import consolidate_session_to_long_term
from harness.memory.long_term import LongTermMemory
from harness.memory.short_term import ShortTermMemory


class AutoConsolidator:
    def __init__(self, ltm: LongTermMemory, interval_seconds: float = 3600.0) -> None:
        self.ltm = ltm
        self.interval_seconds = interval_seconds
        self._queue: dict[str, tuple[ShortTermMemory, str, bool]] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def enqueue_session(self, stm: ShortTermMemory, *, topic: str, ceo_approved: bool) -> None:
        if not ceo_approved:
            raise PermissionError("AutoConsolidator only accepts CEO-approved sessions.")
        with self._lock:
            self._queue[stm.session_id] = (stm, topic, True)

    def run_once(self) -> int:
        with self._lock:
            snapshot = dict(self._queue)
            self._queue.clear()
        count = 0
        for _sid, (stm, topic, approved) in snapshot.items():
            consolidate_session_to_long_term(stm, self.ltm, topic=topic, ceo_approved=approved)
            count += 1
        return count

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()

        def _loop() -> None:
            while not self._stop_event.wait(self.interval_seconds):
                self.run_once()

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
