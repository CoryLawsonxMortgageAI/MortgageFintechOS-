"""Central orchestrator daemon for MortgageFintechOS.

Manages agent lifecycle, task dispatch, scheduling, health monitoring,
dashboard, and state persistence. Designed for 24/7 autonomous operation.
"""

import asyncio
import signal
from collections import deque
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
from dashboard.server import DashboardServer
from integrations.github_client import GitHubClient
from monitoring.health_monitor import HealthMonitor
from persistence.state_store import StateStore
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
        self._state_store = StateStore(data_dir=self.settings.data_dir)
        self._github: GitHubClient | None = None
        self._dashboard: DashboardServer | None = None
        self._running = False
        self._start_time: datetime | None = None
        self._log = logger.bind(component="orchestrator")

        # Watchdog state
        self._subsystem_tasks: dict[str, asyncio.Task[None]] = {}
        self._crash_history: dict[str, deque[datetime]] = {
            "dispatch": deque(maxlen=20),
            "scheduler": deque(maxlen=20),
            "health_monitor": deque(maxlen=20),
        }
        self._degraded = False

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

    async def start(self, dashboard_host: str = "0.0.0.0", dashboard_port: int = 8080) -> None:
        """Start the orchestrator and all subsystems."""
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._log.info("orchestrator_starting")

        # 1. Start state store
        await self._state_store.start()

        # 2. Register agents and attach state stores
        self._register_default_agents()
        for agent in self._agents.values():
            agent.set_state_store(self._state_store)
            await agent.load_state()

        # 3. Restore task queue history
        queue_data = await self._state_store.load("task_queue")
        if queue_data:
            self._task_queue.restore_from_dict(queue_data)
            self._log.info("task_queue_restored", history_count=len(queue_data.get("history", [])))

        # 4. Setup integrations
        self._setup_github()
        self._setup_schedule()
        self._scheduler.set_state_store(self._state_store)
        self._health_monitor.set_task_queue(self._task_queue)

        # 5. Start dashboard
        self._dashboard = DashboardServer(self, host=dashboard_host, port=dashboard_port)
        await self._dashboard.start()

        # 6. Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self._log.info(
            "orchestrator_started",
            agents=list(self._agents.keys()),
            scheduled_jobs=len(self._scheduler.list_jobs()),
            dashboard=f"http://{dashboard_host}:{dashboard_port}",
        )

        # 7. Launch subsystems with watchdog supervision
        await self._watchdog_loop()

    async def stop(self) -> None:
        """Gracefully stop all subsystems and persist state."""
        self._log.info("orchestrator_stopping")
        self._running = False

        # Cancel subsystem tasks
        for name, task in self._subsystem_tasks.items():
            if not task.done():
                task.cancel()

        # Stop agents
        for agent in self._agents.values():
            agent.stop()
            await agent.save_state()

        # Persist task queue
        await self._state_store.save("task_queue", self._task_queue.to_dict())

        # Stop subsystems
        self._scheduler.stop()
        self._health_monitor.stop()

        if self._dashboard:
            await self._dashboard.stop()

        # Flush and stop state store
        await self._state_store.stop()
        self._log.info("orchestrator_stopped")

    # --- Watchdog ---

    async def _watchdog_loop(self) -> None:
        """Supervise subsystem tasks — restart any that crash."""
        self._launch_subsystems()

        while self._running:
            await asyncio.sleep(self.settings.watchdog_interval)

            for name, task in list(self._subsystem_tasks.items()):
                if task.done() and self._running:
                    exc = task.exception() if not task.cancelled() else None
                    self._log.warning(
                        "subsystem_crashed",
                        subsystem=name,
                        error=str(exc) if exc else "cancelled",
                    )
                    self._record_crash(name)

                    if self._is_crash_loop(name):
                        self._degraded = True
                        self._log.error("subsystem_crash_loop", subsystem=name)
                        if self._github:
                            asyncio.create_task(self._github.create_issue(
                                title=f"[ALERT] {name} subsystem crash loop",
                                body=f"Subsystem `{name}` crashed {self.settings.watchdog_max_crashes}+ times in 5 minutes. System in degraded mode.",
                                labels=["critical", "automated"],
                            ))
                    else:
                        self._log.info("subsystem_restarting", subsystem=name)
                        self._subsystem_tasks[name] = asyncio.create_task(
                            self._get_subsystem_coro(name)
                        )

    def _launch_subsystems(self) -> None:
        self._subsystem_tasks["dispatch"] = asyncio.create_task(self._dispatch_loop())
        self._subsystem_tasks["scheduler"] = asyncio.create_task(self._scheduler.start())
        self._subsystem_tasks["health_monitor"] = asyncio.create_task(self._health_monitor.start())

    def _get_subsystem_coro(self, name: str) -> Any:
        mapping = {
            "dispatch": self._dispatch_loop,
            "scheduler": self._scheduler.start,
            "health_monitor": self._health_monitor.start,
        }
        return mapping[name]()

    def _record_crash(self, name: str) -> None:
        self._crash_history[name].append(datetime.now(timezone.utc))

    def _is_crash_loop(self, name: str) -> bool:
        now = datetime.now(timezone.utc)
        recent = sum(
            1 for t in self._crash_history[name]
            if (now - t).total_seconds() < 300
        )
        return recent >= self.settings.watchdog_max_crashes

    # --- Task dispatch ---

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

                # Auto-create GitHub issue for completed high-priority tasks
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

            # Persist queue state periodically
            await self._state_store.save_debounced("task_queue", self._task_queue.to_dict())

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
            "degraded": self._degraded,
            "agents": {name: agent.get_info() for name, agent in self._agents.items()},
            "queue": self._task_queue.get_stats(),
            "health": self._health_monitor.get_full_health().get("overall", "unknown"),
            "scheduled_jobs": self._scheduler.list_jobs(),
        }

    def get_health(self) -> dict[str, Any]:
        return self._health_monitor.get_full_health()

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.get_info() for agent in self._agents.values()]
