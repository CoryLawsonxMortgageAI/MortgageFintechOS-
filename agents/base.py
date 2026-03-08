"""Abstract base agent for MortgageFintechOS AI agents."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

from core.task_queue import Task

if TYPE_CHECKING:
    from integrations.github_client import GitHubClient
    from integrations.notion_client import NotionClient
    from integrations.gdrive_client import GDriveClient
    from integrations.llm_router import LLMRouter
    from persistence.state_store import StateStore

logger = structlog.get_logger()


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCategory(str, Enum):
    MORTGAGE = "mortgage"
    ENGINEERING = "engineering"


class BaseAgent(ABC):
    """Base class for all MortgageFintechOS agents."""

    def __init__(self, name: str, max_retries: int = 3, category: AgentCategory = AgentCategory.MORTGAGE):
        self.name = name
        self.category = category
        self.status = AgentStatus.IDLE
        self.last_heartbeat: datetime = datetime.now(timezone.utc)
        self.error_count: int = 0
        self.tasks_completed: int = 0
        self.max_retries = max_retries
        self._running = False
        self._state_store: "StateStore | None" = None
        self._github: "GitHubClient | None" = None
        self._notion: "NotionClient | None" = None
        self._gdrive: "GDriveClient | None" = None
        self._llm: "LLMRouter | None" = None
        self._log = logger.bind(agent=name)

    @abstractmethod
    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a task. Must be implemented by each agent."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return agent health status. Must be implemented by each agent."""

    async def run_task(self, task: Task) -> dict[str, Any]:
        """Run a task with retry logic."""
        self.status = AgentStatus.RUNNING
        self._update_heartbeat()

        for attempt in range(1, self.max_retries + 1):
            try:
                self._log.info("executing_task", task_id=task.id, action=task.action, attempt=attempt)
                result = await self.execute(task)
                self.tasks_completed += 1
                self.status = AgentStatus.IDLE
                self._update_heartbeat()
                self._log.info("task_completed", task_id=task.id)
                return result
            except Exception as e:
                self.error_count += 1
                self._log.error("task_failed", task_id=task.id, attempt=attempt, error=str(e))
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.status = AgentStatus.ERROR
                    raise

        return {}

    def stop(self) -> None:
        self._running = False
        self.status = AgentStatus.STOPPED
        self._log.info("agent_stopped")

    def _update_heartbeat(self) -> None:
        self.last_heartbeat = datetime.now(timezone.utc)

    # --- Integration hooks ---

    def set_integrations(
        self,
        github: "GitHubClient | None" = None,
        notion: "NotionClient | None" = None,
        gdrive: "GDriveClient | None" = None,
        llm: "LLMRouter | None" = None,
    ) -> None:
        """Inject integration clients for this agent to use."""
        self._github = github
        self._notion = notion
        self._gdrive = gdrive
        self._llm = llm
        self._log.info("integrations_set", github=bool(github), notion=bool(notion), gdrive=bool(gdrive), llm=bool(llm))

    async def llm_complete(
        self,
        action: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Route an LLM completion through the router. Returns response text."""
        if not self._llm:
            return ""
        result = await self._llm.complete(
            agent_name=self.name,
            action=action,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result.get("response", "")

    # --- Persistence hooks ---

    def set_state_store(self, store: "StateStore") -> None:
        self._state_store = store

    async def save_state(self) -> None:
        """Persist agent state to disk (debounced)."""
        if self._state_store:
            data = self._get_state()
            if data:
                await self._state_store.save_debounced(f"agent_{self.name.lower()}", data)

    async def load_state(self) -> None:
        """Restore agent state from disk."""
        if self._state_store:
            data = await self._state_store.load(f"agent_{self.name.lower()}")
            if data:
                self._restore_state(data)
                self._log.info("state_restored", keys=list(data.keys()))

    def _get_state(self) -> dict[str, Any]:
        """Return serializable agent state. Override in subclasses."""
        return {}

    def _restore_state(self, data: dict[str, Any]) -> None:
        """Restore agent state from dict. Override in subclasses."""

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "error_count": self.error_count,
            "tasks_completed": self.tasks_completed,
        }
