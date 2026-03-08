"""Central orchestrator daemon for MortgageFintechOS.

Manages agent lifecycle, task dispatch, scheduling, health monitoring,
dashboard, and state persistence. Designed for 24/7 autonomous operation.
Integrates Notion, Google Drive, Wispr Flow, GitHub, and multi-LLM routing.
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
from agents.sentinel import SentinelAgent
from config.settings import Settings
from core.task_queue import Task, TaskQueue, TaskPriority, TaskStatus
from dashboard.server import DashboardServer
from integrations.github_client import GitHubClient
from integrations.notion_client import NotionClient
from integrations.gdrive_client import GDriveClient
from integrations.wispr_client import WisprClient
from integrations.llm_router import LLMRouter
from integrations.paperclip_service import PaperclipService
from integrations.ghost_client import GhostClient
from integrations.pentagi_client import PentAGIClient
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
        self._notion: NotionClient | None = None
        self._gdrive: GDriveClient | None = None
        self._wispr: WisprClient | None = None
        self._llm: LLMRouter | None = None
        self._paperclip: PaperclipService | None = None
        self._ghost: GhostClient | None = None
        self._pentagi: PentAGIClient | None = None
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
        # Mortgage Operations
        self.register_agent(DiegoAgent(max_retries=retry))
        self.register_agent(MartinAgent(max_retries=retry))
        self.register_agent(NovaAgent(max_retries=retry))
        self.register_agent(JarvisAgent(max_retries=retry))
        # Engineering
        self.register_agent(AtlasAgent(max_retries=retry))
        self.register_agent(CipherAgent(max_retries=retry))
        self.register_agent(ForgeAgent(max_retries=retry))
        self.register_agent(NexusAgent(max_retries=retry))
        self.register_agent(StormAgent(max_retries=retry))
        # Intelligence
        self.register_agent(SentinelAgent(max_retries=retry))

    # --- Integration setup ---

    def _setup_github(self) -> None:
        if self.settings.github_token:
            self._github = GitHubClient(
                token=self.settings.github_token,
                repo=self.settings.github_repo,
            )
            self._log.info("github_integration_enabled")

    def _setup_notion(self) -> None:
        if self.settings.notion_api_token:
            self._notion = NotionClient(
                token=self.settings.notion_api_token,
                database_id=self.settings.notion_database_id,
                data_source_id=self.settings.notion_data_source_id,
            )
            self._log.info("notion_integration_enabled", api_version="2025-09-03")

    def _setup_gdrive(self) -> None:
        if self.settings.google_service_account_json:
            self._gdrive = GDriveClient(
                service_account_json=self.settings.google_service_account_json,
                folder_id=self.settings.google_drive_folder_id,
            )
            self._log.info("gdrive_integration_enabled")

    def _setup_wispr(self) -> None:
        self._wispr = WisprClient(
            webhook_secret=self.settings.wispr_webhook_secret,
        )
        self._log.info("wispr_integration_enabled")

    def _setup_llm(self) -> None:
        if any([self.settings.openai_api_key, self.settings.anthropic_api_key, self.settings.openrouter_api_key]):
            self._llm = LLMRouter(
                openai_key=self.settings.openai_api_key,
                anthropic_key=self.settings.anthropic_api_key,
                openrouter_key=self.settings.openrouter_api_key,
                default_provider=self.settings.default_llm_provider,
                default_model=self.settings.default_llm_model,
            )
            self._log.info("llm_router_enabled", providers=self._llm.get_status()["available_providers"])

    async def _setup_paperclip(self) -> None:
        self._paperclip = PaperclipService()
        await self._paperclip.start(self._state_store)
        self._log.info("paperclip_integration_enabled")

    def _setup_ghost(self) -> None:
        if self.settings.ghost_api_key or self.settings.ghost_base_url != "http://localhost:5000":
            self._ghost = GhostClient(
                base_url=self.settings.ghost_base_url,
                api_key=self.settings.ghost_api_key,
            )
            self._log.info("ghost_osint_integration_enabled")

    def _setup_pentagi(self) -> None:
        if self.settings.pentagi_api_key or self.settings.pentagi_base_url != "http://localhost:8443":
            self._pentagi = PentAGIClient(
                base_url=self.settings.pentagi_base_url,
                api_key=self.settings.pentagi_api_key,
            )
            self._log.info("pentagi_integration_enabled")

    def _inject_integrations(self) -> None:
        """Inject integration clients into all agents."""
        for agent in self._agents.values():
            agent.set_integrations(
                github=self._github,
                notion=self._notion,
                gdrive=self._gdrive,
                llm=self._llm,
                ghost=self._ghost,
                pentagi=self._pentagi,
            )
        self._log.info("integrations_injected", agents=len(self._agents))

    def _setup_schedule(self) -> None:
        # 03:00 — CIPHER security scan
        self._scheduler.add_job(ScheduledJob(
            name="security_scan",
            run_time=time(self.settings.security_scan_hour, self.settings.security_scan_minute),
            callback=self._scheduled_security_scan,
        ))
        # 05:30 — Google Drive import
        if self._gdrive:
            self._scheduler.add_job(ScheduledJob(
                name="drive_auto_import",
                run_time=time(self.settings.drive_import_hour, self.settings.drive_import_minute),
                callback=self._scheduled_drive_import,
            ))
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
        # 07:30 — Notion audit sync
        if self._notion:
            self._scheduler.add_job(ScheduledJob(
                name="notion_audit_sync",
                run_time=time(self.settings.notion_sync_hour, self.settings.notion_sync_minute),
                callback=self._scheduled_notion_sync,
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

        # 4. Setup all integrations
        self._setup_github()
        self._setup_notion()
        self._setup_gdrive()
        self._setup_wispr()
        self._setup_llm()
        await self._setup_paperclip()
        self._setup_ghost()
        self._setup_pentagi()
        self._inject_integrations()
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

        for name, task in self._subsystem_tasks.items():
            if not task.done():
                task.cancel()

        for agent in self._agents.values():
            agent.stop()
            await agent.save_state()

        await self._state_store.save("task_queue", self._task_queue.to_dict())
        if self._paperclip:
            await self._state_store.save("paperclip", self._paperclip.to_dict())
        self._scheduler.stop()
        self._health_monitor.stop()

        if self._dashboard:
            await self._dashboard.stop()

        await self._state_store.stop()
        self._log.info("orchestrator_stopped")

    # --- Watchdog ---

    async def _watchdog_loop(self) -> None:
        self._launch_subsystems()
        while self._running:
            await asyncio.sleep(self.settings.watchdog_interval)
            for name, task in list(self._subsystem_tasks.items()):
                if task.done() and self._running:
                    exc = task.exception() if not task.cancelled() else None
                    self._log.warning("subsystem_crashed", subsystem=name, error=str(exc) if exc else "cancelled")
                    self._record_crash(name)
                    if self._is_crash_loop(name):
                        self._degraded = True
                        self._log.error("subsystem_crash_loop", subsystem=name)
                        if self._github:
                            asyncio.create_task(self._github.create_issue(
                                title=f"[ALERT] {name} subsystem crash loop",
                                body=f"Subsystem `{name}` crashed {self.settings.watchdog_max_crashes}+ times in 5 minutes.",
                                labels=["critical", "automated"],
                            ))
                    else:
                        self._log.info("subsystem_restarting", subsystem=name)
                        self._subsystem_tasks[name] = asyncio.create_task(self._get_subsystem_coro(name))

    def _launch_subsystems(self) -> None:
        self._subsystem_tasks["dispatch"] = asyncio.create_task(self._dispatch_loop())
        self._subsystem_tasks["scheduler"] = asyncio.create_task(self._scheduler.start())
        self._subsystem_tasks["health_monitor"] = asyncio.create_task(self._health_monitor.start())

    def _get_subsystem_coro(self, name: str) -> Any:
        return {"dispatch": self._dispatch_loop, "scheduler": self._scheduler.start, "health_monitor": self._health_monitor.start}[name]()

    def _record_crash(self, name: str) -> None:
        self._crash_history[name].append(datetime.now(timezone.utc))

    def _is_crash_loop(self, name: str) -> bool:
        now = datetime.now(timezone.utc)
        return sum(1 for t in self._crash_history[name] if (now - t).total_seconds() < 300) >= self.settings.watchdog_max_crashes

    # --- Task dispatch ---

    async def submit_task(self, agent_name: str, action: str, payload: dict[str, Any] | None = None, priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        task = Task(priority=priority, agent_name=agent_name, action=action, payload=payload or {}, max_retries=self.settings.agent_retry_count)
        task_id = await self._task_queue.enqueue(task)
        self._log.info("task_submitted", task_id=task_id, agent=agent_name, action=action)
        return task_id

    async def _dispatch_loop(self) -> None:
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

                # Auto-create GitHub issue for high-priority tasks
                if self._github and task.priority <= TaskPriority.HIGH:
                    await self._github.create_agent_task_issue(agent_name=agent.name, task_action=task.action, result=result)

                # Auto-sync completed tasks to Notion
                if self._notion and task.priority <= TaskPriority.HIGH:
                    try:
                        await self._notion.sync_agent_result(agent_name=agent.name, action=task.action, result=result)
                    except Exception as e:
                        self._log.warning("notion_sync_failed", error=str(e))

            except Exception as e:
                self._log.error("task_dispatch_failed", task_id=task.id, error=str(e))
                self._task_queue.fail(task, str(e))
                self._health_monitor.record_task(success=False)
                if task.status == TaskStatus.RETRYING:
                    await self._task_queue.enqueue(task)

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

    async def _scheduled_security_scan(self) -> None:
        await self.submit_task("CIPHER", "owasp_scan", priority=TaskPriority.HIGH)

    async def _scheduled_drive_import(self) -> None:
        if self._gdrive:
            await self.drive_import_folder()

    async def _scheduled_notion_sync(self) -> None:
        if self._notion:
            await self.notion_sync_audit()

    # --- Coordination: Notion ---

    async def notion_create_page(self, title: str, content: str = "") -> dict[str, Any]:
        if not self._notion:
            return {"error": "Notion not configured"}
        return await self._notion.create_page(title=title, content=content)

    async def notion_query_pages(self, filter_obj: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._notion:
            return {"error": "Notion not configured"}
        return await self._notion.query_data_source(filter_obj)

    async def notion_review_page(self, page_id: str) -> dict[str, Any]:
        if not self._notion:
            return {"error": "Notion not configured"}
        page = await self._notion.get_page_content(page_id)
        texts = []
        for block in page.get("blocks", []):
            if block.get("type") == "paragraph":
                for rt in block.get("paragraph", {}).get("rich_text", []):
                    texts.append(rt.get("text", {}).get("content", ""))
        text = " ".join(texts)
        classification = {}
        if text and "MARTIN" in self._agents:
            task = Task(priority=TaskPriority.MEDIUM, agent_name="MARTIN", action="classify_document", payload={"text_content": text, "filename": page_id})
            classification = await self._agents["MARTIN"].run_task(task)
        return {"page": page, "classification": classification}

    async def notion_sync_audit(self) -> dict[str, Any]:
        if not self._notion:
            return {"error": "Notion not configured"}
        task = Task(priority=TaskPriority.MEDIUM, agent_name="MARTIN", action="run_document_audit", payload={})
        audit = await self._agents["MARTIN"].run_task(task)
        notion = await self._notion.sync_document_audit(audit)
        return {"audit": audit, "notion": notion}

    # --- Coordination: Google Drive ---

    async def drive_import_folder(self, folder_id: str = "") -> dict[str, Any]:
        if not self._gdrive:
            return {"error": "Google Drive not configured"}
        result = await self._gdrive.import_folder(folder_id=folder_id)
        classifications = []
        for f in result.get("files", []):
            task = Task(priority=TaskPriority.LOW, agent_name="MARTIN", action="classify_document", payload={"text_content": "", "filename": f["name"]})
            cls = await self._agents["MARTIN"].run_task(task)
            classifications.append({"file": f["name"], "classification": cls})
        return {"import": result, "classifications": classifications}

    # --- Coordination: Wispr ---

    async def process_wispr_note(self, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._wispr:
            return {"error": "Wispr not configured"}
        note = self._wispr.process_note(text, metadata)
        target = note.get("target_agent", "MARTIN")
        task_id = await self.submit_task(agent_name=target, action="classify_document", payload={"text_content": text, "source": "wispr_flow"}, priority=TaskPriority.MEDIUM)
        if self._notion:
            await self._notion.create_page(title=f"Voice Note — {note.get('timestamp', '')}", content=f"Source: Wispr Flow\nAgent: {target}\n\n{text}")
        return {"note": note, "task_id": task_id}

    # --- Coordination: GitHub ---

    async def github_scan_security(self) -> dict[str, Any]:
        if not self._github:
            return {"error": "GitHub not configured"}
        return await self._github.get_security_summary()

    async def github_list_prs(self, state: str = "open") -> dict[str, Any]:
        if not self._github:
            return {"error": "GitHub not configured"}
        return await self._github.list_pull_requests(state=state)

    # --- Coordination: Paperclip ---

    async def paperclip_execute_ticket(self, ticket_id: str) -> None:
        """After Board approval, start the ticket, dispatch work, then complete it."""
        if not self._paperclip:
            return
        ticket = self._paperclip._find_ticket(ticket_id)
        if not ticket or ticket["status"] != "approved":
            return
        await self._paperclip.start_ticket(ticket_id)
        agent_name = ticket["owner"]
        agent = self._agents.get(agent_name)
        if agent:
            actions = list(agent.handlers.keys()) if hasattr(agent, "handlers") else []
            action = actions[0] if actions else "classify_document"
            try:
                task_id = await self.submit_task(agent_name, action, payload={"ticket_id": ticket_id, "title": ticket["title"]}, priority=TaskPriority.MEDIUM)
                self._log.info("paperclip_ticket_dispatched", ticket_id=ticket_id, agent=agent_name, task_id=task_id)
            except Exception as e:
                self._log.error("paperclip_dispatch_failed", ticket_id=ticket_id, error=str(e))
        await self._paperclip.complete_ticket(ticket_id)

    # --- Coordination: GHOST OSINT ---

    async def ghost_verify_borrower(self, name: str, email: str = "", phone: str = "", employer: str = "") -> dict[str, Any]:
        if not self._ghost:
            return {"error": "GHOST OSINT not configured"}
        return await self._ghost.verify_borrower(name, email, phone, employer)

    async def ghost_search_entities(self, query: str, entity_type: str = "") -> dict[str, Any]:
        if not self._ghost:
            return {"error": "GHOST OSINT not configured"}
        return await self._ghost.search_entities(query, entity_type)

    async def ghost_create_investigation(self, title: str, description: str = "") -> dict[str, Any]:
        if not self._ghost:
            return {"error": "GHOST OSINT not configured"}
        return await self._ghost.create_investigation(title, description)

    # --- Coordination: PentAGI ---

    async def pentagi_run_assessment(self, target: str = "self") -> dict[str, Any]:
        if not self._pentagi:
            return {"error": "PentAGI not configured"}
        return await self._pentagi.run_security_assessment(target)

    async def pentagi_list_vulnerabilities(self, severity: str = "") -> dict[str, Any]:
        if not self._pentagi:
            return {"error": "PentAGI not configured"}
        return await self._pentagi.list_vulnerabilities(severity)

    # --- Status ---

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
            "integrations": {
                "github": bool(self._github),
                "notion": bool(self._notion),
                "gdrive": bool(self._gdrive),
                "wispr": bool(self._wispr),
                "llm": self._llm.get_status() if self._llm else None,
                "paperclip": self._paperclip.get_status() if self._paperclip else None,
                "ghost_osint": self._ghost.get_status() if self._ghost else None,
                "pentagi": self._pentagi.get_status() if self._pentagi else None,
            },
        }

    def get_health(self) -> dict[str, Any]:
        return self._health_monitor.get_full_health()

    def list_agents(self) -> list[dict[str, Any]]:
        return [agent.get_info() for agent in self._agents.values()]
