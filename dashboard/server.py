"""Dashboard web server for MortgageFintechOS.

Serves a professional web UI and JSON API endpoints for monitoring
the autonomous AI operating system in real time. Includes endpoints
for Notion, Google Drive, Wispr Flow, and GitHub code operations.
"""

import json
from datetime import datetime
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
    """HTTP server providing dashboard UI and status API."""

    def __init__(self, orchestrator: "Orchestrator", host: str = "0.0.0.0", port: int = 8080):
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._log = logger.bind(component="dashboard")
        self._setup_routes()

    def _setup_routes(self) -> None:
        # Core
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/healthz", self._handle_healthz)
        self._app.router.add_get("/api/status", self._handle_status)
        self._app.router.add_get("/api/health", self._handle_health)
        self._app.router.add_get("/api/agents", self._handle_agents)
        self._app.router.add_get("/api/queue", self._handle_queue)
        self._app.router.add_get("/api/schedule", self._handle_schedule)
        self._app.router.add_get("/api/alerts", self._handle_alerts)

        # Notion
        self._app.router.add_get("/api/notion/status", self._handle_notion_status)
        self._app.router.add_get("/api/notion/pages", self._handle_notion_query)
        self._app.router.add_post("/api/notion/pages", self._handle_notion_create)
        self._app.router.add_get("/api/notion/pages/{page_id}", self._handle_notion_review)
        self._app.router.add_post("/api/notion/sync-audit", self._handle_notion_sync_audit)

        # Google Drive
        self._app.router.add_get("/api/drive/files", self._handle_drive_list)
        self._app.router.add_post("/api/drive/import", self._handle_drive_import)

        # Wispr Flow
        self._app.router.add_post("/api/wispr/webhook", self._handle_wispr_webhook)
        self._app.router.add_get("/api/wispr/status", self._handle_wispr_status)

        # GitHub Code Ops
        self._app.router.add_get("/api/github/repo", self._handle_github_repo)
        self._app.router.add_get("/api/github/prs", self._handle_github_prs)
        self._app.router.add_get("/api/github/security", self._handle_github_security)
        self._app.router.add_post("/api/github/security/scan", self._handle_github_scan)
        self._app.router.add_get("/api/github/actions", self._handle_github_actions)
        self._app.router.add_get("/api/github/commits", self._handle_github_commits)
        self._app.router.add_get("/api/github/branches", self._handle_github_branches)

        # Static files
        self._app.router.add_static("/static", STATIC_DIR, show_index=False)

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

    # --- Core handlers ---

    async def _handle_healthz(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _handle_index(self, request: web.Request) -> web.Response:
        return web.FileResponse(STATIC_DIR / "index.html")

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator.get_status(), dumps=_json_dumps)

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator.get_health(), dumps=_json_dumps)

    async def _handle_agents(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator.list_agents(), dumps=_json_dumps)

    async def _handle_queue(self, request: web.Request) -> web.Response:
        data = self.orchestrator._task_queue.get_stats()
        history = [{
            "id": t.id, "agent": t.agent_name, "action": t.action,
            "status": t.status.value, "priority": t.priority.name,
            "created_at": t.created_at.isoformat(),
        } for t in self.orchestrator._task_queue.history[-50:]]
        data["recent_tasks"] = history
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_schedule(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._scheduler.list_jobs(), dumps=_json_dumps)

    async def _handle_alerts(self, request: web.Request) -> web.Response:
        alerts = [a.to_dict() for a in list(self.orchestrator._health_monitor._alerts)[-50:]]
        return web.json_response(alerts, dumps=_json_dumps)

    # --- Notion handlers ---

    async def _handle_notion_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "configured": self.orchestrator._notion is not None,
            "data_source_id": self.orchestrator.settings.notion_data_source_id or None,
            "database_id": self.orchestrator.settings.notion_database_id or None,
            "api_version": "2025-09-03",
        })

    async def _handle_notion_query(self, request: web.Request) -> web.Response:
        filter_str = request.query.get("filter")
        filter_obj = json.loads(filter_str) if filter_str else None
        data = await self.orchestrator.notion_query_pages(filter_obj)
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_notion_create(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.orchestrator.notion_create_page(title=body.get("title", "Untitled"), content=body.get("content", ""))
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_notion_review(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.notion_review_page(request.match_info["page_id"])
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_notion_sync_audit(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.notion_sync_audit()
        return web.json_response(data, dumps=_json_dumps)

    # --- Google Drive handlers ---

    async def _handle_drive_list(self, request: web.Request) -> web.Response:
        if not self.orchestrator._gdrive:
            return web.json_response({"error": "Google Drive not configured"}, status=503)
        data = await self.orchestrator._gdrive.list_files(folder_id=request.query.get("folder_id", ""))
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_drive_import(self, request: web.Request) -> web.Response:
        body = await request.json() if request.content_length else {}
        data = await self.orchestrator.drive_import_folder(folder_id=body.get("folder_id", ""))
        return web.json_response(data, dumps=_json_dumps)

    # --- Wispr Flow handlers ---

    async def _handle_wispr_webhook(self, request: web.Request) -> web.Response:
        body_bytes = await request.read()
        if self.orchestrator._wispr and not self.orchestrator._wispr.validate_webhook(dict(request.headers), body_bytes):
            return web.json_response({"error": "Invalid signature"}, status=401)
        try:
            body = json.loads(body_bytes)
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        text = body.get("text", body.get("transcription", ""))
        data = await self.orchestrator.process_wispr_note(text, body.get("metadata", {}))
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_wispr_status(self, request: web.Request) -> web.Response:
        if self.orchestrator._wispr:
            return web.json_response(self.orchestrator._wispr.get_status())
        return web.json_response({"configured": False})

    # --- GitHub Code Ops handlers ---

    async def _handle_github_repo(self, request: web.Request) -> web.Response:
        if not self.orchestrator._github:
            return web.json_response({"error": "GitHub not configured"}, status=503)
        return web.json_response(await self.orchestrator._github.get_repo_info(), dumps=_json_dumps)

    async def _handle_github_prs(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.github_list_prs(state=request.query.get("state", "open"))
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_github_security(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.github_scan_security()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_github_scan(self, request: web.Request) -> web.Response:
        from core.task_queue import TaskPriority
        task_id = await self.orchestrator.submit_task("CIPHER", "owasp_scan", priority=TaskPriority.HIGH)
        return web.json_response({"task_id": task_id, "status": "scan_queued"})

    async def _handle_github_actions(self, request: web.Request) -> web.Response:
        if not self.orchestrator._github:
            return web.json_response({"error": "GitHub not configured"}, status=503)
        return web.json_response(await self.orchestrator._github.list_workflow_runs(), dumps=_json_dumps)

    async def _handle_github_commits(self, request: web.Request) -> web.Response:
        if not self.orchestrator._github:
            return web.json_response({"error": "GitHub not configured"}, status=503)
        return web.json_response(await self.orchestrator._github.list_commits(), dumps=_json_dumps)

    async def _handle_github_branches(self, request: web.Request) -> web.Response:
        if not self.orchestrator._github:
            return web.json_response({"error": "GitHub not configured"}, status=503)
        return web.json_response(await self.orchestrator._github.list_branches(), dumps=_json_dumps)


def _json_dumps(obj: Any) -> str:
    """JSON serializer that handles datetime and bytes objects."""
    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return f"<{len(o)} bytes>"
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, default=default)
