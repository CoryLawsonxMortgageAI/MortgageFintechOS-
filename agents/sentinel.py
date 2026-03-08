"""SENTINEL — Codebase Intelligence Agent.

Scans and studies codebases, follows technology trends, reverse engineers
software patterns, and generates build plans for other agents to execute.
Acts as the technical architect directing ATLAS, CIPHER, FORGE, NEXUS, STORM.
"""

import json
from datetime import datetime, timezone
from typing import Any

import structlog

from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are SENTINEL, a senior software architect and codebase intelligence agent
for MortgageFintechOS — an autonomous AI operating system for mortgage lending.

You analyze codebases to understand architecture, identify patterns, spot anti-patterns,
and generate actionable build plans that other engineering agents can execute.

Your analysis should be structured, specific, and production-ready. Reference exact file
paths, function names, and line numbers when applicable. Your build plans should be
step-by-step instructions that ATLAS, CIPHER, FORGE, NEXUS, or STORM can directly execute."""


class SentinelAgent(BaseAgent):
    """SENTINEL: Codebase intelligence — scanning, trend analysis, reverse engineering."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="SENTINEL", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._scan_history: list[dict[str, Any]] = []
        self._trend_cache: dict[str, Any] = {}

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "scan_codebase": self._scan_codebase,
            "analyze_trends": self._analyze_trends,
            "reverse_engineer": self._reverse_engineer,
            "generate_build_plan": self._generate_build_plan,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown SENTINEL action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "scans_completed": len(self._scan_history),
        }

    def _get_state(self) -> dict[str, Any]:
        return {"scan_history": self._scan_history[-50:], "trend_cache": self._trend_cache}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._scan_history = data.get("scan_history", [])
        self._trend_cache = data.get("trend_cache", {})

    async def _scan_codebase(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Scan a GitHub repo's structure, patterns, and architecture."""
        repo = payload.get("repo", "")
        branch = payload.get("branch", "main")
        focus = payload.get("focus", "architecture")

        if not self._github:
            return {"error": "GitHub client not configured"}

        # Get repo info
        repo_info = await self._github.get_repo_info()

        # List root directory structure
        root_listing = await self._github.list_directory("", ref=branch)

        # Get recent commits to understand activity
        commits = await self._github.list_commits(sha=branch, per_page=10)

        # Get branches
        branches = await self._github.list_branches()

        # Build codebase summary
        structure = {
            "repo": repo_info,
            "root_files": root_listing.get("items", []),
            "recent_commits": commits.get("commits", []),
            "branches": branches.get("branches", []),
        }

        # Use LLM to analyze the structure
        analysis = ""
        if self._llm:
            prompt = f"""Analyze this codebase structure and provide a detailed architectural overview.

Focus area: {focus}

Repository info:
{json.dumps(repo_info, indent=2, default=str)}

Root directory listing:
{json.dumps(root_listing.get('items', []), indent=2)}

Recent commits:
{json.dumps(commits.get('commits', []), indent=2)}

Branches:
{json.dumps(branches.get('branches', []), indent=2)}

Provide:
1. Architecture overview (what type of project, key patterns)
2. Technology stack identified
3. Code organization quality (1-10)
4. Key files to review deeper
5. Potential improvements
6. Security considerations"""

            analysis = await self.llm_complete(
                action="scan_codebase",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
            )

        scan_result = {
            "repo": repo_info.get("name", repo),
            "branch": branch,
            "focus": focus,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "structure": structure,
            "analysis": analysis,
            "files_found": root_listing.get("count", 0),
            "recent_activity": len(commits.get("commits", [])),
        }

        self._scan_history.append({
            "repo": scan_result["repo"],
            "scanned_at": scan_result["scanned_at"],
            "files_found": scan_result["files_found"],
        })
        await self.save_state()

        return scan_result

    async def _analyze_trends(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze technology trends relevant to the codebase."""
        domain = payload.get("domain", "mortgage fintech")
        stack = payload.get("stack", "python, javascript, ai/ml")

        analysis = ""
        if self._llm:
            prompt = f"""Analyze current technology trends for the following domain and stack:

Domain: {domain}
Technology Stack: {stack}

Provide a structured analysis covering:
1. Emerging patterns and best practices in this domain
2. New libraries/frameworks worth adopting
3. Security trends and compliance requirements
4. AI/ML integration opportunities
5. Performance optimization techniques
6. Recommended architecture patterns
7. What top engineering teams are doing differently

Be specific with library names, version numbers, and implementation approaches."""

            analysis = await self.llm_complete(
                action="analyze_trends",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.5,
            )

        result = {
            "domain": domain,
            "stack": stack,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
        }
        self._trend_cache[domain] = result
        await self.save_state()
        return result

    async def _reverse_engineer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Reverse engineer a specific file or module from the repo."""
        path = payload.get("path", "")
        branch = payload.get("branch", "main")

        if not self._github:
            return {"error": "GitHub client not configured"}

        # Read the target file
        file_data = await self._github.get_file_content(path, ref=branch)
        if "error" in file_data:
            return file_data

        content = file_data.get("content", "")

        analysis = ""
        if self._llm:
            prompt = f"""Reverse engineer this code and provide a comprehensive analysis:

File: {path}
```
{content[:8000]}
```

Provide:
1. Purpose and responsibilities of this module
2. Design patterns used
3. Dependencies and coupling analysis
4. Data flow diagram (text-based)
5. Public API / interface contract
6. Internal implementation details
7. Edge cases and error handling
8. Suggestions for improvement
9. How to replicate this pattern for new features
10. Integration points with other modules"""

            analysis = await self.llm_complete(
                action="reverse_engineer",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=6000,
            )

        return {
            "path": path,
            "size": len(content),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
        }

    async def _generate_build_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate a production-ready build plan for other agents to execute."""
        feature = payload.get("feature", "")
        context = payload.get("context", "")
        target_agents = payload.get("target_agents", ["ATLAS", "NEXUS", "FORGE"])

        plan = ""
        if self._llm:
            prompt = f"""Generate a detailed, production-ready build plan for implementing the following feature.

Feature: {feature}
Context: {context}
Available agents to assign work:
- ATLAS: Full-stack engineering (API gen, features, migrations, component scaffolding)
- CIPHER: Security engineering (OWASP scanning, compliance, encryption audits)
- FORGE: DevOps (deploy, rollback, CI/CD pipeline, secret rotation)
- NEXUS: Code quality (PR review, test generation, tech debt analysis, refactoring)
- STORM: Data engineering (ETL, HMDA reporting, ULDD export, query optimization)

Target agents for this plan: {', '.join(target_agents)}

Generate a step-by-step build plan with:
1. Architecture decisions and rationale
2. Specific tasks for each target agent (with exact action names and payloads)
3. File paths to create/modify
4. Database changes needed
5. Test plan
6. Security considerations (for CIPHER)
7. Deployment steps (for FORGE)
8. Rollback strategy
9. Monitoring and alerting setup
10. Definition of done

Format each task as:
AGENT: [agent_name]
ACTION: [action_name]
PAYLOAD: [json payload]
DESCRIPTION: [what this step does]"""

            plan = await self.llm_complete(
                action="generate_build_plan",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                max_tokens=8000,
                temperature=0.4,
            )

        return {
            "feature": feature,
            "target_agents": target_agents,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "plan": plan,
        }
