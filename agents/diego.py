"""DIEGO — Pipeline Orchestration Agent.

Handles loan triage, workflow management, pipeline stage tracking,
and priority assignment for the MortgageFintechOS system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from agents.base import BaseAgent
from core.task_queue import Task

logger = structlog.get_logger()


class LoanType(str, Enum):
    FHA = "FHA"
    VA = "VA"
    CONVENTIONAL = "CONV"
    USDA = "USDA"
    JUMBO = "JUMBO"


class PipelineStage(str, Enum):
    APPLICATION = "application"
    PROCESSING = "processing"
    UNDERWRITING = "underwriting"
    CONDITIONAL_APPROVAL = "conditional_approval"
    CLEAR_TO_CLOSE = "clear_to_close"
    CLOSING = "closing"
    FUNDING = "funding"
    FUNDED = "funded"


STAGE_ORDER = list(PipelineStage)

ROUTING_RULES = {
    LoanType.FHA: {
        "required_docs": ["w2", "paystubs", "bank_statements", "tax_returns", "fha_case_number"],
        "min_credit_score": 580,
        "max_dti": 0.5695,
    },
    LoanType.VA: {
        "required_docs": ["w2", "paystubs", "bank_statements", "dd214", "coe"],
        "min_credit_score": 620,
        "max_dti": 0.60,
    },
    LoanType.CONVENTIONAL: {
        "required_docs": ["w2", "paystubs", "bank_statements", "tax_returns"],
        "min_credit_score": 620,
        "max_dti": 0.50,
    },
    LoanType.USDA: {
        "required_docs": ["w2", "paystubs", "bank_statements", "tax_returns", "usda_eligibility"],
        "min_credit_score": 640,
        "max_dti": 0.46,
    },
}


class DiegoAgent(BaseAgent):
    """DIEGO: Pipeline orchestration — loan triage, workflow management."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="DIEGO", max_retries=max_retries)
        self._pipeline: dict[str, dict[str, Any]] = {}

    async def execute(self, task: Task) -> dict[str, Any]:
        action = task.action
        payload = task.payload

        handlers = {
            "triage_loan": self._triage_loan,
            "advance_stage": self._advance_stage,
            "check_pipeline_health": self._check_pipeline_health,
            "get_pipeline_report": self._get_pipeline_report,
            "assign_priority": self._assign_priority,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown DIEGO action: {action}")

        return await handler(payload)

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": self.status.value,
            "active_loans": len(self._pipeline),
            "stages": self._stage_counts(),
        }

    async def _triage_loan(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        loan_type_str = payload.get("loan_type", "CONV").upper()
        loan_type = LoanType(loan_type_str) if loan_type_str in LoanType.__members__ else LoanType.CONVENTIONAL

        rules = ROUTING_RULES[loan_type]
        credit_score = payload.get("credit_score", 0)
        dti = payload.get("dti", 0.0)

        flags = []
        if credit_score < rules["min_credit_score"]:
            flags.append(f"Credit score {credit_score} below minimum {rules['min_credit_score']}")
        if dti > rules["max_dti"]:
            flags.append(f"DTI {dti:.2%} exceeds maximum {rules['max_dti']:.2%}")

        self._pipeline[loan_id] = {
            "loan_id": loan_id,
            "loan_type": loan_type.value,
            "stage": PipelineStage.APPLICATION.value,
            "priority": "high" if not flags else "review",
            "flags": flags,
            "required_docs": rules["required_docs"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info("loan_triaged", loan_id=loan_id, loan_type=loan_type.value, flags=len(flags))
        return {
            "loan_id": loan_id,
            "loan_type": loan_type.value,
            "stage": PipelineStage.APPLICATION.value,
            "flags": flags,
            "recommendation": "proceed" if not flags else "manual_review",
        }

    async def _advance_stage(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        loan = self._pipeline.get(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} not found in pipeline")

        current = PipelineStage(loan["stage"])
        current_idx = STAGE_ORDER.index(current)

        if current_idx >= len(STAGE_ORDER) - 1:
            return {"loan_id": loan_id, "stage": current.value, "message": "Already at final stage"}

        next_stage = STAGE_ORDER[current_idx + 1]
        loan["stage"] = next_stage.value
        logger.info("stage_advanced", loan_id=loan_id, from_stage=current.value, to_stage=next_stage.value)

        return {"loan_id": loan_id, "previous_stage": current.value, "new_stage": next_stage.value}

    async def _assign_priority(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        loan = self._pipeline.get(loan_id)
        if not loan:
            raise ValueError(f"Loan {loan_id} not found in pipeline")

        lock_expiry = payload.get("lock_expiry_days", 30)
        investor_deadline = payload.get("investor_deadline_days", 45)

        if lock_expiry <= 5 or investor_deadline <= 7:
            priority = "critical"
        elif lock_expiry <= 10 or investor_deadline <= 14:
            priority = "high"
        elif lock_expiry <= 20:
            priority = "medium"
        else:
            priority = "low"

        loan["priority"] = priority
        return {"loan_id": loan_id, "priority": priority, "lock_expiry_days": lock_expiry}

    async def _check_pipeline_health(self, _payload: dict[str, Any]) -> dict[str, Any]:
        counts = self._stage_counts()
        bottlenecks = []
        for stage, count in counts.items():
            if count > 10:
                bottlenecks.append({"stage": stage, "count": count, "severity": "warning"})

        return {
            "total_loans": len(self._pipeline),
            "stage_distribution": counts,
            "bottlenecks": bottlenecks,
            "health": "healthy" if not bottlenecks else "attention_needed",
        }

    async def _get_pipeline_report(self, _payload: dict[str, Any]) -> dict[str, Any]:
        counts = self._stage_counts()
        type_counts: dict[str, int] = {}
        for loan in self._pipeline.values():
            lt = loan["loan_type"]
            type_counts[lt] = type_counts.get(lt, 0) + 1

        return {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "total_active_loans": len(self._pipeline),
            "by_stage": counts,
            "by_type": type_counts,
        }

    def _stage_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for loan in self._pipeline.values():
            stage = loan["stage"]
            counts[stage] = counts.get(stage, 0) + 1
        return counts
