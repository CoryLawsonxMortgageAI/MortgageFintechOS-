"""NEXUS — Code Quality Agent.

Handles PR review, test generation, tech debt analysis,
and automated refactoring via real GitHub PR APIs and LLM-powered analysis.
"""

import json
from datetime import datetime, timezone
from typing import Any
import structlog
from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are NEXUS, a code quality agent for MortgageFintechOS.
You review pull requests, generate tests, analyze technical debt, and refactor code.
Your reviews should be thorough, specific, and constructive. Reference exact lines.
Follow SOLID principles, clean code practices, and mortgage industry security standards."""


class NexusAgent(BaseAgent):
    """NEXUS: Code quality — PR review, tests, tech debt via GitHub APIs."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="NEXUS", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._review_history: list[dict[str, Any]] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "review_pr": self._review_pr,
            "generate_tests": self._generate_tests,
            "analyze_debt": self._analyze_debt,
            "refactor": self._refactor,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown NEXUS action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "reviews_completed": len(self._review_history),
        }

    def _get_state(self) -> dict[str, Any]:
        return {"review_history": self._review_history[-100:]}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._review_history = data.get("review_history", [])

    async def _review_pr(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Review a pull request using real GitHub diff + LLM analysis."""
        pr_number = payload.get("pr_number", 0)
        if not pr_number:
            return {"error": "pr_number is required"}

        result: dict[str, Any] = {
            "pr_number": pr_number,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        if not self._github:
            return {**result, "error": "GitHub not configured"}

        pr_info = await self._github.get_pull_request(pr_number)
        pr_files = await self._github.get_pr_files(pr_number)
        pr_diff = await self._github.get_pr_diff(pr_number)

        result["pr_info"] = pr_info
        result["files_changed"] = pr_files.get("count", 0)

        if self._llm:
            review_text = await self.llm_complete(
                action="review_pr",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Review this pull request:

Title: {pr_info.get('title', '')}
Description: {pr_info.get('body', '')[:500]}
Author: {pr_info.get('user', '')}
Files changed: {pr_files.get('count', 0)}
Additions: {pr_info.get('additions', 0)}, Deletions: {pr_info.get('deletions', 0)}

Changed files:
{json.dumps(pr_files.get('files', []), default=str)[:4000]}

Diff (truncated):
{pr_diff.get('diff', '')[:6000]}

Provide:
1. Overall quality score (1-100)
2. Summary of changes
3. Issues found (bugs, security, performance, style)
4. Positive aspects
5. Recommendation: APPROVE, REQUEST_CHANGES, or COMMENT
6. Specific inline comments""",
                max_tokens=4000,
            )

            event = "COMMENT"
            if "APPROVE" in review_text[:200].upper():
                event = "APPROVE"
            elif "REQUEST_CHANGES" in review_text[:200].upper():
                event = "REQUEST_CHANGES"

            review_result = await self._github.create_review(
                pr_number=pr_number,
                body=f"## NEXUS Code Review\n\n{review_text}",
                event=event,
            )
            result["review"] = review_result
            result["recommendation"] = event
            result["analysis"] = review_text[:500]

        self._review_history.append({"pr": pr_number, "at": result["reviewed_at"]})
        await self.save_state()
        return result

    async def _generate_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate tests for a module by reading source code from GitHub."""
        module = payload.get("module", "")
        path = payload.get("path", "")
        branch = payload.get("branch", f"nexus/tests-{module or 'new'}")

        result: dict[str, Any] = {"module": module, "generated_at": datetime.now(timezone.utc).isoformat()}

        source_code = ""
        if self._github and path:
            file_data = await self._github.get_file_content(path)
            source_code = file_data.get("content", "")

        if self._llm and source_code:
            test_code = await self.llm_complete(
                action="generate_tests",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate comprehensive pytest tests for this module:

File: {path}
```python
{source_code[:6000]}
```

Generate unit tests, edge case tests, error handling tests.
Use pytest fixtures and parametrize. Return ONLY the Python test code.""",
                max_tokens=6000,
            )

            if self._github and test_code:
                await self._github.create_branch(branch)
                test_path = f"tests/test_{path.split('/')[-1]}" if "/" in path else f"tests/test_{path}"
                file_result = await self._github.create_or_update_file(
                    path=test_path, content=test_code,
                    message=f"[NEXUS] Generate tests for {path}", branch=branch,
                )
                result["test_file"] = file_result
                result["branch"] = branch

        return result

    async def _analyze_debt(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze technical debt by examining repo history."""
        result: dict[str, Any] = {"analyzed_at": datetime.now(timezone.utc).isoformat()}
        commits_data: dict[str, Any] = {}

        if self._github:
            commits_data = await self._github.list_commits(per_page=20)
            repo_info = await self._github.get_repo_info()
            result["recent_commits"] = commits_data.get("count", 0)
            result["repo_size_kb"] = repo_info.get("size_kb", 0)

        if self._llm:
            analysis = await self.llm_complete(
                action="analyze_debt",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Analyze technical debt for MortgageFintechOS:
Recent commits: {json.dumps(commits_data.get('commits', []), default=str)[:2000]}

Assess: code churn, commit quality, complexity, test coverage, architecture coupling.
Provide debt score (1-10) and top 3 priorities.""",
            )
            result["analysis"] = analysis

        return result

    async def _refactor(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Refactor a file and create a PR."""
        target = payload.get("target", "")
        reason = payload.get("reason", "improve code quality")
        branch = payload.get("branch", f"nexus/refactor-{target.replace('/', '-').replace('.', '-')}")

        result: dict[str, Any] = {"target": target, "generated_at": datetime.now(timezone.utc).isoformat()}

        if not self._github or not target:
            return {**result, "note": "GitHub not configured or no target"}

        file_data = await self._github.get_file_content(target)
        if "error" in file_data:
            return {**result, "error": file_data["error"]}

        if self._llm:
            refactored = await self.llm_complete(
                action="refactor",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Refactor this code. Reason: {reason}
File: {target}
```python
{file_data['content'][:8000]}
```
Apply SOLID principles, reduce complexity, improve naming. Return ONLY the code.""",
                max_tokens=8000,
            )

            if refactored:
                await self._github.create_branch(branch)
                await self._github.create_or_update_file(
                    path=target, content=refactored,
                    message=f"[NEXUS] Refactor {target}: {reason}",
                    branch=branch, sha=file_data["sha"],
                )
                pr = await self._github.create_pull_request(
                    title=f"[NEXUS] Refactor: {target}",
                    body=f"## Refactoring\n\n**Target:** `{target}`\n**Reason:** {reason}",
                    head=branch,
                )
                result["pull_request"] = pr
                result["branch"] = branch

        return result
