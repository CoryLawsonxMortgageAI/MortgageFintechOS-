"""Central orchestrator daemon for MortgageFintechOS.

Manages agent lifecycle, task dispatch, scheduling, health monitoring,
dashboard, AIOS Kernel, and state persistence. Designed for 24/7 autonomous
operation with 9 AI agents (4 mortgage ops + 5 coding experts).
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
from agents.atlas import AtlasAgent
from agents.cipher import CipherAgent
from agents.forge import ForgeAgent
from agents.nexus import NexusAgent
from agents.storm import StormAgent
from config.settings import Settings
from core.aios_kernel import AIOSKernel
from core.task_queue import Task, TaskQueue, TaskPriority, TaskStatus
from dashboard.server import DashboardServer
from integrations.github_client import GitHubClient
from integrations.twitter_client import TwitterClient
from monitoring.health_monitor import HealthMonitor
from knowledge.reference_store import ReferenceStore
from persistence.state_store import StateStore
from schedulers.daily_scheduler import DailyScheduler, ScheduledJob

logger = structlog.get_logger()


class Orchestrator:
    """Central daemon managing all agents, task queue, AIOS Kernel, and system health."""

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
        self._kernel = AIOSKernel()
        self._github: GitHubClient | None = None
        self._twitter: TwitterClient | None = None
        self._reference_store = ReferenceStore()
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

        # Mortgage Operations Agents
        self.register_agent(DiegoAgent(max_retries=retry))
        self.register_agent(MartinAgent(max_retries=retry))
        self.register_agent(NovaAgent(max_retries=retry))
        self.register_agent(JarvisAgent(max_retries=retry))

        # Agentic Coding Expert Agents
        self.register_agent(AtlasAgent(max_retries=retry))
        self.register_agent(CipherAgent(max_retries=retry))
        self.register_agent(ForgeAgent(max_retries=retry))
        self.register_agent(NexusAgent(max_retries=retry))
        self.register_agent(StormAgent(max_retries=retry))

    def _setup_kernel(self) -> None:
        """Initialize the AIOS Kernel with all registered agents."""
        self._kernel.initialize(list(self._agents.keys()))
        self._kernel.set_pipeline_callback(self._pipeline_trigger)
        self._log.info("aios_kernel_initialized", agents=len(self._agents))

    async def _pipeline_trigger(self, agent_name: str, action: str, upstream_result: dict[str, Any]) -> None:
        """Callback for AIOS Kernel pipeline triggers."""
        await self.submit_task(agent_name, action, payload=upstream_result, priority=TaskPriority.HIGH)

    def _setup_github(self) -> None:
        if self.settings.github_token:
            self._github = GitHubClient(
                token=self.settings.github_token,
                repo=self.settings.github_repo,
            )
            self._log.info("github_integration_enabled")

    def _setup_twitter(self) -> None:
        self._twitter = TwitterClient(
            api_key=self.settings.x_api_key,
            api_secret=self.settings.x_api_secret,
            access_token=self.settings.x_access_token,
            access_secret=self.settings.x_access_secret,
        )
        if self._twitter.available:
            self._log.info("twitter_integration_enabled")
        else:
            self._twitter = None

    def _setup_schedule(self) -> None:
        # === Mortgage Operations Schedule ===

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

        # === Coding Expert Agent Schedule ===

        # 00:00 — CIPHER security scan (daily midnight)
        self._scheduler.add_job(ScheduledJob(
            name="security_audit",
            run_time=time(0, 0),
            callback=self._scheduled_security_audit,
        ))
        # 01:00 — NEXUS code quality analysis
        self._scheduler.add_job(ScheduledJob(
            name="code_quality_analysis",
            run_time=time(1, 0),
            callback=self._scheduled_quality_analysis,
        ))
        # 02:00 — STORM data quality checks
        self._scheduler.add_job(ScheduledJob(
            name="data_quality_check",
            run_time=time(2, 0),
            callback=self._scheduled_data_quality,
        ))
        # 03:00 — FORGE environment health check
        self._scheduler.add_job(ScheduledJob(
            name="environment_health_check",
            run_time=time(3, 0),
            callback=self._scheduled_environment_check,
        ))
        # Every 4 hours — ATLAS shipping report
        self._scheduler.add_job(ScheduledJob(
            name="shipping_report",
            run_time=time(0, 0),
            callback=self._scheduled_shipping_report,
            interval_minutes=240,
        ))
        # Every 2 hours — CIPHER compliance check
        self._scheduler.add_job(ScheduledJob(
            name="compliance_check",
            run_time=time(0, 0),
            callback=self._scheduled_compliance_check,
            interval_minutes=120,
        ))
        # Every 6 hours — NEXUS tech debt scan
        self._scheduler.add_job(ScheduledJob(
            name="tech_debt_scan",
            run_time=time(0, 0),
            callback=self._scheduled_tech_debt_scan,
            interval_minutes=360,
        ))
        # Weekly — STORM regulatory report (Friday 22:00)
        self._scheduler.add_job(ScheduledJob(
            name="weekly_regulatory_report",
            run_time=time(22, 0),
            callback=self._scheduled_regulatory_report,
            day_of_week=4,  # Friday
        ))
        # Weekly — FORGE secret rotation (Sunday 03:00)
        self._scheduler.add_job(ScheduledJob(
            name="secret_rotation",
            run_time=time(3, 0),
            callback=self._scheduled_secret_rotation,
            day_of_week=6,  # Sunday
        ))

    async def start(self, dashboard_host: str = "0.0.0.0", dashboard_port: int = 8080) -> None:
        """Start the orchestrator and all subsystems."""
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._log.info("orchestrator_starting")

        # 1. Start state store
        await self._state_store.start()

        # 2. Register all 9 agents and attach state stores
        self._register_default_agents()
        for agent in self._agents.values():
            agent.set_state_store(self._state_store)
            await agent.load_state()

        # 3. Initialize AIOS Kernel
        self._setup_kernel()
        kernel_state = await self._state_store.load("aios_kernel")
        if kernel_state:
            self._kernel.restore_state(kernel_state)
            self._log.info("aios_kernel_state_restored")

        # 4. Restore task queue history
        queue_data = await self._state_store.load("task_queue")
        if queue_data:
            self._task_queue.restore_from_dict(queue_data)
            self._log.info("task_queue_restored", history_count=len(queue_data.get("history", [])))

        # 5. Setup integrations
        self._setup_github()
        self._setup_twitter()
        self._reference_store.start()
        self._setup_schedule()
        self._scheduler.set_state_store(self._state_store)
        self._health_monitor.set_task_queue(self._task_queue)

        # 6. Start dashboard
        self._dashboard = DashboardServer(self, host=dashboard_host, port=dashboard_port)
        await self._dashboard.start()

        # 7. Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self._log.info(
            "orchestrator_started",
            agents=list(self._agents.keys()),
            scheduled_jobs=len(self._scheduler.list_jobs()),
            dashboard=f"http://{dashboard_host}:{dashboard_port}",
            kernel="AIOS Kernel v1.0.0",
        )

        # Post system status to X.com on startup
        if self._twitter:
            asyncio.create_task(self._twitter.post_system_status())

        # 8. Launch subsystems with watchdog supervision
        await self._watchdog_loop()

    async def stop(self) -> None:
        """Gracefully stop all subsystems and persist state."""
        self._log.info("orchestrator_stopping")
        self._running = False

        # Cancel subsystem tasks
        for name, task in self._subsystem_tasks.items():
            if not task.done():
                task.cancel()

        # Stop agents and persist state
        for agent in self._agents.values():
            agent.stop()
            await agent.save_state()

        # Persist task queue and kernel state
        await self._state_store.save("task_queue", self._task_queue.to_dict())
        await self._state_store.save("aios_kernel", self._kernel.get_state())

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

    # --- Task dispatch with AIOS Kernel integration ---

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
        """Main loop: dequeue tasks, check kernel quotas, route to agents."""
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

            # AIOS Kernel: check if agent can accept task
            if not self._kernel.can_schedule(task.agent_name):
                self._log.warning("agent_at_capacity", agent=task.agent_name, task_id=task.id)
                # Re-queue with slight delay
                await asyncio.sleep(1)
                await self._task_queue.enqueue(task)
                continue

            # Acquire execution slot
            self._kernel.acquire_slot(task.agent_name)

            try:
                result = await agent.run_task(task)
                self._task_queue.complete(task, result)
                self._health_monitor.record_task(success=True)

                # AIOS Kernel: record resource usage
                self._kernel.record_resource_usage(task.agent_name, cpu_time_ms=50, io_ops=1)

                # AIOS Kernel: trigger downstream pipeline agents
                triggered = await self._kernel.trigger_downstream(task.agent_name, task.action, result)
                if triggered:
                    self._log.info("pipeline_triggered", agent=task.agent_name, downstream=triggered)

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

            finally:
                # Always release kernel slot
                self._kernel.release_slot(task.agent_name)

            # Persist queue state periodically
            await self._state_store.save_debounced("task_queue", self._task_queue.to_dict())

    # --- Scheduled callbacks: Mortgage Operations ---

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

    # --- Scheduled callbacks: Coding Expert Agents ---

    async def _scheduled_security_audit(self) -> None:
        await self.submit_task("CIPHER", "run_security_audit", payload={"scope": "full"}, priority=TaskPriority.HIGH)

    async def _scheduled_quality_analysis(self) -> None:
        await self.submit_task("NEXUS", "analyze_quality", payload={"scope": "project"}, priority=TaskPriority.MEDIUM)

    async def _scheduled_data_quality(self) -> None:
        await self.submit_task("STORM", "run_data_quality", payload={"table": "loans"}, priority=TaskPriority.MEDIUM)

    async def _scheduled_environment_check(self) -> None:
        await self.submit_task("FORGE", "check_environment_health", priority=TaskPriority.HIGH)

    async def _scheduled_shipping_report(self) -> None:
        await self.submit_task("ATLAS", "get_shipping_report", priority=TaskPriority.LOW)

    async def _scheduled_compliance_check(self) -> None:
        await self.submit_task("CIPHER", "run_compliance_check", payload={"framework": "SOC2"}, priority=TaskPriority.MEDIUM)

    async def _scheduled_tech_debt_scan(self) -> None:
        await self.submit_task("NEXUS", "track_tech_debt", payload={"action": "scan"}, priority=TaskPriority.LOW)

    async def _scheduled_regulatory_report(self) -> None:
        await self.submit_task("STORM", "generate_regulatory_report", payload={"type": "HMDA"}, priority=TaskPriority.HIGH)

    async def _scheduled_secret_rotation(self) -> None:
        await self.submit_task("FORGE", "rotate_secrets", payload={"scope": "all"}, priority=TaskPriority.HIGH)

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
            "kernel": self._kernel.get_kernel_status(),
        }

    def get_health(self) -> dict[str, Any]:
        return self._health_monitor.get_full_health()

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.get_info() for agent in self._agents.values()]
