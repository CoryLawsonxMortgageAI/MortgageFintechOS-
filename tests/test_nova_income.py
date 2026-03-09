"""Tests for NOVA agent income calculations.

Covers W-2 dual-method (FHA HB 4000.1 II.A.5.b), Schedule C (II.A.4.c.ii),
DTI with compensating factors (II.A.4.b), and Collections 5% rule (II.A.4.d.v).
"""

import pytest
from decimal import Decimal

from agents.nova import NovaAgent
from core.task_queue import Task, TaskPriority


@pytest.fixture
def nova() -> NovaAgent:
    return NovaAgent()


def _make_task(action: str, payload: dict) -> Task:
    return Task(priority=TaskPriority.MEDIUM, agent_name="NOVA", action=action, payload=payload)


# --- W-2 Dual-Method Income (FHA HB 4000.1 II.A.5.b) ---


@pytest.mark.asyncio
async def test_w2_dual_method_uses_lower(nova, sample_w2_payload):
    """W-2 calculation should use the LOWER of Method 1 and Method 2."""
    result = await nova.execute(_make_task("calculate_w2_income", sample_w2_payload))

    method_1 = Decimal(result["method_1_monthly"])
    method_2 = Decimal(result["method_2_monthly"])
    qualifying = Decimal(result["qualifying_monthly_income"])

    assert qualifying == min(method_1, method_2)
    assert "FHA HB 4000.1 II.A.5.b" in result["fha_citation"]


@pytest.mark.asyncio
async def test_w2_method_1_annualizes_ytd(nova):
    """Method 1: YTD / months worked."""
    result = await nova.execute(_make_task("calculate_w2_income", {
        "current_w2_ytd": "60000",
        "months_worked_ytd": 6,
        "prior_year_w2": "0",
    }))
    # $60k / 6 months = $10,000/month
    assert result["method_1_monthly"] == "10000.00"


@pytest.mark.asyncio
async def test_w2_no_prior_year_uses_method_1(nova):
    """Without prior year W-2, qualifying income should equal Method 1."""
    result = await nova.execute(_make_task("calculate_w2_income", {
        "current_w2_ytd": "48000",
        "months_worked_ytd": 6,
    }))
    assert result["qualifying_monthly_income"] == result["method_1_monthly"]


@pytest.mark.asyncio
async def test_w2_declining_income_flagged(nova):
    """Income declining >10% should be flagged."""
    result = await nova.execute(_make_task("calculate_w2_income", {
        "current_w2_ytd": "30000",
        "months_worked_ytd": 6,
        "prior_year_w2": "100000",
    }))
    assert result["income_trending"] == "declining"


@pytest.mark.asyncio
async def test_w2_increasing_income_flagged(nova):
    """Income increasing >10% should be flagged."""
    result = await nova.execute(_make_task("calculate_w2_income", {
        "current_w2_ytd": "60000",
        "months_worked_ytd": 6,
        "prior_year_w2": "80000",
    }))
    assert result["income_trending"] == "increasing"


# --- Schedule C Self-Employment (FHA HB 4000.1 II.A.4.c.ii) ---


@pytest.mark.asyncio
async def test_schedule_c_two_year_average(nova, sample_schedule_c_payload):
    """Schedule C uses 2-year average with depreciation add-back."""
    result = await nova.execute(_make_task("analyze_schedule_c", sample_schedule_c_payload))

    # Year 1: 72000 + 5000 = 77000, Year 2: 78000 + 4500 = 82500
    # Total: 159500 / 24 = 6645.83
    assert result["year1_adjusted"] == "77000"
    assert result["year2_adjusted"] == "82500"
    assert result["monthly_income"] == "6645.83"
    assert result["usable"] is True
    assert "FHA HB 4000.1 II.A.4.c.ii" in result["fha_citation"]


@pytest.mark.asyncio
async def test_schedule_c_declining_over_25_pct_unusable(nova):
    """Significantly declining SE income (>25%) should be flagged unusable."""
    result = await nova.execute(_make_task("analyze_schedule_c", {
        "year1_net_profit": "100000",
        "year2_net_profit": "60000",
        "year1_depreciation": "0",
        "year2_depreciation": "0",
    }))
    assert result["trending"] == "significantly_declining"
    assert result["usable"] is False


# --- DTI Ratios (FHA HB 4000.1 II.A.4.b) ---


@pytest.mark.asyncio
async def test_dti_standard_pass(nova, sample_dti_payload):
    """Standard DTI should pass when within 31/43 limits."""
    sample_dti_payload["monthly_income"] = "10000"
    sample_dti_payload["housing_expense"] = "2500"
    sample_dti_payload["total_monthly_obligations"] = "4000"

    result = await nova.execute(_make_task("calculate_dti", sample_dti_payload))
    assert result["tier"] == "standard"
    assert result["front_pass"] is True
    assert result["back_pass"] is True
    assert result["overall_pass"] is True


@pytest.mark.asyncio
async def test_dti_standard_fail(nova):
    """Standard DTI should fail when back ratio exceeds 43%."""
    result = await nova.execute(_make_task("calculate_dti", {
        "monthly_income": "7000",
        "housing_expense": "2500",
        "total_monthly_obligations": "3500",
    }))
    assert result["overall_pass"] is False


@pytest.mark.asyncio
async def test_dti_compensating_factors_raise_limit(nova):
    """Two compensating factors should allow up to 40/56.95 DTI."""
    result = await nova.execute(_make_task("calculate_dti", {
        "monthly_income": "10000",
        "housing_expense": "3800",
        "total_monthly_obligations": "5500",
        "compensating_factors": ["verified_cash_reserves", "residual_income"],
    }))
    assert result["tier"] == "compensating_max"
    assert result["back_limit"] == "0.5695"
    assert result["overall_pass"] is True


@pytest.mark.asyncio
async def test_dti_zero_income_raises(nova):
    """Zero monthly income should raise ValueError."""
    with pytest.raises(ValueError, match="positive"):
        await nova.execute(_make_task("calculate_dti", {
            "monthly_income": "0",
            "housing_expense": "2000",
            "total_monthly_obligations": "3000",
        }))


# --- Collections 5% Rule (FHA HB 4000.1 II.A.4.d.v) ---


@pytest.mark.asyncio
async def test_collections_above_threshold(nova):
    """Collections >= $2,000 should require 5% monthly obligation."""
    result = await nova.execute(_make_task("evaluate_collections", {
        "collection_accounts": [
            {"balance": "1500"},
            {"balance": "800"},
        ]
    }))
    assert result["exceeds_threshold"] is True
    assert result["monthly_obligation"] == "115.00"  # 2300 * 0.05
    assert result["include_in_dti"] is True


@pytest.mark.asyncio
async def test_collections_below_threshold(nova):
    """Collections < $2,000 should not be included in DTI."""
    result = await nova.execute(_make_task("evaluate_collections", {
        "collection_accounts": [
            {"balance": "500"},
            {"balance": "400"},
        ]
    }))
    assert result["exceeds_threshold"] is False
    assert result["monthly_obligation"] == "0"
    assert result["include_in_dti"] is False
