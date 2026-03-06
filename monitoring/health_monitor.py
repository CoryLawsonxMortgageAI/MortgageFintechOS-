"""Health monitoring for MortgageFintechOS agents and system.

Tracks agent heartbeats, queue backlogs, error rates,
and system resource usage.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any

import structlog

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from agents.base import BaseAgent
from core.task_queue import TaskQueue

logger = structlog.get_logger()


class Alert:
    def __init__(self, severity: str, source: str, message: str):
        self.severity = severity
        self.source = source
        self.message = message
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthMonitor:
    """Monitors agent health, queue depth, error rates, and system resources."""

    def __init__(
        self,
        heartbeat_timeout: int = 60,
        queue_backlog_threshold: int = 50,
        error_rate_threshold: float = 0.10,
        error_rate_window: int = 300,
    ):
        self._agents: dict[str, BaseAgent] = {}
        self._task_queue: TaskQueue | None = None
        self._heartbeat_timeout = heartbeat_timeout
        self._queue_backlog_threshold = queue_backlog_threshold
        self._error_rate_threshold = error_rate_threshold
        self._error_rate_window = error_rate_window
        self._alerts: deque[Alert] = deque(maxlen=1000)
        self._error_timestamps: deque[datetime] = deque(maxlen=10000)
        self._task_timestamps: deque[datetime] = deque(maxlen=10000)
        self._running = False
        self._start_time = datetime.now(timezone.utc)
        self._log = logger.bind(component="health_monitor")

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def set_task_queue(self, queue: TaskQueue) -> None:
        self._task_queue = queue

    def record_task(self, success: bool) -> None:
        now = datetime.now(timezone.utc)
        self._task_timestamps.append(now)
        if not success:
            self._error_timestamps.append(now)

    async def start(self) -> None:
        self._running = True
        self._log.info("health_monitor_started")
        while self._running:
            await self._run_checks()
            await asyncio.sleep(15)

    def stop(self) -> None:
        self._running = False
        self._log.info("health_monitor_stopped")

    async def _run_checks(self) -> None:
        self._check_heartbeats()
        self._check_queue_backlog()
        self._check_error_rate()

    def _check_heartbeats(self) -> None:
        now = datetime.now(timezone.utc)
        for name, agent in self._agents.items():
            elapsed = (now - agent.last_heartbeat).total_seconds()
            if elapsed > self._heartbeat_timeout:
                alert = Alert(
                    severity="critical",
                    source=name,
                    message=f"Agent {name} heartbeat timeout ({elapsed:.0f}s > {self._heartbeat_timeout}s)",
                )
                self._alerts.append(alert)
                self._log.warning("heartbeat_timeout", agent=name, elapsed=elapsed)

    def _check_queue_backlog(self) -> None:
        if self._task_queue and self._task_queue.size > self._queue_backlog_threshold:
            alert = Alert(
                severity="warning",
                source="task_queue",
                message=f"Queue backlog: {self._task_queue.size} tasks (threshold: {self._queue_backlog_threshold})",
            )
            self._alerts.append(alert)
            self._log.warning("queue_backlog", size=self._task_queue.size)

    def _check_error_rate(self) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self._error_rate_window

        recent_errors = sum(1 for t in self._error_timestamps if t.timestamp() > cutoff)
        recent_tasks = sum(1 for t in self._task_timestamps if t.timestamp() > cutoff)

        if recent_tasks > 0:
            rate = recent_errors / recent_tasks
            if rate > self._error_rate_threshold:
                alert = Alert(
                    severity="warning",
                    source="system",
                    message=f"Error rate {rate:.1%} exceeds threshold {self._error_rate_threshold:.1%}",
                )
                self._alerts.append(alert)
                self._log.warning("high_error_rate", rate=rate)

    def get_system_metrics(self) -> dict[str, Any]:
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        metrics: dict[str, Any] = {"uptime_seconds": uptime}

        if HAS_PSUTIL:
            metrics["cpu_percent"] = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            metrics["memory_percent"] = mem.percent
            metrics["memory_used_mb"] = mem.used / (1024 * 1024)

        return metrics

    def get_full_health(self) -> dict[str, Any]:
        agent_health = {}
        for name, agent in self._agents.items():
            agent_health[name] = agent.get_info()

        queue_stats = self._task_queue.get_stats() if self._task_queue else {}
        recent_alerts = [a.to_dict() for a in list(self._alerts)[-20:]]

        has_critical = any(a.severity == "critical" for a in list(self._alerts)[-20:])
        overall = "critical" if has_critical else "healthy"

        return {
            "overall": overall,
            "agents": agent_health,
            "queue": queue_stats,
            "system": self.get_system_metrics(),
            "recent_alerts": recent_alerts,
        }
