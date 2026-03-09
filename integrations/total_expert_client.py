"""Total Expert CRM integration client for MortgageFintechOS.

Provides async Total Expert API operations for contact management,
loan pipeline tracking, marketing campaigns, task management,
communications logging, loan officer management, document handling,
and webhook subscriptions.
"""

import asyncio
import base64
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger()

DEFAULT_BASE_URL = "https://api.totalexpert.net/v1"


class TotalExpertClient:
    """Async Total Expert CRM API client for MortgageFintechOS operations.

    SAFETY: Deletion operations for contacts and loans are permanently
    disabled. AI agents can read, create, and update records but can
    NEVER delete borrower or loan data. Contacts and loans may only
    be deactivated via status updates. This is an immutable architectural
    constraint.
    """

    # Operations that are ALWAYS blocked — no override, no flag, no exception
    BLOCKED_OPERATIONS = frozenset({
        "delete_contact",
        "delete_loan",
        "delete_loan_officer",
        "delete_document",
    })

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        rate_limit: int = 100,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._log = logger.bind(component="total_expert")
        self._blocked_attempts: list[dict[str, str]] = []

        # OAuth2 token state
        self._access_token: str = ""
        self._token_expiry: datetime | None = None

        # Rate limiting — token bucket (requests per minute)
        self._rate_limit = rate_limit
        self._tokens = float(rate_limit)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    # ═══════════════════════════════════════════════════════
    # AUTH & REQUEST INFRASTRUCTURE
    # ═══════════════════════════════════════════════════════

    async def _ensure_token(self) -> str:
        """Get or refresh OAuth2 bearer token via client credentials flow."""
        now = datetime.now(timezone.utc)
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        token_url = f"{self._base_url}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, json=payload) as resp:
                data = await resp.json()
                if resp.status == 200:
                    self._access_token = data["access_token"]
                    expires_in = data.get("expires_in", 3600)
                    self._token_expiry = datetime.fromtimestamp(
                        time.time() + expires_in - 60, tz=timezone.utc
                    )
                    self._log.info("token_refreshed", expires_in=expires_in)
                    return self._access_token
                else:
                    self._log.error("token_refresh_failed", status=resp.status, error=str(data)[:200])
                    raise RuntimeError(f"OAuth2 token refresh failed: {resp.status} — {str(data)[:200]}")

    async def _wait_for_rate_limit(self) -> None:
        """Token bucket rate limiter — 100 requests/minute default."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                float(self._rate_limit),
                self._tokens + elapsed * (self._rate_limit / 60.0),
            )
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / (self._rate_limit / 60.0)
                self._log.warning("rate_limit_wait", wait_seconds=round(wait_time, 2))
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0

    async def _request(
        self,
        method: str,
        endpoint: str,
        retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Central request handler with auth, rate limiting, and retries."""
        await self._wait_for_rate_limit()
        token = await self._ensure_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self._base_url}{endpoint}"

        for attempt in range(1, retries + 1):
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.request(method, url, **kwargs) as resp:
                        # Rate limit hit — back off and retry
                        if resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", "5"))
                            self._log.warning(
                                "rate_limited",
                                attempt=attempt,
                                retry_after=retry_after,
                                endpoint=endpoint,
                            )
                            await asyncio.sleep(retry_after)
                            continue

                        # Server error — retry with exponential backoff
                        if resp.status >= 500 and attempt < retries:
                            wait = 2 ** attempt
                            self._log.warning(
                                "server_error_retry",
                                status=resp.status,
                                attempt=attempt,
                                wait=wait,
                                endpoint=endpoint,
                            )
                            await asyncio.sleep(wait)
                            continue

                        # Token expired mid-request — refresh and retry once
                        if resp.status == 401 and attempt == 1:
                            self._access_token = ""
                            self._token_expiry = None
                            token = await self._ensure_token()
                            headers["Authorization"] = f"Bearer {token}"
                            continue

                        # Return raw bytes for document downloads
                        if kwargs.get("_raw_response"):
                            if resp.status == 200:
                                content = await resp.read()
                                return {"content": content, "status": resp.status}
                            else:
                                error = await resp.text()
                                return {"error": error[:200], "status": resp.status}

                        # No-content responses (204)
                        if resp.status == 204:
                            return {"success": True, "status": 204}

                        data = await resp.json()
                        if resp.status in (200, 201):
                            return data if isinstance(data, dict) else {"data": data}
                        else:
                            self._log.error(
                                "request_failed",
                                method=method,
                                endpoint=endpoint,
                                status=resp.status,
                                error=str(data)[:200],
                            )
                            return {"error": str(data)[:200], "status": resp.status}

            except aiohttp.ClientError as e:
                if attempt < retries:
                    wait = 2 ** attempt
                    self._log.warning(
                        "connection_error_retry",
                        error=str(e)[:100],
                        attempt=attempt,
                        wait=wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    self._log.error("request_error", endpoint=endpoint, error=str(e)[:200])
                    return {"error": f"Connection error: {str(e)[:200]}", "status": 0}

        return {"error": "Max retries exceeded", "status": 0}

    # ═══════════════════════════════════════════════════════
    # CONTACTS (Borrowers / Leads)
    # ═══════════════════════════════════════════════════════

    async def list_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List contacts with optional filters (status, source, assigned_to, date range)."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if filters:
            params.update(filters)
        result = await self._request("GET", "/contacts", params=params)
        if "error" not in result:
            self._log.info("contacts_listed", count=len(result.get("data", [])), page=page)
        return result

    async def get_contact(self, contact_id: str) -> dict[str, Any]:
        """Get a single contact by ID."""
        result = await self._request("GET", f"/contacts/{contact_id}")
        if "error" not in result:
            self._log.info("contact_fetched", contact_id=contact_id)
        return result

    async def create_contact(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new contact (borrower/lead)."""
        result = await self._request("POST", "/contacts", json=data)
        if "error" not in result:
            self._log.info("contact_created", contact_id=result.get("id", ""))
        return result

    async def update_contact(self, contact_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing contact."""
        result = await self._request("PUT", f"/contacts/{contact_id}", json=data)
        if "error" not in result:
            self._log.info("contact_updated", contact_id=contact_id)
        return result

    async def search_contacts(self, query: str) -> dict[str, Any]:
        """Search contacts by name, email, or phone."""
        params = {"q": query}
        result = await self._request("GET", "/contacts/search", params=params)
        if "error" not in result:
            self._log.info("contacts_searched", query=query, count=len(result.get("data", [])))
        return result

    async def deactivate_contact(self, contact_id: str) -> dict[str, Any]:
        """Deactivate a contact (safe alternative to deletion)."""
        return await self.update_contact(contact_id, {"status": "inactive"})

    async def delete_contact(self, contact_id: str) -> dict[str, Any]:
        """BLOCKED: Deletion is permanently disabled. Use deactivate_contact instead."""
        self._log.warning(
            "delete_blocked",
            operation="delete_contact",
            target=contact_id,
            reason="AI agents are prohibited from deleting borrower data",
        )
        self._blocked_attempts.append({
            "operation": "delete_contact",
            "target": contact_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "error": "BLOCKED: Deletion operations are permanently disabled for contacts. "
                     "Use deactivate_contact() to set status to inactive.",
            "operation": "delete_contact",
            "target": contact_id,
            "blocked": True,
        }

    # ═══════════════════════════════════════════════════════
    # LOANS (Mortgage Applications)
    # ═══════════════════════════════════════════════════════

    async def list_loans(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List loans with optional filters (status, loan_officer_id, date range)."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if filters:
            params.update(filters)
        result = await self._request("GET", "/loans", params=params)
        if "error" not in result:
            self._log.info("loans_listed", count=len(result.get("data", [])), page=page)
        return result

    async def get_loan(self, loan_id: str) -> dict[str, Any]:
        """Get a single loan by ID."""
        result = await self._request("GET", f"/loans/{loan_id}")
        if "error" not in result:
            self._log.info("loan_fetched", loan_id=loan_id)
        return result

    async def create_loan(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new loan application."""
        result = await self._request("POST", "/loans", json=data)
        if "error" not in result:
            self._log.info("loan_created", loan_id=result.get("id", ""))
        return result

    async def update_loan(self, loan_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing loan."""
        result = await self._request("PUT", f"/loans/{loan_id}", json=data)
        if "error" not in result:
            self._log.info("loan_updated", loan_id=loan_id)
        return result

    async def get_loan_pipeline(self, loan_officer_id: str | None = None) -> dict[str, Any]:
        """Get loan pipeline — optionally filtered by loan officer."""
        params: dict[str, Any] = {}
        if loan_officer_id:
            params["loan_officer_id"] = loan_officer_id
        result = await self._request("GET", "/loans/pipeline", params=params)
        if "error" not in result:
            self._log.info("pipeline_fetched", loan_officer_id=loan_officer_id)
        return result

    async def delete_loan(self, loan_id: str) -> dict[str, Any]:
        """BLOCKED: Deletion is permanently disabled. Loans can only be status-updated."""
        self._log.warning(
            "delete_blocked",
            operation="delete_loan",
            target=loan_id,
            reason="AI agents are prohibited from deleting loan data",
        )
        self._blocked_attempts.append({
            "operation": "delete_loan",
            "target": loan_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "error": "BLOCKED: Deletion operations are permanently disabled for loans. "
                     "Update the loan_status field to 'denied' or 'withdrawn' instead.",
            "operation": "delete_loan",
            "target": loan_id,
            "blocked": True,
        }

    # ═══════════════════════════════════════════════════════
    # CAMPAIGNS (Marketing)
    # ═══════════════════════════════════════════════════════

    async def list_campaigns(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List marketing campaigns with optional filters."""
        params: dict[str, Any] = {}
        if filters:
            params.update(filters)
        result = await self._request("GET", "/campaigns", params=params)
        if "error" not in result:
            self._log.info("campaigns_listed", count=len(result.get("data", [])))
        return result

    async def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        """Get a single campaign by ID."""
        result = await self._request("GET", f"/campaigns/{campaign_id}")
        if "error" not in result:
            self._log.info("campaign_fetched", campaign_id=campaign_id)
        return result

    async def create_campaign(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new marketing campaign."""
        result = await self._request("POST", "/campaigns", json=data)
        if "error" not in result:
            self._log.info("campaign_created", campaign_id=result.get("id", ""))
        return result

    # ═══════════════════════════════════════════════════════
    # TASKS (Action Items)
    # ═══════════════════════════════════════════════════════

    async def list_tasks(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List tasks with optional filters (status, assigned_to, priority, due_date)."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if filters:
            params.update(filters)
        result = await self._request("GET", "/tasks", params=params)
        if "error" not in result:
            self._log.info("tasks_listed", count=len(result.get("data", [])), page=page)
        return result

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get a single task by ID."""
        result = await self._request("GET", f"/tasks/{task_id}")
        if "error" not in result:
            self._log.info("task_fetched", task_id=task_id)
        return result

    async def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        result = await self._request("POST", "/tasks", json=data)
        if "error" not in result:
            self._log.info("task_created", task_id=result.get("id", ""))
        return result

    async def update_task(self, task_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing task."""
        result = await self._request("PUT", f"/tasks/{task_id}", json=data)
        if "error" not in result:
            self._log.info("task_updated", task_id=task_id)
        return result

    async def complete_task(self, task_id: str) -> dict[str, Any]:
        """Mark a task as completed."""
        return await self.update_task(task_id, {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

    # ═══════════════════════════════════════════════════════
    # COMMUNICATIONS (Emails, Calls, Texts)
    # ═══════════════════════════════════════════════════════

    async def list_communications(
        self,
        contact_id: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List communications, optionally filtered by contact."""
        params: dict[str, Any] = {}
        if contact_id:
            params["contact_id"] = contact_id
        if filters:
            params.update(filters)
        result = await self._request("GET", "/communications", params=params)
        if "error" not in result:
            self._log.info("communications_listed", count=len(result.get("data", [])))
        return result

    async def get_communication(self, comm_id: str) -> dict[str, Any]:
        """Get a single communication record by ID."""
        result = await self._request("GET", f"/communications/{comm_id}")
        if "error" not in result:
            self._log.info("communication_fetched", comm_id=comm_id)
        return result

    async def log_communication(self, data: dict[str, Any]) -> dict[str, Any]:
        """Log a new communication (email, phone, sms, in_person)."""
        result = await self._request("POST", "/communications", json=data)
        if "error" not in result:
            self._log.info(
                "communication_logged",
                comm_id=result.get("id", ""),
                type=data.get("type", ""),
                direction=data.get("direction", ""),
            )
        return result

    # ═══════════════════════════════════════════════════════
    # LOAN OFFICERS (Staff)
    # ═══════════════════════════════════════════════════════

    async def list_loan_officers(self) -> dict[str, Any]:
        """List all loan officers."""
        result = await self._request("GET", "/loan-officers")
        if "error" not in result:
            self._log.info("loan_officers_listed", count=len(result.get("data", [])))
        return result

    async def get_loan_officer(self, lo_id: str) -> dict[str, Any]:
        """Get a single loan officer by ID."""
        result = await self._request("GET", f"/loan-officers/{lo_id}")
        if "error" not in result:
            self._log.info("loan_officer_fetched", lo_id=lo_id)
        return result

    # ═══════════════════════════════════════════════════════
    # DOCUMENTS (Loan Documents)
    # ═══════════════════════════════════════════════════════

    async def list_documents(self, loan_id: str) -> dict[str, Any]:
        """List documents associated with a loan."""
        params = {"loan_id": loan_id}
        result = await self._request("GET", "/documents", params=params)
        if "error" not in result:
            self._log.info("documents_listed", loan_id=loan_id, count=len(result.get("data", [])))
        return result

    async def upload_document(
        self,
        loan_id: str,
        name: str,
        doc_type: str,
        content: bytes,
    ) -> dict[str, Any]:
        """Upload a document for a loan.

        doc_type: income, asset, credit, property, compliance
        """
        encoded = base64.b64encode(content).decode()
        payload = {
            "loan_id": loan_id,
            "name": name,
            "type": doc_type,
            "content": encoded,
        }
        result = await self._request("POST", "/documents", json=payload)
        if "error" not in result:
            self._log.info("document_uploaded", loan_id=loan_id, name=name, doc_type=doc_type)
        return result

    async def get_document(self, doc_id: str) -> dict[str, Any]:
        """Download a document by ID."""
        result = await self._request("GET", f"/documents/{doc_id}", _raw_response=True)
        if "error" not in result:
            self._log.info("document_downloaded", doc_id=doc_id, size=len(result.get("content", b"")))
        return result

    # ═══════════════════════════════════════════════════════
    # WEBHOOKS (Event Subscriptions)
    # ═══════════════════════════════════════════════════════

    async def register_webhook(
        self,
        event: str,
        url: str,
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Register a webhook for an event.

        Events: contact.created, contact.updated, loan.created,
        loan.status_changed, task.created, task.completed,
        document.uploaded, campaign.completed
        """
        payload: dict[str, Any] = {"event": event, "url": url}
        if secret:
            payload["secret"] = secret
        result = await self._request("POST", "/webhooks", json=payload)
        if "error" not in result:
            self._log.info("webhook_registered", event=event, webhook_id=result.get("id", ""))
        return result

    async def unregister_webhook(self, webhook_id: str) -> dict[str, Any]:
        """Unregister (delete) a webhook subscription."""
        result = await self._request("DELETE", f"/webhooks/{webhook_id}")
        if "error" not in result:
            self._log.info("webhook_unregistered", webhook_id=webhook_id)
        return result

    # ═══════════════════════════════════════════════════════
    # BULK / SYNC METHODS
    # ═══════════════════════════════════════════════════════

    async def sync_all_contacts(self, since: str | None = None) -> dict[str, Any]:
        """Paginate through all contacts, optionally filtered by updated_at >= since."""
        all_contacts: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            filters: dict[str, Any] = {}
            if since:
                filters["updated_since"] = since
            result = await self.list_contacts(filters=filters, page=page, per_page=per_page)
            if "error" in result:
                return result

            batch = result.get("data", [])
            if not batch:
                break
            all_contacts.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        self._log.info("contacts_synced", total=len(all_contacts), since=since)
        return {"contacts": all_contacts, "total": len(all_contacts), "synced_at": datetime.now(timezone.utc).isoformat()}

    async def sync_all_loans(self, since: str | None = None) -> dict[str, Any]:
        """Paginate through all loans, optionally filtered by updated_at >= since."""
        all_loans: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            filters: dict[str, Any] = {}
            if since:
                filters["updated_since"] = since
            result = await self.list_loans(filters=filters, page=page, per_page=per_page)
            if "error" in result:
                return result

            batch = result.get("data", [])
            if not batch:
                break
            all_loans.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        self._log.info("loans_synced", total=len(all_loans), since=since)
        return {"loans": all_loans, "total": len(all_loans), "synced_at": datetime.now(timezone.utc).isoformat()}

    async def get_pipeline_summary(self) -> dict[str, Any]:
        """Aggregate pipeline summary across all loan officers."""
        officers_result = await self.list_loan_officers()
        if "error" in officers_result:
            return officers_result

        officers = officers_result.get("data", [])
        summary: dict[str, Any] = {
            "total_officers": len(officers),
            "officers": [],
            "totals": {
                "active_loans": 0,
                "pipeline_volume": 0.0,
                "ytd_funded": 0.0,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        for officer in officers:
            officer_summary = {
                "id": officer.get("id", ""),
                "name": officer.get("name", ""),
                "nmls_id": officer.get("nmls_id", ""),
                "active_loans_count": officer.get("active_loans_count", 0),
                "pipeline_volume": officer.get("pipeline_volume", 0.0),
                "ytd_funded": officer.get("ytd_funded", 0.0),
            }
            summary["officers"].append(officer_summary)
            summary["totals"]["active_loans"] += officer.get("active_loans_count", 0)
            summary["totals"]["pipeline_volume"] += officer.get("pipeline_volume", 0.0)
            summary["totals"]["ytd_funded"] += officer.get("ytd_funded", 0.0)

        self._log.info(
            "pipeline_summary_generated",
            officers=len(officers),
            active_loans=summary["totals"]["active_loans"],
        )
        return summary

    # ═══════════════════════════════════════════════════════
    # STATUS & AUDIT
    # ═══════════════════════════════════════════════════════

    def get_blocked_attempts(self) -> list[dict[str, str]]:
        """Return audit log of blocked deletion attempts."""
        return list(self._blocked_attempts)

    def get_status(self) -> dict[str, Any]:
        """Return client connection and auth status."""
        now = datetime.now(timezone.utc)
        token_valid = bool(
            self._access_token
            and self._token_expiry
            and now < self._token_expiry
        )
        return {
            "component": "total_expert",
            "base_url": self._base_url,
            "authenticated": token_valid,
            "token_expires_at": self._token_expiry.isoformat() if self._token_expiry else None,
            "rate_limit": self._rate_limit,
            "rate_tokens_remaining": round(self._tokens, 1),
            "blocked_attempts": len(self._blocked_attempts),
            "checked_at": now.isoformat(),
        }
