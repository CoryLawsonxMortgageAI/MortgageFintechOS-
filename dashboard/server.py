"""Dashboard web server for MortgageFintechOS.

Serves a professional web UI, JSON API endpoints, Agno-compatible Agent UI API,
GitHub webhooks receiver, and real-time monitoring for the autonomous AI
operating system with AIOS Kernel and 9 AI agents.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from aiohttp import web

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator

logger = structlog.get_logger()

STATIC_DIR = Path(__file__).parent / "static"


class DashboardServer:
    """HTTP server providing dashboard UI, monitoring API, Agent UI, and webhooks."""

    def __init__(self, orchestrator: "Orchestrator", host: str = "0.0.0.0", port: int = 8080):
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._log = logger.bind(component="dashboard")
        self._setup_routes()
        self._setup_integrations()

    def _setup_routes(self) -> None:
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/healthz", self._handle_healthz)
        self._app.router.add_get("/api/status", self._handle_status)
        self._app.router.add_get("/api/health", self._handle_health)
        self._app.router.add_get("/api/agents", self._handle_agents)
        self._app.router.add_get("/api/queue", self._handle_queue)
        self._app.router.add_get("/api/schedule", self._handle_schedule)
        self._app.router.add_get("/api/alerts", self._handle_alerts)
        self._app.router.add_get("/api/kernel", self._handle_kernel)
        self._app.router.add_get("/api/references", self._handle_references)
        self._app.router.add_get("/api/references/search/{keyword}", self._handle_reference_search)
        self._app.router.add_get("/api/references/{name}", self._handle_reference_detail)
        self._app.router.add_post("/api/references/{name}", self._handle_reference_save)
        self._app.router.add_static("/static", STATIC_DIR, show_index=False)

    def _setup_integrations(self) -> None:
        """Register webhook, Agent UI API, Telegram bot, and Twitter routes."""
        from integrations.webhooks import WebhookReceiver
        from integrations.agent_ui_api import AgentUIAPI
        from integrations.telegram_bot import TelegramBot
        from integrations.twitter_client import TwitterClient

        settings = self.orchestrator.settings

        webhook_secret = settings.webhook_secret if hasattr(settings, 'webhook_secret') else ""
        self._webhook_receiver = WebhookReceiver(self.orchestrator, secret=webhook_secret)
        self._webhook_receiver.register_routes(self._app)

        self._agent_ui = AgentUIAPI(self.orchestrator)
        self._agent_ui.register_routes(self._app)

        # Telegram bot
        self._telegram_bot = None
        if settings.telegram_bot_token:
            self._telegram_bot = TelegramBot(
                orchestrator=self.orchestrator,
                token=settings.telegram_bot_token,
                webhook_secret=settings.telegram_webhook_secret,
            )
            self._telegram_bot.register_routes(self._app)
            self._log.info("telegram_bot_enabled")

        # Twitter client (stored on orchestrator for agent access)
        self._twitter_client = TwitterClient(
            api_key=settings.x_api_key,
            api_secret=settings.x_api_secret,
            access_token=settings.x_access_token,
            access_secret=settings.x_access_secret,
        )
        if self._twitter_client.available:
            self._log.info("twitter_integration_enabled")

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        self._log.info("dashboard_started", host=self.host, port=self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
        self._log.info("dashboard_stopped")

    # --- Route handlers ---

    async def _handle_healthz(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _handle_index(self, request: web.Request) -> web.Response:
        index_path = STATIC_DIR / "index.html"
        return web.FileResponse(index_path)

    async def _handle_status(self, request: web.Request) -> web.Response:
        data = self.orchestrator.get_status()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_health(self, request: web.Request) -> web.Response:
        data = self.orchestrator.get_health()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_agents(self, request: web.Request) -> web.Response:
        data = self.orchestrator.list_agents()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_queue(self, request: web.Request) -> web.Response:
        data = self.orchestrator._task_queue.get_stats()
        history = []
        for task in self.orchestrator._task_queue.history[-50:]:
            history.append({
                "id": task.id,
                "agent": task.agent_name,
                "action": task.action,
                "status": task.status.value,
                "priority": task.priority.name,
                "created_at": task.created_at.isoformat(),
            })
        data["recent_tasks"] = history
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_schedule(self, request: web.Request) -> web.Response:
        data = self.orchestrator._scheduler.list_jobs()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_alerts(self, request: web.Request) -> web.Response:
        alerts = [a.to_dict() for a in list(self.orchestrator._health_monitor._alerts)[-50:]]
        return web.json_response(alerts, dumps=_json_dumps)

    async def _handle_kernel(self, request: web.Request) -> web.Response:
        data = self.orchestrator._kernel.get_kernel_status()
        return web.json_response(data, dumps=_json_dumps)

    # --- Reference store endpoints ---

    async def _handle_references(self, request: web.Request) -> web.Response:
        if hasattr(self.orchestrator, '_reference_store'):
            data = self.orchestrator._reference_store.list_files()
        else:
            data = []
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_reference_detail(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        if not hasattr(self.orchestrator, '_reference_store'):
            return web.json_response({"error": "Reference store not available"}, status=404)
        ref = self.orchestrator._reference_store.get(name)
        if not ref:
            return web.json_response({"error": f"Reference '{name}' not found"}, status=404)
        data = ref.to_dict()
        data["content"] = ref.raw_content
        data["sections_content"] = ref.sections
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_reference_save(self, request: web.Request) -> web.Response:
        name = request.match_info["name"]
        if not hasattr(self.orchestrator, '_reference_store'):
            return web.json_response({"error": "Reference store not available"}, status=404)
        body = await request.json()
        content = body.get("content", "")
        if not content:
            return web.json_response({"error": "Content is required"}, status=400)
        result = self.orchestrator._reference_store.save_file(name, content)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_reference_search(self, request: web.Request) -> web.Response:
        keyword = request.match_info["keyword"]
        if not hasattr(self.orchestrator, '_reference_store'):
            return web.json_response([], dumps=_json_dumps)
        results = self.orchestrator._reference_store.search(keyword)
        return web.json_response(results, dumps=_json_dumps)


def _json_dumps(obj: Any) -> str:
    """JSON serializer that handles datetime objects."""
    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, default=default)
