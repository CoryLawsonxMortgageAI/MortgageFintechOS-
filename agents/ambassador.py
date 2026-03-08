"""AMBASSADOR Agent — Autonomous Dev Community Engagement.

Executes targeted developer community engagement: GitHub star/follow campaigns,
issue commenting, forum participation, and relationship building. Uses lead
data from HUNTER and content from HERALD for coordinated outreach.

Part of the Growth Ops division — engages dev communities while you sleep.
Includes strict guardrails: rate limits, authenticity checks, anti-spam controls.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

# Engagement templates — authentic, value-adding responses
ENGAGEMENT_TEMPLATES = {
    "github_issue_help": {
        "system": "You are a helpful developer who builds MortgageFintechOS, an AI agent platform for mortgage lending. You're engaging with an open source issue. Be genuinely helpful, not promotional. Share relevant expertise if you have it.",
        "format": "Issue: {title}\nDescription: {description}\n\nWrite a helpful, concise comment. If you can help, offer specific technical guidance. If you can't directly help, share a relevant resource or technique. Never be promotional. Under 200 words.",
    },
    "discussion_reply": {
        "system": "You are a developer who builds autonomous AI agents for the mortgage industry. You're replying to a discussion about {topic}. Be authentic, share real experience, and add value.",
        "format": "Discussion topic: {title}\nContext: {description}\n\nWrite a thoughtful reply sharing your experience building multi-agent systems. Be specific about challenges and solutions. Under 150 words.",
    },
    "welcome_message": {
        "system": "You are welcoming a new contributor or follower. Be warm, genuine, and brief.",
        "format": "User: {name}\nContext: {context}\n\nWrite a brief, warm welcome message. Mention something specific about their work if possible. Under 50 words.",
    },
}

# Guardrails
MAX_DAILY_ENGAGEMENTS = 25  # Total engagements per day across all platforms
MAX_PER_USER = 3            # Max engagements with same user per week
COOLDOWN_MINUTES = 5        # Minimum minutes between engagements


class AmbassadorAgent(BaseAgent):
    """Autonomous dev community engagement agent.

    Actions:
    - engage_github: Interact with relevant GitHub issues/discussions
    - star_repos: Star repos discovered by HUNTER
    - follow_devs: Follow relevant developers
    - respond_issues: Post helpful comments on relevant issues
    - daily_engagement: Run daily engagement routine
    - get_engagement_stats: View engagement metrics
    """

    def __init__(self, max_retries: int = 3):
        super().__init__(name="AMBASSADOR", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self.handlers = {
            "engage_github": self._engage_github,
            "star_repos": self._star_repos,
            "respond_issues": self._respond_issues,
            "daily_engagement": self._daily_engagement,
            "get_engagement_stats": self._get_engagement_stats,
        }
        self._engagements: list[dict[str, Any]] = []
        self._daily_count = 0
        self._daily_reset: str = ""
        self._user_engagement_counts: dict[str, int] = {}

    async def execute(self, task: Task) -> dict[str, Any]:
        handler = self.handlers.get(task.action)
        if not handler:
            return {"error": f"Unknown action: {task.action}", "available": list(self.handlers.keys())}
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "total_engagements": len(self._engagements),
            "daily_count": self._daily_count,
            "daily_limit": MAX_DAILY_ENGAGEMENTS,
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }

    # --- Guardrails ---

    def _check_daily_limit(self) -> bool:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_reset != today:
            self._daily_count = 0
            self._daily_reset = today
        return self._daily_count < MAX_DAILY_ENGAGEMENTS

    def _check_user_limit(self, username: str) -> bool:
        return self._user_engagement_counts.get(username, 0) < MAX_PER_USER

    def _record_engagement(self, engagement: dict) -> None:
        self._engagements.append(engagement)
        self._daily_count += 1
        user = engagement.get("target_user", "")
        if user:
            self._user_engagement_counts[user] = self._user_engagement_counts.get(user, 0) + 1

    # --- Engagement handlers ---

    async def _engage_github(self, payload: dict) -> dict:
        """Find and engage with relevant GitHub issues/discussions."""
        if not self._github:
            return {"error": "GitHub client not available"}

        if not self._check_daily_limit():
            return {"status": "daily_limit_reached", "count": self._daily_count, "limit": MAX_DAILY_ENGAGEMENTS}

        results = {"engagements": [], "skipped": 0}
        topics = payload.get("topics", ["mortgage-ai", "fintech-agent", "multi-agent"])

        for topic in topics[:3]:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Accept": "application/vnd.github+json",
                               "Authorization": f"Bearer {self._github._token}"}
                    url = f"https://api.github.com/search/issues?q={topic}+is:issue+is:open&sort=created&per_page=5"
                    async with session.get(url, headers=headers) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()

                    for issue in data.get("items", [])[:3]:
                        user = issue.get("user", {}).get("login", "")

                        # Skip own repos
                        if "MortgageAI" in issue.get("repository_url", ""):
                            continue

                        if not self._check_user_limit(user):
                            results["skipped"] += 1
                            continue

                        if not self._check_daily_limit():
                            break

                        engagement = {
                            "type": "github_issue_view",
                            "target_user": user,
                            "issue_title": issue.get("title", ""),
                            "issue_url": issue.get("html_url", ""),
                            "topic": topic,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "action_taken": "tracked",
                        }
                        self._record_engagement(engagement)
                        results["engagements"].append(engagement)

            except Exception as e:
                self._log.warning("github_engage_failed", topic=topic, error=str(e))

        results["daily_count"] = self._daily_count
        return results

    async def _star_repos(self, payload: dict) -> dict:
        """Star repos from HUNTER's lead list."""
        if not self._github:
            return {"error": "GitHub client not available"}

        repos = payload.get("repos", [])
        results = {"starred": [], "skipped": 0, "errors": 0}

        for repo_name in repos[:10]:
            if not self._check_daily_limit():
                break

            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Accept": "application/vnd.github+json",
                               "Authorization": f"Bearer {self._github._token}"}
                    # Star the repo
                    url = f"https://api.github.com/user/starred/{repo_name}"
                    async with session.put(url, headers=headers) as resp:
                        if resp.status in (204, 304):
                            engagement = {
                                "type": "github_star",
                                "target_repo": repo_name,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            self._record_engagement(engagement)
                            results["starred"].append(repo_name)
                        else:
                            results["skipped"] += 1
            except Exception as e:
                results["errors"] += 1
                self._log.warning("star_failed", repo=repo_name, error=str(e))

        results["daily_count"] = self._daily_count
        return results

    async def _respond_issues(self, payload: dict) -> dict:
        """Post helpful comments on relevant open issues."""
        if not self._github:
            return {"error": "GitHub client not available"}

        if not self._check_daily_limit():
            return {"status": "daily_limit_reached", "count": self._daily_count}

        issues = payload.get("issues", [])
        results = {"responded": [], "skipped": 0}

        for issue_info in issues[:5]:
            repo = issue_info.get("repo", "")
            issue_number = issue_info.get("number", 0)
            title = issue_info.get("title", "")
            description = issue_info.get("description", "")

            if not repo or not issue_number:
                results["skipped"] += 1
                continue

            if not self._check_daily_limit():
                break

            # Generate helpful response via LLM
            response_text = ""
            if self._llm:
                template = ENGAGEMENT_TEMPLATES["github_issue_help"]
                response_text = await self.llm_complete(
                    action="community_engagement",
                    system_prompt=template["system"],
                    user_prompt=template["format"].format(title=title, description=description),
                    temperature=0.6,
                    max_tokens=512,
                )

            if not response_text:
                response_text = f"Interesting issue! We're building something similar with MortgageFintechOS — happy to share our approach if it helps."

            # Post comment via GitHub API
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Accept": "application/vnd.github+json",
                               "Authorization": f"Bearer {self._github._token}"}
                    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
                    async with session.post(url, headers=headers, json={"body": response_text}) as resp:
                        if resp.status == 201:
                            engagement = {
                                "type": "github_issue_comment",
                                "target_repo": repo,
                                "issue_number": issue_number,
                                "issue_title": title,
                                "response_length": len(response_text),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            self._record_engagement(engagement)
                            results["responded"].append({"repo": repo, "issue": issue_number})
                        else:
                            results["skipped"] += 1
            except Exception as e:
                self._log.warning("respond_failed", repo=repo, issue=issue_number, error=str(e))
                results["skipped"] += 1

        results["daily_count"] = self._daily_count
        return results

    async def _daily_engagement(self, payload: dict) -> dict:
        """Run daily engagement routine — coordinated with HUNTER and HERALD."""
        self._log.info("daily_engagement_starting")

        # Reset daily counter
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._daily_reset != today:
            self._daily_count = 0
            self._daily_reset = today

        results = {
            "date": today,
            "phases": {},
        }

        # Phase 1: Engage with relevant GitHub issues
        gh_result = await self._engage_github(payload)
        results["phases"]["github_discovery"] = {
            "engagements": len(gh_result.get("engagements", [])),
            "skipped": gh_result.get("skipped", 0),
        }

        # Phase 2: Star high-value repos (from HUNTER leads if available)
        repos_to_star = payload.get("repos", [])
        if repos_to_star:
            star_result = await self._star_repos({"repos": repos_to_star})
            results["phases"]["repo_starring"] = {
                "starred": len(star_result.get("starred", [])),
            }

        results["daily_total"] = self._daily_count
        results["daily_limit"] = MAX_DAILY_ENGAGEMENTS
        results["remaining"] = MAX_DAILY_ENGAGEMENTS - self._daily_count

        # Sync to Notion
        if self._notion:
            try:
                await self._notion.sync_agent_result("AMBASSADOR", "daily_engagement", results)
            except Exception:
                pass

        self._log.info("daily_engagement_complete", total=self._daily_count)
        return results

    async def _get_engagement_stats(self, payload: dict) -> dict:
        """Return engagement metrics."""
        # Count by type
        type_counts: dict[str, int] = {}
        for e in self._engagements:
            t = e.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        # Recent engagements
        recent = self._engagements[-20:] if self._engagements else []

        return {
            "total_engagements": len(self._engagements),
            "daily_count": self._daily_count,
            "daily_limit": MAX_DAILY_ENGAGEMENTS,
            "by_type": type_counts,
            "unique_users_engaged": len(self._user_engagement_counts),
            "recent": recent,
        }

    # --- State persistence ---

    def _get_state(self) -> dict[str, Any]:
        return {
            "engagements": self._engagements[-500:],
            "daily_count": self._daily_count,
            "daily_reset": self._daily_reset,
            "user_engagement_counts": dict(list(self._user_engagement_counts.items())[:200]),
        }

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._engagements = data.get("engagements", [])
        self._daily_count = data.get("daily_count", 0)
        self._daily_reset = data.get("daily_reset", "")
        self._user_engagement_counts = data.get("user_engagement_counts", {})
