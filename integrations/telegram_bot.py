"""Telegram Bot integration for MortgageFintechOS.

Provides a full Telegram bot interface for interacting with all 9 AI agents,
receiving real-time alerts, and monitoring system status directly from Telegram.

Features:
- Command-based agent interaction (/atlas, /cipher, /forge, etc.)
- Inline keyboard menus for agent actions
- Real-time deployment and security alert notifications
- System status and health reports on demand
- Webhook-based (no polling) for production reliability

Setup:
1. Message @BotFather on Telegram → /newbot → get token
2. Set TELEGRAM_BOT_TOKEN in .env
3. Set TELEGRAM_WEBHOOK_SECRET in .env
4. System auto-registers webhook on startup
"""

import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import aiohttp
import structlog
from aiohttp import web

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator

logger = structlog.get_logger()

TELEGRAM_API = "https://api.telegram.org/bot{token}"

# Agent command mapping
AGENT_COMMANDS = {
    "/diego": ("DIEGO", "Pipeline Orchestration"),
    "/martin": ("MARTIN", "Document Intelligence"),
    "/nova": ("NOVA", "Income & DTI Analysis"),
    "/jarvis": ("JARVIS", "Condition Resolution"),
    "/atlas": ("ATLAS", "Full-Stack Engineering"),
    "/cipher": ("CIPHER", "Security Engineering"),
    "/forge": ("FORGE", "CI/CD & DevOps"),
    "/nexus": ("NEXUS", "Code Quality & Review"),
    "/storm": ("STORM", "Data Engineering"),
}

# Agent action menus (inline keyboards)
AGENT_ACTIONS = {
    "DIEGO": [
        ("Triage Loan", "diego_triage_loan"),
        ("Pipeline Health", "diego_check_pipeline_health"),
        ("Pipeline Report", "diego_get_pipeline_report"),
    ],
    "MARTIN": [
        ("Document Audit", "martin_run_document_audit"),
        ("Classify Doc", "martin_classify_document"),
    ],
    "NOVA": [
        ("Full Analysis", "nova_full_analysis"),
        ("Calculate DTI", "nova_calculate_dti"),
    ],
    "JARVIS": [
        ("Map Conditions", "jarvis_map_conditions"),
        ("Draft LOE", "jarvis_draft_loe"),
    ],
    "ATLAS": [
        ("Generate Feature", "atlas_generate_feature"),
        ("Shipping Report", "atlas_get_shipping_report"),
        ("Generate API", "atlas_generate_api_endpoint"),
    ],
    "CIPHER": [
        ("Security Audit", "cipher_run_security_audit"),
        ("OWASP Scan", "cipher_scan_owasp_top_10"),
        ("Compliance Check", "cipher_run_compliance_check"),
    ],
    "FORGE": [
        ("Run Pipeline", "forge_run_pipeline"),
        ("Deploy Staging", "forge_deploy_staging"),
        ("Env Health", "forge_check_environment_health"),
    ],
    "NEXUS": [
        ("Quality Analysis", "nexus_analyze_quality"),
        ("Tech Debt Scan", "nexus_track_tech_debt"),
        ("Coverage Report", "nexus_coverage_report"),
    ],
    "STORM": [
        ("Data Quality", "storm_run_data_quality"),
        ("HMDA Report", "storm_generate_regulatory_report"),
        ("Build Pipeline", "storm_build_pipeline"),
    ],
}


class TelegramBot:
    """Telegram bot for MortgageFintechOS agent interaction and monitoring."""

    def __init__(
        self,
        orchestrator: "Orchestrator",
        token: str,
        webhook_secret: str = "",
    ):
        self._orchestrator = orchestrator
        self._token = token
        self._webhook_secret = webhook_secret
        self._api_base = TELEGRAM_API.format(token=token)
        self._log = logger.bind(component="telegram_bot")
        self._authorized_chats: set[int] = set()
        self._total_messages: int = 0

    def register_routes(self, app: web.Application) -> None:
        """Register the Telegram webhook route on the aiohttp app."""
        app.router.add_post("/webhooks/telegram", self._handle_update)

    async def setup_webhook(self, public_url: str) -> dict[str, Any]:
        """Register the webhook URL with Telegram."""
        webhook_url = f"{public_url}/webhooks/telegram"
        payload: dict[str, Any] = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"],
            "max_connections": 40,
        }
        if self._webhook_secret:
            payload["secret_token"] = self._webhook_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self._api_base}/setWebhook", json=payload) as resp:
                result = await resp.json()
                if result.get("ok"):
                    self._log.info("telegram_webhook_set", url=webhook_url)
                else:
                    self._log.error("telegram_webhook_failed", result=result)
                return result

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str = "HTML",
    ) -> dict[str, Any]:
        """Send a message to a Telegram chat."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self._api_base}/sendMessage", json=payload) as resp:
                return await resp.json()

    async def send_alert(self, text: str) -> None:
        """Send an alert to all authorized chats."""
        for chat_id in self._authorized_chats:
            await self.send_message(chat_id, text)

    # --- Webhook handler ---

    async def _handle_update(self, request: web.Request) -> web.Response:
        """Handle incoming Telegram webhook update."""
        # Verify secret token
        if self._webhook_secret:
            header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if header_secret != self._webhook_secret:
                return web.Response(status=403)

        update = await request.json()
        self._total_messages += 1

        if "message" in update:
            await self._handle_message(update["message"])
        elif "callback_query" in update:
            await self._handle_callback(update["callback_query"])

        return web.Response(text="ok")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle a text message."""
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        username = message.get("from", {}).get("username", "unknown")

        self._authorized_chats.add(chat_id)
        self._log.info("telegram_message", chat_id=chat_id, text=text[:50], user=username)

        if text == "/start":
            await self._cmd_start(chat_id)
        elif text == "/status":
            await self._cmd_status(chat_id)
        elif text == "/health":
            await self._cmd_health(chat_id)
        elif text == "/agents":
            await self._cmd_agents(chat_id)
        elif text == "/kernel":
            await self._cmd_kernel(chat_id)
        elif text == "/help":
            await self._cmd_help(chat_id)
        elif text in AGENT_COMMANDS:
            agent_name, description = AGENT_COMMANDS[text]
            await self._cmd_agent_menu(chat_id, agent_name, description)
        else:
            await self.send_message(
                chat_id,
                "Unknown command. Use /help to see available commands.",
            )

    async def _handle_callback(self, callback: dict[str, Any]) -> None:
        """Handle an inline keyboard button press."""
        callback_id = callback["id"]
        data = callback.get("data", "")
        chat_id = callback["message"]["chat"]["id"]

        # Acknowledge the callback immediately
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self._api_base}/answerCallbackQuery",
                json={"callback_query_id": callback_id, "text": "Processing..."},
            )

        # Parse callback data: "agentname_action"
        parts = data.split("_", 1)
        if len(parts) != 2:
            return

        agent_name = parts[0].upper()
        action = parts[1]

        # Special deploy actions
        if data == "forge_deploy_staging":
            agent_name = "FORGE"
            action = "deploy"
            payload = {"environment": "staging", "version": "latest", "strategy": "rolling"}
        else:
            payload = {}

        from core.task_queue import TaskPriority
        try:
            task_id = await self._orchestrator.submit_task(
                agent_name, action, payload=payload, priority=TaskPriority.MEDIUM,
            )
            await self.send_message(
                chat_id,
                f"<b>{agent_name}</b> task submitted\n"
                f"<code>Action:</code> {action}\n"
                f"<code>Task ID:</code> {task_id}",
            )
        except Exception as e:
            await self.send_message(chat_id, f"Error: {e}")

    # --- Commands ---

    async def _cmd_start(self, chat_id: int) -> None:
        await self.send_message(
            chat_id,
            "<b>MortgageFintechOS</b> — AIOS Kernel v1.0\n\n"
            "9 AI Agents running 24/7:\n"
            "  <b>Mortgage Ops:</b> DIEGO, MARTIN, NOVA, JARVIS\n"
            "  <b>Coding Experts:</b> ATLAS, CIPHER, FORGE, NEXUS, STORM\n\n"
            "Use /help to see all commands.",
        )

    async def _cmd_help(self, chat_id: int) -> None:
        lines = [
            "<b>Commands</b>\n",
            "/status — System status",
            "/health — Health report",
            "/agents — List all agents",
            "/kernel — AIOS Kernel status",
            "",
            "<b>Agent Commands</b>",
        ]
        for cmd, (name, desc) in AGENT_COMMANDS.items():
            lines.append(f"{cmd} — {name}: {desc}")

        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_status(self, chat_id: int) -> None:
        status = self._orchestrator.get_status()
        queue = status.get("queue", {})
        agents = status.get("agents", {})

        agent_lines = []
        for name, info in agents.items():
            icon = "🟢" if info["status"] == "idle" else "🔴" if info["status"] == "error" else "🔵"
            agent_lines.append(f"  {icon} <b>{name}</b> — {info['status']} | tasks={info['tasks_completed']}")

        text = (
            f"<b>MortgageFintechOS Status</b>\n\n"
            f"<code>Running:</code>  {status['running']}\n"
            f"<code>Uptime:</code>   {status.get('uptime', '—')}\n"
            f"<code>Degraded:</code> {status.get('degraded', False)}\n\n"
            f"<b>Queue</b>\n"
            f"  Pending: {queue.get('pending', 0)} | "
            f"Completed: {queue.get('completed', 0)} | "
            f"Failed: {queue.get('failed', 0)}\n\n"
            f"<b>Agents</b>\n" + "\n".join(agent_lines)
        )
        await self.send_message(chat_id, text)

    async def _cmd_health(self, chat_id: int) -> None:
        health = self._orchestrator.get_health()
        overall = health.get("overall", "unknown")
        icon = "🟢" if overall == "healthy" else "🔴"
        system = health.get("system", {})

        text = (
            f"<b>Health Report</b>\n\n"
            f"Overall: {icon} {overall}\n"
            f"CPU: {system.get('cpu_percent', '—')}%\n"
            f"Memory: {system.get('memory_percent', '—')}%\n"
        )
        await self.send_message(chat_id, text)

    async def _cmd_agents(self, chat_id: int) -> None:
        agents = self._orchestrator.list_agents()
        keyboard = []
        row = []
        for agent in agents:
            name = agent["name"]
            cmd = f"/{name.lower()}"
            row.append({"text": name, "callback_data": f"{name.lower()}_menu"})
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        await self.send_message(
            chat_id,
            "<b>All Agents</b> — tap to interact:",
            reply_markup={"inline_keyboard": keyboard},
        )

    async def _cmd_kernel(self, chat_id: int) -> None:
        kernel = self._orchestrator._kernel.get_kernel_status()
        agents = kernel.get("agents", {})

        lines = [
            f"<b>AIOS Kernel v{kernel.get('kernel_version', '1.0.0')}</b>\n",
            f"Messages: {kernel.get('total_messages', 0)}",
            f"Pipeline Triggers: {kernel.get('total_pipeline_triggers', 0)}",
            f"Preemptions: {kernel.get('total_preemptions', 0)}\n",
            "<b>Agent Slots</b>",
        ]
        for name, info in agents.items():
            suspended = " [SUSPENDED]" if info.get("suspended") else ""
            lines.append(
                f"  <b>{name}</b> [{info['priority']}] "
                f"{info['active_tasks']}/{info['max_concurrent']} slots{suspended}"
            )

        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_agent_menu(self, chat_id: int, agent_name: str, description: str) -> None:
        """Show inline keyboard with agent actions."""
        actions = AGENT_ACTIONS.get(agent_name, [])
        keyboard = []
        for label, callback_data in actions:
            keyboard.append([{"text": label, "callback_data": callback_data}])

        await self.send_message(
            chat_id,
            f"<b>{agent_name}</b> — {description}\n\nSelect an action:",
            reply_markup={"inline_keyboard": keyboard},
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": bool(self._token),
            "authorized_chats": len(self._authorized_chats),
            "total_messages": self._total_messages,
        }
