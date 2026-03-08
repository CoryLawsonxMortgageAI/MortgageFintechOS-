"""Predictive Telemetry Engine for MortgageFintechOS.

Full telemetry capture and downstream risk prediction. Studies agent
workflows in real-time, calculates contextual risk scores, predicts
failures before they happen, and provides actionable solutions.

Risk Calculation Formula:
  R(agent) = w1*E(t) + w2*L(t) + w3*D(t) + w4*C(t) + w5*Q(t)

Where:
  E(t) = Error rate trend (exponential weighted moving average)
  L(t) = Latency deviation from baseline (z-score)
  D(t) = Dependency health (cascade risk from upstream agents)
  C(t) = Capacity pressure (queue depth / throughput ratio)
  Q(t) = Quality degradation (success rate delta over sliding window)

Weights: w1=0.30, w2=0.15, w3=0.25, w4=0.15, w5=0.15
"""

import math
from collections import deque
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# Risk calculation weights
W_ERROR = 0.30
W_LATENCY = 0.15
W_DEPENDENCY = 0.25
W_CAPACITY = 0.15
W_QUALITY = 0.15

# Thresholds
RISK_CRITICAL = 0.75
RISK_HIGH = 0.50
RISK_MEDIUM = 0.25

# Agent dependency graph for cascade risk calculation
DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "DIEGO": [],
    "MARTIN": ["DIEGO"],
    "NOVA": ["MARTIN"],
    "JARVIS": ["NOVA", "MARTIN"],
    "ATLAS": [],
    "CIPHER": [],
    "FORGE": ["ATLAS"],
    "NEXUS": ["ATLAS"],
    "STORM": [],
    "SENTINEL": [],
    "HUNTER": [],
    "HERALD": ["HUNTER"],
    "AMBASSADOR": ["HERALD", "HUNTER"],
}

# Solutions database keyed by risk factor
SOLUTIONS: dict[str, list[dict[str, str]]] = {
    "high_error_rate": [
        {"action": "Check integration credentials (GitHub token, Notion API key)", "severity": "critical"},
        {"action": "Review agent logs for recurring exception patterns", "severity": "high"},
        {"action": "Increase max_retries if failures are transient (network)", "severity": "medium"},
        {"action": "Reduce task frequency to lower API rate limit pressure", "severity": "medium"},
    ],
    "high_latency": [
        {"action": "Reduce LLM max_tokens for this agent's prompts", "severity": "high"},
        {"action": "Increase heartbeat_timeout_seconds in settings", "severity": "medium"},
        {"action": "Check if GitHub API is rate-limited (X-RateLimit headers)", "severity": "high"},
        {"action": "Split large tasks into smaller sub-tasks", "severity": "medium"},
    ],
    "cascade_risk": [
        {"action": "Fix upstream agent first — downstream agents depend on its output", "severity": "critical"},
        {"action": "Add circuit breaker: skip dependent tasks when upstream is unhealthy", "severity": "high"},
        {"action": "Queue dependent tasks with delay to allow upstream recovery", "severity": "medium"},
    ],
    "capacity_pressure": [
        {"action": "Spread scheduled jobs across more time slots", "severity": "high"},
        {"action": "Lower priority of non-critical tasks to reduce queue pressure", "severity": "medium"},
        {"action": "Increase queue_check_interval_minutes for less frequent health checks", "severity": "low"},
    ],
    "quality_degradation": [
        {"action": "Review recent LLM prompt changes that may have reduced output quality", "severity": "high"},
        {"action": "Check if input data quality has changed (new doc formats, API schema changes)", "severity": "high"},
        {"action": "Run CIPHER compliance check to verify system integrity", "severity": "medium"},
    ],
}


class TelemetryPoint:
    """Single telemetry measurement for an agent."""

    __slots__ = ("timestamp", "agent", "action", "duration_ms", "success", "error_msg", "queue_depth")

    def __init__(self, agent: str, action: str, duration_ms: int, success: bool,
                 error_msg: str = "", queue_depth: int = 0):
        self.timestamp = datetime.now(timezone.utc)
        self.agent = agent
        self.action = action
        self.duration_ms = duration_ms
        self.success = success
        self.error_msg = error_msg
        self.queue_depth = queue_depth


class AgentTelemetry:
    """Per-agent telemetry accumulator with sliding windows."""

    def __init__(self, agent_name: str, window_size: int = 100):
        self.agent = agent_name
        self._points: deque[TelemetryPoint] = deque(maxlen=window_size)
        self._baseline_latency: float = 0.0
        self._baseline_set = False

    def record(self, point: TelemetryPoint) -> None:
        self._points.append(point)
        if not self._baseline_set and len(self._points) >= 10:
            self._baseline_latency = sum(p.duration_ms for p in self._points) / len(self._points)
            self._baseline_set = True

    @property
    def error_rate(self) -> float:
        if not self._points:
            return 0.0
        failures = sum(1 for p in self._points if not p.success)
        return failures / len(self._points)

    @property
    def ewma_error_rate(self) -> float:
        """Exponentially weighted moving average of error rate."""
        if not self._points:
            return 0.0
        alpha = 0.3
        ewma = 0.0
        for p in self._points:
            val = 0.0 if p.success else 1.0
            ewma = alpha * val + (1 - alpha) * ewma
        return ewma

    @property
    def latency_zscore(self) -> float:
        """Z-score of recent latency vs baseline."""
        if not self._baseline_set or len(self._points) < 5:
            return 0.0
        recent = [p.duration_ms for p in list(self._points)[-10:]]
        recent_mean = sum(recent) / len(recent)
        all_durations = [p.duration_ms for p in self._points]
        variance = sum((d - self._baseline_latency) ** 2 for d in all_durations) / len(all_durations)
        std = math.sqrt(variance) if variance > 0 else 1.0
        return (recent_mean - self._baseline_latency) / std

    @property
    def avg_latency_ms(self) -> float:
        if not self._points:
            return 0.0
        return sum(p.duration_ms for p in self._points) / len(self._points)

    @property
    def quality_delta(self) -> float:
        """Success rate change: first half vs second half of window."""
        if len(self._points) < 10:
            return 0.0
        mid = len(self._points) // 2
        points_list = list(self._points)
        first_half = points_list[:mid]
        second_half = points_list[mid:]
        rate_first = sum(1 for p in first_half if p.success) / len(first_half)
        rate_second = sum(1 for p in second_half if p.success) / len(second_half)
        return rate_first - rate_second  # Positive = degrading

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "total_points": len(self._points),
            "error_rate": round(self.error_rate, 4),
            "ewma_error_rate": round(self.ewma_error_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "latency_zscore": round(self.latency_zscore, 2),
            "quality_delta": round(self.quality_delta, 4),
            "baseline_latency_ms": round(self._baseline_latency, 1),
        }


class PredictiveTelemetry:
    """Predictive telemetry engine with downstream risk calculation."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentTelemetry] = {}
        self._log = logger.bind(component="telemetry")
        self._global_queue_depth: int = 0
        self._global_throughput: float = 1.0  # tasks/minute

    def record(self, agent: str, action: str, duration_ms: int, success: bool,
               error_msg: str = "", queue_depth: int = 0) -> None:
        if agent not in self._agents:
            self._agents[agent] = AgentTelemetry(agent)
        point = TelemetryPoint(agent, action, duration_ms, success, error_msg, queue_depth)
        self._agents[agent].record(point)
        self._global_queue_depth = queue_depth

    def set_throughput(self, tasks_per_minute: float) -> None:
        self._global_throughput = max(tasks_per_minute, 0.01)

    def calculate_risk(self, agent_name: str) -> dict[str, Any]:
        """Calculate downstream risk score for an agent.

        R(agent) = w1*E(t) + w2*L(t) + w3*D(t) + w4*C(t) + w5*Q(t)
        """
        tel = self._agents.get(agent_name)
        if not tel:
            return {"agent": agent_name, "risk_score": 0.0, "level": "unknown", "factors": {}}

        # E(t) — Error rate (EWMA, 0-1)
        e_t = min(tel.ewma_error_rate, 1.0)

        # L(t) — Latency deviation (normalize z-score to 0-1 via sigmoid)
        z = tel.latency_zscore
        l_t = 1.0 / (1.0 + math.exp(-z)) if abs(z) < 10 else (1.0 if z > 0 else 0.0)
        l_t = max(l_t - 0.5, 0.0) * 2  # Only penalize above-average latency

        # D(t) — Dependency cascade risk
        deps = DEPENDENCY_GRAPH.get(agent_name, [])
        d_t = 0.0
        if deps:
            dep_risks = []
            for dep in deps:
                dep_tel = self._agents.get(dep)
                if dep_tel:
                    dep_risks.append(dep_tel.ewma_error_rate)
            d_t = max(dep_risks) if dep_risks else 0.0

        # C(t) — Capacity pressure (queue depth / throughput)
        c_t = min(self._global_queue_depth / (self._global_throughput * 60), 1.0)

        # Q(t) — Quality degradation
        q_t = max(tel.quality_delta, 0.0)  # Only count degradation, not improvement

        # Weighted risk score
        risk = W_ERROR * e_t + W_LATENCY * l_t + W_DEPENDENCY * d_t + W_CAPACITY * c_t + W_QUALITY * q_t
        risk = min(risk, 1.0)

        # Determine risk level
        if risk >= RISK_CRITICAL:
            level = "critical"
        elif risk >= RISK_HIGH:
            level = "high"
        elif risk >= RISK_MEDIUM:
            level = "medium"
        else:
            level = "low"

        # Generate solutions for dominant risk factors
        factors = {
            "error_rate": {"value": round(e_t, 4), "weight": W_ERROR, "contribution": round(W_ERROR * e_t, 4)},
            "latency": {"value": round(l_t, 4), "weight": W_LATENCY, "contribution": round(W_LATENCY * l_t, 4)},
            "dependency": {"value": round(d_t, 4), "weight": W_DEPENDENCY, "contribution": round(W_DEPENDENCY * d_t, 4),
                          "upstream_agents": deps},
            "capacity": {"value": round(c_t, 4), "weight": W_CAPACITY, "contribution": round(W_CAPACITY * c_t, 4)},
            "quality": {"value": round(q_t, 4), "weight": W_QUALITY, "contribution": round(W_QUALITY * q_t, 4)},
        }

        # Find dominant risk factor and attach solutions
        dominant = max(factors.items(), key=lambda x: x[1]["contribution"])
        solutions = self._get_solutions(dominant[0], e_t, l_t, d_t, c_t, q_t)

        return {
            "agent": agent_name,
            "risk_score": round(risk, 4),
            "level": level,
            "factors": factors,
            "dominant_factor": dominant[0],
            "solutions": solutions,
            "telemetry": tel.to_dict(),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_solutions(self, dominant: str, e: float, l: float, d: float, c: float, q: float) -> list[dict[str, str]]:
        """Get contextual solutions based on dominant risk factor."""
        solutions = []
        if e > 0.1:
            solutions.extend(SOLUTIONS["high_error_rate"])
        if l > 0.3:
            solutions.extend(SOLUTIONS["high_latency"])
        if d > 0.2:
            solutions.extend(SOLUTIONS["cascade_risk"])
        if c > 0.5:
            solutions.extend(SOLUTIONS["capacity_pressure"])
        if q > 0.1:
            solutions.extend(SOLUTIONS["quality_degradation"])
        return solutions[:6]  # Top 6 most relevant

    def get_all_risks(self) -> dict[str, Any]:
        """Calculate risk for all tracked agents."""
        risks = {}
        for agent_name in self._agents:
            risks[agent_name] = self.calculate_risk(agent_name)

        # Overall system risk = max of individual risks
        max_risk = max((r["risk_score"] for r in risks.values()), default=0.0)
        critical_agents = [name for name, r in risks.items() if r["level"] in ("critical", "high")]

        return {
            "system_risk": round(max_risk, 4),
            "system_level": "critical" if max_risk >= RISK_CRITICAL else "high" if max_risk >= RISK_HIGH else "medium" if max_risk >= RISK_MEDIUM else "low",
            "agents": risks,
            "critical_agents": critical_agents,
            "total_tracked": len(self._agents),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    def predict_failures(self) -> list[dict[str, Any]]:
        """Predict which agents are likely to fail based on telemetry trends."""
        predictions = []
        for agent_name, tel in self._agents.items():
            risk = self.calculate_risk(agent_name)
            if risk["risk_score"] < RISK_MEDIUM:
                continue

            prediction = {
                "agent": agent_name,
                "risk_score": risk["risk_score"],
                "level": risk["level"],
                "dominant_factor": risk["dominant_factor"],
                "prediction": "",
                "confidence": 0.0,
                "solutions": risk["solutions"][:3],
            }

            # Generate prediction text
            if risk["dominant_factor"] == "error_rate":
                prediction["prediction"] = f"{agent_name} error rate trending up ({tel.ewma_error_rate:.1%}). Likely to fail within next 5 tasks."
                prediction["confidence"] = min(tel.ewma_error_rate * 2, 0.95)
            elif risk["dominant_factor"] == "dependency":
                deps = DEPENDENCY_GRAPH.get(agent_name, [])
                prediction["prediction"] = f"{agent_name} at risk due to upstream issues in {', '.join(deps)}. Cascade failure probable."
                prediction["confidence"] = risk["factors"]["dependency"]["value"]
            elif risk["dominant_factor"] == "latency":
                prediction["prediction"] = f"{agent_name} latency {tel.avg_latency_ms:.0f}ms (baseline: {tel._baseline_latency:.0f}ms). May timeout."
                prediction["confidence"] = min(abs(tel.latency_zscore) / 3, 0.9)
            elif risk["dominant_factor"] == "capacity":
                prediction["prediction"] = f"Queue pressure may starve {agent_name}. {self._global_queue_depth} tasks pending."
                prediction["confidence"] = risk["factors"]["capacity"]["value"]
            elif risk["dominant_factor"] == "quality":
                prediction["prediction"] = f"{agent_name} output quality degrading. Success rate dropped {tel.quality_delta:.1%}."
                prediction["confidence"] = min(tel.quality_delta * 3, 0.85)

            prediction["confidence"] = round(prediction["confidence"], 2)
            predictions.append(prediction)

        predictions.sort(key=lambda p: p["risk_score"], reverse=True)
        return predictions

    def get_dependency_cascade(self, agent_name: str) -> dict[str, Any]:
        """Show full downstream impact if an agent fails."""
        affected: list[str] = []
        visited: set[str] = set()

        def _find_dependents(name: str) -> None:
            for agent, deps in DEPENDENCY_GRAPH.items():
                if name in deps and agent not in visited:
                    visited.add(agent)
                    affected.append(agent)
                    _find_dependents(agent)

        _find_dependents(agent_name)

        return {
            "source_agent": agent_name,
            "affected_agents": affected,
            "cascade_depth": len(affected),
            "impact_description": f"If {agent_name} fails, {len(affected)} downstream agents are affected: {', '.join(affected)}" if affected else f"{agent_name} has no downstream dependents.",
        }

    def get_workflow_context(self) -> dict[str, Any]:
        """Capture full workflow context for study and analysis."""
        context: dict[str, Any] = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "agents_tracked": len(self._agents),
            "dependency_graph": DEPENDENCY_GRAPH,
            "risk_formula": "R(agent) = 0.30*E(t) + 0.15*L(t) + 0.25*D(t) + 0.15*C(t) + 0.15*Q(t)",
            "thresholds": {
                "critical": RISK_CRITICAL,
                "high": RISK_HIGH,
                "medium": RISK_MEDIUM,
            },
            "agent_telemetry": {},
        }
        for name, tel in self._agents.items():
            context["agent_telemetry"][name] = tel.to_dict()
        return context
