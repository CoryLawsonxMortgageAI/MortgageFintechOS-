"""STORM — Data Engineering Agent.

Handles ETL pipeline building, HMDA reporting, ULDD export,
and query optimization with real GitHub integration and LLM-powered data analysis.
"""

import json
from datetime import datetime, timezone
from typing import Any
import structlog
from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are STORM, a data engineering agent for MortgageFintechOS.
You build ETL pipelines, generate HMDA compliance reports, create ULDD investor
exports, and optimize database queries. You understand mortgage data schemas,
regulatory reporting requirements, and data warehouse best practices."""


class StormAgent(BaseAgent):
    """STORM: Data engineering — ETL, HMDA, ULDD, query optimization."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="STORM", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._pipeline_history: list[dict[str, Any]] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "build_etl": self._build_etl,
            "hmda_report": self._hmda_report,
            "uldd_export": self._uldd_export,
            "optimize_query": self._optimize_query,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown STORM action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "pipelines_built": len(self._pipeline_history),
        }

    def _get_state(self) -> dict[str, Any]:
        return {"pipeline_history": self._pipeline_history[-50:]}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._pipeline_history = data.get("pipeline_history", [])

    async def _build_etl(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Build an ETL pipeline config and commit to GitHub."""
        pipeline = payload.get("pipeline", "loan_ingestion")
        source = payload.get("source", "")
        destination = payload.get("destination", "")

        result: dict[str, Any] = {
            "pipeline": pipeline,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._llm:
            etl_code = await self.llm_complete(
                action="build_etl",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate a Python ETL pipeline named '{pipeline}'.
Source: {source or 'configurable'}
Destination: {destination or 'configurable'}

Include: extract, transform, load stages with error handling, logging, and retry logic.
Use asyncio for async processing. Return ONLY the Python code.""",
                max_tokens=4000,
            )

            if self._github and etl_code:
                file_result = await self._github.create_or_update_file(
                    path=f"etl/{pipeline}.py",
                    content=etl_code,
                    message=f"[STORM] Build ETL pipeline: {pipeline}",
                    branch="main",
                )
                result["file"] = file_result

            result["stages"] = ["extract", "transform", "load"]

        self._pipeline_history.append({"pipeline": pipeline, "at": result["generated_at"]})
        await self.save_state()
        return result

    async def _hmda_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate HMDA compliance report."""
        year = payload.get("year", datetime.now().year)

        result: dict[str, Any] = {
            "year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._llm:
            report = await self.llm_complete(
                action="hmda_report",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate a HMDA (Home Mortgage Disclosure Act) report template for year {year}.

Include:
1. Required data fields per Regulation C
2. LAR (Loan Application Register) format
3. Data validation rules
4. Submission timeline and requirements
5. Common compliance pitfalls
Format as a structured report.""",
            )
            result["report"] = report

            if self._github:
                await self._github.create_or_update_file(
                    path=f"reports/hmda_{year}.md",
                    content=f"# HMDA Report {year}\n\n{report}",
                    message=f"[STORM] Generate HMDA report for {year}",
                    branch="main",
                )

        return result

    async def _uldd_export(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate ULDD investor export format."""
        investor = payload.get("investor", "FNMA")

        result: dict[str, Any] = {
            "investor": investor,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._llm:
            export_spec = await self.llm_complete(
                action="uldd_export",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate a ULDD (Uniform Loan Delivery Dataset) export specification for {investor}.

Include:
1. Required fields for {investor} delivery
2. XML schema structure (ULDD 3.4 format)
3. Data mapping from loan origination fields
4. Validation rules per {investor} requirements
5. Sample export template""",
            )
            result["specification"] = export_spec

        return result

    async def _optimize_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Analyze and optimize a database query."""
        query = payload.get("query", "")
        context = payload.get("context", "")

        result: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._llm and query:
            optimization = await self.llm_complete(
                action="optimize_query",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Optimize this database query:

```sql
{query}
```

Context: {context}

Provide:
1. Analysis of current query performance
2. Optimized query
3. Recommended indexes
4. Estimated improvement
5. Explain plan analysis""",
            )
            result["optimization"] = optimization

        return result
