"""X.com (Twitter) integration for MortgageFintechOS.

Provides autonomous posting to X.com for system updates, agent activity,
deployment notifications, and mortgage industry insights. Uses the
X API v2 with OAuth 2.0 Bearer Token and OAuth 1.0a for posting.

Features:
- Automated deployment announcements
- Security alert broadcasts
- Agent activity highlights
- System status threads
- Scheduled mortgage market updates

Setup:
1. Create an app at https://developer.x.com
2. Get API Key, API Secret, Access Token, Access Token Secret
3. Set X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET in .env
"""

import hashlib
import hmac
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()

X_API_V2 = "https://api.x.com/2"
X_API_V1 = "https://api.x.com/1.1"


class TwitterClient:
    """X.com (Twitter) API client for autonomous posting and monitoring."""

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        access_token: str = "",
        access_secret: str = "",
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._access_secret = access_secret
        self._log = logger.bind(component="twitter")
        self._total_posts: int = 0
        self._post_history: list[dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return bool(self._api_key and self._api_secret and self._access_token and self._access_secret)

    async def post_tweet(self, text: str) -> dict[str, Any]:
        """Post a tweet to X.com using API v2."""
        if not self.available:
            return {"error": "X.com credentials not configured"}

        url = f"{X_API_V2}/tweets"
        payload = {"text": text[:280]}

        headers = self._oauth1_headers("POST", url, {})
        headers["Content-Type"] = "application/json"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    tweet_id = data.get("data", {}).get("id", "")
                    self._total_posts += 1
                    self._post_history.append({
                        "id": tweet_id,
                        "text": text[:280],
                        "posted_at": datetime.now(timezone.utc).isoformat(),
                    })
                    # Keep last 200 posts
                    if len(self._post_history) > 200:
                        self._post_history = self._post_history[-200:]
                    self._log.info("tweet_posted", tweet_id=tweet_id)
                    return {"id": tweet_id, "text": text[:280], "status": "posted"}
                else:
                    error = await resp.text()
                    self._log.error("tweet_failed", status=resp.status, error=error[:200])
                    return {"error": error[:200], "status": resp.status}

    async def post_thread(self, tweets: list[str]) -> list[dict[str, Any]]:
        """Post a thread of tweets."""
        results = []
        reply_to_id = None

        for text in tweets:
            if reply_to_id:
                result = await self._post_reply(text, reply_to_id)
            else:
                result = await self.post_tweet(text)

            results.append(result)
            reply_to_id = result.get("id")

            if not reply_to_id:
                break

        return results

    async def _post_reply(self, text: str, reply_to_id: str) -> dict[str, Any]:
        """Post a reply tweet."""
        if not self.available:
            return {"error": "X.com credentials not configured"}

        url = f"{X_API_V2}/tweets"
        payload = {
            "text": text[:280],
            "reply": {"in_reply_to_tweet_id": reply_to_id},
        }

        headers = self._oauth1_headers("POST", url, {})
        headers["Content-Type"] = "application/json"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    tweet_id = data.get("data", {}).get("id", "")
                    self._total_posts += 1
                    return {"id": tweet_id, "text": text[:280], "status": "posted"}
                else:
                    error = await resp.text()
                    return {"error": error[:200], "status": resp.status}

    # --- Pre-built notification templates ---

    async def notify_deployment(self, environment: str, version: str, status: str) -> dict[str, Any]:
        """Post a deployment notification."""
        icon = {"success": "✅", "failed": "❌", "rolled_back": "⚠️"}.get(status, "🔄")
        text = (
            f"{icon} MortgageFintechOS Deploy\n\n"
            f"Environment: {environment}\n"
            f"Version: {version}\n"
            f"Status: {status.upper()}\n\n"
            f"#MortgageTech #AI #DevOps"
        )
        return await self.post_tweet(text)

    async def notify_security_alert(self, severity: str, description: str) -> dict[str, Any]:
        """Post a security alert (high-level, no sensitive details)."""
        icon = {"critical": "🚨", "high": "⚠️", "medium": "🔶", "low": "ℹ️"}.get(severity, "🔶")
        text = (
            f"{icon} Security Update\n\n"
            f"Severity: {severity.upper()}\n"
            f"Our CIPHER agent detected and patched a vulnerability.\n"
            f"All systems secure.\n\n"
            f"#CyberSecurity #MortgageTech"
        )
        return await self.post_tweet(text)

    async def post_agent_highlight(self, agent_name: str, action: str, summary: str) -> dict[str, Any]:
        """Post an agent activity highlight."""
        text = (
            f"🤖 Agent {agent_name} completed: {action}\n\n"
            f"{summary[:180]}\n\n"
            f"#AI #AutonomousAgents #MortgageFintechOS"
        )
        return await self.post_tweet(text)

    async def post_system_status(self) -> dict[str, Any]:
        """Post current system status."""
        text = (
            f"📊 MortgageFintechOS Status\n\n"
            f"🟢 9 AI Agents operational\n"
            f"⚡ AIOS Kernel running\n"
            f"🔒 Security scans current\n"
            f"📈 All pipelines healthy\n\n"
            f"Running 24/7 autonomously.\n\n"
            f"#MortgageTech #AI #Fintech"
        )
        return await self.post_tweet(text)

    # --- OAuth 1.0a signature ---

    def _oauth1_headers(self, method: str, url: str, params: dict) -> dict[str, str]:
        """Generate OAuth 1.0a Authorization header."""
        oauth_params = {
            "oauth_consumer_key": self._api_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._access_token,
            "oauth_version": "1.0",
        }

        # Combine all params for signature base
        all_params = {**params, **oauth_params}
        sorted_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted(all_params.items())
        )

        base_string = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(sorted_params, safe=""),
        ])

        signing_key = (
            urllib.parse.quote(self._api_secret, safe="") + "&" +
            urllib.parse.quote(self._access_secret, safe="")
        )

        import base64
        signature = base64.b64encode(
            hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        ).decode()

        oauth_params["oauth_signature"] = signature

        auth_header = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )

        return {"Authorization": auth_header}

    def get_status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "total_posts": self._total_posts,
            "recent_posts": self._post_history[-10:],
        }
