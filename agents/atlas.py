"""ATLAS — Full-Stack Engineering Agent.

Handles API generation, feature building, database migrations,
and component scaffolding via real GitHub operations and LLM-powered code generation.
"""

import json
from datetime import datetime, timezone
from typing import Any
import structlog
from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are ATLAS, a full-stack engineering agent for MortgageFintechOS.
You generate production-ready code for APIs, features, migrations, and components.
Your code should follow best practices, include error handling, and be ready to commit to a repo.
Use Python for backend, TypeScript/React for frontend. Follow existing patterns in the codebase."""


class AtlasAgent(BaseAgent):
    """ATLAS: Full-stack engineering — API gen, features, migrations via GitHub."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="ATLAS", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._work_history: list[dict[str, Any]] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "generate_api": self._generate_api,
            "build_feature": self._build_feature,
            "run_migration": self._run_migration,
            "scaffold_component": self._scaffold_component,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown ATLAS action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "work_items": len(self._work_history),
        }

    def _get_state(self) -> dict[str, Any]:
        return {"work_history": self._work_history[-100:]}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._work_history = data.get("work_history", [])

    async def _generate_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate an API endpoint and commit to GitHub."""
        resource = payload.get("resource", "loans")
        methods = payload.get("methods", ["GET", "POST", "PUT", "DELETE"])
        branch = payload.get("branch", f"atlas/api-{resource}")

        # Use LLM to generate the code
        code = await self.llm_complete(
            action="generate_api",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Generate a complete Python REST API endpoint for the '{resource}' resource.

Methods: {', '.join(methods)}
Framework: aiohttp (matching existing dashboard/server.py pattern)
Include: input validation, error handling, structured logging, JSON responses.
Return ONLY the Python code, no explanation.""",
        )

        result: dict[str, Any] = {
            "resource": resource,
            "methods": methods,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github and code:
            # Create branch and commit the file
            await self._github.create_branch(branch)
            file_result = await self._github.create_or_update_file(
                path=f"api/{resource}.py",
                content=code,
                message=f"[ATLAS] Generate API endpoint for {resource}",
                branch=branch,
            )
            result["file"] = file_result
            result["branch"] = branch
            result["code_length"] = len(code)
        elif code:
            result["code"] = code[:500]
            result["code_length"] = len(code)
        else:
            result["note"] = "LLM not configured — endpoint spec generated"
            result["endpoint"] = f"/api/v1/{resource}"

        self._work_history.append({"action": "generate_api", "resource": resource, "at": result["generated_at"]})
        await self.save_state()
        return result

    async def _build_feature(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build a complete feature with multiple files on a new branch."""
        feature = payload.get("feature", "borrower_dashboard")
        description = payload.get("description", "")
        branch = payload.get("branch", f"atlas/feature-{feature}")

        code_plan = await self.llm_complete(
            action="build_feature",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Plan and generate code for the '{feature}' feature.
Description: {description}

Generate a JSON response with this structure:
{{"files": [{{"path": "relative/path/file.py", "content": "file content..."}}]}}

Include all necessary files: models, routes, tests. Return ONLY valid JSON.""",
            max_tokens=8000,
        )

        result: dict[str, Any] = {
            "feature": feature,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github and code_plan:
            await self._github.create_branch(branch)
            try:
                plan = json.loads(code_plan)
                files_created = 0
                for f in plan.get("files", []):
                    await self._github.create_or_update_file(
                        path=f["path"],
                        content=f["content"],
                        message=f"[ATLAS] {feature}: add {f['path']}",
                        branch=branch,
                    )
                    files_created += 1
                result["files_created"] = files_created
                result["branch"] = branch
            except json.JSONDecodeError:
                result["note"] = "LLM output not parseable as JSON — raw output stored"
                result["raw_plan"] = code_plan[:1000]
        else:
            result["note"] = "Feature spec generated"

        self._work_history.append({"action": "build_feature", "feature": feature, "at": result["generated_at"]})
        await self.save_state()
        return result

    async def _run_migration(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate and commit a database migration."""
        name = payload.get("name", "add_agent_table")
        description = payload.get("description", "")

        migration_code = await self.llm_complete(
            action="run_migration",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Generate a database migration named '{name}'.
Description: {description}
Format: SQL migration with UP and DOWN sections.
Return ONLY the SQL code.""",
        )

        result: dict[str, Any] = {
            "migration": name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github and migration_code:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            file_result = await self._github.create_or_update_file(
                path=f"migrations/{ts}_{name}.sql",
                content=migration_code,
                message=f"[ATLAS] Migration: {name}",
                branch="main",
            )
            result["file"] = file_result
        else:
            result["note"] = "Migration spec generated"

        return result

    async def _scaffold_component(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate a frontend component and commit to GitHub."""
        component = payload.get("component", "LoanTable")
        branch = payload.get("branch", f"atlas/component-{component}")

        code = await self.llm_complete(
            action="scaffold_component",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"""Generate a React TypeScript component named '{component}'.
Include: component file, test file, and CSS module.
Return JSON: {{"files": [{{"path": "...", "content": "..."}}]}}
Return ONLY valid JSON.""",
        )

        result: dict[str, Any] = {
            "component": component,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github and code:
            await self._github.create_branch(branch)
            try:
                plan = json.loads(code)
                for f in plan.get("files", []):
                    await self._github.create_or_update_file(
                        path=f["path"], content=f["content"],
                        message=f"[ATLAS] Scaffold {component}: {f['path']}", branch=branch,
                    )
                result["files"] = [f["path"] for f in plan.get("files", [])]
                result["branch"] = branch
            except json.JSONDecodeError:
                result["note"] = "Component spec generated"
        else:
            result["files"] = [f"{component}.tsx", f"{component}.test.tsx", f"{component}.module.css"]

        return result
