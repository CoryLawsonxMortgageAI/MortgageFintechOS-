"""GHOST OSINT CRM integration for MortgageFintechOS.

Connects to a GHOST OSINT CRM instance for entity investigation,
relationship mapping, travel analysis, and network risk scoring.
Used by agents for borrower background verification, fraud investigation,
and compliance due diligence.
"""

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()


class GhostClient:
    """Async client for GHOST OSINT CRM API."""

    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._log = logger.bind(component="ghost_osint")
        self._headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        self._connected = False

    async def _request(self, method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make authenticated request to GHOST API."""
        url = f"{self._base_url}/api{path}"
        try:
            async with aiohttp.ClientSession() as session:
                kwargs: dict[str, Any] = {"headers": self._headers, "timeout": aiohttp.ClientTimeout(total=15)}
                if data and method in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = data
                elif data and method == "GET":
                    kwargs["params"] = data
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status == 200:
                        self._connected = True
                        return await resp.json()
                    text = await resp.text()
                    return {"error": f"HTTP {resp.status}: {text[:300]}"}
        except aiohttp.ClientError as e:
            self._log.warning("ghost_request_failed", path=path, error=str(e))
            return {"error": f"Connection failed: {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    # --- Health ---

    async def health_check(self) -> dict[str, Any]:
        """Check GHOST CRM connectivity."""
        result = await self._request("GET", "/health")
        if "error" not in result:
            self._connected = True
        return {"connected": self._connected, "base_url": self._base_url, **result}

    # --- Entities ---

    async def create_entity(self, name: str, entity_type: str = "person", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a new investigation entity (person, company, address, phone, email)."""
        payload = {
            "name": name,
            "type": entity_type,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self._request("POST", "/entities", payload)

    async def search_entities(self, query: str, entity_type: str = "", limit: int = 20) -> dict[str, Any]:
        """Search entities by name or attributes."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if entity_type:
            params["type"] = entity_type
        return await self._request("GET", "/entities/search", params)

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        """Get full entity details including relationships."""
        return await self._request("GET", f"/entities/{entity_id}")

    async def update_entity(self, entity_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update entity attributes."""
        return await self._request("PUT", f"/entities/{entity_id}", updates)

    # --- Relationships ---

    async def create_relationship(self, source_id: str, target_id: str, rel_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a relationship between two entities."""
        payload = {
            "source_id": source_id,
            "target_id": target_id,
            "type": rel_type,
            "metadata": metadata or {},
        }
        return await self._request("POST", "/relationships", payload)

    async def get_entity_network(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        """Get the relationship network graph for an entity."""
        return await self._request("GET", f"/entities/{entity_id}/network", {"depth": depth})

    # --- Investigations ---

    async def create_investigation(self, title: str, description: str = "", entities: list[str] | None = None) -> dict[str, Any]:
        """Create a new investigation case."""
        payload = {
            "title": title,
            "description": description,
            "entity_ids": entities or [],
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self._request("POST", "/investigations", payload)

    async def list_investigations(self, status: str = "", limit: int = 20) -> dict[str, Any]:
        """List investigations."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/investigations", params)

    async def get_investigation(self, investigation_id: str) -> dict[str, Any]:
        """Get investigation details."""
        return await self._request("GET", f"/investigations/{investigation_id}")

    # --- Risk Scoring ---

    async def calculate_risk(self, entity_id: str) -> dict[str, Any]:
        """Calculate risk score for an entity based on network analysis."""
        return await self._request("POST", f"/entities/{entity_id}/risk-score")

    # --- OSINT Lookups ---

    async def osint_lookup(self, query: str, lookup_type: str = "general") -> dict[str, Any]:
        """Run an OSINT lookup on a target (email, phone, domain, person)."""
        payload = {
            "query": query,
            "type": lookup_type,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self._request("POST", "/osint/lookup", payload)

    # --- Convenience for MortgageFintechOS ---

    async def verify_borrower(self, name: str, email: str = "", phone: str = "", employer: str = "") -> dict[str, Any]:
        """Run a comprehensive borrower verification combining entity search + OSINT."""
        results: dict[str, Any] = {
            "name": name,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        # Search for existing entities
        search = await self.search_entities(name, entity_type="person")
        results["existing_records"] = search.get("results", search.get("entities", []))

        # OSINT lookups
        if email:
            results["checks"]["email"] = await self.osint_lookup(email, "email")
        if phone:
            results["checks"]["phone"] = await self.osint_lookup(phone, "phone")
        if employer:
            results["checks"]["employer"] = await self.osint_lookup(employer, "company")

        # Create entity for tracking
        entity = await self.create_entity(name, "person", {
            "email": email, "phone": phone, "employer": employer,
            "source": "mortgage_application",
        })
        results["entity_id"] = entity.get("id")

        return results

    # --- Status ---

    def get_status(self) -> dict[str, Any]:
        return {
            "service": "ghost-osint-crm",
            "connected": self._connected,
            "base_url": self._base_url,
            "authenticated": bool(self._api_key),
        }
