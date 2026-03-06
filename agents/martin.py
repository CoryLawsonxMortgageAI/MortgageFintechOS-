"""MARTIN — Document Intelligence Agent.

Handles document classification, OCR validation, fraud detection,
and completeness auditing for the MortgageFintechOS system.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from agents.base import BaseAgent
from core.task_queue import Task

logger = structlog.get_logger()


class DocumentType(str, Enum):
    W2 = "w2"
    PAYSTUB = "paystub"
    BANK_STATEMENT = "bank_statement"
    TAX_RETURN = "tax_return"
    DRIVERS_LICENSE = "drivers_license"
    SOCIAL_SECURITY = "social_security_card"
    GIFT_LETTER = "gift_letter"
    LOE = "letter_of_explanation"
    APPRAISAL = "appraisal"
    TITLE_REPORT = "title_report"
    HOMEOWNERS_INSURANCE = "homeowners_insurance"
    UNKNOWN = "unknown"


DOCUMENT_SIGNATURES = {
    "w-2": DocumentType.W2,
    "wage and tax statement": DocumentType.W2,
    "paystub": DocumentType.PAYSTUB,
    "pay stub": DocumentType.PAYSTUB,
    "earnings statement": DocumentType.PAYSTUB,
    "bank statement": DocumentType.BANK_STATEMENT,
    "account statement": DocumentType.BANK_STATEMENT,
    "1040": DocumentType.TAX_RETURN,
    "tax return": DocumentType.TAX_RETURN,
    "driver": DocumentType.DRIVERS_LICENSE,
    "gift letter": DocumentType.GIFT_LETTER,
    "appraisal": DocumentType.APPRAISAL,
    "title": DocumentType.TITLE_REPORT,
    "insurance": DocumentType.HOMEOWNERS_INSURANCE,
}

LOAN_REQUIRED_DOCS = {
    "FHA": [DocumentType.W2, DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.TAX_RETURN],
    "VA": [DocumentType.W2, DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT],
    "CONV": [DocumentType.W2, DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.TAX_RETURN],
    "USDA": [DocumentType.W2, DocumentType.PAYSTUB, DocumentType.BANK_STATEMENT, DocumentType.TAX_RETURN],
}


class MartinAgent(BaseAgent):
    """MARTIN: Document intelligence — OCR, classification, fraud detection."""

    def __init__(self, max_retries: int = 3):
        super().__init__(name="MARTIN", max_retries=max_retries)
        self._document_store: dict[str, list[dict[str, Any]]] = {}

    async def execute(self, task: Task) -> dict[str, Any]:
        action = task.action
        payload = task.payload

        handlers = {
            "classify_document": self._classify_document,
            "validate_ocr": self._validate_ocr,
            "detect_fraud": self._detect_fraud,
            "audit_completeness": self._audit_completeness,
            "run_document_audit": self._run_document_audit,
        }

        handler = handlers.get(action)
        if not handler:
            raise ValueError(f"Unknown MARTIN action: {action}")

        return await handler(payload)

    async def health_check(self) -> dict[str, Any]:
        total_docs = sum(len(docs) for docs in self._document_store.values())
        return {
            "agent": self.name,
            "status": self.status.value,
            "loans_tracked": len(self._document_store),
            "total_documents": total_docs,
        }

    async def _classify_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        text_content = payload.get("text_content", "").lower()
        filename = payload.get("filename", "").lower()

        detected_type = DocumentType.UNKNOWN
        confidence = 0.0

        for keyword, doc_type in DOCUMENT_SIGNATURES.items():
            if keyword in text_content or keyword in filename:
                detected_type = doc_type
                confidence = 0.92 if keyword in text_content else 0.75
                break

        loan_id = payload.get("loan_id", "")
        if loan_id:
            self._document_store.setdefault(loan_id, []).append({
                "type": detected_type.value,
                "filename": payload.get("filename", ""),
                "confidence": confidence,
                "classified_at": datetime.now(timezone.utc).isoformat(),
            })

        logger.info("document_classified", type=detected_type.value, confidence=confidence)
        return {
            "document_type": detected_type.value,
            "confidence": confidence,
            "needs_manual_review": confidence < 0.80,
        }

    async def _validate_ocr(self, payload: dict[str, Any]) -> dict[str, Any]:
        extracted_data = payload.get("extracted_data", {})
        issues = []

        if "income" in extracted_data:
            income = extracted_data["income"]
            if isinstance(income, (int, float)) and (income < 0 or income > 10_000_000):
                issues.append({"field": "income", "issue": "Value out of expected range"})

        if "ssn" in extracted_data:
            ssn = str(extracted_data["ssn"]).replace("-", "")
            if len(ssn) != 9 or not ssn.isdigit():
                issues.append({"field": "ssn", "issue": "Invalid SSN format"})

        if "date" in extracted_data:
            try:
                datetime.strptime(str(extracted_data["date"]), "%Y-%m-%d")
            except ValueError:
                issues.append({"field": "date", "issue": "Invalid date format"})

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "fields_checked": len(extracted_data),
        }

    async def _detect_fraud(self, payload: dict[str, Any]) -> dict[str, Any]:
        signals = []
        risk_score = 0.0

        metadata = payload.get("metadata", {})
        if metadata.get("font_count", 1) > 3:
            signals.append({"type": "font_inconsistency", "severity": "high", "detail": "Multiple fonts detected"})
            risk_score += 0.3

        if metadata.get("has_layers", False):
            signals.append({"type": "document_layers", "severity": "high", "detail": "Hidden layers found in PDF"})
            risk_score += 0.35

        if metadata.get("creation_date") and metadata.get("modification_date"):
            if metadata["creation_date"] != metadata["modification_date"]:
                signals.append({"type": "date_mismatch", "severity": "medium", "detail": "Document modified after creation"})
                risk_score += 0.15

        if metadata.get("resolution_dpi", 300) < 150:
            signals.append({"type": "low_resolution", "severity": "low", "detail": "Unusually low scan resolution"})
            risk_score += 0.1

        risk_score = min(risk_score, 1.0)

        logger.info("fraud_check_complete", signals=len(signals), risk_score=risk_score)
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": "high" if risk_score > 0.5 else "medium" if risk_score > 0.25 else "low",
            "signals": signals,
            "recommendation": "flag_for_review" if risk_score > 0.3 else "pass",
        }

    async def _audit_completeness(self, payload: dict[str, Any]) -> dict[str, Any]:
        loan_id = payload["loan_id"]
        loan_type = payload.get("loan_type", "CONV")

        required = LOAN_REQUIRED_DOCS.get(loan_type, LOAN_REQUIRED_DOCS["CONV"])
        on_file = self._document_store.get(loan_id, [])
        on_file_types = {doc["type"] for doc in on_file}

        missing = [doc.value for doc in required if doc.value not in on_file_types]

        return {
            "loan_id": loan_id,
            "loan_type": loan_type,
            "required": len(required),
            "received": len(on_file_types & {d.value for d in required}),
            "missing": missing,
            "complete": len(missing) == 0,
        }

    async def _run_document_audit(self, _payload: dict[str, Any]) -> dict[str, Any]:
        results = []
        for loan_id in list(self._document_store.keys()):
            audit = await self._audit_completeness({"loan_id": loan_id})
            if not audit["complete"]:
                results.append(audit)

        logger.info("document_audit_complete", loans_checked=len(self._document_store), incomplete=len(results))
        return {
            "audit_date": datetime.now(timezone.utc).isoformat(),
            "loans_audited": len(self._document_store),
            "incomplete_loans": results,
        }
