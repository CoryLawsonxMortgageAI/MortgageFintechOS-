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
            "run_autoresearch": self._run_autoresearch,
            "deep_security_audit": self._deep_security_audit,
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

    async def _run_autoresearch(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Autonomous ML research: modify → train → evaluate → iterate.

        Based on karpathy/autoresearch pattern. SENTINEL generates code modifications,
        evaluates them via LLM analysis, and commits successful experiments to GitHub.
        """
        target = payload.get("target", "risk_model")
        directive = payload.get("directive", "")
        max_experiments = payload.get("max_experiments", 1)

        experiments = []
        best_score = 0.0

        for i in range(max_experiments):
            experiment = {"id": i + 1, "target": target, "started_at": datetime.now(timezone.utc).isoformat()}

            if self._llm:
                prompt = f"""You are running an autoresearch experiment (karpathy/autoresearch pattern).

Target model: {target}
Research directive: {directive}
Experiment #{i + 1} of {max_experiments}

Generate a focused code modification to improve the model. Return JSON:
{{
    "modification": "description of the change",
    "code": "python code implementing the change",
    "hypothesis": "why this should improve the model",
    "expected_metric_improvement": "what metric and by how much",
    "risk_level": "low/medium/high",
    "estimated_score": 0.0 to 1.0
}}"""

                result_text = await self.llm_complete(
                    action="run_autoresearch",
                    system_prompt=SYSTEM_PROMPT + "\nYou are also a senior ML research scientist.",
                    user_prompt=prompt,
                    temperature=0.6,
                )

                # Try to parse JSON from result
                try:
                    # Find JSON in response
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        parsed = json.loads(result_text[json_start:json_end])
                        experiment.update(parsed)
                        score = float(parsed.get("estimated_score", 0))
                        if score > best_score:
                            best_score = score
                except (json.JSONDecodeError, ValueError):
                    experiment["raw_result"] = result_text[:500]

            experiment["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Commit successful experiments to GitHub
            if self._github and experiment.get("code") and experiment.get("risk_level") != "high":
                try:
                    branch = f"sentinel/autoresearch-{target}-{i+1}"
                    await self._github.create_branch(branch)
                    await self._github.create_or_update_file(
                        path=f"research/experiments/{target}_exp_{i+1}.py",
                        content=experiment["code"],
                        message=f"[SENTINEL] AutoResearch: {target} experiment #{i+1} — {experiment.get('modification', 'optimization')}",
                        branch=branch,
                    )
                    experiment["branch"] = branch
                    experiment["committed"] = True
                except Exception as e:
                    experiment["commit_error"] = str(e)

            experiments.append(experiment)

        self._scan_history.append({
            "type": "autoresearch",
            "target": target,
            "experiments": len(experiments),
            "best_score": best_score,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        await self.save_state()

        return {
            "target": target,
            "experiments_run": len(experiments),
            "best_score": best_score,
            "experiments": experiments,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _deep_security_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Deep security audit combining GitHub scanning + LLM-powered analysis.

        Inspired by CyberStrikeAI penetration testing patterns. Performs:
        - GitHub code scanning alerts analysis
        - Dependabot vulnerability assessment
        - Secret scanning
        - LLM-powered OWASP Top 10 mapping
        - Attack surface analysis
        """
        branch = payload.get("branch", "main")
        focus = payload.get("focus", "full")

        if not self._github:
            return {"error": "GitHub client not configured"}

        # Gather all security data from GitHub
        security_summary = await self._github.get_security_summary()
        code_alerts = security_summary.get("code_scanning_alerts", [])
        dep_alerts = security_summary.get("dependabot_alerts", [])
        secret_alerts = security_summary.get("secret_scanning_alerts", [])

        # Read key security-sensitive files
        sensitive_files = []
        for path in ["config/settings.py", "dashboard/server.py", "core/orchestrator.py", ".env.example"]:
            try:
                content = await self._github.get_file_content(path, ref=branch)
                if "error" not in content:
                    sensitive_files.append({"path": path, "size": len(content.get("content", ""))})
            except Exception:
                pass

        analysis = ""
        if self._llm:
            prompt = f"""Perform a deep security audit of this codebase.

GitHub Security Alerts:
- Code Scanning: {len(code_alerts)} alerts
- Dependabot: {len(dep_alerts)} dependency vulnerabilities
- Secret Scanning: {len(secret_alerts)} exposed secrets

Alert Details:
{json.dumps(code_alerts[:5], indent=2, default=str)}
{json.dumps(dep_alerts[:5], indent=2, default=str)}

Files analyzed: {json.dumps([f['path'] for f in sensitive_files])}

Provide a structured security audit report:
1. CRITICAL vulnerabilities requiring immediate action
2. OWASP Top 10 mapping (which categories are affected)
3. Dependency risk assessment
4. Secret/credential exposure risk
5. API security analysis
6. Authentication/authorization gaps
7. Data protection compliance (PII, GLBA, SOC2)
8. Attack surface map
9. Remediation priority list (ordered by risk)
10. Recommended security controls to implement"""

            analysis = await self.llm_complete(
                action="deep_security_audit",
                system_prompt=SYSTEM_PROMPT + "\nYou are also a senior cybersecurity penetration testing expert.",
                user_prompt=prompt,
                max_tokens=6000,
            )

        result = {
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "branch": branch,
            "code_scanning_alerts": len(code_alerts),
            "dependabot_alerts": len(dep_alerts),
            "secret_scanning_alerts": len(secret_alerts),
            "total_alerts": len(code_alerts) + len(dep_alerts) + len(secret_alerts),
            "files_analyzed": len(sensitive_files),
            "analysis": analysis,
            "risk_level": "critical" if secret_alerts else "high" if dep_alerts else "medium" if code_alerts else "low",
        }

        # Create GitHub issue with audit results if critical
        if self._github and result["total_alerts"] > 0:
            try:
                await self._github.create_issue(
                    title=f"[SENTINEL] Security Audit — {result['total_alerts']} alerts found",
                    body=f"## Security Audit Report\n\n"
                         f"- Code Scanning: {len(code_alerts)} alerts\n"
                         f"- Dependabot: {len(dep_alerts)} vulnerabilities\n"
                         f"- Secret Scanning: {len(secret_alerts)} exposed\n"
                         f"- Risk Level: **{result['risk_level'].upper()}**\n\n"
                         f"### Analysis\n{analysis[:2000]}",
                    labels=["security", "automated"],
                )
                result["issue_created"] = True
            except Exception:
                pass

        self._scan_history.append({
            "type": "security_audit",
            "total_alerts": result["total_alerts"],
            "risk_level": result["risk_level"],
            "audited_at": result["audited_at"],
        })
        await self.save_state()

        return result
