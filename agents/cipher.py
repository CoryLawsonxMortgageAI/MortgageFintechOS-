"""CIPHER — Security Engineering Agent.

Handles OWASP scanning, compliance checks (SOC2/PCI/GLBA),
encryption auditing, and vulnerability patching via real
GitHub security APIs and LLM-powered analysis.
"""

import json
from datetime import datetime, timezone
from typing import Any
import structlog
from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are CIPHER, a security engineering agent for MortgageFintechOS.
You analyze code for vulnerabilities, check compliance with SOC2/PCI/GLBA,
audit encryption implementations, and generate patches for CVEs.
You have access to GitHub security scanning alerts (code scanning, Dependabot, secret scanning).
Your analysis should reference OWASP Top 10, CWE IDs, and CVSS scores where applicable."""


class CipherAgent(BaseAgent):
    """CIPHER: Security engineering — OWASP, compliance, encryption via GitHub scanning."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="CIPHER", max_retries=max_retries, category=AgentCategory.ENGINEERING)
        self._scan_history: list[dict[str, Any]] = []

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {
            "owasp_scan": self._owasp_scan,
            "compliance_check": self._compliance_check,
            "encryption_audit": self._encryption_audit,
            "patch_vulnerability": self._patch_vulnerability,
        }
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown CIPHER action: {task.action}")
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
        return {"scan_history": self._scan_history[-50:]}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._scan_history = data.get("scan_history", [])

    async def _owasp_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Scan for OWASP vulnerabilities using GitHub code scanning + LLM analysis."""
        result: dict[str, Any] = {"scanned_at": datetime.now(timezone.utc).isoformat()}

        if self._github:
            # Pull real security alerts from GitHub
            security = await self._github.get_security_summary()
            result["github_security"] = security

            # Use LLM to map alerts to OWASP categories
            if self._llm and security.get("total_open", 0) > 0:
                analysis = await self.llm_complete(
                    action="owasp_scan",
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=f"""Analyze these GitHub security alerts and map them to OWASP Top 10 categories:

Code Scanning Alerts: {json.dumps(security.get('code_scanning', {}).get('alerts', []), default=str)}
Dependabot Alerts: {json.dumps(security.get('dependabot', {}).get('alerts', []), default=str)}
Secret Scanning: {json.dumps(security.get('secret_scanning', {}).get('alerts', []), default=str)}

Provide:
1. OWASP category mapping for each alert
2. Risk prioritization (critical/high/medium/low)
3. Remediation recommendations
4. Overall security posture score (1-100)""",
                )
                result["owasp_analysis"] = analysis
            else:
                result["owasp_analysis"] = "No open alerts found — security posture: clean"

            result["total_vulnerabilities"] = security.get("total_open", 0)
        else:
            result["note"] = "GitHub not configured — manual scan required"

        self._scan_history.append({"action": "owasp_scan", "at": result["scanned_at"], "vulns": result.get("total_vulnerabilities", 0)})
        await self.save_state()
        return result

    async def _compliance_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Check compliance with SOC2/PCI/GLBA frameworks."""
        frameworks = payload.get("frameworks", ["SOC2", "PCI", "GLBA"])

        result: dict[str, Any] = {
            "frameworks": frameworks,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # Gather codebase info for analysis
        repo_info = {}
        if self._github:
            repo_info = await self._github.get_repo_info()
            security = await self._github.get_security_summary()
            result["security_alerts"] = security.get("total_open", 0)

        if self._llm:
            analysis = await self.llm_complete(
                action="compliance_check",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Perform a compliance check for a mortgage fintech application against these frameworks: {', '.join(frameworks)}

Repository info: {json.dumps(repo_info, default=str)[:2000]}

Check these compliance controls:
- SOC2: Access controls, encryption, monitoring, incident response
- PCI: Cardholder data protection, network security, vulnerability management
- GLBA: Customer data privacy, safeguards rule, information security program

For each framework, provide:
1. Controls assessed
2. Controls passed / failed
3. Specific findings
4. Remediation steps for failures
5. Overall compliance status""",
            )
            result["analysis"] = analysis
        else:
            result["analysis"] = f"Manual compliance review required for: {', '.join(frameworks)}"

        return result

    async def _encryption_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Audit encryption implementations across the codebase."""
        result: dict[str, Any] = {"audited_at": datetime.now(timezone.utc).isoformat()}

        if self._github:
            # Check for common encryption-related files
            for path in ["config/settings.py", ".env.example", "requirements.txt"]:
                file_data = await self._github.get_file_content(path)
                if "content" in file_data:
                    result[f"reviewed_{path.replace('/', '_')}"] = True

            # Check for secrets in scanning
            secrets = await self._github.list_secret_scanning_alerts()
            result["exposed_secrets"] = secrets.get("count", 0)

        if self._llm:
            analysis = await self.llm_complete(
                action="encryption_audit",
                system_prompt=SYSTEM_PROMPT,
                user_prompt="""Audit the encryption posture for a mortgage fintech platform. Check:
1. Data at rest encryption (AES-256 minimum)
2. Data in transit (TLS 1.3)
3. Key management and rotation policies
4. Secret storage practices
5. API authentication mechanisms
6. Database encryption
7. File upload/download security

Provide specific recommendations for each area.""",
            )
            result["analysis"] = analysis
        else:
            result["analysis"] = "Manual encryption audit required"

        return result

    async def _patch_vulnerability(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Generate and commit a patch for a specific vulnerability."""
        cve = payload.get("cve", "")
        alert_number = payload.get("alert_number", 0)
        description = payload.get("description", "")

        result: dict[str, Any] = {
            "cve": cve,
            "patched_at": datetime.now(timezone.utc).isoformat(),
        }

        patch_code = ""
        if self._llm:
            patch_code = await self.llm_complete(
                action="patch_vulnerability",
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"""Generate a patch for vulnerability: {cve}
Description: {description}

Provide the specific code changes needed as a unified diff format.
Include the file path, the old code, and the new code.""",
            )
            result["patch_plan"] = patch_code[:2000]

        if self._github and patch_code:
            branch = f"cipher/patch-{cve.lower().replace('-', '_')}" if cve else f"cipher/security-patch-{alert_number}"
            await self._github.create_branch(branch)
            # Create a patch description file
            await self._github.create_or_update_file(
                path=f"security/patches/{cve or f'alert-{alert_number}'}.md",
                content=f"# Security Patch: {cve}\n\n{patch_code}",
                message=f"[CIPHER] Security patch for {cve or f'alert #{alert_number}'}",
                branch=branch,
            )
            # Create PR
            pr_result = await self._github.create_pull_request(
                title=f"[CIPHER] Security patch: {cve or f'Alert #{alert_number}'}",
                body=f"## Security Patch\n\n**CVE:** {cve}\n**Description:** {description}\n\n{patch_code[:1000]}",
                head=branch,
            )
            result["pull_request"] = pr_result
            result["branch"] = branch
        else:
            result["note"] = "Patch plan generated — manual application required"

        return result
