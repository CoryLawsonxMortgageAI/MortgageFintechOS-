"""GitHub Webhooks Receiver for event-driven agent operations.

Receives GitHub events (push, PR, issues) and triggers agent tasks
automatically. This makes the coding agents truly event-driven —
they respond to real development activity in real time.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import structlog
from aiohttp import web

if TYPE_CHECKING:
    from core.orchestrator import Orchestrator

logger = structlog.get_logger()


class WebhookReceiver:
    """Receives GitHub webhooks and triggers agent tasks."""

    def __init__(self, orchestrator: "Orchestrator", secret: str = ""):
        self._orchestrator = orchestrator
        self._secret = secret
        self._log = logger.bind(component="webhooks")
        self._events_received: list[dict[str, Any]] = []
        self._total_events: int = 0

    def register_routes(self, app: web.Application) -> None:
        """Register webhook routes on an aiohttp app."""
        app.router.add_post("/webhooks/github", self._handle_github)
        app.router.add_get("/webhooks/status", self._handle_status)

    async def _handle_github(self, request: web.Request) -> web.Response:
        """Handle incoming GitHub webhook events."""
        # Verify signature if secret is configured
        if self._secret:
            signature = request.headers.get("X-Hub-Signature-256", "")
            body = await request.read()
            if not self._verify_signature(body, signature):
                self._log.warning("webhook_signature_invalid")
                return web.json_response({"error": "Invalid signature"}, status=401)
            payload = json.loads(body)
        else:
            payload = await request.json()

        event_type = request.headers.get("X-GitHub-Event", "unknown")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")

        self._total_events += 1
        event_record = {
            "id": delivery_id,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events_received.append(event_record)
        # Keep last 500 events
        if len(self._events_received) > 500:
            self._events_received = self._events_received[-500:]

        self._log.info("webhook_received", event=event_type, delivery=delivery_id)

        # Route event to appropriate agent tasks
        await self._route_event(event_type, payload)

        return web.json_response({"status": "accepted", "event": event_type})

    async def _route_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Route a GitHub event to the appropriate agent tasks."""
        from core.task_queue import TaskPriority

        if event_type == "push":
            branch = payload.get("ref", "").replace("refs/heads/", "")
            commits = payload.get("commits", [])
            files_changed = []
            for commit in commits:
                files_changed.extend(commit.get("added", []))
                files_changed.extend(commit.get("modified", []))

            # NEXUS reviews pushed code
            await self._orchestrator.submit_task(
                "NEXUS", "review_code",
                payload={"branch": branch, "files": files_changed, "author": payload.get("pusher", {}).get("name", "")},
                priority=TaskPriority.HIGH,
            )

            # CIPHER scans for security issues on main/production branches
            if branch in ("main", "master", "production"):
                await self._orchestrator.submit_task(
                    "CIPHER", "scan_owasp_top_10",
                    payload={"target": "push", "branch": branch},
                    priority=TaskPriority.CRITICAL,
                )

        elif event_type == "pull_request":
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})

            if action in ("opened", "synchronize"):
                # NEXUS reviews the PR
                await self._orchestrator.submit_task(
                    "NEXUS", "review_code",
                    payload={
                        "pr_number": pr.get("number"),
                        "branch": pr.get("head", {}).get("ref", ""),
                        "author": pr.get("user", {}).get("login", ""),
                        "files": [],
                    },
                    priority=TaskPriority.HIGH,
                )

            if action == "closed" and pr.get("merged"):
                # FORGE deploys merged PRs to staging
                await self._orchestrator.submit_task(
                    "FORGE", "run_pipeline",
                    payload={"template": "standard", "branch": pr.get("base", {}).get("ref", "main")},
                    priority=TaskPriority.HIGH,
                )

        elif event_type == "issues":
            action = payload.get("action", "")
            issue = payload.get("issue", {})
            labels = [l.get("name", "") for l in issue.get("labels", [])]

            if action == "opened":
                # If labeled as feature request, ATLAS starts designing
                if "feature" in labels or "enhancement" in labels:
                    await self._orchestrator.submit_task(
                        "ATLAS", "generate_feature",
                        payload={
                            "feature_id": f"issue-{issue.get('number')}",
                            "title": issue.get("title", ""),
                            "spec": {"body": issue.get("body", ""), "labels": labels},
                        },
                        priority=TaskPriority.MEDIUM,
                    )

                # If labeled as bug, NEXUS generates tests
                if "bug" in labels:
                    await self._orchestrator.submit_task(
                        "NEXUS", "generate_tests",
                        payload={"module": f"bugfix_{issue.get('number')}", "types": ["unit", "integration"]},
                        priority=TaskPriority.HIGH,
                    )

        elif event_type == "release":
            action = payload.get("action", "")
            if action == "published":
                release = payload.get("release", {})
                # FORGE deploys to production
                await self._orchestrator.submit_task(
                    "FORGE", "deploy",
                    payload={
                        "environment": "production",
                        "version": release.get("tag_name", "latest"),
                        "strategy": "rolling",
                    },
                    priority=TaskPriority.CRITICAL,
                )

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "total_events": self._total_events,
            "recent_events": self._events_received[-20:],
        })

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            self._secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
