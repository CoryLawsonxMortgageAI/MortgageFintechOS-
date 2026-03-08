"""HUNTER Agent — Autonomous Dev Lead Discovery.

Runs 24/7 scanning GitHub trending, Hacker News, Reddit, and Product Hunt
for developer leads. Identifies high-value targets (active open source devs,
fintech builders, mortgage tech teams) and scores them for outreach priority.

Part of the Growth Ops division — operates autonomously while you sleep.
"""

import re
from datetime import datetime, timezone
from typing import Any

import structlog

from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

# Lead scoring keywords — weighted by relevance to mortgage fintech
LEAD_SIGNALS = {
    "mortgage": 10, "fintech": 8, "lending": 9, "loan": 7,
    "underwriting": 10, "compliance": 6, "regtech": 8,
    "ai-agent": 7, "autonomous": 6, "multi-agent": 8,
    "agentic": 7, "orchestration": 5, "llm": 4,
    "banking": 5, "defi": 3, "credit": 5, "financial": 4,
    "real-estate": 6, "proptech": 7, "hmda": 10, "uldd": 10,
    "document-processing": 6, "ocr": 4, "fraud-detection": 7,
}

# Subreddits to monitor
TARGET_SUBREDDITS = [
    "fintech", "artificial", "MachineLearning", "programming",
    "Python", "javascript", "devops", "startups",
    "realestate", "mortgage",
]


class HunterAgent(BaseAgent):
    """Autonomous dev lead discovery agent.

    Actions:
    - scan_github: Search GitHub trending + topic repos for dev leads
    - scan_hn: Monitor Hacker News for fintech/AI discussions
    - scan_reddit: Monitor subreddits for relevant threads
    - score_leads: Score and rank discovered leads
    - full_sweep: Run all scans + scoring in sequence
    """

    def __init__(self, max_retries: int = 3):
        super().__init__(name="HUNTER", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self.handlers = {
            "scan_github": self._scan_github,
            "scan_hn": self._scan_hn,
            "scan_reddit": self._scan_reddit,
            "score_leads": self._score_leads,
            "full_sweep": self._full_sweep,
        }
        self._leads: list[dict[str, Any]] = []
        self._sweep_count = 0

    async def execute(self, task: Task) -> dict[str, Any]:
        handler = self.handlers.get(task.action)
        if not handler:
            return {"error": f"Unknown action: {task.action}", "available": list(self.handlers.keys())}
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "leads_discovered": len(self._leads),
            "sweep_count": self._sweep_count,
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }

    # --- Lead scoring ---

    def _score_text(self, text: str) -> int:
        """Score text content against lead signals."""
        text_lower = text.lower()
        score = 0
        matched = []
        for keyword, weight in LEAD_SIGNALS.items():
            if keyword in text_lower:
                score += weight
                matched.append(keyword)
        return score

    def _deduplicate_leads(self, new_leads: list[dict]) -> list[dict]:
        """Deduplicate against existing leads by URL or name."""
        existing_keys = {(l.get("url", ""), l.get("name", "")) for l in self._leads}
        unique = []
        for lead in new_leads:
            key = (lead.get("url", ""), lead.get("name", ""))
            if key not in existing_keys:
                existing_keys.add(key)
                unique.append(lead)
        return unique

    # --- Scan handlers ---

    async def _scan_github(self, payload: dict) -> dict:
        """Scan GitHub for dev leads via trending repos and topic searches."""
        if not hasattr(self, "_browser") or not self._browser:
            # Try to use browser client from integrations
            browser = getattr(self, "_browser_client", None)
            if not browser:
                return await self._scan_github_via_api(payload)

        language = payload.get("language", "python")
        results = {"source": "github", "leads": [], "repos_scanned": 0}

        # 1. Trending repos
        trending = await self._browser_client.github_trending(language=language)
        if trending.get("ok") and isinstance(trending.get("body"), dict):
            for repo in trending["body"].get("items", [])[:20]:
                score = self._score_text(f"{repo.get('description', '')} {repo.get('full_name', '')}")
                if score >= 5:
                    lead = {
                        "type": "github_repo",
                        "name": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "language": repo.get("language", ""),
                        "owner": repo.get("owner", {}).get("login", ""),
                        "score": score,
                        "source": "github_trending",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                    results["leads"].append(lead)
                results["repos_scanned"] += 1

        # 2. Topic searches
        for topic in ["mortgage-ai", "fintech-agent", "loan-automation", "multi-agent-system"]:
            search = await self._browser_client.github_search(topic, "repositories",
                                                              token=self._github._token if self._github else "")
            if search.get("ok") and isinstance(search.get("body"), dict):
                for repo in search["body"].get("items", [])[:10]:
                    score = self._score_text(f"{repo.get('description', '')} {repo.get('full_name', '')} {topic}")
                    lead = {
                        "type": "github_repo",
                        "name": repo.get("full_name", ""),
                        "url": repo.get("html_url", ""),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "owner": repo.get("owner", {}).get("login", ""),
                        "score": score,
                        "source": f"github_topic:{topic}",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                    results["leads"].append(lead)
                    results["repos_scanned"] += 1

        # Deduplicate and store
        new_leads = self._deduplicate_leads(results["leads"])
        self._leads.extend(new_leads)
        results["new_leads"] = len(new_leads)
        results["total_leads"] = len(self._leads)

        # Sync to Notion if available
        if self._notion and new_leads:
            try:
                await self._notion.sync_agent_result("HUNTER", "scan_github", {
                    "new_leads": len(new_leads), "top_leads": sorted(new_leads, key=lambda l: l["score"], reverse=True)[:5]
                })
            except Exception:
                pass

        return results

    async def _scan_github_via_api(self, payload: dict) -> dict:
        """Fallback: scan GitHub using the GitHub client directly."""
        if not self._github:
            return {"error": "No GitHub client or browser client available"}

        results = {"source": "github_api", "leads": [], "repos_scanned": 0}

        # Use GitHub client's search if available (via raw API)
        for query in ["mortgage AI", "fintech agent", "multi-agent LLM", "loan automation"]:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Accept": "application/vnd.github+json",
                               "Authorization": f"Bearer {self._github._token}"}
                    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=10"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for repo in data.get("items", []):
                                score = self._score_text(f"{repo.get('description', '')} {query}")
                                if score >= 3:
                                    results["leads"].append({
                                        "type": "github_repo", "name": repo.get("full_name", ""),
                                        "url": repo.get("html_url", ""), "description": repo.get("description", ""),
                                        "stars": repo.get("stargazers_count", 0), "score": score,
                                        "source": f"github_api:{query}",
                                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                                    })
                                results["repos_scanned"] += 1
            except Exception as e:
                self._log.warning("github_api_search_failed", query=query, error=str(e))

        new_leads = self._deduplicate_leads(results["leads"])
        self._leads.extend(new_leads)
        results["new_leads"] = len(new_leads)
        results["total_leads"] = len(self._leads)
        return results

    async def _scan_hn(self, payload: dict) -> dict:
        """Scan Hacker News frontpage for relevant discussions."""
        browser = getattr(self, "_browser_client", None)
        results = {"source": "hackernews", "leads": [], "stories_scanned": 0}

        if browser:
            hn = await browser.fetch_hn_frontpage()
            stories = hn.get("stories", [])
        else:
            # Fallback: direct API call
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://hacker-news.firebaseio.com/v0/topstories.json") as resp:
                        ids = await resp.json()
                    stories = []
                    for sid in ids[:20]:
                        async with session.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json") as resp:
                            s = await resp.json()
                            stories.append({"title": s.get("title", ""), "url": s.get("url", ""),
                                            "score": s.get("score", 0), "by": s.get("by", "")})
            except Exception as e:
                return {"source": "hackernews", "error": str(e), "leads": []}

        for story in stories:
            score = self._score_text(story.get("title", ""))
            if score >= 4:
                results["leads"].append({
                    "type": "hn_story", "name": story.get("title", ""),
                    "url": story.get("url", ""), "hn_score": story.get("score", 0),
                    "author": story.get("by", ""), "score": score,
                    "source": "hackernews",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                })
            results["stories_scanned"] += 1

        new_leads = self._deduplicate_leads(results["leads"])
        self._leads.extend(new_leads)
        results["new_leads"] = len(new_leads)
        results["total_leads"] = len(self._leads)
        return results

    async def _scan_reddit(self, payload: dict) -> dict:
        """Scan targeted subreddits for relevant posts."""
        browser = getattr(self, "_browser_client", None)
        subreddits = payload.get("subreddits", TARGET_SUBREDDITS[:5])
        results = {"source": "reddit", "leads": [], "posts_scanned": 0}

        for sub in subreddits:
            if browser:
                data = await browser.fetch_reddit_posts(sub, limit=10)
                posts = data.get("posts", [])
            else:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        headers = {"User-Agent": "MortgageFintechOS/1.0"}
                        async with session.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=10", headers=headers) as resp:
                            raw = await resp.json()
                            posts = []
                            for child in raw.get("data", {}).get("children", []):
                                d = child.get("data", {})
                                posts.append({"title": d.get("title", ""), "url": d.get("url", ""),
                                              "score": d.get("score", 0), "author": d.get("author", "")})
                except Exception:
                    continue

            for post in posts:
                score = self._score_text(post.get("title", ""))
                if score >= 4:
                    results["leads"].append({
                        "type": "reddit_post", "name": post.get("title", ""),
                        "url": post.get("url", ""), "reddit_score": post.get("score", 0),
                        "author": post.get("author", ""), "subreddit": sub, "score": score,
                        "source": f"reddit:{sub}",
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    })
                results["posts_scanned"] += 1

        new_leads = self._deduplicate_leads(results["leads"])
        self._leads.extend(new_leads)
        results["new_leads"] = len(new_leads)
        results["total_leads"] = len(self._leads)
        return results

    async def _score_leads(self, payload: dict) -> dict:
        """Re-score and rank all discovered leads."""
        for lead in self._leads:
            # Re-score with latest signals
            text = f"{lead.get('name', '')} {lead.get('description', '')} {lead.get('source', '')}"
            lead["score"] = self._score_text(text)

            # Bonus: high engagement
            if lead.get("stars", 0) > 1000:
                lead["score"] += 5
            if lead.get("hn_score", 0) > 100:
                lead["score"] += 3
            if lead.get("reddit_score", 0) > 50:
                lead["score"] += 2

        # Sort by score
        ranked = sorted(self._leads, key=lambda l: l["score"], reverse=True)

        # Tier classification
        tiers = {"hot": [], "warm": [], "cold": []}
        for lead in ranked:
            if lead["score"] >= 15:
                tiers["hot"].append(lead)
            elif lead["score"] >= 8:
                tiers["warm"].append(lead)
            else:
                tiers["cold"].append(lead)

        return {
            "total_leads": len(self._leads),
            "hot": len(tiers["hot"]),
            "warm": len(tiers["warm"]),
            "cold": len(tiers["cold"]),
            "top_10": ranked[:10],
            "tiers": {k: len(v) for k, v in tiers.items()},
        }

    async def _full_sweep(self, payload: dict) -> dict:
        """Run complete lead discovery sweep across all platforms."""
        self._sweep_count += 1
        self._log.info("full_sweep_starting", sweep_number=self._sweep_count)

        gh = await self._scan_github(payload)
        hn = await self._scan_hn(payload)
        rd = await self._scan_reddit(payload)
        scored = await self._score_leads(payload)

        result = {
            "sweep_number": self._sweep_count,
            "github": {"new_leads": gh.get("new_leads", 0), "repos_scanned": gh.get("repos_scanned", 0)},
            "hackernews": {"new_leads": hn.get("new_leads", 0), "stories_scanned": hn.get("stories_scanned", 0)},
            "reddit": {"new_leads": rd.get("new_leads", 0), "posts_scanned": rd.get("posts_scanned", 0)},
            "scoring": scored,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Auto-sync results to Notion
        if self._notion:
            try:
                await self._notion.sync_agent_result("HUNTER", "full_sweep", {
                    "sweep": self._sweep_count,
                    "total_leads": scored["total_leads"],
                    "hot": scored["hot"], "warm": scored["warm"],
                })
            except Exception:
                pass

        self._log.info("full_sweep_complete", **{k: v for k, v in result.items() if k != "scoring"})
        return result

    # --- State persistence ---

    def _get_state(self) -> dict[str, Any]:
        return {"leads": self._leads[-500:], "sweep_count": self._sweep_count}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._leads = data.get("leads", [])
        self._sweep_count = data.get("sweep_count", 0)

    def set_browser_client(self, browser: Any) -> None:
        self._browser_client = browser
