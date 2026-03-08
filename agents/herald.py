"""HERALD Agent — Autonomous Build-in-Public Content Creation.

Generates dev-focused content: tweets/threads, dev.to articles, changelogs,
and LinkedIn posts. Uses LLM routing for high-quality writing with mortgage
fintech domain expertise. Maintains a content calendar and tracks engagement.

Part of the Growth Ops division — creates content while you sleep.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

# Content templates for build-in-public posts
TEMPLATES = {
    "milestone": {
        "system": "You are a developer advocate writing build-in-public updates for a mortgage fintech AI platform called MortgageFintechOS. Write engaging, technical, authentic content that resonates with developers.",
        "format": "Milestone: {title}\n\nDetails: {details}\n\nWrite a concise, authentic build-in-public post. Include what was built, why it matters, and a technical insight. Keep it under {max_chars} characters.",
    },
    "technical_insight": {
        "system": "You are a senior engineer sharing technical insights from building an autonomous AI agent system for mortgage lending. Write for a dev audience on Twitter/X.",
        "format": "Topic: {title}\n\nContext: {details}\n\nWrite a technical thread (3-5 tweets, each under 280 chars). Focus on architecture decisions, trade-offs, and lessons learned. Use a conversational, authentic tone.",
    },
    "changelog": {
        "system": "You are writing a changelog entry for MortgageFintechOS, an AI-powered mortgage operating system with 13+ autonomous agents.",
        "format": "Changes:\n{changes}\n\nWrite a developer-friendly changelog in markdown. Group by category (Added, Changed, Fixed, Security). Be specific and concise.",
    },
    "devto_article": {
        "system": "You are writing a dev.to article about building AI agents for the mortgage industry. Write engaging, technical content with code examples where relevant.",
        "format": "Title: {title}\n\nOutline: {details}\n\nWrite a complete dev.to article (800-1500 words). Include an engaging intro, technical details with code snippets, architecture diagrams described in text, and a conclusion with next steps.",
    },
    "linkedin_post": {
        "system": "You are a fintech founder sharing insights about building MortgageFintechOS. Write professional but authentic LinkedIn content that demonstrates technical expertise.",
        "format": "Topic: {title}\n\nKey points: {details}\n\nWrite a LinkedIn post (200-400 words). Open with a hook, share specific insights, and end with a question to drive engagement.",
    },
}

# Content calendar — maps day_of_week to default content types
CONTENT_CALENDAR = {
    0: "milestone",          # Monday: weekly milestone update
    1: "technical_insight",  # Tuesday: technical thread
    2: "devto_article",      # Wednesday: long-form article
    3: "technical_insight",  # Thursday: technical thread
    4: "changelog",          # Friday: weekly changelog
    5: "linkedin_post",      # Saturday: professional insight
    6: "milestone",          # Sunday: week preview
}


class HeraldAgent(BaseAgent):
    """Autonomous build-in-public content creation agent.

    Actions:
    - generate_post: Create a single post (tweet, thread, article)
    - generate_changelog: Create changelog from recent commits/changes
    - generate_thread: Create a Twitter/X thread on a technical topic
    - generate_article: Create a dev.to article
    - daily_content: Auto-generate content based on content calendar
    - get_content_queue: View pending content
    """

    def __init__(self, max_retries: int = 3):
        super().__init__(name="HERALD", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self.handlers = {
            "generate_post": self._generate_post,
            "generate_changelog": self._generate_changelog,
            "generate_thread": self._generate_thread,
            "generate_article": self._generate_article,
            "daily_content": self._daily_content,
            "get_content_queue": self._get_content_queue,
        }
        self._content_queue: list[dict[str, Any]] = []
        self._published: list[dict[str, Any]] = []
        self._content_count = 0

    async def execute(self, task: Task) -> dict[str, Any]:
        handler = self.handlers.get(task.action)
        if not handler:
            return {"error": f"Unknown action: {task.action}", "available": list(self.handlers.keys())}
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "content_generated": self._content_count,
            "queue_size": len(self._content_queue),
            "published": len(self._published),
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }

    # --- Content generation ---

    async def _llm_generate(self, template_name: str, variables: dict[str, str], max_chars: int = 280) -> str:
        """Generate content using LLM with template."""
        template = TEMPLATES.get(template_name, TEMPLATES["milestone"])
        variables["max_chars"] = str(max_chars)
        prompt = template["format"].format(**{k: variables.get(k, "") for k in ["title", "details", "changes", "max_chars"]})

        if self._llm:
            content = await self.llm_complete(
                action="content_generation",
                system_prompt=template["system"],
                user_prompt=prompt,
                temperature=0.7,
                max_tokens=2048,
            )
            if content:
                return content

        # Fallback: structured template without LLM
        title = variables.get("title", "Update")
        details = variables.get("details", "")
        return f"Building in public: {title}\n\n{details}\n\n#buildinpublic #fintech #ai #mortgage"

    async def _generate_post(self, payload: dict) -> dict:
        """Generate a single social media post."""
        title = payload.get("title", "MortgageFintechOS Update")
        details = payload.get("details", "")
        platform = payload.get("platform", "twitter")
        template = payload.get("template", "milestone")

        max_chars = {"twitter": 280, "linkedin": 3000, "devto": 10000}.get(platform, 280)

        content = await self._llm_generate(template, {"title": title, "details": details}, max_chars)

        post = {
            "id": f"post_{self._content_count}",
            "type": template,
            "platform": platform,
            "content": content,
            "title": title,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._content_queue.append(post)
        self._content_count += 1

        return {"post": post, "content_count": self._content_count}

    async def _generate_changelog(self, payload: dict) -> dict:
        """Generate a changelog from recent changes."""
        changes = payload.get("changes", "")

        # Try to get real changes from GitHub
        if not changes and self._github:
            try:
                commits = await self._github.list_commits(per_page=20)
                if isinstance(commits, list):
                    changes = "\n".join([
                        f"- {c.get('commit', {}).get('message', '').split(chr(10))[0]}"
                        for c in commits[:15]
                    ])
            except Exception:
                pass

        if not changes:
            changes = "- System improvements and stability updates"

        content = await self._llm_generate("changelog", {"changes": changes, "title": "", "details": ""}, max_chars=5000)

        post = {
            "id": f"changelog_{self._content_count}",
            "type": "changelog",
            "platform": "all",
            "content": content,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._content_queue.append(post)
        self._content_count += 1

        return {"changelog": post}

    async def _generate_thread(self, payload: dict) -> dict:
        """Generate a Twitter/X thread on a technical topic."""
        title = payload.get("title", "Building AI Agents for Mortgage Lending")
        details = payload.get("details", "Architecture, challenges, and lessons learned")

        content = await self._llm_generate("technical_insight", {"title": title, "details": details}, max_chars=1400)

        # Split into tweets
        tweets = []
        if content:
            parts = content.split("\n\n")
            for i, part in enumerate(parts):
                part = part.strip()
                if part and len(part) > 10:
                    tweets.append({"index": i + 1, "text": part[:280], "chars": len(part[:280])})

        post = {
            "id": f"thread_{self._content_count}",
            "type": "thread",
            "platform": "twitter",
            "tweets": tweets,
            "tweet_count": len(tweets),
            "title": title,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._content_queue.append(post)
        self._content_count += 1

        return {"thread": post}

    async def _generate_article(self, payload: dict) -> dict:
        """Generate a dev.to style article."""
        title = payload.get("title", "How We Built an Autonomous AI Agent System for Mortgage Lending")
        details = payload.get("details", "Architecture overview, agent design, LLM routing, and lessons learned")

        content = await self._llm_generate("devto_article", {"title": title, "details": details}, max_chars=10000)

        post = {
            "id": f"article_{self._content_count}",
            "type": "article",
            "platform": "devto",
            "content": content,
            "title": title,
            "word_count": len(content.split()) if content else 0,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._content_queue.append(post)
        self._content_count += 1

        return {"article": post}

    async def _daily_content(self, payload: dict) -> dict:
        """Auto-generate content based on content calendar."""
        day = datetime.now(timezone.utc).weekday()
        content_type = CONTENT_CALENDAR.get(day, "milestone")

        # Generate content based on calendar
        topics = {
            "milestone": {"title": "Weekly Progress Update", "details": "Agent system improvements, new integrations, performance gains"},
            "technical_insight": {"title": "AI Agent Architecture Deep Dive", "details": "How our 13-agent system handles concurrent mortgage workflows"},
            "changelog": {},
            "devto_article": {"title": "Building Autonomous AI Agents for Mortgage Lending", "details": "Complete architecture walkthrough"},
            "linkedin_post": {"title": "The Future of Mortgage Tech", "details": "How AI agents are transforming loan processing"},
        }

        defaults = topics.get(content_type, topics["milestone"])
        merged = {**defaults, **payload}

        handler_map = {
            "milestone": self._generate_post,
            "technical_insight": self._generate_thread,
            "changelog": self._generate_changelog,
            "devto_article": self._generate_article,
            "linkedin_post": self._generate_post,
        }

        handler = handler_map.get(content_type, self._generate_post)
        if content_type == "linkedin_post":
            merged["platform"] = "linkedin"
            merged["template"] = "linkedin_post"

        result = await handler(merged)
        result["calendar_day"] = day
        result["content_type"] = content_type

        return result

    async def _get_content_queue(self, payload: dict) -> dict:
        """Return pending content in the queue."""
        status_filter = payload.get("status", "")
        items = self._content_queue
        if status_filter:
            items = [c for c in items if c.get("status") == status_filter]

        return {
            "queue": items[-20:],
            "total": len(items),
            "drafts": sum(1 for c in self._content_queue if c.get("status") == "draft"),
            "published": len(self._published),
        }

    # --- State persistence ---

    def _get_state(self) -> dict[str, Any]:
        return {
            "content_queue": self._content_queue[-100:],
            "published": self._published[-100:],
            "content_count": self._content_count,
        }

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._content_queue = data.get("content_queue", [])
        self._published = data.get("published", [])
        self._content_count = data.get("content_count", 0)
