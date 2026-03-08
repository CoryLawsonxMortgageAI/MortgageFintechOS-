"""Notion integration client for MortgageFintechOS.

Provides async Notion API operations using API v2025-09-03 with
data_source support for page creation, querying, content retrieval,
and document management.
"""

import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"


class NotionClient:
    """Async Notion API client using v2025-09-03 with data_source support."""

    def __init__(self, token: str, database_id: str = "", data_source_id: str = ""):
        self._token = token
        self._database_id = database_id
        self._data_source_id = data_source_id
        self._log = logger.bind(component="notion")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _parent(self) -> dict[str, str]:
        """Build parent object using data_source_id (v2025-09-03) or database_id fallback."""
        if self._data_source_id:
            return {"data_source_id": self._data_source_id}
        return {"database_id": self._database_id}

    async def create_page(
        self,
        title: str,
        content: str = "",
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a page in the configured database/data_source."""
        url = f"{NOTION_API}/pages"
        props = properties or {}
        props.setdefault("Name", {"title": [{"text": {"content": title}}]})

        body: dict[str, Any] = {"parent": self._parent(), "properties": props}

        if content:
            body["children"] = self._text_to_blocks(content)

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.post(url, json=body) as resp:
                data = await resp.json()
                if resp.status == 200:
                    self._log.info("page_created", page_id=data.get("id", "")[:8], title=title)
                    return {"page_id": data["id"], "url": data.get("url", "")}
                else:
                    self._log.error("page_create_failed", status=resp.status, error=str(data)[:200])
                    return {"error": str(data)[:200], "status": resp.status}

    async def get_page_content(self, page_id: str) -> dict[str, Any]:
        """Fetch page properties and all child blocks."""
        async with aiohttp.ClientSession(headers=self._headers) as session:
            # Fetch page properties
            async with session.get(f"{NOTION_API}/pages/{page_id}") as resp:
                if resp.status != 200:
                    error = await resp.text()
                    return {"error": error[:200], "status": resp.status}
                page_data = await resp.json()

            # Fetch child blocks
            async with session.get(f"{NOTION_API}/blocks/{page_id}/children?page_size=100") as resp:
                blocks_data = await resp.json() if resp.status == 200 else {"results": []}

        self._log.info("page_fetched", page_id=page_id[:8], blocks=len(blocks_data.get("results", [])))
        return {
            "id": page_data.get("id"),
            "properties": page_data.get("properties", {}),
            "blocks": blocks_data.get("results", []),
            "url": page_data.get("url", ""),
        }

    async def query_data_source(
        self,
        filter_obj: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Query pages. Uses /data_sources/ (v2025-09-03) or /databases/ fallback."""
        if self._data_source_id:
            url = f"{NOTION_API}/data_sources/{self._data_source_id}/query"
        else:
            url = f"{NOTION_API}/databases/{self._database_id}/query"

        body: dict[str, Any] = {"page_size": page_size}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.patch(url, json=body) as resp:
                data = await resp.json()
                if resp.status == 200:
                    self._log.info("query_success", results=len(data.get("results", [])))
                    return {
                        "results": data.get("results", []),
                        "has_more": data.get("has_more", False),
                        "next_cursor": data.get("next_cursor"),
                    }
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    async def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Update page properties."""
        url = f"{NOTION_API}/pages/{page_id}"
        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.patch(url, json={"properties": properties}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    self._log.info("page_updated", page_id=page_id[:8])
                    return {"page_id": data["id"], "url": data.get("url", "")}
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    async def add_blocks(self, page_id: str, blocks: list[dict[str, Any]] | list[str]) -> dict[str, Any]:
        """Append blocks to a page. Accepts block dicts or plain strings."""
        url = f"{NOTION_API}/blocks/{page_id}/children"
        children = []
        for block in blocks:
            if isinstance(block, str):
                children.extend(self._text_to_blocks(block))
            else:
                children.append(block)

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.patch(url, json={"children": children}) as resp:
                data = await resp.json()
                if resp.status == 200:
                    self._log.info("blocks_added", page_id=page_id[:8], count=len(children))
                    return {"results": data.get("results", [])}
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    async def search(self, query: str, filter_type: str = "page") -> dict[str, Any]:
        """Search Notion. Use filter_type='data_source' for databases (v2025-09-03)."""
        url = f"{NOTION_API}/search"
        body: dict[str, Any] = {"query": query}
        if filter_type:
            body["filter"] = {"value": filter_type, "property": "object"}

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.post(url, json=body) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return {"results": data.get("results", []), "has_more": data.get("has_more", False)}
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    async def get_data_sources(self) -> dict[str, Any]:
        """Get schema of configured data source or database."""
        if self._data_source_id:
            url = f"{NOTION_API}/data_sources/{self._data_source_id}"
        else:
            url = f"{NOTION_API}/databases/{self._database_id}"

        async with aiohttp.ClientSession(headers=self._headers) as session:
            async with session.get(url) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return data
                else:
                    return {"error": str(data)[:200], "status": resp.status}

    # --- Convenience methods for agent workflows ---

    async def sync_agent_result(
        self, agent_name: str, action: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a Notion page logging an agent task result."""
        now = datetime.now(timezone.utc)
        title = f"[{agent_name}] {action} — {now.strftime('%Y-%m-%d %H:%M')}"
        content = f"Agent: {agent_name}\nAction: {action}\nTimestamp: {now.isoformat()}\n\n"
        content += json.dumps(result, indent=2, default=str)[:1800]
        return await self.create_page(title=title, content=content)

    async def sync_document_audit(self, audit_result: dict[str, Any]) -> dict[str, Any]:
        """Create a Notion page summarizing a document audit."""
        now = datetime.now(timezone.utc)
        title = f"Document Audit — {now.strftime('%Y-%m-%d')}"
        lines = [
            f"Audit Date: {audit_result.get('audit_date', now.isoformat())}",
            f"Loans Audited: {audit_result.get('loans_audited', 0)}",
            f"Incomplete Loans: {len(audit_result.get('incomplete_loans', []))}",
            "",
        ]
        for loan in audit_result.get("incomplete_loans", [])[:20]:
            lines.append(f"• Loan {loan.get('loan_id', '?')}: missing {', '.join(loan.get('missing', []))}")
        return await self.create_page(title=title, content="\n".join(lines))

    # --- Internal helpers ---

    @staticmethod
    def _text_to_blocks(text: str) -> list[dict[str, Any]]:
        """Convert plain text to Notion paragraph blocks (2000 char limit per block)."""
        blocks = []
        chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
        for chunk in chunks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": chunk}}]
                },
            })
        return blocks
