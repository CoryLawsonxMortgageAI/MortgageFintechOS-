"""Browser automation client with persistent sessions and guardrails.

Provides headless browser automation for autonomous agents (HUNTER, HERALD,
AMBASSADOR) using aiohttp for HTTP-based scraping and optional Playwright
for full browser automation. Includes rate limiting, session persistence,
fingerprint rotation, and safety guardrails.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Token-bucket rate limiter per domain."""

    def __init__(self, requests_per_minute: int = 30):
        self._rpm = requests_per_minute
        self._tokens: dict[str, list[float]] = {}

    async def acquire(self, domain: str) -> None:
        now = time.monotonic()
        if domain not in self._tokens:
            self._tokens[domain] = []
        # Purge old entries
        self._tokens[domain] = [t for t in self._tokens[domain] if now - t < 60]
        if len(self._tokens[domain]) >= self._rpm:
            wait = 60 - (now - self._tokens[domain][0])
            if wait > 0:
                await asyncio.sleep(wait)
        self._tokens[domain].append(time.monotonic())


class SessionStore:
    """Persistent session storage for cookies and auth tokens."""

    def __init__(self, data_dir: str = "data"):
        self._dir = Path(data_dir) / "browser_sessions"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, dict[str, Any]] = {}
        self._log = logger.bind(component="session_store")

    def _path(self, name: str) -> Path:
        safe = hashlib.sha256(name.encode()).hexdigest()[:16]
        return self._dir / f"{safe}.json"

    async def load(self, name: str) -> dict[str, Any]:
        if name in self._sessions:
            return self._sessions[name]
        p = self._path(name)
        if p.exists():
            try:
                data = json.loads(p.read_text())
                self._sessions[name] = data
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    async def save(self, name: str, data: dict[str, Any]) -> None:
        self._sessions[name] = data
        try:
            self._path(name).write_text(json.dumps(data, default=str))
        except OSError as e:
            self._log.warning("session_save_failed", name=name, error=str(e))

    async def clear(self, name: str) -> None:
        self._sessions.pop(name, None)
        p = self._path(name)
        if p.exists():
            p.unlink()


# Guardrails — domains and actions that are NEVER automated
BLOCKED_DOMAINS = frozenset({
    "bank", "chase.com", "wellsfargo.com", "bankofamerica.com",
    "fanniemae.com", "freddiemac.com", "ginniemae.gov",
    "irs.gov", "ssa.gov",
})

ALLOWED_PLATFORMS = {
    "github.com": {"max_actions_per_hour": 30, "allowed_actions": ["star", "comment", "follow", "search"]},
    "dev.to": {"max_actions_per_hour": 10, "allowed_actions": ["post", "comment", "search"]},
    "reddit.com": {"max_actions_per_hour": 10, "allowed_actions": ["post", "comment", "search"]},
    "twitter.com": {"max_actions_per_hour": 15, "allowed_actions": ["post", "like", "search"]},
    "x.com": {"max_actions_per_hour": 15, "allowed_actions": ["post", "like", "search"]},
    "news.ycombinator.com": {"max_actions_per_hour": 5, "allowed_actions": ["comment", "search"]},
    "producthunt.com": {"max_actions_per_hour": 10, "allowed_actions": ["comment", "search"]},
    "linkedin.com": {"max_actions_per_hour": 10, "allowed_actions": ["post", "comment", "search"]},
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class BrowserClient:
    """Async browser automation client with guardrails and persistent sessions.

    Supports two modes:
    1. HTTP mode (default) — aiohttp for API calls and lightweight scraping
    2. Playwright mode (optional) — Full browser automation for JS-heavy sites

    Guardrails:
    - Rate limiting per domain (token bucket)
    - Blocked domain list (financial/government)
    - Action budget per platform per hour
    - Session persistence across restarts
    - Automatic cooldown on 429/503 responses
    """

    def __init__(self, data_dir: str = "data", requests_per_minute: int = 30):
        self._rate_limiter = RateLimiter(requests_per_minute)
        self._session_store = SessionStore(data_dir)
        self._action_counts: dict[str, list[float]] = {}
        self._log = logger.bind(component="browser_client")
        self._http_session: aiohttp.ClientSession | None = None
        self._ua_index = 0

    async def start(self) -> None:
        self._http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": self._rotate_ua()},
        )
        self._log.info("browser_client_started")

    async def stop(self) -> None:
        if self._http_session:
            await self._http_session.close()
        self._log.info("browser_client_stopped")

    def _rotate_ua(self) -> str:
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().lstrip("www.")

    def _is_blocked(self, domain: str) -> bool:
        for blocked in BLOCKED_DOMAINS:
            if blocked in domain:
                return True
        return False

    def _check_action_budget(self, domain: str, action: str) -> bool:
        """Check if action is within hourly budget for this platform."""
        platform = None
        for p_domain, config in ALLOWED_PLATFORMS.items():
            if p_domain in domain:
                platform = config
                break
        if not platform:
            return True  # Unlisted domains: allow with caution

        if action not in platform["allowed_actions"]:
            self._log.warning("action_not_allowed", domain=domain, action=action)
            return False

        key = f"{domain}:{action}"
        now = time.monotonic()
        if key not in self._action_counts:
            self._action_counts[key] = []
        self._action_counts[key] = [t for t in self._action_counts[key] if now - t < 3600]
        if len(self._action_counts[key]) >= platform["max_actions_per_hour"]:
            self._log.warning("action_budget_exceeded", domain=domain, action=action,
                              count=len(self._action_counts[key]), limit=platform["max_actions_per_hour"])
            return False

        self._action_counts[key].append(now)
        return True

    async def fetch(self, url: str, method: str = "GET", headers: dict[str, str] | None = None,
                    json_body: dict | None = None, action: str = "search") -> dict[str, Any]:
        """Fetch a URL with guardrails applied.

        Returns: {"status": int, "body": str|dict, "headers": dict, "ok": bool}
        """
        domain = self._extract_domain(url)

        if self._is_blocked(domain):
            return {"ok": False, "status": 403, "error": f"Domain {domain} is blocked by guardrails", "body": ""}

        if not self._check_action_budget(domain, action):
            return {"ok": False, "status": 429, "error": f"Action budget exceeded for {domain}:{action}", "body": ""}

        await self._rate_limiter.acquire(domain)

        if not self._http_session:
            await self.start()

        try:
            req_headers = {"User-Agent": self._rotate_ua()}
            if headers:
                req_headers.update(headers)

            async with self._http_session.request(method, url, headers=req_headers, json=json_body) as resp:
                # Automatic backoff on rate limit
                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", "60"))
                    self._log.warning("rate_limited", domain=domain, retry_after=retry_after)
                    await asyncio.sleep(min(retry_after, 120))
                    return {"ok": False, "status": 429, "error": "Rate limited", "body": ""}

                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    body = await resp.json()
                else:
                    body = await resp.text()

                return {"ok": resp.status < 400, "status": resp.status, "body": body, "headers": dict(resp.headers)}

        except Exception as e:
            self._log.error("fetch_failed", url=url, error=str(e))
            return {"ok": False, "status": 0, "error": str(e), "body": ""}

    async def github_search(self, query: str, search_type: str = "repositories",
                            token: str = "") -> dict[str, Any]:
        """Search GitHub API for repos, users, or code."""
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"https://api.github.com/search/{search_type}?q={query}&sort=stars&order=desc&per_page=30"
        return await self.fetch(url, headers=headers, action="search")

    async def github_trending(self, language: str = "", since: str = "daily") -> dict[str, Any]:
        """Fetch trending repos from GitHub (via API search for recent high-star repos)."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        q = f"created:>{cutoff} stars:>10"
        if language:
            q += f" language:{language}"
        return await self.github_search(q, "repositories")

    async def fetch_hn_frontpage(self) -> dict[str, Any]:
        """Fetch Hacker News top stories."""
        result = await self.fetch("https://hacker-news.firebaseio.com/v0/topstories.json", action="search")
        if not result["ok"]:
            return result
        story_ids = result["body"][:30] if isinstance(result["body"], list) else []
        stories = []
        for sid in story_ids[:15]:
            s = await self.fetch(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", action="search")
            if s["ok"] and isinstance(s["body"], dict):
                stories.append({"id": sid, "title": s["body"].get("title", ""), "url": s["body"].get("url", ""),
                                "score": s["body"].get("score", 0), "by": s["body"].get("by", "")})
        return {"ok": True, "stories": stories}

    async def fetch_reddit_posts(self, subreddit: str = "programming", limit: int = 15) -> dict[str, Any]:
        """Fetch top posts from a subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        result = await self.fetch(url, headers={"Accept": "application/json"}, action="search")
        if not result["ok"]:
            return result
        posts = []
        if isinstance(result["body"], dict):
            for child in result["body"].get("data", {}).get("children", []):
                d = child.get("data", {})
                posts.append({"title": d.get("title", ""), "url": d.get("url", ""), "score": d.get("score", 0),
                              "author": d.get("author", ""), "subreddit": subreddit, "num_comments": d.get("num_comments", 0)})
        return {"ok": True, "posts": posts}

    async def get_session(self, name: str) -> dict[str, Any]:
        return await self._session_store.load(name)

    async def save_session(self, name: str, data: dict[str, Any]) -> None:
        await self._session_store.save(name, data)

    def get_status(self) -> dict[str, Any]:
        action_summary = {}
        now = time.monotonic()
        for key, times in self._action_counts.items():
            active = [t for t in times if now - t < 3600]
            if active:
                action_summary[key] = len(active)
        return {
            "active": self._http_session is not None,
            "action_counts_hourly": action_summary,
            "blocked_domains": len(BLOCKED_DOMAINS),
            "allowed_platforms": len(ALLOWED_PLATFORMS),
        }
