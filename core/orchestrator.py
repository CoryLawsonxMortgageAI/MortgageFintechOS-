"""Central orchestrator daemon for MortgageFintechOS.

Manages agent lifecycle, task dispatch, scheduling, health monitoring,
and GitHub integration. Designed for 24/7 autonomous operation.
"""

import asyncio
import signal
from datetime import datetime, time, timezone
from typing import Any

import structlog

from agents.base import BaseAgent, AgentStatus
from agents.diego import DiegoAgent
from agents.martin import MartinAgent
from agents.nova import NovaAgent
from agents.jarvis import JarvisAgent
from config.settings import Settings
from core.task_queue import Task, TaskQueue, TaskPriority, TaskStatus
from integrations.github_client import GitHubClient
from monitoring.health_monitor import HealthMonitor
from schedulers.daily_scheduler import DailyScheduler, ScheduledJob

logger = structlog.get_logger()


class Orchestrator:
    """Central daemon managing all agents, task queue, and system health."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self._agents: dict[str, BaseAgent] = {}
        self._task_queue = TaskQueue()
        self._scheduler = DailyScheduler()
        self._health_monitor = HealthMonitor(
            heartbeat_timeout=self.settings.heartbeat_timeout_seconds,
            queue_backlog_threshold=self.settings.queue_backlog_threshold,
            error_rate_threshold=self.settings.error_rate_threshold,
            error_rate_window=self.settings.error_rate_window_seconds,
        )
        self._github: GitHubClient | None = None
        self._running = False
        self._start_time: datetime | None = None
        self._log = logger.bind(component="orchestrator")

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent
        self._health_monitor.register_agent(agent)
        self._log.info("agent_registered", agent=agent.name)

    def _register_default_agents(self) -> None:
        retry = self.settings.agent_retry_count
        self.register_agent(DiegoAgent(max_retries=retry))
        self.register_agent(MartinAgent(max_retries=retry))
        self.register_agent(NovaAgent(max_retries=retry))
        self.register_agent(JarvisAgent(max_retries=retry))

    def _setup_github(self) -> None:
        if self.settings.github_token:
            self._github = GitHubClient(
                token=self.settings.github_token,
                repo=self.settings.github_repo,
            )
            self._log.info("github_integration_enabled")

    def _setup_schedule(self) -> None:
        # 06:00 — MARTIN document audit
        self._scheduler.add_job(ScheduledJob(
            name="document_audit",
            run_time=time(self.settings.document_audit_hour, self.settings.document_audit_minute),
            callback=self._scheduled_document_audit,
        ))
        # 06:30 — NOVA income recalculation
        self._scheduler.add_job(ScheduledJob(
            name="income_recalculation",
            run_time=time(self.settings.income_recalc_hour, self.settings.income_recalc_minute),
            callback=self._scheduled_income_recalc,
        ))
        # 07:00 — DIEGO pipeline health check
        self._scheduler.add_job(ScheduledJob(
            name="pipeline_health_check",
            run_time=time(self.settings.pipeline_check_hour, self.settings.pipeline_check_minute),
            callback=self._scheduled_pipeline_check,
        ))
        # Hourly — Queue health check
        self._scheduler.add_job(ScheduledJob(
            name="queue_health_check",
            run_time=time(0, 0),
            callback=self._scheduled_queue_check,
            interval_minutes=self.settings.queue_check_interval_minutes,
        ))
        # Weekly — Pipeline report (Monday 08:00)
        self._scheduler.add_job(ScheduledJob(
            name="weekly_pipeline_report",
            run_time=time(8, 0),
            callback=self._scheduled_weekly_report,
            day_of_week=self.settings.weekly_report_day,
        ))

    async def start(self) -> None:
        """Start the orchestrator and all subsystems."""
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._log.info("orchestrator_starting")

        self._register_default_agents()
        self._setup_github()
        self._setup_schedule()
        self._health_monitor.set_task_queue(self._task_queue)

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self._log.info(
            "orchestrator_started",
            agents=list(self._agents.keys()),
            scheduled_jobs=len(self._scheduler.list_jobs()),
        )

        # Run subsystems concurrently
        await asyncio.gather(
            self._dispatch_loop(),
            self._scheduler.start(),
            self._health_monitor.start(),
            return_exceptions=True,
        )

    async def stop(self) -> None:
        """Gracefully stop all subsystems."""
        self._log.info("orchestrator_stopping")
        self._running = False

        for agent in self._agents.values():
            agent.stop()

        self._scheduler.stop()
        self._health_monitor.stop()
        self._log.info("orchestrator_stopped")

    async def submit_task(
        self,
        agent_name: str,
        action: str,
        payload: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> str:
        """Submit a task to the queue."""
        task = Task(
            priority=priority,
            agent_name=agent_name,
            action=action,
            payload=payload or {},
            max_retries=self.settings.agent_retry_count,
        )
        task_id = await self._task_queue.enqueue(task)
        self._log.info("task_submitted", task_id=task_id, agent=agent_name, action=action)
        return task_id

    async def _dispatch_loop(self) -> None:
        """Main loop: dequeue tasks and route to agents."""
        while self._running:
            try:
                # Use wait_for to avoid blocking forever
                task = await asyncio.wait_for(self._task_queue.dequeue(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            agent = self._agents.get(task.agent_name)
            if not agent:
                self._log.error("agent_not_found", agent=task.agent_name, task_id=task.id)
                self._task_queue.fail(task, f"Agent {task.agent_name} not found")
                continue

            try:
                result = await agent.run_task(task)
                self._task_queue.complete(task, result)
                self._health_monitor.record_task(success=True)

                # Auto-create GitHub issue for completed tasks if configured
                if self._github and task.priority <= TaskPriority.HIGH:
                    await self._github.create_agent_task_issue(
                        agent_name=agent.name,
                        task_action=task.action,
                        result=result,
                    )

            except Exception as e:
                self._log.error("task_dispatch_failed", task_id=task.id, error=str(e))
                self._task_queue.fail(task, str(e))
                self._health_monitor.record_task(success=False)

                # Re-queue if retries remain
                if task.status == TaskStatus.RETRYING:
                    await self._task_queue.enqueue(task)

    # --- Scheduled callbacks ---

    async def _scheduled_document_audit(self) -> None:
        await self.submit_task("MARTIN", "run_document_audit", priority=TaskPriority.MEDIUM)

    async def _scheduled_income_recalc(self) -> None:
        await self.submit_task("NOVA", "recalculate_income", priority=TaskPriority.MEDIUM)

    async def _scheduled_pipeline_check(self) -> None:
        await self.submit_task("DIEGO", "check_pipeline_health", priority=TaskPriority.HIGH)

    async def _scheduled_queue_check(self) -> None:
        stats = self._task_queue.get_stats()
        self._log.info("queue_health_check", **stats)

    async def _scheduled_weekly_report(self) -> None:
        await self.submit_task("DIEGO", "get_pipeline_report", priority=TaskPriority.LOW)
        if self._github:
            report = self.get_status()
            await self._github.post_daily_report(report)

    # --- Status methods ---

    def get_status(self) -> dict[str, Any]:
        uptime = ""
        if self._start_time:
            delta = datetime.now(timezone.utc) - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{hours}h {minutes}m {seconds}s"

        return {
            "running": self._running,
            "uptime": uptime,
            "agents": {name: agent.get_info() for name, agent in self._agents.items()},
            "queue": self._task_queue.get_stats(),
            "health": self._health_monitor.get_full_health().get("overall", "unknown"),
            "scheduled_jobs": self._scheduler.list_jobs(),
        }

    def get_health(self) -> dict[str, Any]:
        return self._health_monitor.get_full_health()

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.get_info() for agent in self._agents.values()]
