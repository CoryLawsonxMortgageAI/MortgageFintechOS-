"""NOVA — Income & DTI Analysis Agent.

Handles W-2 dual-method calculations, Schedule C analysis, DTI ratios,
compensating factors, and risk scoring per FHA HB 4000.1.
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import structlog

from agents.base import BaseAgent, AgentCategory
from core.task_queue import Task

logger = structlog.get_logger()

# FHA HB 4000.1 DTI limits with compensating factors
DTI_GRID = {
    "standard": {"front": Decimal("0.31"), "back": Decimal("0.43")},
    "energy_efficient": {"front": Decimal("0.33"), "back": Decimal("0.45")},
    "compensating_1": {"front": Decimal("0.37"), "back": Decimal("0.47")},
    "compensating_2": {"front": Decimal("0.40"), "back": Decimal("0.50")},
    "compensating_max": {"front": Decimal("0.40"), "back": Decimal("0.5695")},
}

COMPENSATING_FACTORS = [
    "verified_cash_reserves",
    "minimal_housing_payment_increase",
    "residual_income",
    "no_discretionary_debt",
    "significant_additional_income",
]


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


class NovaAgent(BaseAgent):
    """NOVA: Income & DTI — W-2 dual-method, Schedule C, risk scoring."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="NOVA", max_retries=max_retries, category=AgentCategory.MORTGAGE)

    async def execute(self, task: Task) -> dict[str, Any]:
        action = task.action
        payload = task.payload

        handlers = {
            "calculate_w2_income": self._calculate_w2_income,
            "analyze_schedule_c": self._analyze_schedule_c,
            "calculate_dti": self._calculate_dti,
            "evaluate_collections": self._evaluate_collections,
            "full_income_analysis": self._full_income_analysis,
            "recalculate_income": self._recalculate_income,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown NOVA action: {action}")

        return await handler(payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
        }

    async def _calculate_w2_income(self, payload: dict[str, Any]) -> dict[str, Any]:
        """W-2 dual-method per FHA HB 4000.1 II.A.5.b.

        Method 1: Current year W-2 YTD / months worked
        Method 2: Prior year W-2 / 12, averaged with Method 1
        Uses the LOWER of the two methods.
        """
        current_w2 = _to_decimal(payload["current_w2_ytd"])
        months_worked = Decimal(str(payload.get("months_worked_ytd", 12)))
        prior_w2 = _to_decimal(payload.get("prior_year_w2", 0))

        # Method 1: YTD annualized
        method_1_monthly = (current_w2 / months_worked).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Method 2: Average of current and prior year
        if prior_w2 > 0:
            prior_monthly = (prior_w2 / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            method_2_monthly = ((method_1_monthly + prior_monthly) / Decimal("2")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            method_2_monthly = method_1_monthly

        qualifying_income = min(method_1_monthly, method_2_monthly)

        income_trending = "stable"
        if prior_w2 > 0:
            current_annualized = current_w2 / months_worked * Decimal("12")
            change = (current_annualized - prior_w2) / prior_w2
            if change < Decimal("-0.10"):
                income_trending = "declining"
            elif change > Decimal("0.10"):
                income_trending = "increasing"

        return {
            "method_1_monthly": str(method_1_monthly),
            "method_2_monthly": str(method_2_monthly),
            "qualifying_monthly_income": str(qualifying_income),
            "income_trending": income_trending,
            "fha_citation": "FHA HB 4000.1 II.A.5.b — W-2 Dual-Method Income Calculation",
        }

    async def _analyze_schedule_c(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Schedule C self-employment income per FHA HB 4000.1 II.A.4.c.ii.

        Requires 2-year history. Net profit minus depreciation add-back,
        averaged over 24 months.
        """
        year1_net = _to_decimal(payload["year1_net_profit"])
        year2_net = _to_decimal(payload["year2_net_profit"])
        year1_depreciation = _to_decimal(payload.get("year1_depreciation", 0))
        year2_depreciation = _to_decimal(payload.get("year2_depreciation", 0))

        year1_adjusted = year1_net + year1_depreciation
        year2_adjusted = year2_net + year2_depreciation

        total_adjusted = year1_adjusted + year2_adjusted
        monthly_income = (total_adjusted / Decimal("24")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        trending = "stable"
        if year1_adjusted > 0:
            change = (year2_adjusted - year1_adjusted) / year1_adjusted
            if change < Decimal("-0.10"):
                trending = "declining"
                if change < Decimal("-0.25"):
                    trending = "significantly_declining"
            elif change > Decimal("0.10"):
                trending = "increasing"

        return {
            "year1_adjusted": str(year1_adjusted),
            "year2_adjusted": str(year2_adjusted),
            "monthly_income": str(monthly_income),
            "trending": trending,
            "usable": monthly_income > 0 and trending != "significantly_declining",
            "fha_citation": "FHA HB 4000.1 II.A.4.c.ii — Schedule C Self-Employment Income",
        }

    async def _calculate_dti(self, payload: dict[str, Any]) -> dict[str, Any]:
        """DTI calculation with compensating factors per FHA HB 4000.1 II.A.4.b."""
        monthly_income = _to_decimal(payload["monthly_income"])
        housing_expense = _to_decimal(payload["housing_expense"])
        total_obligations = _to_decimal(payload["total_monthly_obligations"])
        comp_factors = payload.get("compensating_factors", [])

        if monthly_income <= 0:
            raise ValueError("Monthly income must be positive")

        front_ratio = (housing_expense / monthly_income).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        back_ratio = (total_obligations / monthly_income).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Determine applicable DTI tier
        valid_factors = [f for f in comp_factors if f in COMPENSATING_FACTORS]
        if len(valid_factors) >= 2:
            tier = "compensating_max"
        elif len(valid_factors) == 1:
            tier = "compensating_1"
        else:
            tier = "standard"

        limits = DTI_GRID[tier]
        front_pass = front_ratio <= limits["front"]
        back_pass = back_ratio <= limits["back"]

        return {
            "front_ratio": str(front_ratio),
            "back_ratio": str(back_ratio),
            "front_limit": str(limits["front"]),
            "back_limit": str(limits["back"]),
            "front_pass": front_pass,
            "back_pass": back_pass,
            "overall_pass": front_pass and back_pass,
            "tier": tier,
            "compensating_factors_applied": valid_factors,
            "fha_citation": "FHA HB 4000.1 II.A.4.b — DTI Ratios & Compensating Factors",
        }

    async def _evaluate_collections(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Collections 5% rule per FHA HB 4000.1 II.A.4.d.v.

        If cumulative collection balance >= $2,000, 5% of outstanding
        balance must be included in monthly obligations for DTI.
        """
        collection_accounts = payload.get("collection_accounts", [])
        total_balance = sum(_to_decimal(a.get("balance", 0)) for a in collection_accounts)
        threshold = Decimal("2000")

        if total_balance >= threshold:
            monthly_obligation = (total_balance * Decimal("0.05")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            include_in_dti = True
        else:
            monthly_obligation = Decimal("0")
            include_in_dti = False

        return {
            "total_collection_balance": str(total_balance),
            "threshold": str(threshold),
            "exceeds_threshold": total_balance >= threshold,
            "monthly_obligation": str(monthly_obligation),
            "include_in_dti": include_in_dti,
            "account_count": len(collection_accounts),
            "fha_citation": "FHA HB 4000.1 II.A.4.d.v — Collections 5% Rule",
        }

    async def _full_income_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run complete income analysis combining W-2, Schedule C, collections, and DTI."""
        results: dict[str, Any] = {"loan_id": payload.get("loan_id", ""), "analyses": {}}

        if "current_w2_ytd" in payload:
            results["analyses"]["w2"] = await self._calculate_w2_income(payload)

        if "year1_net_profit" in payload:
            results["analyses"]["schedule_c"] = await self._analyze_schedule_c(payload)

        if "collection_accounts" in payload:
            results["analyses"]["collections"] = await self._evaluate_collections(payload)

        if "monthly_income" in payload:
            results["analyses"]["dti"] = await self._calculate_dti(payload)

        risk_flags = []
        for analysis in results["analyses"].values():
            if isinstance(analysis, dict):
                if analysis.get("income_trending") == "declining":
                    risk_flags.append("Declining income trend")
                if analysis.get("trending") == "significantly_declining":
                    risk_flags.append("Significantly declining self-employment income")
                if analysis.get("overall_pass") is False:
                    risk_flags.append("DTI exceeds limits")

        results["risk_flags"] = risk_flags
        results["risk_level"] = "high" if len(risk_flags) >= 2 else "medium" if risk_flags else "low"

        return results

    async def _recalculate_income(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Scheduled recalculation — wrapper for full_income_analysis."""
        logger.info("income_recalculation_triggered")
        return await self._full_income_analysis(payload)
