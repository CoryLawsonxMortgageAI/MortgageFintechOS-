"""Agent Action Log for MortgageFintechOS.

Centralized, append-only log capturing every agent action with timing,
status, integration calls, and results. Provides real-time visibility
into what agents are doing and have done.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ActionType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    INTEGRATION_CALL = "integration_call"
    SCHEDULE_FIRED = "schedule_fired"
    SAFETY_BLOCKED = "safety_blocked"
    STATE_SAVED = "state_saved"
    HEALTH_ALERT = "health_alert"
    PROPOSAL_CREATED = "proposal_created"


@dataclass
class ActionEntry:
    timestamp: str
    agent: str
    action_type: str
    action: str
    detail: str = ""
    duration_ms: int = 0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action_type": self.action_type,
            "action": self.action,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "metadata": self.metadata,
        }


class ActionLog:
    """Append-only action log with bounded memory and query support."""

    def __init__(self, max_entries: int = 2000):
        self._entries: deque[ActionEntry] = deque(maxlen=max_entries)
        self._log = logger.bind(component="action_log")
        self._counters: dict[str, int] = {}

    def record(
        self,
        agent: str,
        action_type: ActionType | str,
        action: str,
        detail: str = "",
        duration_ms: int = 0,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = ActionEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            action_type=action_type.value if isinstance(action_type, ActionType) else action_type,
            action=action,
            detail=detail[:500],
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
        )
        self._entries.append(entry)

        # Update counters
        key = f"{agent}:{action_type}"
        self._counters[key] = self._counters.get(key, 0) + 1

    def query(
        self,
        agent: str = "",
        action_type: str = "",
        limit: int = 50,
        offset: int = 0,
        success_only: bool = False,
        failures_only: bool = False,
    ) -> list[dict[str, Any]]:
        results = []
        for entry in reversed(self._entries):
            if agent and entry.agent != agent:
                continue
            if action_type and entry.action_type != action_type:
                continue
            if success_only and not entry.success:
                continue
            if failures_only and entry.success:
                continue
            results.append(entry.to_dict())

        return results[offset : offset + limit]

    def get_stats(self) -> dict[str, Any]:
        total = len(self._entries)
        successes = sum(1 for e in self._entries if e.success)
        failures = total - successes

        # Per-agent breakdown
        agent_stats: dict[str, dict[str, int]] = {}
        for entry in self._entries:
            if entry.agent not in agent_stats:
                agent_stats[entry.agent] = {"total": 0, "success": 0, "failed": 0}
            agent_stats[entry.agent]["total"] += 1
            if entry.success:
                agent_stats[entry.agent]["success"] += 1
            else:
                agent_stats[entry.agent]["failed"] += 1

        # Recent action types
        type_counts: dict[str, int] = {}
        for entry in self._entries:
            type_counts[entry.action_type] = type_counts.get(entry.action_type, 0) + 1

        return {
            "total_entries": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / total * 100, 1) if total else 0,
            "agent_breakdown": agent_stats,
            "action_types": type_counts,
        }

    def get_timeline(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get action counts bucketed by hour for timeline visualization."""
        now = datetime.now(timezone.utc)
        buckets: dict[int, dict[str, int]] = {}
        for h in range(hours):
            buckets[h] = {"hour": h, "total": 0, "success": 0, "failed": 0}

        for entry in self._entries:
            ts = datetime.fromisoformat(entry.timestamp)
            age_hours = (now - ts).total_seconds() / 3600
            if age_hours < hours:
                bucket = int(age_hours)
                buckets[bucket]["total"] += 1
                if entry.success:
                    buckets[bucket]["success"] += 1
                else:
                    buckets[bucket]["failed"] += 1

        return list(buckets.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in list(self._entries)[-500:]],
            "counters": self._counters,
        }

    def restore_from_dict(self, data: dict[str, Any]) -> None:
        self._counters = data.get("counters", {})
        for entry_data in data.get("entries", []):
            self._entries.append(ActionEntry(**entry_data))
