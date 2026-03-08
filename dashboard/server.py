"""Dashboard web server for MortgageFintechOS.

Serves a professional web UI and JSON API endpoints for monitoring
the autonomous AI operating system in real time. Includes endpoints
for Notion, Google Drive, Wispr Flow, and GitHub code operations.
"""

import asyncio
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
        self._app.router.add_post("/api/tasks/submit", self._handle_task_submit)
        self._app.router.add_get("/api/tasks/{task_id}", self._handle_task_detail)
        self._app.router.add_get("/api/tasks/results/feed", self._handle_results_feed)

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

        # Paperclip AI — Enterprise Orchestration
        self._app.router.add_get("/api/paperclip/health", self._handle_clip_health)
        self._app.router.add_get("/api/paperclip/status", self._handle_clip_status)
        self._app.router.add_get("/api/paperclip/tickets", self._handle_clip_tickets)
        self._app.router.add_post("/api/paperclip/tickets", self._handle_clip_create_ticket)
        self._app.router.add_post("/api/paperclip/tickets/{ticket_id}/approve", self._handle_clip_approve)
        self._app.router.add_post("/api/paperclip/tickets/{ticket_id}/reject", self._handle_clip_reject)
        self._app.router.add_post("/api/paperclip/tickets/{ticket_id}/start", self._handle_clip_start)
        self._app.router.add_post("/api/paperclip/tickets/{ticket_id}/complete", self._handle_clip_complete)
        self._app.router.add_get("/api/paperclip/budgets", self._handle_clip_budgets)
        self._app.router.add_post("/api/paperclip/budgets/{agent}/set", self._handle_clip_set_budget)
        self._app.router.add_post("/api/paperclip/budgets/{agent}/reset", self._handle_clip_reset_budget)
        self._app.router.add_get("/api/paperclip/audit", self._handle_clip_audit)

        # GHOST OSINT
        self._app.router.add_get("/api/ghost/status", self._handle_ghost_status)
        self._app.router.add_post("/api/ghost/verify", self._handle_ghost_verify)
        self._app.router.add_get("/api/ghost/search", self._handle_ghost_search)
        self._app.router.add_post("/api/ghost/investigations", self._handle_ghost_investigation)

        # PentAGI
        self._app.router.add_get("/api/pentagi/status", self._handle_pentagi_status)
        self._app.router.add_post("/api/pentagi/assess", self._handle_pentagi_assess)
        self._app.router.add_get("/api/pentagi/vulnerabilities", self._handle_pentagi_vulns)

        # Growth Ops — Autonomous 24/7 Agent System
        self._app.router.add_get("/api/growth/status", self._handle_growth_status)
        self._app.router.add_post("/api/growth/sweep", self._handle_growth_sweep)
        self._app.router.add_post("/api/growth/hunter/scan", self._handle_hunter_scan)
        self._app.router.add_get("/api/growth/hunter/leads", self._handle_hunter_leads)
        self._app.router.add_post("/api/growth/herald/generate", self._handle_herald_generate)
        self._app.router.add_get("/api/growth/herald/queue", self._handle_herald_queue)
        self._app.router.add_post("/api/growth/ambassador/engage", self._handle_ambassador_engage)
        self._app.router.add_get("/api/growth/ambassador/stats", self._handle_ambassador_stats)

        # Safety Audit
        self._app.router.add_get("/api/safety/blocked", self._handle_safety_blocked)

        # Agent Action Log
        self._app.router.add_get("/api/action-log", self._handle_action_log)
        self._app.router.add_get("/api/action-log/stats", self._handle_action_log_stats)
        self._app.router.add_get("/api/action-log/timeline", self._handle_action_log_timeline)

        # Schedule Management
        self._app.router.add_post("/api/schedule/{job_name}/update", self._handle_schedule_update)
        self._app.router.add_post("/api/schedule/{job_name}/toggle", self._handle_schedule_toggle)

        # Hydrospeed Ontology
        self._app.router.add_get("/api/hydrospeed/ontology", self._handle_ontology)
        self._app.router.add_get("/api/hydrospeed/agent/{agent_name}", self._handle_ontology_agent)
        self._app.router.add_get("/api/hydrospeed/tips", self._handle_tips)
        self._app.router.add_get("/api/hydrospeed/divisions", self._handle_divisions)
        self._app.router.add_get("/api/hydrospeed/data-flows", self._handle_data_flows)
        self._app.router.add_get("/api/hydrospeed/schedule-recommendations", self._handle_schedule_recommendations)
        self._app.router.add_post("/api/hydrospeed/proposals", self._handle_create_proposal)
        self._app.router.add_get("/api/hydrospeed/proposals", self._handle_list_proposals)

        # Ontology-Telemetry Sync (enriched ontology with live health data)
        self._app.router.add_get("/api/ontology-telemetry-sync", self._handle_ontology_telemetry_sync)

        # Predictive Telemetry
        self._app.router.add_get("/api/telemetry/risks", self._handle_telemetry_risks)
        self._app.router.add_get("/api/telemetry/risks/{agent_name}", self._handle_telemetry_agent_risk)
        self._app.router.add_get("/api/telemetry/predictions", self._handle_telemetry_predictions)
        self._app.router.add_get("/api/telemetry/cascade/{agent_name}", self._handle_telemetry_cascade)
        self._app.router.add_get("/api/telemetry/context", self._handle_telemetry_context)

        # Features Guide
        self._app.router.add_get("/api/features", self._handle_features_guide)

        # Agent Database (Dolt-style version control)
        self._app.router.add_get("/api/agentdb/schema", self._handle_agentdb_schema)
        self._app.router.add_get("/api/agentdb/schema/sql", self._handle_agentdb_schema_sql)
        self._app.router.add_get("/api/agentdb/branches", self._handle_agentdb_branches)
        self._app.router.add_post("/api/agentdb/branches", self._handle_agentdb_create_branch)
        self._app.router.add_delete("/api/agentdb/branches/{branch}", self._handle_agentdb_delete_branch)
        self._app.router.add_get("/api/agentdb/tables", self._handle_agentdb_tables)
        self._app.router.add_get("/api/agentdb/query/{table}", self._handle_agentdb_query)
        self._app.router.add_post("/api/agentdb/insert/{table}", self._handle_agentdb_insert)
        self._app.router.add_post("/api/agentdb/update/{table}/{row_id}", self._handle_agentdb_update)
        self._app.router.add_get("/api/agentdb/diff", self._handle_agentdb_diff)
        self._app.router.add_post("/api/agentdb/merge", self._handle_agentdb_merge)
        self._app.router.add_post("/api/agentdb/reset", self._handle_agentdb_reset)
        self._app.router.add_get("/api/agentdb/log/{branch}", self._handle_agentdb_log)
        self._app.router.add_get("/api/agentdb/agent/{agent_name}", self._handle_agentdb_agent_status)

        # Agent Skills
        self._app.router.add_get("/api/agents/skills", self._handle_agent_skills)

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
        include_results = request.query.get("results", "0") == "1"
        history = [{
            "id": t.id, "agent": t.agent_name, "action": t.action,
            "status": t.status.value, "priority": t.priority.name,
            "created_at": t.created_at.isoformat(),
            **({"result": t.result, "error": t.error} if include_results else {}),
        } for t in self.orchestrator._task_queue.history[-50:]]
        data["recent_tasks"] = history
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_schedule(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._scheduler.list_jobs(), dumps=_json_dumps)

    async def _handle_alerts(self, request: web.Request) -> web.Response:
        alerts = [a.to_dict() for a in list(self.orchestrator._health_monitor._alerts)[-50:]]
        return web.json_response(alerts, dumps=_json_dumps)

    # --- Task submission & results ---

    async def _handle_task_submit(self, request: web.Request) -> web.Response:
        """Submit a task to an agent and return immediately with task_id for polling."""
        body = await request.json()
        agent_name = body.get("agent", "")
        action = body.get("action", "")
        payload = body.get("payload", {})
        priority_str = body.get("priority", "MEDIUM").upper()
        from core.task_queue import TaskPriority
        priority_map = {"CRITICAL": TaskPriority.CRITICAL, "HIGH": TaskPriority.HIGH, "MEDIUM": TaskPriority.MEDIUM, "LOW": TaskPriority.LOW}
        priority = priority_map.get(priority_str, TaskPriority.MEDIUM)
        if not agent_name or not action:
            return web.json_response({"error": "agent and action are required"}, status=400)
        if agent_name not in self.orchestrator._agents:
            return web.json_response({"error": f"Agent {agent_name} not found"}, status=404)
        task_id = await self.orchestrator.submit_task(agent_name, action, payload=payload, priority=priority)
        return web.json_response({"task_id": task_id, "agent": agent_name, "action": action, "status": "queued"})

    async def _handle_task_detail(self, request: web.Request) -> web.Response:
        """Get full details of a specific task including its result."""
        task_id = request.match_info["task_id"]
        for t in self.orchestrator._task_queue.history:
            if t.id == task_id:
                return web.json_response({
                    "id": t.id, "agent": t.agent_name, "action": t.action,
                    "status": t.status.value, "priority": t.priority.name,
                    "created_at": t.created_at.isoformat(),
                    "result": t.result, "error": t.error,
                    "retries": t.retries,
                }, dumps=_json_dumps)
        # Check if task is still in the queue (pending/running)
        return web.json_response({"id": task_id, "status": "pending", "result": None})

    async def _handle_results_feed(self, request: web.Request) -> web.Response:
        """Return recent completed task results with full data for the Results Feed."""
        limit = int(request.query.get("limit", "25"))
        agent_filter = request.query.get("agent")
        from core.task_queue import TaskStatus
        results = []
        for t in reversed(self.orchestrator._task_queue.history):
            if len(results) >= limit:
                break
            if t.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                continue
            if agent_filter and t.agent_name != agent_filter:
                continue
            results.append({
                "id": t.id, "agent": t.agent_name, "action": t.action,
                "status": t.status.value, "priority": t.priority.name,
                "created_at": t.created_at.isoformat(),
                "result": t.result, "error": t.error,
            })
        return web.json_response({"results": results, "total": len(results)}, dumps=_json_dumps)

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

    # --- Paperclip AI handlers ---

    async def _handle_clip_health(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        return web.json_response({"status": "ok", "service": "paperclip-ai", "version": "1.0.0"})

    async def _handle_clip_status(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        return web.json_response(self.orchestrator._paperclip.get_status(), dumps=_json_dumps)

    async def _handle_clip_tickets(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        status = request.query.get("status")
        limit = int(request.query.get("limit", "50"))
        tickets = self.orchestrator._paperclip.list_tickets(status=status, limit=limit)
        return web.json_response({"tickets": tickets}, dumps=_json_dumps)

    async def _handle_clip_create_ticket(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        body = await request.json()
        owner = body.get("owner", "")
        title = body.get("title", "")
        cost = int(body.get("estimated_cost", 0))
        if not owner or not title:
            return web.json_response({"error": "owner and title are required"}, status=400)
        ticket = await self.orchestrator._paperclip.create_ticket(owner=owner, title=title, estimated_cost=cost)
        return web.json_response(ticket, dumps=_json_dumps)

    async def _handle_clip_approve(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        ticket_id = request.match_info["ticket_id"]
        result = await self.orchestrator._paperclip.approve_ticket(ticket_id)
        if "error" in result:
            return web.json_response(result, status=404)
        # Auto-dispatch to agent after approval
        asyncio.create_task(self.orchestrator.paperclip_execute_ticket(ticket_id))
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_reject(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        ticket_id = request.match_info["ticket_id"]
        result = await self.orchestrator._paperclip.reject_ticket(ticket_id)
        if "error" in result:
            return web.json_response(result, status=404)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_start(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        result = await self.orchestrator._paperclip.start_ticket(request.match_info["ticket_id"])
        if "error" in result:
            return web.json_response(result, status=404)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_complete(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        result = await self.orchestrator._paperclip.complete_ticket(request.match_info["ticket_id"])
        if "error" in result:
            return web.json_response(result, status=404)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_budgets(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        return web.json_response(self.orchestrator._paperclip.get_budgets(), dumps=_json_dumps)

    async def _handle_clip_set_budget(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        body = await request.json()
        result = await self.orchestrator._paperclip.set_budget(request.match_info["agent"], int(body.get("budget", 0)))
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_reset_budget(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        result = await self.orchestrator._paperclip.reset_budget(request.match_info["agent"])
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_clip_audit(self, request: web.Request) -> web.Response:
        if not self.orchestrator._paperclip:
            return web.json_response({"error": "Paperclip not initialized"}, status=503)
        limit = int(request.query.get("limit", "50"))
        return web.json_response({"audit": self.orchestrator._paperclip.get_audit_log(limit)}, dumps=_json_dumps)


    # --- GHOST OSINT handlers ---

    async def _handle_ghost_status(self, request: web.Request) -> web.Response:
        if not self.orchestrator._ghost:
            return web.json_response({"configured": False, "error": "GHOST OSINT not configured"})
        return web.json_response(self.orchestrator._ghost.get_status())

    async def _handle_ghost_verify(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.orchestrator.ghost_verify_borrower(
            name=body.get("name", ""), email=body.get("email", ""),
            phone=body.get("phone", ""), employer=body.get("employer", ""),
        )
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_ghost_search(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.ghost_search_entities(
            query=request.query.get("q", ""), entity_type=request.query.get("type", ""),
        )
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_ghost_investigation(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.orchestrator.ghost_create_investigation(
            title=body.get("title", ""), description=body.get("description", ""),
        )
        return web.json_response(data, dumps=_json_dumps)

    # --- PentAGI handlers ---

    async def _handle_pentagi_status(self, request: web.Request) -> web.Response:
        if not self.orchestrator._pentagi:
            return web.json_response({"configured": False, "error": "PentAGI not configured"})
        return web.json_response(self.orchestrator._pentagi.get_status())

    async def _handle_pentagi_assess(self, request: web.Request) -> web.Response:
        body = await request.json() if request.content_length else {}
        data = await self.orchestrator.pentagi_run_assessment(target=body.get("target", "self"))
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_pentagi_vulns(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.pentagi_list_vulnerabilities(severity=request.query.get("severity", ""))
        return web.json_response(data, dumps=_json_dumps)


    # --- Safety Audit handlers ---

    async def _handle_safety_blocked(self, request: web.Request) -> web.Response:
        """Return audit log of all blocked deletion attempts."""
        if not self.orchestrator._github:
            return web.json_response({"blocked_attempts": [], "note": "GitHub not configured"})
        attempts = self.orchestrator._github.get_blocked_attempts()
        return web.json_response({
            "blocked_attempts": attempts,
            "total": len(attempts),
            "guardrail": "AI agents can NEVER delete repository content",
        }, dumps=_json_dumps)

    # --- Growth Ops handlers ---

    async def _handle_growth_status(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.growth_ops_status()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_growth_sweep(self, request: web.Request) -> web.Response:
        data = await self.orchestrator.growth_ops_sweep()
        return web.json_response(data, dumps=_json_dumps)

    async def _handle_hunter_scan(self, request: web.Request) -> web.Response:
        body = await request.json() if request.content_length else {}
        source = body.get("source", "all")
        action = {"github": "scan_github", "hn": "scan_hn", "reddit": "scan_reddit"}.get(source, "full_sweep")
        from core.task_queue import TaskPriority
        task_id = await self.orchestrator.submit_task("HUNTER", action, payload=body, priority=TaskPriority.LOW)
        return web.json_response({"task_id": task_id, "action": action})

    async def _handle_hunter_leads(self, request: web.Request) -> web.Response:
        agent = self.orchestrator._agents.get("HUNTER")
        if not agent:
            return web.json_response({"error": "HUNTER agent not registered"}, status=503)
        from core.task_queue import Task, TaskPriority
        task = Task(priority=TaskPriority.LOW, agent_name="HUNTER", action="score_leads", payload={})
        result = await agent.execute(task)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_herald_generate(self, request: web.Request) -> web.Response:
        body = await request.json() if request.content_length else {}
        action = body.get("action", "daily_content")
        from core.task_queue import TaskPriority
        task_id = await self.orchestrator.submit_task("HERALD", action, payload=body, priority=TaskPriority.LOW)
        return web.json_response({"task_id": task_id, "action": action})

    async def _handle_herald_queue(self, request: web.Request) -> web.Response:
        agent = self.orchestrator._agents.get("HERALD")
        if not agent:
            return web.json_response({"error": "HERALD agent not registered"}, status=503)
        from core.task_queue import Task, TaskPriority
        task = Task(priority=TaskPriority.LOW, agent_name="HERALD", action="get_content_queue", payload={})
        result = await agent.execute(task)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_ambassador_engage(self, request: web.Request) -> web.Response:
        body = await request.json() if request.content_length else {}
        from core.task_queue import TaskPriority
        task_id = await self.orchestrator.submit_task("AMBASSADOR", "daily_engagement", payload=body, priority=TaskPriority.LOW)
        return web.json_response({"task_id": task_id, "action": "daily_engagement"})

    async def _handle_ambassador_stats(self, request: web.Request) -> web.Response:
        agent = self.orchestrator._agents.get("AMBASSADOR")
        if not agent:
            return web.json_response({"error": "AMBASSADOR agent not registered"}, status=503)
        from core.task_queue import Task, TaskPriority
        task = Task(priority=TaskPriority.LOW, agent_name="AMBASSADOR", action="get_engagement_stats", payload={})
        result = await agent.execute(task)
        return web.json_response(result, dumps=_json_dumps)


    # --- Agent Action Log handlers ---

    async def _handle_action_log(self, request: web.Request) -> web.Response:
        agent = request.query.get("agent", "")
        action_type = request.query.get("type", "")
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        failures = request.query.get("failures", "") == "1"
        entries = self.orchestrator._action_log.query(
            agent=agent, action_type=action_type, limit=limit, offset=offset,
            failures_only=failures,
        )
        return web.json_response({"entries": entries, "count": len(entries)}, dumps=_json_dumps)

    async def _handle_action_log_stats(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._action_log.get_stats(), dumps=_json_dumps)

    async def _handle_action_log_timeline(self, request: web.Request) -> web.Response:
        hours = int(request.query.get("hours", "24"))
        return web.json_response({"timeline": self.orchestrator._action_log.get_timeline(hours)}, dumps=_json_dumps)

    # --- Schedule Management handlers ---

    async def _handle_schedule_update(self, request: web.Request) -> web.Response:
        job_name = request.match_info["job_name"]
        body = await request.json()
        hour = int(body.get("hour", 0))
        minute = int(body.get("minute", 0))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return web.json_response({"error": "Invalid time"}, status=400)
        result = self.orchestrator.update_schedule(job_name, hour, minute)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_schedule_toggle(self, request: web.Request) -> web.Response:
        job_name = request.match_info["job_name"]
        body = await request.json()
        enabled = body.get("enabled", True)
        result = self.orchestrator.toggle_schedule(job_name, enabled)
        return web.json_response(result, dumps=_json_dumps)

    # --- Hydrospeed Ontology handlers ---

    async def _handle_ontology_telemetry_sync(self, request: web.Request) -> web.Response:
        """Return ontology graph enriched with live telemetry health data."""
        integration_status = {
            "github": bool(self.orchestrator._github),
            "notion": bool(self.orchestrator._notion),
            "gdrive": bool(self.orchestrator._gdrive),
            "wispr": bool(self.orchestrator._wispr),
            "llm": bool(self.orchestrator._llm),
            "ghost": bool(self.orchestrator._ghost),
            "pentagi": bool(self.orchestrator._pentagi),
            "paperclip": bool(self.orchestrator._paperclip),
            "browser": bool(self.orchestrator._browser),
        }
        enriched = self.orchestrator._hydrospeed.get_telemetry_enriched_ontology(
            self.orchestrator._telemetry, integration_status
        )
        return web.json_response(enriched, dumps=_json_dumps)

    async def _handle_ontology(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._hydrospeed.get_ontology(), dumps=_json_dumps)

    async def _handle_ontology_agent(self, request: web.Request) -> web.Response:
        agent_name = request.match_info["agent_name"]
        return web.json_response(self.orchestrator._hydrospeed.get_agent_profile(agent_name), dumps=_json_dumps)

    async def _handle_tips(self, request: web.Request) -> web.Response:
        category = request.query.get("category", "")
        agent = request.query.get("agent", "")
        tips = self.orchestrator._hydrospeed.get_expert_tips(category=category, agent=agent)
        return web.json_response({"tips": tips, "count": len(tips)}, dumps=_json_dumps)

    async def _handle_divisions(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._hydrospeed.get_divisions(), dumps=_json_dumps)

    async def _handle_data_flows(self, request: web.Request) -> web.Response:
        return web.json_response({"flows": self.orchestrator._hydrospeed.get_data_flows()}, dumps=_json_dumps)

    async def _handle_schedule_recommendations(self, request: web.Request) -> web.Response:
        current = self.orchestrator._scheduler.list_jobs()
        recs = self.orchestrator._hydrospeed.get_schedule_recommendations(current)
        return web.json_response({"recommendations": recs}, dumps=_json_dumps)

    async def _handle_create_proposal(self, request: web.Request) -> web.Response:
        body = await request.json()
        result = self.orchestrator._hydrospeed.create_proposal(
            title=body.get("title", ""),
            description=body.get("description", ""),
            agents=body.get("agents", []),
            workflow_steps=body.get("workflow_steps", []),
            priority=body.get("priority", "medium"),
        )
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_list_proposals(self, request: web.Request) -> web.Response:
        return web.json_response({"proposals": self.orchestrator._hydrospeed.list_proposals()}, dumps=_json_dumps)

    # --- Predictive Telemetry handlers ---

    async def _handle_telemetry_risks(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._telemetry.get_all_risks(), dumps=_json_dumps)

    async def _handle_telemetry_agent_risk(self, request: web.Request) -> web.Response:
        agent_name = request.match_info["agent_name"]
        return web.json_response(self.orchestrator._telemetry.calculate_risk(agent_name), dumps=_json_dumps)

    async def _handle_telemetry_predictions(self, request: web.Request) -> web.Response:
        return web.json_response({"predictions": self.orchestrator._telemetry.predict_failures()}, dumps=_json_dumps)

    async def _handle_telemetry_cascade(self, request: web.Request) -> web.Response:
        agent_name = request.match_info["agent_name"]
        return web.json_response(self.orchestrator._telemetry.get_dependency_cascade(agent_name), dumps=_json_dumps)

    async def _handle_telemetry_context(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._telemetry.get_workflow_context(), dumps=_json_dumps)

    # --- Agent Database handlers (Dolt-style version control) ---

    async def _handle_agentdb_schema(self, request: web.Request) -> web.Response:
        return web.json_response(self.orchestrator._agent_db.get_schema(), dumps=_json_dumps)

    async def _handle_agentdb_schema_sql(self, request: web.Request) -> web.Response:
        return web.Response(text=self.orchestrator._agent_db.get_schema_sql(),
                            content_type="text/plain")

    async def _handle_agentdb_branches(self, request: web.Request) -> web.Response:
        return web.json_response({"branches": self.orchestrator._agent_db.list_branches()}, dumps=_json_dumps)

    async def _handle_agentdb_create_branch(self, request: web.Request) -> web.Response:
        body = await request.json()
        name = body.get("name", "")
        from_branch = body.get("from", "main")
        if not name:
            return web.json_response({"error": "Branch name required"}, status=400)
        result = self.orchestrator._agent_db.create_branch(name, from_branch)
        if "error" in result:
            return web.json_response(result, status=409)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_delete_branch(self, request: web.Request) -> web.Response:
        branch = request.match_info["branch"]
        result = self.orchestrator._agent_db.delete_branch(branch)
        if "error" in result:
            return web.json_response(result, status=400)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_tables(self, request: web.Request) -> web.Response:
        branch = request.query.get("branch", "main")
        return web.json_response(self.orchestrator._agent_db.get_table_stats(branch), dumps=_json_dumps)

    async def _handle_agentdb_query(self, request: web.Request) -> web.Response:
        table = request.match_info["table"]
        branch = request.query.get("branch", "main")
        limit = int(request.query.get("limit", "50"))
        offset = int(request.query.get("offset", "0"))
        # Parse filters from query params (exclude reserved params)
        reserved = {"branch", "limit", "offset"}
        filters = {k: v for k, v in request.query.items() if k not in reserved}
        result = self.orchestrator._agent_db.query(branch, table, filters or None, limit, offset)
        if "error" in result:
            return web.json_response(result, status=404)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_insert(self, request: web.Request) -> web.Response:
        table = request.match_info["table"]
        body = await request.json()
        branch = body.pop("branch", "main")
        author = body.pop("author", "DASHBOARD")
        result = self.orchestrator._agent_db.insert(branch, table, body, author)
        if "error" in result:
            return web.json_response(result, status=400)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_update(self, request: web.Request) -> web.Response:
        table = request.match_info["table"]
        row_id = request.match_info["row_id"]
        body = await request.json()
        branch = body.pop("branch", "main")
        author = body.pop("author", "DASHBOARD")
        result = self.orchestrator._agent_db.update(branch, table, row_id, body, author)
        if "error" in result:
            return web.json_response(result, status=404)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_diff(self, request: web.Request) -> web.Response:
        from_branch = request.query.get("from", "main")
        to_branch = request.query.get("to", "")
        table = request.query.get("table")
        if not to_branch:
            return web.json_response({"error": "'to' branch required"}, status=400)
        diffs = self.orchestrator._agent_db.diff(from_branch, to_branch, table)
        return web.json_response({"diffs": diffs, "from": from_branch, "to": to_branch, "count": len(diffs)}, dumps=_json_dumps)

    async def _handle_agentdb_merge(self, request: web.Request) -> web.Response:
        body = await request.json()
        source = body.get("source", "")
        target = body.get("target", "main")
        author = body.get("author", "DASHBOARD")
        if not source:
            return web.json_response({"error": "Source branch required"}, status=400)
        result = self.orchestrator._agent_db.merge(source, target, author)
        if "error" in result:
            return web.json_response(result, status=400)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_reset(self, request: web.Request) -> web.Response:
        body = await request.json()
        branch = body.get("branch", "")
        commit_id = body.get("commit_id")
        steps = int(body.get("steps", 1))
        if not branch:
            return web.json_response({"error": "Branch required"}, status=400)
        result = self.orchestrator._agent_db.reset(branch, commit_id, steps)
        if "error" in result:
            return web.json_response(result, status=400)
        return web.json_response(result, dumps=_json_dumps)

    async def _handle_agentdb_log(self, request: web.Request) -> web.Response:
        branch = request.match_info["branch"]
        limit = int(request.query.get("limit", "20"))
        commits = self.orchestrator._agent_db.log(branch, limit)
        return web.json_response({"branch": branch, "commits": commits}, dumps=_json_dumps)

    async def _handle_agentdb_agent_status(self, request: web.Request) -> web.Response:
        agent_name = request.match_info["agent_name"]
        return web.json_response(self.orchestrator._agent_db.get_agent_branch_status(agent_name), dumps=_json_dumps)

    # --- Features Guide handler ---

    async def _handle_features_guide(self, request: web.Request) -> web.Response:
        return web.json_response(_FEATURES_GUIDE, dumps=_json_dumps)


# --- Features Guide Data ---

_FEATURES_GUIDE = {
    "system": "MortgageFintechOS",
    "version": "3.0.0",
    "tagline": "Fully Connected Autonomous AI Operating System",
    "sections": [
        {
            "title": "Autonomous Agent System",
            "icon": "cpu",
            "description": "13 AI agents organized into 4 divisions operate 24/7 with zero human intervention. Each agent has specialized capabilities, state persistence, and integration access.",
            "tech": "Python asyncio, BaseAgent abstract class, task queue with priority routing, exponential backoff retry",
            "how_to_use": "Submit tasks via POST /api/tasks/submit with {agent, action, payload, priority}. Monitor via the Agents table. Tasks auto-dispatch through the queue.",
            "agents": [
                {"name": "DIEGO", "division": "Mortgage Ops", "actions": ["pipeline_triage", "check_pipeline_health", "get_pipeline_report"]},
                {"name": "MARTIN", "division": "Mortgage Ops", "actions": ["classify_document", "run_document_audit"]},
                {"name": "NOVA", "division": "Mortgage Ops", "actions": ["calculate_income", "recalculate_income"]},
                {"name": "JARVIS", "division": "Mortgage Ops", "actions": ["track_conditions", "draft_loe", "check_compliance"]},
                {"name": "ATLAS", "division": "Engineering", "actions": ["generate_api", "build_feature", "run_migration", "scaffold_component"]},
                {"name": "CIPHER", "division": "Engineering", "actions": ["owasp_scan", "compliance_check", "encryption_audit", "patch_vulnerability"]},
                {"name": "FORGE", "division": "Engineering", "actions": ["deploy", "rollback", "build_pipeline", "rotate_secrets"]},
                {"name": "NEXUS", "division": "Engineering", "actions": ["review_pr", "generate_tests", "analyze_debt", "refactor"]},
                {"name": "STORM", "division": "Engineering", "actions": ["build_etl", "hmda_report", "uldd_export", "optimize_query"]},
                {"name": "SENTINEL", "division": "Intelligence", "actions": ["anomaly_scan", "threat_assessment"]},
                {"name": "HUNTER", "division": "Growth Ops", "actions": ["full_sweep", "scan_github", "scan_hn", "score_leads"]},
                {"name": "HERALD", "division": "Growth Ops", "actions": ["daily_content", "generate_blog", "generate_social"]},
                {"name": "AMBASSADOR", "division": "Growth Ops", "actions": ["daily_engagement", "community_scan"]},
            ],
        },
        {
            "title": "Hydrospeed Ontology",
            "icon": "share-2",
            "description": "Live ontology engine that maps all agent relationships, data flows, and integration dependencies as an interactive graph. Provides agent proposals and workflow recommendations.",
            "tech": "Graph-based ontology with nodes (agents, integrations, data sources) and typed edges (data_flow, dependency, orchestration, powers, governs). Real-time schedule analysis.",
            "how_to_use": "View the Ontology tab to see agent relationships. Click any agent for its full profile. Create proposals for new workflows. Check schedule recommendations for optimization tips.",
        },
        {
            "title": "Predictive Telemetry",
            "icon": "activity",
            "description": "Full telemetry capture with downstream risk prediction. Studies workflows in real-time, calculates contextual risk scores using a 5-factor weighted formula, predicts failures before they happen.",
            "tech": "R(agent) = 0.30*ErrorRate + 0.15*Latency + 0.25*DependencyHealth + 0.15*CapacityPressure + 0.15*QualityDelta. EWMA for error smoothing, z-score for latency deviation, cascade graph for dependency risk.",
            "how_to_use": "View the Telemetry tab for system-wide risk. Click any agent for detailed risk breakdown. Check Predictions for upcoming failures. Each prediction includes actionable solutions.",
        },
        {
            "title": "Agent Action Log",
            "icon": "list",
            "description": "Centralized, append-only log capturing every agent action with timing, status, and integration calls. Provides timeline visualization and per-agent breakdowns.",
            "tech": "Bounded deque (2000 entries), per-agent counters, hourly bucketing for timeline charts. Persisted across restarts via StateStore.",
            "how_to_use": "View the Action Log tab. Filter by agent or action type. Toggle to show failures only. Timeline shows activity patterns over 24 hours.",
        },
        {
            "title": "Schedule Control",
            "icon": "clock",
            "description": "Configurable job scheduling with runtime updates. Change job times, enable/disable jobs, and get expert recommendations on schedule optimization.",
            "tech": "DailyScheduler with time-based, interval-based, and weekly job support. State persistence for last-run times. Runtime modification via API.",
            "how_to_use": "Click any scheduled job to edit its time. Toggle jobs on/off. Check the Recommendations panel for dependency ordering and conflict warnings.",
        },
        {
            "title": "Agent Database",
            "icon": "database",
            "description": "Dolt-inspired version-controlled database with Git-style branching for agent data. Each agent works on an isolated branch — changes are reviewed via diffs before merging to main. Supports instant rollback, UUID primary keys, and auto-commit on every write.",
            "tech": "In-memory relational store with 6 tables (agent_operations, agent_state, integration_events, schedule_history, audit_trail, workflow_proposals). Branch-per-agent isolation, DOLT_DIFF-style change computation, atomic merge, commit graph with parent tracking. Persisted via StateStore.",
            "how_to_use": "View the Agent DB tab. Browse branches, view table data, compute diffs between branches, merge agent changes to main, and rollback mistakes. Each agent auto-creates its own branch on first operation.",
        },
        {
            "title": "Safety Guardrails",
            "icon": "shield",
            "description": "Two-layer immutable deletion blocking. AI agents can read, create, and update code but can NEVER delete files, branches, or repository content. All blocked attempts are audit-logged.",
            "tech": "Layer 1: GitHubClient blocked method stubs (frozenset). Layer 2: BaseAgent.safe_github() wrapper blocks any method containing 'delete'. No override mechanism exists.",
            "how_to_use": "Safety is always active. Check GET /api/safety/blocked for audit log. The guardrail is architectural — it cannot be disabled.",
        },
        {
            "title": "Integration Hub",
            "icon": "link",
            "description": "9 integration systems providing external connectivity: GitHub (code ops), Notion (knowledge base), Google Drive (documents), Wispr Flow (voice), LLM Router (AI), Paperclip (governance), GHOST OSINT (verification), PentAGI (security), Browser (web).",
            "tech": "All async via aiohttp. Service account auth for Drive. JWT tokens for Notion. Webhook validation for Wispr. Multi-provider LLM routing.",
            "how_to_use": "Set credentials in .env file. Integrations auto-initialize on startup. Agents gracefully degrade when integrations are missing.",
        },
        {
            "title": "Expert Tips",
            "icon": "zap",
            "description": "18 expert-curated tips covering scheduling, cost optimization, safety, monitoring, workflows, scaling, resilience, deployment, and compliance. Contextual to each agent.",
            "tech": "Static knowledge base with category/severity/agent filtering. Schedule recommendations generated dynamically by analyzing current job configuration.",
            "how_to_use": "View the Tips tab. Filter by category or agent. Tips marked 'critical' should be addressed immediately.",
        },
    ],
}


def _json_dumps(obj: Any) -> str:
    """JSON serializer that handles datetime and bytes objects."""
    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, bytes):
            return f"<{len(o)} bytes>"
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, default=default)
