"""Tests for DIEGO agent pipeline orchestration.

Covers loan triage routing rules, pipeline stage advancement,
priority assignment, and pipeline health monitoring.
"""

from typing import Any

import pytest

from agents.diego import DiegoAgent, PipelineStage
from core.task_queue import Task, TaskPriority


@pytest.fixture
def diego() -> DiegoAgent:
    return DiegoAgent()


def _make_task(action: str, payload: dict[str, Any]) -> Task:
    return Task(priority=TaskPriority.MEDIUM, agent_name="DIEGO", action=action, payload=payload)


# --- Loan Triage Routing ---


@pytest.mark.asyncio
async def test_triage_fha_clean(diego):
    """FHA loan with good credit and DTI should proceed."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "FHA-001",
        "loan_type": "FHA",
        "credit_score": 680,
        "dti": 0.40,
    }))
    assert result["loan_type"] == "FHA"
    assert result["stage"] == "application"
    assert result["recommendation"] == "proceed"
    assert result["flags"] == []


@pytest.mark.asyncio
async def test_triage_fha_low_credit(diego):
    """FHA loan below minimum credit score should flag for review."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "FHA-002",
        "loan_type": "FHA",
        "credit_score": 550,
        "dti": 0.35,
    }))
    assert result["recommendation"] == "manual_review"
    assert len(result["flags"]) == 1
    assert "580" in result["flags"][0]


@pytest.mark.asyncio
async def test_triage_fha_high_dti(diego):
    """FHA loan exceeding max DTI should flag for review."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "FHA-003",
        "loan_type": "FHA",
        "credit_score": 700,
        "dti": 0.60,
    }))
    assert result["recommendation"] == "manual_review"
    assert any("DTI" in f for f in result["flags"])


@pytest.mark.asyncio
async def test_triage_va_loan(diego):
    """VA loan should apply VA-specific routing rules."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "VA-001",
        "loan_type": "VA",
        "credit_score": 650,
        "dti": 0.45,
    }))
    assert result["loan_type"] == "VA"
    assert result["recommendation"] == "proceed"


@pytest.mark.asyncio
async def test_triage_conventional_loan(diego):
    """Conventional loan with good profile should proceed."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "CONV-001",
        "loan_type": "CONV",
        "credit_score": 720,
        "dti": 0.38,
    }))
    assert result["loan_type"] == "CONV"
    assert result["recommendation"] == "proceed"


@pytest.mark.asyncio
async def test_triage_unknown_type_defaults_to_conventional(diego):
    """Unknown loan type should default to CONV rules."""
    result = await diego.execute(_make_task("triage_loan", {
        "loan_id": "UNK-001",
        "loan_type": "WEIRD",
        "credit_score": 720,
        "dti": 0.35,
    }))
    assert result["loan_type"] == "CONV"


@pytest.mark.asyncio
async def test_triage_stores_in_pipeline(diego):
    """Triaged loan should be stored in the internal pipeline."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "STORE-001",
        "loan_type": "FHA",
        "credit_score": 700,
        "dti": 0.35,
    }))
    assert "STORE-001" in diego._pipeline
    assert diego._pipeline["STORE-001"]["stage"] == "application"


# --- Pipeline Stage Advancement ---


@pytest.mark.asyncio
async def test_advance_stage_normal(diego):
    """Advancing should move to the next pipeline stage."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "ADV-001", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("advance_stage", {"loan_id": "ADV-001"}))
    assert result["previous_stage"] == "application"
    assert result["new_stage"] == "processing"


@pytest.mark.asyncio
async def test_advance_stage_full_progression(diego):
    """Loan should advance through all 8 stages."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "FULL-001", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    stages_seen = ["application"]
    for _ in range(7):  # 7 more stages to reach funded
        result = await diego.execute(_make_task("advance_stage", {"loan_id": "FULL-001"}))
        stages_seen.append(result["new_stage"])

    expected = [s.value for s in PipelineStage]
    assert stages_seen == expected


@pytest.mark.asyncio
async def test_advance_stage_already_at_final(diego):
    """Loan already at funded should not advance further."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "DONE-001", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    # Advance through all stages
    for _ in range(7):
        await diego.execute(_make_task("advance_stage", {"loan_id": "DONE-001"}))
    # Try to advance past funded
    result = await diego.execute(_make_task("advance_stage", {"loan_id": "DONE-001"}))
    assert result["stage"] == "funded"
    assert "final stage" in result["message"].lower()


@pytest.mark.asyncio
async def test_advance_stage_unknown_loan(diego):
    """Advancing nonexistent loan should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await diego.execute(_make_task("advance_stage", {"loan_id": "GHOST-001"}))


# --- Priority Assignment ---


@pytest.mark.asyncio
async def test_assign_priority_critical(diego):
    """Lock expiry <= 5 days should be critical priority."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "PRI-001", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("assign_priority", {
        "loan_id": "PRI-001", "lock_expiry_days": 3,
    }))
    assert result["priority"] == "critical"


@pytest.mark.asyncio
async def test_assign_priority_high(diego):
    """Lock expiry 6-10 days should be high priority."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "PRI-002", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("assign_priority", {
        "loan_id": "PRI-002", "lock_expiry_days": 8,
    }))
    assert result["priority"] == "high"


@pytest.mark.asyncio
async def test_assign_priority_medium(diego):
    """Lock expiry 11-20 days should be medium priority."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "PRI-003", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("assign_priority", {
        "loan_id": "PRI-003", "lock_expiry_days": 15,
    }))
    assert result["priority"] == "medium"


@pytest.mark.asyncio
async def test_assign_priority_low(diego):
    """Lock expiry > 20 days should be low priority."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "PRI-004", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("assign_priority", {
        "loan_id": "PRI-004", "lock_expiry_days": 25,
    }))
    assert result["priority"] == "low"


@pytest.mark.asyncio
async def test_assign_priority_investor_deadline_critical(diego):
    """Investor deadline <= 7 days should be critical regardless of lock."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "PRI-005", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    result = await diego.execute(_make_task("assign_priority", {
        "loan_id": "PRI-005", "lock_expiry_days": 30, "investor_deadline_days": 5,
    }))
    assert result["priority"] == "critical"


# --- Pipeline Health Check ---


@pytest.mark.asyncio
async def test_pipeline_health_empty(diego):
    """Empty pipeline should be healthy."""
    result = await diego.execute(_make_task("check_pipeline_health", {}))
    assert result["total_loans"] == 0
    assert result["health"] == "healthy"
    assert result["bottlenecks"] == []


@pytest.mark.asyncio
async def test_pipeline_health_bottleneck(diego):
    """Stage with >10 loans should be flagged as bottleneck."""
    for i in range(12):
        await diego.execute(_make_task("triage_loan", {
            "loan_id": f"BOTTLE-{i:03d}", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
        }))
    result = await diego.execute(_make_task("check_pipeline_health", {}))
    assert result["health"] == "attention_needed"
    assert len(result["bottlenecks"]) == 1
    assert result["bottlenecks"][0]["stage"] == "application"
    assert result["bottlenecks"][0]["count"] == 12


# --- Pipeline Report ---


@pytest.mark.asyncio
async def test_pipeline_report(diego):
    """Report should show stage and type distribution."""
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "RPT-001", "loan_type": "FHA", "credit_score": 700, "dti": 0.35,
    }))
    await diego.execute(_make_task("triage_loan", {
        "loan_id": "RPT-002", "loan_type": "VA", "credit_score": 650, "dti": 0.40,
    }))
    await diego.execute(_make_task("advance_stage", {"loan_id": "RPT-001"}))

    result = await diego.execute(_make_task("get_pipeline_report", {}))
    assert result["total_active_loans"] == 2
    assert "FHA" in result["by_type"]
    assert "VA" in result["by_type"]


# --- Unknown Action ---


@pytest.mark.asyncio
async def test_unknown_action_raises(diego):
    """Unknown action should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown DIEGO action"):
        await diego.execute(_make_task("nonexistent_action", {}))
