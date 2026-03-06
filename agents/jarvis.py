"""JARVIS — Condition Resolution Agent.

Handles LOE drafting, condition-to-document mapping, compliance citation
lookup, and condition clearing workflows for MortgageFintechOS.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from agents.base import BaseAgent
from core.task_queue import Task

logger = structlog.get_logger()


class ConditionType(str, Enum):
    PRIOR_TO_DOC = "prior_to_doc"
    PRIOR_TO_FUNDING = "prior_to_funding"
    PRIOR_TO_CLOSING = "prior_to_closing"
    POST_CLOSING = "post_closing"


class ConditionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    CLEARED = "cleared"
    WAIVED = "waived"


COMPLIANCE_CITATIONS = {
    "income_verification": {
        "FHA": "FHA HB 4000.1 II.A.5 — Income Requirements",
        "FNMA": "FNMA Selling Guide B3-3.1 — Employment & Income",
        "FHLMC": "FHLMC Guide 5301.1 — Income Assessment",
    },
    "asset_verification": {
        "FHA": "FHA HB 4000.1 II.A.4.d — Assets",
        "FNMA": "FNMA Selling Guide B3-4.1 — Asset Documentation",
        "FHLMC": "FHLMC Guide 5401.1 — Asset Requirements",
    },
    "credit_verification": {
        "FHA": "FHA HB 4000.1 II.A.4.c — Credit Requirements",
        "FNMA": "FNMA Selling Guide B3-5 — Credit Assessment",
        "FHLMC": "FHLMC Guide 5201.1 — Credit Evaluation",
    },
    "employment_verification": {
        "FHA": "FHA HB 4000.1 II.A.5.a — Employment Verification",
        "FNMA": "FNMA Selling Guide B3-3.1 — Employment Verification",
        "FHLMC": "FHLMC Guide 5301.2 — Employment Verification",
    },
    "appraisal": {
        "FHA": "FHA HB 4000.1 II.D — FHA Appraisal Requirements",
        "FNMA": "FNMA Selling Guide B4-1 — Property Assessment",
        "FHLMC": "FHLMC Guide 5601 — Appraisal Requirements",
    },
    "flood_insurance": {
        "FHA": "FHA HB 4000.1 II.A.1.b — Flood Insurance",
        "FNMA": "FNMA Selling Guide B7-3 — Flood Insurance",
        "FHLMC": "FHLMC Guide 5703 — Flood Insurance",
    },
    "title": {
        "FHA": "FHA HB 4000.1 II.A.1 — Title Requirements",
        "FNMA": "FNMA Selling Guide B7-2 — Title Insurance",
        "FHLMC": "FHLMC Guide 5701 — Title Requirements",
    },
    "gift_funds": {
        "FHA": "FHA HB 4000.1 II.A.4.d.iii — Gift Funds",
        "FNMA": "FNMA Selling Guide B3-4.3 — Gift Funds",
        "FHLMC": "FHLMC Guide 5405 — Gift Fund Documentation",
    },
}

CONDITION_TO_DOCUMENT_MAP = {
    "verify_income": ["w2", "paystubs", "tax_returns"],
    "verify_assets": ["bank_statements"],
    "verify_employment": ["voe", "paystubs"],
    "gift_letter": ["gift_letter", "donor_bank_statement"],
    "explain_gap": ["letter_of_explanation"],
    "explain_deposit": ["letter_of_explanation", "bank_statements"],
    "explain_credit": ["letter_of_explanation"],
    "appraisal_update": ["appraisal"],
    "flood_cert": ["flood_certificate"],
    "title_update": ["title_commitment"],
    "insurance": ["homeowners_insurance"],
}

LOE_TEMPLATES = {
    "employment_gap": (
        "To Whom It May Concern,\n\n"
        "I, {borrower_name}, am writing to explain the gap in my employment "
        "from {gap_start} to {gap_end}. {reason}\n\n"
        "I have since resumed stable employment as of {resume_date} with {employer}.\n\n"
        "Sincerely,\n{borrower_name}"
    ),
    "large_deposit": (
        "To Whom It May Concern,\n\n"
        "I, {borrower_name}, am writing to explain the deposit of ${amount} "
        "into my {account_type} account on {deposit_date}. {reason}\n\n"
        "This deposit is not a loan and does not require repayment.\n\n"
        "Sincerely,\n{borrower_name}"
    ),
    "credit_inquiry": (
        "To Whom It May Concern,\n\n"
        "I, {borrower_name}, am writing to explain the credit inquiry from "
        "{creditor} on {inquiry_date}. {reason}\n\n"
        "No new credit was obtained as a result of this inquiry.\n\n"
        "Sincerely,\n{borrower_name}"
    ),
    "address_discrepancy": (
        "To Whom It May Concern,\n\n"
        "I, {borrower_name}, am writing to explain the address discrepancy "
        "between {address_1} and {address_2}. {reason}\n\n"
        "My current address is {current_address}.\n\n"
        "Sincerely,\n{borrower_name}"
    ),
    "general": (
        "To Whom It May Concern,\n\n"
        "I, {borrower_name}, am writing to explain the following: {explanation}\n\n"
        "Sincerely,\n{borrower_name}"
    ),
}


class JarvisAgent(BaseAgent):
    """JARVIS: Condition resolution — LOE drafting, compliance citations."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="JARVIS", max_retries=max_retries)
        self._conditions: dict[str, list[dict[str, Any]]] = {}

    async def execute(self, task: Task) -> dict[str, Any]:
        action = task.action
        payload = task.payload

        handlers = {
            "draft_loe": self._draft_loe,
            "map_conditions": self._map_conditions,
            "lookup_citation": self._lookup_citation,
            "add_condition": self._add_condition,
            "clear_condition": self._clear_condition,
            "get_condition_status": self._get_condition_status,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown JARVIS action: {action}")

        return await handler(payload)

    async def health_check(self) -> dict[str, Any]:
        total = sum(len(c) for c in self._conditions.values())
        open_count = sum(
            1 for conds in self._conditions.values()
            for c in conds if c["status"] in (ConditionStatus.OPEN.value, ConditionStatus.IN_PROGRESS.value)
        )
        return {
            "agent": self.name,
            "status": self.status.value,
            "total_conditions": total,
            "open_conditions": open_count,
        }

    def _get_state(self) -> dict[str, Any]:
        return {"conditions": self._conditions}

    def _restore_state(self, data: dict[str, Any]) -> None:
        self._conditions = data.get("conditions", {})

    async def _draft_loe(self, payload: dict[str, Any]) -> dict[str, Any]:
        loe_type = payload.get("loe_type", "general")
        template = LOE_TEMPLATES.get(loe_type, LOE_TEMPLATES["general"])

        try:
            letter = template.format(**payload)
        except KeyError as e:
            missing = str(e).strip("'")
            return {
                "error": f"Missing required field: {missing}",
                "required_fields": [
                    k for k in template.split("{") if "}" in k
                ],
                "loe_type": loe_type,
            }

        logger.info("loe_drafted", loe_type=loe_type)
        return {
            "loe_type": loe_type,
            "letter": letter,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _map_conditions(self, payload: dict[str, Any]) -> dict[str, Any]:
        conditions = payload.get("conditions", [])
        mappings = []

        for condition in conditions:
            condition_type = condition.get("type", "")
            required_docs = CONDITION_TO_DOCUMENT_MAP.get(condition_type, [])
            mappings.append({
                "condition": condition_type,
                "description": condition.get("description", ""),
                "required_documents": required_docs,
            })

        return {"mappings": mappings, "total_documents_needed": sum(len(m["required_documents"]) for m in mappings)}

    async def _lookup_citation(self, payload: dict[str, Any]) -> dict[str, Any]:
        category = payload.get("category", "")
        investor = payload.get("investor", "FHA")

        citations = COMPLIANCE_CITATIONS.get(category, {})
        if investor in citations:
            return {"category": category, "investor": investor, "citation": citations[investor]}

        return {
            "category": category,
            "investor": investor,
            "citation": None,
            "available_categories": list(COMPLIANCE_CITATIONS.keys()),
        }

    async def _add_condition(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        condition = {
            "id": f"COND-{len(self._conditions.get(loan_id, [])) + 1:03d}",
            "type": payload.get("condition_type", ""),
            "description": payload.get("description", ""),
            "category": ConditionType(payload.get("category", "prior_to_doc")).value,
            "status": ConditionStatus.OPEN.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "required_docs": CONDITION_TO_DOCUMENT_MAP.get(payload.get("condition_type", ""), []),
        }

        self._conditions.setdefault(loan_id, []).append(condition)
        await self.save_state()
        logger.info("condition_added", loan_id=loan_id, condition_id=condition["id"])
        return condition

    async def _clear_condition(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        condition_id = payload["condition_id"]

        conditions = self._conditions.get(loan_id, [])
        for condition in conditions:
            if condition["id"] == condition_id:
                condition["status"] = ConditionStatus.CLEARED.value
                condition["cleared_at"] = datetime.now(timezone.utc).isoformat()
                condition["cleared_by"] = payload.get("cleared_by", "JARVIS")
                await self.save_state()
                logger.info("condition_cleared", loan_id=loan_id, condition_id=condition_id)
                return condition

        raise ValueError(f"Condition {condition_id} not found for loan {loan_id}")

    async def _get_condition_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        conditions = self._conditions.get(loan_id, [])

        summary = {"open": 0, "in_progress": 0, "submitted": 0, "cleared": 0, "waived": 0}
        for c in conditions:
            summary[c["status"]] = summary.get(c["status"], 0) + 1

        return {
            "loan_id": loan_id,
            "total_conditions": len(conditions),
            "summary": summary,
            "conditions": conditions,
            "all_cleared": all(
                c["status"] in (ConditionStatus.CLEARED.value, ConditionStatus.WAIVED.value)
                for c in conditions
            ) if conditions else False,
        }
