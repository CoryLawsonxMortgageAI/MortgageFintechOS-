"""PentAGI integration for MortgageFintechOS.

Connects to a PentAGI autonomous penetration testing agent for
continuous security assessment. Provides automated vulnerability
scanning, attack surface analysis, and remediation tracking.
Used by CIPHER and SENTINEL agents for security operations.
"""

from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()


class PentAGIClient:
    """Async client for PentAGI autonomous pentesting API."""

    def __init__(self, base_url: str = "http://localhost:8443", api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._log = logger.bind(component="pentagi")
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            self._headers["X-API-Key"] = api_key
        self._connected = False

    async def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated request to PentAGI API."""
        url = f"{self._base_url}/api/v1{path}"
        try:
            async with aiohttp.ClientSession() as session:
                kwargs: dict[str, Any] = {"headers": self._headers, "timeout": aiohttp.ClientTimeout(total=30)}
                if data and method in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = data
                elif data and method == "GET":
                    kwargs["params"] = data
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in (200, 201):
                        self._connected = True
                        return await resp.json()
                    text = await resp.text()
                    return {"error": f"HTTP {resp.status}: {text[:300]}"}
        except aiohttp.ClientError as e:
            self._log.warning("pentagi_request_failed", path=path, error=str(e))
            return {"error": f"Connection failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    # --- Health ---

    async def health_check(self) -> dict[str, Any]:
        """Check PentAGI connectivity."""
        result = await self._request("GET", "/health")
        if "error" not in result:
            self._connected = True
        return {"connected": self._connected, "base_url": self._base_url, **result}

    # --- Scans ---

    async def create_scan(self, target: str, scan_type: str = "full", config: dict[str, Any] | None = None) -> dict[str, Any]:
        """Launch a new penetration test scan."""
        payload = {
            "target": target,
            "scan_type": scan_type,
            "config": config or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self._request("POST", "/scans", payload)

    async def get_scan(self, scan_id: str) -> dict[str, Any]:
        """Get scan status and results."""
        return await self._request("GET", f"/scans/{scan_id}")

    async def list_scans(self, status: str = "", limit: int = 20) -> dict[str, Any]:
        """List all scans."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/scans", params)

    async def cancel_scan(self, scan_id: str) -> dict[str, Any]:
        """Cancel a running scan."""
        return await self._request("POST", f"/scans/{scan_id}/cancel")

    # --- Vulnerabilities ---

    async def list_vulnerabilities(self, severity: str = "", limit: int = 50) -> dict[str, Any]:
        """List discovered vulnerabilities."""
        params: dict[str, Any] = {"limit": limit}
        if severity:
            params["severity"] = severity
        return await self._request("GET", "/vulnerabilities", params)

    async def get_vulnerability(self, vuln_id: str) -> dict[str, Any]:
        """Get vulnerability details including proof of concept."""
        return await self._request("GET", f"/vulnerabilities/{vuln_id}")

    async def update_vulnerability_status(self, vuln_id: str, status: str, notes: str = "") -> dict[str, Any]:
        """Update vulnerability status (open, confirmed, mitigated, false_positive)."""
        return await self._request("PATCH", f"/vulnerabilities/{vuln_id}", {"status": status, "notes": notes})

    # --- Attack Surface ---

    async def get_attack_surface(self, target: str = "") -> dict[str, Any]:
        """Get the attack surface analysis for a target."""
        params = {"target": target} if target else {}
        return await self._request("GET", "/attack-surface", params)

    # --- Reports ---

    async def generate_report(self, scan_id: str = "", report_type: str = "executive") -> dict[str, Any]:
        """Generate a security report."""
        payload = {"report_type": report_type}
        if scan_id:
            payload["scan_id"] = scan_id
        return await self._request("POST", "/reports", payload)

    async def list_reports(self, limit: int = 10) -> dict[str, Any]:
        """List generated reports."""
        return await self._request("GET", "/reports", {"limit": limit})

    # --- Agent Tasks ---

    async def submit_task(self, task_type: str, target: str, instructions: str = "") -> dict[str, Any]:
        """Submit an autonomous agent task (recon, exploit, report)."""
        payload = {
            "type": task_type,
            "target": target,
            "instructions": instructions,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self._request("POST", "/tasks", payload)

    async def get_task_result(self, task_id: str) -> dict[str, Any]:
        """Get task execution result."""
        return await self._request("GET", f"/tasks/{task_id}")

    # --- Convenience for MortgageFintechOS ---

    async def run_security_assessment(self, target: str = "self") -> dict[str, Any]:
        """Run a full security assessment combining scan + attack surface + report."""
        results: dict[str, Any] = {
            "target": target,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Launch scan
        scan = await self.create_scan(target, scan_type="full")
        results["scan"] = scan

        # Get attack surface
        surface = await self.get_attack_surface(target)
        results["attack_surface"] = surface

        # List existing vulnerabilities
        vulns = await self.list_vulnerabilities(severity="critical")
        results["critical_vulnerabilities"] = vulns

        return results

    # --- Status ---

    def get_status(self) -> dict[str, Any]:
        return {
            "service": "pentagi",
            "connected": self._connected,
            "base_url": self._base_url,
            "authenticated": bool(self._api_key),
        }
