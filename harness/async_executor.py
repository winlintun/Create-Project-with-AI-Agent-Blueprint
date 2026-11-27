"""Async Parallel Staff Executor (`asyncio.gather` + `Semaphore`)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


class AsyncStaffExecutor:
    def __init__(self, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.max_concurrency = max_concurrency

    async def run_parallel(
        self, tasks: list[tuple[str, Callable[[], Awaitable[Any]]]]
    ) -> dict[str, Any]:
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _guarded(
            name: str, factory: Callable[[], Awaitable[Any]]
        ) -> tuple[str, Any]:
            async with sem:
                return name, await factory()

        return dict(await asyncio.gather(*(_guarded(n, f) for n, f in tasks)))
