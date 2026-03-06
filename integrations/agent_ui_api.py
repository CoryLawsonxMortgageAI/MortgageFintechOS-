"""Agno-compatible Agent UI API layer.

Provides a REST API compatible with Agno's Agent UI (https://docs.agno.com/other/agent-ui)
so the MortgageFintechOS agents can be interacted with through a professional chat interface.

Endpoints:
    GET  /v1/agents           - List all agents
    GET  /v1/agents/{id}      - Get agent details
    POST /v1/agents/{id}/chat - Send a message to an agent
    GET  /v1/agents/{id}/sessions  - List agent sessions
    GET  /v1/status           - System status
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import structlog
from aiohttp import web

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator

logger = structlog.get_logger()

AGENT_CAPABILITIES = {
    "DIEGO": {
        "description": "Pipeline Orchestration — loan triage, workflow management, priority assignment",
        "actions": ["triage_loan", "advance_stage", "check_pipeline_health", "get_pipeline_report", "assign_priority"],
        "category": "mortgage_ops",
    },
    "MARTIN": {
        "description": "Document Intelligence — OCR, classification, fraud detection, completeness audit",
        "actions": ["classify_document", "validate_ocr", "detect_fraud", "run_document_audit"],
        "category": "mortgage_ops",
    },
    "NOVA": {
        "description": "Income & DTI Analysis — W-2 dual-method, Schedule C, FHA HB 4000.1 compliance",
        "actions": ["calculate_w2_income", "analyze_schedule_c", "calculate_dti", "evaluate_collections", "full_analysis"],
        "category": "mortgage_ops",
    },
    "JARVIS": {
        "description": "Condition Resolution — LOE drafting, condition mapping, compliance citations",
        "actions": ["draft_loe", "map_conditions", "get_compliance_citation", "add_condition", "clear_condition"],
        "category": "mortgage_ops",
    },
    "ATLAS": {
        "description": "Full-Stack Engineering — writes production APIs, features, and ships code 24/7",
        "actions": ["generate_api_endpoint", "generate_feature", "generate_migration", "deploy_feature", "get_shipping_report"],
        "category": "coding_expert",
    },
    "CIPHER": {
        "description": "Security Engineering — OWASP audits, compliance, encryption, patches 24/7",
        "actions": ["run_security_audit", "scan_owasp_top_10", "generate_security_patch", "run_compliance_check", "harden_authentication"],
        "category": "coding_expert",
    },
    "FORGE": {
        "description": "DevOps Engineering — CI/CD pipelines, deployments, infrastructure 24/7",
        "actions": ["run_pipeline", "deploy", "rollback", "generate_github_actions", "check_environment_health"],
        "category": "coding_expert",
    },
    "NEXUS": {
        "description": "Code Quality Engineering — reviews, tests, refactoring, tech debt 24/7",
        "actions": ["review_code", "generate_tests", "analyze_quality", "track_tech_debt", "refactor"],
        "category": "coding_expert",
    },
    "STORM": {
        "description": "Data Engineering — ETL pipelines, analytics, regulatory reports, data quality 24/7",
        "actions": ["build_pipeline", "optimize_queries", "generate_analytics", "run_data_quality", "generate_regulatory_report"],
        "category": "coding_expert",
    },
}


class AgentUIAPI:
    """Agno-compatible REST API for Agent UI integration."""

    def __init__(self, orchestrator: "Orchestrator"):
        self._orchestrator = orchestrator
        self._log = logger.bind(component="agent_ui_api")
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def register_routes(self, app: web.Application) -> None:
        """Register Agent UI API routes."""
        app.router.add_get("/v1/agents", self._list_agents)
        app.router.add_get("/v1/agents/{agent_id}", self._get_agent)
        app.router.add_post("/v1/agents/{agent_id}/chat", self._chat)
        app.router.add_get("/v1/agents/{agent_id}/sessions", self._list_sessions)
        app.router.add_get("/v1/status", self._system_status)

    async def _list_agents(self, request: web.Request) -> web.Response:
        """List all available agents with capabilities."""
        agents = []
        for agent_info in self._orchestrator.list_agents():
            name = agent_info["name"]
            caps = AGENT_CAPABILITIES.get(name, {})
            agents.append({
                "id": name.lower(),
                "name": name,
                "description": caps.get("description", ""),
                "category": caps.get("category", "unknown"),
                "status": agent_info["status"],
                "actions": caps.get("actions", []),
                "tasks_completed": agent_info["tasks_completed"],
                "error_count": agent_info["error_count"],
            })
        return web.json_response({"agents": agents})

    async def _get_agent(self, request: web.Request) -> web.Response:
        """Get detailed info for a specific agent."""
        agent_id = request.match_info["agent_id"].upper()
        agents = {a["name"]: a for a in self._orchestrator.list_agents()}
        agent_info = agents.get(agent_id)
        if not agent_info:
            return web.json_response({"error": f"Agent {agent_id} not found"}, status=404)

        caps = AGENT_CAPABILITIES.get(agent_id, {})
        return web.json_response({
            "id": agent_id.lower(),
            "name": agent_id,
            "description": caps.get("description", ""),
            "category": caps.get("category", ""),
            "status": agent_info["status"],
            "actions": caps.get("actions", []),
            "tasks_completed": agent_info["tasks_completed"],
            "error_count": agent_info["error_count"],
            "last_heartbeat": agent_info["last_heartbeat"],
        })

    async def _chat(self, request: web.Request) -> web.Response:
        """Send a task to an agent via chat-style interface."""
        agent_id = request.match_info["agent_id"].upper()
        body = await request.json()

        message = body.get("message", "")
        action = body.get("action", "")
        payload = body.get("payload", {})
        session_id = body.get("session_id", str(uuid.uuid4()))

        # If no explicit action, try to parse from message
        if not action:
            action = self._parse_action(agent_id, message)

        if not action:
            return web.json_response({
                "session_id": session_id,
                "response": f"I'm {agent_id}. Available actions: {', '.join(AGENT_CAPABILITIES.get(agent_id, {}).get('actions', []))}",
                "status": "info",
            })

        # Submit task
        from core.task_queue import TaskPriority
        task_id = await self._orchestrator.submit_task(agent_id, action, payload=payload, priority=TaskPriority.MEDIUM)

        # Record in session
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({
            "role": "user",
            "content": message or f"{action}({json.dumps(payload)})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._sessions[session_id].append({
            "role": "agent",
            "agent": agent_id,
            "content": f"Task `{task_id}` submitted: {action}",
            "task_id": task_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return web.json_response({
            "session_id": session_id,
            "task_id": task_id,
            "agent": agent_id,
            "action": action,
            "status": "submitted",
        })

    async def _list_sessions(self, request: web.Request) -> web.Response:
        agent_id = request.match_info["agent_id"].upper()
        agent_sessions = {
            sid: msgs for sid, msgs in self._sessions.items()
            if any(m.get("agent") == agent_id for m in msgs)
        }
        return web.json_response({"agent": agent_id, "sessions": agent_sessions})

    async def _system_status(self, request: web.Request) -> web.Response:
        status = self._orchestrator.get_status()
        return web.json_response(status, dumps=_json_dumps)

    def _parse_action(self, agent_id: str, message: str) -> str:
        """Try to match a message to an agent action."""
        caps = AGENT_CAPABILITIES.get(agent_id, {})
        actions = caps.get("actions", [])
        msg_lower = message.lower()

        for action in actions:
            if action.replace("_", " ") in msg_lower or action in msg_lower:
                return action
        return ""


def _json_dumps(obj: Any) -> str:
    def default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, default=default)
