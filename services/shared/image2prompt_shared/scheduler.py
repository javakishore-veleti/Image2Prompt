"""A tiny asyncio-based periodic scheduler for background housekeeping.

Lightweight on purpose — no extra dependency (APScheduler etc.). Jobs are plain
sync callables (typically DB prunes) run off the event loop via ``to_thread``.
Fully fail-safe: a job that raises is logged and the loop continues; the whole
scheduler is feature-toggled and cancelled cleanly on shutdown.

Usage (in a FastAPI lifespan):

    scheduler = PeriodicScheduler(enabled=settings.scheduler_enabled)
    scheduler.add_job(name="prune-x", interval_seconds=3600, func=_prune_x)
    await scheduler.start()
    yield
    await scheduler.stop()
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from .logging_config import get_logger

log = get_logger(__name__)


@dataclass
class _Job:
    name: str
    interval_seconds: float
    func: Callable[[], None]
    run_on_start: bool = False


class PeriodicScheduler:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._jobs: list[_Job] = []
        self._tasks: list[asyncio.Task] = []

    def add_job(
        self,
        *,
        name: str,
        interval_seconds: float,
        func: Callable[[], None],
        run_on_start: bool = False,
    ) -> None:
        self._jobs.append(_Job(name, interval_seconds, func, run_on_start))

    async def start(self) -> None:
        if not self.enabled:
            log.info("scheduler disabled; %d job(s) not started", len(self._jobs))
            return
        for job in self._jobs:
            self._tasks.append(asyncio.create_task(self._loop(job)))
        if self._tasks:
            log.info("scheduler started with %d job(s)", len(self._tasks))

    async def _loop(self, job: _Job) -> None:
        try:
            if job.run_on_start:
                await self._run_once(job)
            while True:
                await asyncio.sleep(job.interval_seconds)
                await self._run_once(job)
        except asyncio.CancelledError:
            pass

    async def _run_once(self, job: _Job) -> None:
        try:
            await asyncio.to_thread(job.func)
        except Exception as exc:  # a failing job must never kill the loop
            log.warning("scheduled job '%s' failed: %s", job.name, exc)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
