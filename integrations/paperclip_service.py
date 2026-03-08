"""Paperclip AI — Enterprise Agent Orchestration Service.

Provides ticket management, budget enforcement, audit logging,
and governance workflows for MortgageFintechOS agents.
Persists state to JSON via the StateStore.
"""

import json
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

DEFAULT_BUDGETS = {
    "DIEGO": {"budget": 500, "used": 0},
    "MARTIN": {"budget": 500, "used": 0},
    "NOVA": {"budget": 400, "used": 0},
    "JARVIS": {"budget": 400, "used": 0},
    "ATLAS": {"budget": 800, "used": 0},
    "CIPHER": {"budget": 600, "used": 0},
    "FORGE": {"budget": 700, "used": 0},
    "NEXUS": {"budget": 500, "used": 0},
    "STORM": {"budget": 300, "used": 0},
    "SENTINEL": {"budget": 400, "used": 0},
}


class PaperclipService:
    """In-process Paperclip AI service with persistent state."""

    def __init__(self) -> None:
        self._tickets: list[dict[str, Any]] = []
        self._audit_log: list[dict[str, Any]] = []
        self._budgets: dict[str, dict[str, int]] = {}
        self._log = logger.bind(component="paperclip")
        self._next_ticket_num = 1
        self._started = False

    # --- Lifecycle ---

    async def start(self, state_store: Any) -> None:
        """Load persisted state from the state store."""
        self._state_store = state_store
        data = await state_store.load("paperclip") or {}
        self._tickets = data.get("tickets", [])
        self._audit_log = data.get("audit_log", [])
        self._budgets = data.get("budgets", {})
        self._next_ticket_num = data.get("next_ticket_num", 1)

        # Ensure every agent has a budget entry
        for agent, defaults in DEFAULT_BUDGETS.items():
            if agent not in self._budgets:
                self._budgets[agent] = dict(defaults)

        self._started = True
        self._audit("system", "Paperclip AI service started")
        self._log.info("paperclip_started", tickets=len(self._tickets))

    async def _persist(self) -> None:
        if hasattr(self, "_state_store"):
            await self._state_store.save_debounced("paperclip", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "tickets": self._tickets,
            "audit_log": self._audit_log[-200:],
            "budgets": self._budgets,
            "next_ticket_num": self._next_ticket_num,
        }

    # --- Audit ---

    def _audit(self, event_type: str, message: str) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "msg": message,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > 200:
            self._audit_log = self._audit_log[-200:]
        self._log.info("paperclip_audit", type=event_type, msg=message)

    # --- Tickets ---

    async def create_ticket(self, owner: str, title: str, estimated_cost: int = 0) -> dict[str, Any]:
        ticket_id = f"TKT-{self._next_ticket_num:03d}"
        self._next_ticket_num += 1

        ticket = {
            "id": ticket_id,
            "title": title,
            "owner": owner,
            "status": "open",
            "created": datetime.now(timezone.utc).isoformat(),
            "approved": False,
            "estimated_cost": estimated_cost,
            "completed_at": None,
        }
        self._tickets.insert(0, ticket)
        self._audit("ticket", f'Created {ticket_id}: "{title}" → assigned to {owner}')
        self._audit("governance", f"{ticket_id} requires Board approval before execution")

        # Deduct estimated cost from budget
        if estimated_cost > 0 and owner in self._budgets:
            self._budgets[owner]["used"] += estimated_cost
            used_pct = round(self._budgets[owner]["used"] / self._budgets[owner]["budget"] * 100)
            if used_pct >= 100:
                self._audit("budget", f"{owner} budget EXHAUSTED ({used_pct}%) — agent auto-paused")
            elif used_pct >= 80:
                self._audit("budget", f"{owner} budget WARNING ({used_pct}%)")

        await self._persist()
        return ticket

    async def approve_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._find_ticket(ticket_id)
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found"}
        if ticket["status"] != "open":
            return {"error": f"Ticket {ticket_id} is {ticket['status']}, cannot approve"}

        ticket["status"] = "approved"
        ticket["approved"] = True
        self._audit("approval", f'Board APPROVED {ticket_id}: "{ticket["title"]}"')
        await self._persist()
        return ticket

    async def reject_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._find_ticket(ticket_id)
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found"}
        if ticket["status"] != "open":
            return {"error": f"Ticket {ticket_id} is {ticket['status']}, cannot reject"}

        ticket["status"] = "rejected"
        self._audit("rejection", f'Board REJECTED {ticket_id}: "{ticket["title"]}"')
        await self._persist()
        return ticket

    async def start_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._find_ticket(ticket_id)
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found"}
        if ticket["status"] != "approved":
            return {"error": f"Ticket {ticket_id} is {ticket['status']}, must be approved first"}

        ticket["status"] = "in_progress"
        self._audit("execution", f'{ticket["owner"]} started work on {ticket_id}')
        await self._persist()
        return ticket

    async def complete_ticket(self, ticket_id: str) -> dict[str, Any]:
        ticket = self._find_ticket(ticket_id)
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found"}

        ticket["status"] = "completed"
        ticket["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._audit("completion", f'{ticket["owner"]} completed {ticket_id}: "{ticket["title"]}"')
        await self._persist()
        return ticket

    def _find_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        return next((t for t in self._tickets if t["id"] == ticket_id), None)

    def list_tickets(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        tickets = self._tickets
        if status:
            tickets = [t for t in tickets if t["status"] == status]
        return tickets[:limit]

    # --- Budgets ---

    def get_budgets(self) -> dict[str, dict[str, Any]]:
        result = {}
        for agent, b in self._budgets.items():
            pct = round(b["used"] / b["budget"] * 100) if b["budget"] > 0 else 0
            result[agent] = {
                "budget": b["budget"],
                "used": b["used"],
                "pct": pct,
                "status": "PAUSED" if pct >= 100 else "WARNING" if pct >= 80 else "ACTIVE",
            }
        return result

    async def set_budget(self, agent: str, budget: int) -> dict[str, Any]:
        if agent not in self._budgets:
            return {"error": f"Agent {agent} not found"}
        self._budgets[agent]["budget"] = budget
        self._audit("budget", f"{agent} budget updated to ${budget}/mo")
        await self._persist()
        return self._budgets[agent]

    async def reset_budget(self, agent: str) -> dict[str, Any]:
        if agent not in self._budgets:
            return {"error": f"Agent {agent} not found"}
        self._budgets[agent]["used"] = 0
        self._audit("budget", f"{agent} budget usage reset to $0")
        await self._persist()
        return self._budgets[agent]

    def is_agent_paused(self, agent: str) -> bool:
        b = self._budgets.get(agent)
        if not b:
            return False
        return b["used"] >= b["budget"]

    # --- Audit Log ---

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._audit_log[-limit:]))

    # --- Status ---

    def get_status(self) -> dict[str, Any]:
        return {
            "connected": self._started,
            "tickets_total": len(self._tickets),
            "tickets_open": sum(1 for t in self._tickets if t["status"] == "open"),
            "tickets_completed": sum(1 for t in self._tickets if t["status"] == "completed"),
            "budgets": self.get_budgets(),
            "audit_entries": len(self._audit_log),
        }
