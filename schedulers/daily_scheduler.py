"""Daily task scheduler for MortgageFintechOS.

Manages cron-like scheduled operations for all agents including
document audits, income recalculations, and pipeline health checks.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import TYPE_CHECKING, Any, Callable, Coroutine

import structlog

if TYPE_CHECKING:
    from persistence.state_store import StateStore

logger = structlog.get_logger()


@dataclass
class ScheduledJob:
    name: str
    run_time: time
    callback: Callable[..., Coroutine[Any, Any, Any]]
    kwargs: dict[str, Any] = field(default_factory=dict)
    interval_minutes: int | None = None  # For recurring jobs
    day_of_week: int | None = None  # 0=Monday, for weekly jobs
    last_run: datetime | None = None
    enabled: bool = True


class DailyScheduler:
    """Async scheduler for daily, hourly, and weekly agent operations."""

    def __init__(self):
        self._jobs: list[ScheduledJob] = []
        self._running = False
        self._state_store: "StateStore | None" = None
        self._log = logger.bind(component="scheduler")

    def set_state_store(self, store: "StateStore") -> None:
        self._state_store = store

    def add_job(self, job: ScheduledJob) -> None:
        self._jobs.append(job)
        self._log.info("job_added", name=job.name, run_time=str(job.run_time))

    def remove_job(self, name: str) -> bool:
        before = len(self._jobs)
        self._jobs = [j for j in self._jobs if j.name != name]
        return len(self._jobs) < before

    def list_jobs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": j.name,
                "run_time": str(j.run_time) if j.run_time else None,
                "interval_minutes": j.interval_minutes,
                "day_of_week": j.day_of_week,
                "last_run": j.last_run.isoformat() if j.last_run else None,
                "enabled": j.enabled,
            }
            for j in self._jobs
        ]

    async def start(self) -> None:
        self._running = True
        await self._load_last_runs()
        await self.recover_missed_jobs()
        self._log.info("scheduler_started", jobs=len(self._jobs))
        while self._running:
            await self._check_and_run()
            await asyncio.sleep(30)

    def stop(self) -> None:
        self._running = False
        self._log.info("scheduler_stopped")

    async def _check_and_run(self) -> None:
        now = datetime.now(timezone.utc)
        current_time = now.time().replace(second=0, microsecond=0)

        for job in self._jobs:
            if not job.enabled:
                continue

            should_run = False

            # Interval-based jobs (hourly, etc.)
            if job.interval_minutes is not None:
                if job.last_run is None:
                    should_run = True
                else:
                    elapsed = (now - job.last_run).total_seconds() / 60
                    should_run = elapsed >= job.interval_minutes

            # Weekly jobs
            elif job.day_of_week is not None:
                if now.weekday() == job.day_of_week and job.run_time:
                    job_time = job.run_time.replace(second=0, microsecond=0)
                    if current_time == job_time:
                        if job.last_run is None or job.last_run.date() < now.date():
                            should_run = True

            # Daily time-based jobs
            elif job.run_time is not None:
                job_time = job.run_time.replace(second=0, microsecond=0)
                if current_time == job_time:
                    if job.last_run is None or job.last_run.date() < now.date():
                        should_run = True

            if should_run:
                await self._execute_job(job, now)

    async def recover_missed_jobs(self) -> None:
        """Run any daily jobs that were missed while the system was down."""
        now = datetime.now(timezone.utc)
        for job in self._jobs:
            if not job.enabled or job.interval_minutes is not None:
                continue
            if job.last_run is None or job.last_run.date() < now.date():
                # This daily/weekly job hasn't run today — run it now
                if job.day_of_week is not None and now.weekday() != job.day_of_week:
                    continue
                self._log.info("recovering_missed_job", name=job.name)
                await self._execute_job(job, now)

    async def _load_last_runs(self) -> None:
        """Restore last-run timestamps from state store."""
        if not self._state_store:
            return
        data = await self._state_store.load("scheduler")
        if not data:
            return
        last_runs = data.get("last_runs", {})
        for job in self._jobs:
            if job.name in last_runs:
                job.last_run = datetime.fromisoformat(last_runs[job.name])
        self._log.info("scheduler_state_restored", jobs_restored=len(last_runs))

    async def _save_last_runs(self) -> None:
        """Persist last-run timestamps to state store."""
        if not self._state_store:
            return
        last_runs = {}
        for job in self._jobs:
            if job.last_run:
                last_runs[job.name] = job.last_run.isoformat()
        await self._state_store.save_debounced("scheduler", {"last_runs": last_runs})

    async def _execute_job(self, job: ScheduledJob, now: datetime) -> None:
        try:
            self._log.info("job_executing", name=job.name)
            await job.callback(**job.kwargs)
            job.last_run = now
            await self._save_last_runs()
            self._log.info("job_completed", name=job.name)
        except Exception as e:
            self._log.error("job_failed", name=job.name, error=str(e))
