"""Notification integrations for Slack, Discord, and generic webhooks.

Sends real-time notifications about agent activity, deployments,
security alerts, and system health to external channels.
"""

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()


class NotificationClient:
    """Multi-channel notification sender."""

    def __init__(
        self,
        slack_webhook_url: str = "",
        discord_webhook_url: str = "",
        custom_webhook_url: str = "",
    ):
        self._slack_url = slack_webhook_url
        self._discord_url = discord_webhook_url
        self._custom_url = custom_webhook_url
        self._log = logger.bind(component="notifications")
        self._sent_count: int = 0

    async def notify(
        self,
        title: str,
        message: str,
        severity: str = "info",
        fields: dict[str, str] | None = None,
        channels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a notification to configured channels."""
        targets = channels or ["slack", "discord"]
        results = {}

        if "slack" in targets and self._slack_url:
            results["slack"] = await self._send_slack(title, message, severity, fields)

        if "discord" in targets and self._discord_url:
            results["discord"] = await self._send_discord(title, message, severity, fields)

        if "custom" in targets and self._custom_url:
            results["custom"] = await self._send_custom(title, message, severity, fields)

        self._sent_count += 1
        return results

    async def notify_deployment(self, environment: str, version: str, status: str, agent: str = "FORGE") -> None:
        """Send deployment notification."""
        color = {"success": "good", "failed": "danger", "rolled_back": "warning"}.get(status, "info")
        await self.notify(
            title=f"Deployment {status.upper()}: {environment}",
            message=f"Version `{version}` deployed to `{environment}` by {agent}",
            severity=color,
            fields={"Environment": environment, "Version": version, "Status": status, "Agent": agent},
        )

    async def notify_security_alert(self, vuln_id: str, severity: str, description: str) -> None:
        """Send security alert notification."""
        await self.notify(
            title=f"Security Alert: {severity.upper()}",
            message=f"`{vuln_id}`: {description}",
            severity="danger" if severity in ("critical", "high") else "warning",
            fields={"Vulnerability": vuln_id, "Severity": severity},
        )

    async def notify_agent_event(self, agent: str, action: str, result_summary: str) -> None:
        """Send agent activity notification."""
        await self.notify(
            title=f"Agent {agent}: {action}",
            message=result_summary,
            severity="info",
            fields={"Agent": agent, "Action": action},
        )

    async def _send_slack(self, title: str, message: str, severity: str, fields: dict[str, str] | None) -> dict:
        """Send Slack webhook notification."""
        color_map = {"info": "#0dcaf0", "good": "#198754", "warning": "#fd7e14", "danger": "#dc3545"}
        color = color_map.get(severity, "#6c757d")

        slack_fields = []
        if fields:
            for k, v in fields.items():
                slack_fields.append({"title": k, "value": v, "short": True})

        payload = {
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "fields": slack_fields,
                "footer": "MortgageFintechOS",
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }]
        }

        return await self._post(self._slack_url, payload)

    async def _send_discord(self, title: str, message: str, severity: str, fields: dict[str, str] | None) -> dict:
        """Send Discord webhook notification."""
        color_map = {"info": 0x0DCAF0, "good": 0x198754, "warning": 0xFD7E14, "danger": 0xDC3545}
        color = color_map.get(severity, 0x6C757D)

        embed_fields = []
        if fields:
            for k, v in fields.items():
                embed_fields.append({"name": k, "value": v, "inline": True})

        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "fields": embed_fields,
                "footer": {"text": "MortgageFintechOS"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }]
        }

        return await self._post(self._discord_url, payload)

    async def _send_custom(self, title: str, message: str, severity: str, fields: dict[str, str] | None) -> dict:
        """Send generic webhook notification."""
        payload = {
            "title": title,
            "message": message,
            "severity": severity,
            "fields": fields or {},
            "source": "MortgageFintechOS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self._post(self._custom_url, payload)

    async def _post(self, url: str, payload: dict) -> dict:
        """POST JSON to a webhook URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status in (200, 204):
                        self._log.info("notification_sent", url=url[:50])
                        return {"status": "sent"}
                    else:
                        error = await resp.text()
                        self._log.error("notification_failed", status=resp.status, error=error[:200])
                        return {"status": "failed", "error": error[:200]}
        except Exception as e:
            self._log.error("notification_error", error=str(e))
            return {"status": "error", "error": str(e)}
