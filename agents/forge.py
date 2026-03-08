"""FORGE — DevOps Engineering Agent.

Handles deployments, rollbacks, CI/CD pipeline building,
and secret rotation via real GitHub Actions and LLM-powered automation.
"""

import json
from datetime import datetime, timezone
from typing import Any
import structlog
from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are FORGE, a DevOps engineering agent for MortgageFintechOS.
You manage CI/CD pipelines, deployments, rollbacks, and infrastructure.
You use GitHub Actions for automation and generate production-ready workflow YAML.
Follow GitOps best practices and zero-downtime deployment patterns."""


class ForgeAgent(BaseAgent):
    """FORGE: DevOps engineering — deploy, rollback, CI/CD via GitHub Actions."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="FORGE", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._deploy_history: list[dict[str, Any]] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "deploy": self._deploy,
            "rollback": self._rollback,
            "build_pipeline": self._build_pipeline,
            "rotate_secrets": self._rotate_secrets,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown FORGE action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "deploys": len(self._deploy_history),
        }

    def _get_state(self) -> dict[str, Any]:
        return {"deploy_history": self._deploy_history[-50:]}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._deploy_history = data.get("deploy_history", [])

    async def _deploy(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Trigger a deployment via GitHub Actions workflow dispatch."""
        environment = payload.get("environment", "production")
        workflow = payload.get("workflow", "deploy.yml")
        ref = payload.get("ref", "main")

        result: dict[str, Any] = {
            "environment": environment,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github:
            # Trigger the deployment workflow
            trigger_result = await self._github.trigger_workflow(
                workflow_id=workflow, ref=ref,
                inputs={"environment": environment},
            )
            result["trigger"] = trigger_result

            # Check recent runs to get the triggered run
            runs = await self._github.list_workflow_runs(workflow_id=workflow, per_page=1)
            if runs.get("runs"):
                latest = runs["runs"][0]
                result["run_id"] = latest["id"]
                result["run_status"] = latest["status"]
                result["run_url"] = latest["url"]
        else:
            result["note"] = f"Deploy to {environment} queued — GitHub Actions not configured"

        deploy_record = {"env": environment, "at": result["triggered_at"], "ref": ref}
        self._deploy_history.append(deploy_record)
        await self.save_state()
        return result

    async def _rollback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Trigger a rollback via workflow dispatch or revert commit."""
        version = payload.get("version", "")
        environment = payload.get("environment", "production")

        result: dict[str, Any] = {
            "environment": environment,
            "target_version": version,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github:
            trigger_result = await self._github.trigger_workflow(
                workflow_id="rollback.yml", ref="main",
                inputs={"version": version, "environment": environment},
            )
            result["trigger"] = trigger_result
        else:
            result["note"] = f"Rollback to {version} queued"

        return result

    async def _build_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate and commit a GitHub Actions workflow YAML."""
        pipeline_name = payload.get("name", "ci")
        stages = payload.get("stages", ["lint", "test", "build", "deploy"])
        trigger = payload.get("trigger", "push")

        workflow_yaml = ""
        if self._llm:
            workflow_yaml = await self.llm_complete(
                action="build_pipeline",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate a GitHub Actions workflow YAML for '{pipeline_name}'.

Stages: {', '.join(stages)}
Trigger: {trigger}
Language: Python 3.11+
Include: caching, artifact uploads, environment secrets, status badges.
Return ONLY the YAML content.""",
            )

        result: dict[str, Any] = {
            "pipeline": pipeline_name,
            "stages": stages,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._github and workflow_yaml:
            file_result = await self._github.create_or_update_file(
                path=f".github/workflows/{pipeline_name}.yml",
                content=workflow_yaml,
                message=f"[FORGE] Create CI/CD pipeline: {pipeline_name}",
                branch="main",
            )
            result["file"] = file_result
        else:
            result["note"] = "Pipeline YAML generated"
            if workflow_yaml:
                result["yaml_preview"] = workflow_yaml[:500]

        return result

    async def _rotate_secrets(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Log secret rotation event and create tracking issue."""
        secrets = payload.get("secrets", ["GITHUB_TOKEN", "ENCRYPTION_KEY", "NOTION_API_TOKEN"])

        result: dict[str, Any] = {
            "secrets_to_rotate": secrets,
            "rotated_at": datetime.now(timezone.utc).isoformat(),
            "next_rotation": "90 days",
        }

        if self._github:
            # Create tracking issue for manual rotation
            issue = await self._github.create_issue(
                title=f"[FORGE] Secret Rotation — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
                body=f"## Secret Rotation Required\n\nSecrets to rotate:\n" +
                     "\n".join(f"- [ ] `{s}`" for s in secrets) +
                     f"\n\nNext rotation: 90 days\n\n---\n*Auto-created by FORGE agent*",
                labels=["security", "automated"],
            )
            result["tracking_issue"] = issue

        return result
