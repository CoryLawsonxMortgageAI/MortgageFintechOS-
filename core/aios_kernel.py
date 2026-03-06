"""AIOS Kernel — Intelligent Agent Operating System Kernel.

The AIOS Kernel sits atop the orchestrator as a dedicated resource manager
built specifically for agent operations. It governs agent behavior in real
time with priority scheduling, resource isolation, dependency resolution,
context management, and agent-to-agent communication.

Architecture:
    Traditional OS Kernel → Python asyncio event loop
    AIOS Kernel → Agent-aware scheduler, resource manager, IPC layer
    Agents → DIEGO, MARTIN, NOVA, JARVIS, ATLAS, CIPHER, FORGE, NEXUS, STORM

Key capabilities:
- Priority-based agent scheduling with preemption
- Resource quotas per agent (concurrency, memory budget, I/O limits)
- Agent dependency graph and pipeline orchestration
- Inter-agent communication via message bus
- Context window management for LLM-backed agents
- Real-time telemetry and resource accounting
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


class AgentPriority(int, Enum):
    """Agent scheduling priority (lower = higher priority)."""
    CRITICAL = 0   # Security patches (CIPHER)
    HIGH = 1       # Production deployments (FORGE), Pipeline ops (DIEGO)
    NORMAL = 2     # Feature development (ATLAS), Code review (NEXUS)
    LOW = 3        # Analytics (STORM), Reporting
    BACKGROUND = 4 # Tech debt, optimization


class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    LLM_CONTEXT = "llm_context"


@dataclass
class AgentQuota:
    """Resource quota for an agent."""
    max_concurrent_tasks: int = 3
    memory_budget_mb: int = 512
    io_ops_per_second: int = 100
    network_requests_per_minute: int = 60
    llm_context_tokens: int = 128000
    priority: AgentPriority = AgentPriority.NORMAL
    preemptible: bool = True


@dataclass
class AgentContext:
    """Runtime context for a managed agent."""
    name: str
    quota: AgentQuota
    active_tasks: int = 0
    total_cpu_time_ms: float = 0
    total_memory_mb: float = 0
    total_io_ops: int = 0
    total_network_requests: int = 0
    last_scheduled: datetime | None = None
    suspended: bool = False
    suspend_reason: str = ""


@dataclass
class AgentMessage:
    """Inter-agent communication message."""
    id: str
    from_agent: str
    to_agent: str
    message_type: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


@dataclass
class AgentDependency:
    """Dependency between two agents for pipeline orchestration."""
    upstream: str
    downstream: str
    trigger_action: str
    target_action: str
    auto_trigger: bool = True


# Default resource quotas per agent role
DEFAULT_QUOTAS = {
    # Mortgage Operations Agents
    "DIEGO":  AgentQuota(max_concurrent_tasks=5, memory_budget_mb=256, priority=AgentPriority.HIGH),
    "MARTIN": AgentQuota(max_concurrent_tasks=4, memory_budget_mb=512, priority=AgentPriority.NORMAL, io_ops_per_second=200),
    "NOVA":   AgentQuota(max_concurrent_tasks=3, memory_budget_mb=384, priority=AgentPriority.NORMAL),
    "JARVIS": AgentQuota(max_concurrent_tasks=3, memory_budget_mb=256, priority=AgentPriority.NORMAL),
    # Coding Expert Agents
    "ATLAS":  AgentQuota(max_concurrent_tasks=3, memory_budget_mb=1024, priority=AgentPriority.NORMAL, llm_context_tokens=200000),
    "CIPHER": AgentQuota(max_concurrent_tasks=2, memory_budget_mb=512, priority=AgentPriority.CRITICAL, preemptible=False),
    "FORGE":  AgentQuota(max_concurrent_tasks=2, memory_budget_mb=768, priority=AgentPriority.HIGH, network_requests_per_minute=120),
    "NEXUS":  AgentQuota(max_concurrent_tasks=4, memory_budget_mb=512, priority=AgentPriority.NORMAL, llm_context_tokens=200000),
    "STORM":  AgentQuota(max_concurrent_tasks=3, memory_budget_mb=1024, priority=AgentPriority.LOW, io_ops_per_second=500),
}

# Default agent pipelines (dependency chains)
DEFAULT_PIPELINES = [
    # Code shipping pipeline: ATLAS writes → NEXUS reviews → CIPHER scans → FORGE deploys
    AgentDependency("ATLAS", "NEXUS", "generate_feature", "review_code"),
    AgentDependency("NEXUS", "CIPHER", "review_code", "run_security_audit"),
    AgentDependency("CIPHER", "FORGE", "run_security_audit", "run_pipeline"),
    AgentDependency("FORGE", "FORGE", "run_pipeline", "deploy"),
    # Document pipeline: MARTIN classifies → NOVA analyzes income → JARVIS resolves conditions
    AgentDependency("MARTIN", "NOVA", "classify_document", "analyze_income"),
    AgentDependency("NOVA", "JARVIS", "analyze_income", "map_conditions"),
    # Data pipeline: STORM generates reports → ATLAS builds dashboards
    AgentDependency("STORM", "ATLAS", "generate_analytics", "generate_feature"),
]


class AIOSKernel:
    """Intelligent Agent Operating System Kernel.

    Manages agent lifecycle, resource allocation, priority scheduling,
    inter-agent communication, and dependency-driven pipelines.
    """

    def __init__(self) -> None:
        self._log = logger.bind(component="aios_kernel")
        self._contexts: dict[str, AgentContext] = {}
        self._message_bus: dict[str, deque[AgentMessage]] = defaultdict(lambda: deque(maxlen=1000))
        self._dependencies: list[AgentDependency] = list(DEFAULT_PIPELINES)
        self._scheduler_queue: asyncio.PriorityQueue[tuple[int, str, dict]] = asyncio.PriorityQueue()
        self._running = False
        self._telemetry: list[dict[str, Any]] = []
        self._total_messages: int = 0
        self._total_preemptions: int = 0
        self._total_pipeline_triggers: int = 0
        self._pipeline_callback: Callable[..., Coroutine] | None = None

    def initialize(self, agent_names: list[str]) -> None:
        """Initialize kernel with registered agents."""
        for name in agent_names:
            quota = DEFAULT_QUOTAS.get(name, AgentQuota())
            self._contexts[name] = AgentContext(name=name, quota=quota)
            self._message_bus[name] = deque(maxlen=1000)
        self._log.info("kernel_initialized", agents=agent_names)

    def set_pipeline_callback(self, callback: Callable[..., Coroutine]) -> None:
        """Set callback for triggering downstream agent tasks."""
        self._pipeline_callback = callback

    # --- Resource Management ---

    def can_schedule(self, agent_name: str) -> bool:
        """Check if an agent can accept another task based on its resource quota."""
        ctx = self._contexts.get(agent_name)
        if not ctx:
            return False
        if ctx.suspended:
            return False
        return ctx.active_tasks < ctx.quota.max_concurrent_tasks

    def acquire_slot(self, agent_name: str) -> bool:
        """Acquire a task execution slot for an agent."""
        ctx = self._contexts.get(agent_name)
        if not ctx or not self.can_schedule(agent_name):
            return False
        ctx.active_tasks += 1
        ctx.last_scheduled = datetime.now(timezone.utc)
        return True

    def release_slot(self, agent_name: str) -> None:
        """Release a task execution slot."""
        ctx = self._contexts.get(agent_name)
        if ctx and ctx.active_tasks > 0:
            ctx.active_tasks -= 1

    def suspend_agent(self, agent_name: str, reason: str = "") -> None:
        """Suspend an agent from scheduling."""
        ctx = self._contexts.get(agent_name)
        if ctx:
            ctx.suspended = True
            ctx.suspend_reason = reason
            self._log.warning("agent_suspended", agent=agent_name, reason=reason)

    def resume_agent(self, agent_name: str) -> None:
        """Resume a suspended agent."""
        ctx = self._contexts.get(agent_name)
        if ctx:
            ctx.suspended = False
            ctx.suspend_reason = ""
            self._log.info("agent_resumed", agent=agent_name)

    def should_preempt(self, running_agent: str, incoming_agent: str) -> bool:
        """Determine if incoming task should preempt the running agent."""
        running_ctx = self._contexts.get(running_agent)
        incoming_ctx = self._contexts.get(incoming_agent)
        if not running_ctx or not incoming_ctx:
            return False
        if not running_ctx.quota.preemptible:
            return False
        return incoming_ctx.quota.priority.value < running_ctx.quota.priority.value

    # --- Resource Accounting ---

    def record_resource_usage(
        self,
        agent_name: str,
        cpu_time_ms: float = 0,
        memory_mb: float = 0,
        io_ops: int = 0,
        network_requests: int = 0,
    ) -> None:
        """Record resource usage for an agent."""
        ctx = self._contexts.get(agent_name)
        if ctx:
            ctx.total_cpu_time_ms += cpu_time_ms
            ctx.total_memory_mb = max(ctx.total_memory_mb, memory_mb)
            ctx.total_io_ops += io_ops
            ctx.total_network_requests += network_requests

            # Check quota violations
            if memory_mb > ctx.quota.memory_budget_mb:
                self._log.warning("memory_quota_exceeded", agent=agent_name, used=memory_mb, limit=ctx.quota.memory_budget_mb)

    # --- Inter-Agent Communication ---

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> str:
        """Send a message from one agent to another."""
        msg_id = f"MSG-{self._total_messages + 1}"
        message = AgentMessage(
            id=msg_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
        )
        self._message_bus[to_agent].append(message)
        self._total_messages += 1
        self._log.debug("message_sent", msg_id=msg_id, from_agent=from_agent, to_agent=to_agent, type=message_type)
        return msg_id

    def receive_messages(self, agent_name: str, message_type: str | None = None) -> list[AgentMessage]:
        """Receive pending messages for an agent."""
        inbox = self._message_bus.get(agent_name, deque())
        messages = []
        remaining = deque()

        for msg in inbox:
            if not msg.acknowledged and (message_type is None or msg.message_type == message_type):
                msg.acknowledged = True
                messages.append(msg)
            else:
                remaining.append(msg)

        self._message_bus[agent_name] = remaining
        return messages

    def get_inbox_count(self, agent_name: str) -> int:
        """Get count of unread messages for an agent."""
        return sum(1 for m in self._message_bus.get(agent_name, deque()) if not m.acknowledged)

    # --- Pipeline Orchestration ---

    async def trigger_downstream(self, completed_agent: str, completed_action: str, result: dict[str, Any]) -> list[str]:
        """Trigger downstream agents in dependency pipelines."""
        triggered = []

        for dep in self._dependencies:
            if dep.upstream == completed_agent and dep.trigger_action == completed_action and dep.auto_trigger:
                if self._pipeline_callback:
                    self._log.info(
                        "pipeline_trigger",
                        upstream=dep.upstream,
                        downstream=dep.downstream,
                        action=dep.target_action,
                    )

                    # Send context via message bus
                    self.send_message(
                        from_agent=completed_agent,
                        to_agent=dep.downstream,
                        message_type="pipeline_context",
                        payload={"upstream_action": completed_action, "upstream_result": result},
                    )

                    await self._pipeline_callback(dep.downstream, dep.target_action, result)
                    triggered.append(f"{dep.downstream}.{dep.target_action}")
                    self._total_pipeline_triggers += 1

        return triggered

    def add_dependency(self, dependency: AgentDependency) -> None:
        """Add a new agent dependency."""
        self._dependencies.append(dependency)

    def get_dependency_graph(self) -> list[dict[str, str]]:
        """Return the dependency graph as a list of edges."""
        return [
            {
                "upstream": d.upstream,
                "downstream": d.downstream,
                "trigger": d.trigger_action,
                "target": d.target_action,
                "auto": d.auto_trigger,
            }
            for d in self._dependencies
        ]

    # --- Telemetry & Status ---

    def get_kernel_status(self) -> dict[str, Any]:
        """Return full kernel status for dashboard/API."""
        agents = {}
        for name, ctx in self._contexts.items():
            agents[name] = {
                "priority": ctx.quota.priority.name,
                "active_tasks": ctx.active_tasks,
                "max_concurrent": ctx.quota.max_concurrent_tasks,
                "memory_budget_mb": ctx.quota.memory_budget_mb,
                "memory_used_mb": round(ctx.total_memory_mb, 1),
                "total_cpu_time_ms": round(ctx.total_cpu_time_ms, 1),
                "total_io_ops": ctx.total_io_ops,
                "suspended": ctx.suspended,
                "suspend_reason": ctx.suspend_reason,
                "inbox_count": self.get_inbox_count(name),
                "last_scheduled": ctx.last_scheduled.isoformat() if ctx.last_scheduled else None,
            }

        return {
            "kernel_version": "1.0.0",
            "agents": agents,
            "total_messages": self._total_messages,
            "total_preemptions": self._total_preemptions,
            "total_pipeline_triggers": self._total_pipeline_triggers,
            "dependency_graph": self.get_dependency_graph(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_state(self) -> dict[str, Any]:
        """Return serializable kernel state for persistence."""
        return {
            "total_messages": self._total_messages,
            "total_preemptions": self._total_preemptions,
            "total_pipeline_triggers": self._total_pipeline_triggers,
            "agent_contexts": {
                name: {
                    "total_cpu_time_ms": ctx.total_cpu_time_ms,
                    "total_memory_mb": ctx.total_memory_mb,
                    "total_io_ops": ctx.total_io_ops,
                    "total_network_requests": ctx.total_network_requests,
                }
                for name, ctx in self._contexts.items()
            },
        }

    def restore_state(self, data: dict[str, Any]) -> None:
        """Restore kernel state from persistence."""
        self._total_messages = data.get("total_messages", 0)
        self._total_preemptions = data.get("total_preemptions", 0)
        self._total_pipeline_triggers = data.get("total_pipeline_triggers", 0)

        for name, ctx_data in data.get("agent_contexts", {}).items():
            if name in self._contexts:
                self._contexts[name].total_cpu_time_ms = ctx_data.get("total_cpu_time_ms", 0)
                self._contexts[name].total_memory_mb = ctx_data.get("total_memory_mb", 0)
                self._contexts[name].total_io_ops = ctx_data.get("total_io_ops", 0)
                self._contexts[name].total_network_requests = ctx_data.get("total_network_requests", 0)
