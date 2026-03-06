"""Priority-based async task queue for MortgageFintechOS."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, Enum
from typing import Any


class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(order=True)
class Task:
    priority: TaskPriority
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8], compare=False)
    agent_name: str = field(default="", compare=False)
    action: str = field(default="", compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), compare=False
    )
    result: dict[str, Any] | None = field(default=None, compare=False)
    error: str | None = field(default=None, compare=False)


class TaskQueue:
    """Async priority queue for agent tasks."""

    def __init__(self, maxsize: int = 0):
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue(maxsize=maxsize)
        self._history: list[Task] = []

    async def enqueue(self, task: Task) -> str:
        await self._queue.put(task)
        return task.id

    async def dequeue(self) -> Task:
        task = await self._queue.get()
        task.status = TaskStatus.RUNNING
        return task

    def complete(self, task: Task, result: dict[str, Any] | None = None) -> None:
        task.status = TaskStatus.COMPLETED
        task.result = result
        self._history.append(task)

    def fail(self, task: Task, error: str) -> None:
        task.error = error
        if task.retries < task.max_retries:
            task.retries += 1
            task.status = TaskStatus.RETRYING
        else:
            task.status = TaskStatus.FAILED
            self._history.append(task)

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def history(self) -> list[Task]:
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        completed = sum(1 for t in self._history if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._history if t.status == TaskStatus.FAILED)
        return {
            "pending": self._queue.qsize(),
            "completed": completed,
            "failed": failed,
            "total_processed": len(self._history),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize queue history for persistence."""
        return {
            "history": [
                {
                    "id": t.id,
                    "priority": t.priority.value,
                    "agent_name": t.agent_name,
                    "action": t.action,
                    "payload": t.payload,
                    "retries": t.retries,
                    "max_retries": t.max_retries,
                    "status": t.status.value,
                    "created_at": t.created_at.isoformat(),
                    "result": t.result,
                    "error": t.error,
                }
                for t in self._history
            ]
        }

    def restore_from_dict(self, data: dict[str, Any]) -> None:
        """Restore queue history from persisted data."""
        for item in data.get("history", []):
            task = Task(
                priority=TaskPriority(item["priority"]),
                id=item["id"],
                agent_name=item["agent_name"],
                action=item["action"],
                payload=item.get("payload", {}),
                retries=item.get("retries", 0),
                max_retries=item.get("max_retries", 3),
                status=TaskStatus(item["status"]),
                result=item.get("result"),
                error=item.get("error"),
            )
            if "created_at" in item:
                task.created_at = datetime.fromisoformat(item["created_at"])
            self._history.append(task)
