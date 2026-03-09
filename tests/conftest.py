"""Shared test fixtures for MortgageFintechOS."""

import pytest

from core.task_queue import Task, TaskPriority


@pytest.fixture
def sample_w2_payload() -> dict:
    """Standard W-2 borrower payload for NOVA income tests."""
    return {
        "current_w2_ytd": "45000",
        "months_worked_ytd": 6,
        "prior_year_w2": "85000",
    }


@pytest.fixture
def sample_schedule_c_payload() -> dict:
    """Self-employment payload for Schedule C tests."""
    return {
        "year1_net_profit": "72000",
        "year2_net_profit": "78000",
        "year1_depreciation": "5000",
        "year2_depreciation": "4500",
    }


@pytest.fixture
def sample_dti_payload() -> dict:
    """DTI calculation payload."""
    return {
        "monthly_income": "7500",
        "housing_expense": "2100",
        "total_monthly_obligations": "3200",
        "compensating_factors": [],
    }


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        priority=TaskPriority.MEDIUM,
        agent_name="NOVA",
        action="calculate_w2_income",
        payload={"current_w2_ytd": "45000", "months_worked_ytd": 6, "prior_year_w2": "85000"},
    )
