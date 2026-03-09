"""Tests for MARTIN agent document intelligence.

Covers document classification, OCR validation, fraud detection,
and completeness auditing for the MortgageFintechOS system.
"""

from typing import Any

import pytest

from agents.martin import MartinAgent
from core.task_queue import Task, TaskPriority


@pytest.fixture
def martin() -> MartinAgent:
    return MartinAgent()


def _make_task(action: str, payload: dict[str, Any]) -> Task:
    return Task(priority=TaskPriority.MEDIUM, agent_name="MARTIN", action=action, payload=payload)


# --- Document Classification ---


@pytest.mark.asyncio
async def test_classify_w2_by_text(martin):
    """W-2 keyword in text content should classify as W2 with high confidence."""
    result = await martin.execute(_make_task("classify_document", {
        "text_content": "W-2 Wage and Tax Statement 2025",
        "filename": "document.pdf",
    }))
    assert result["document_type"] == "w2"
    assert result["confidence"] == 0.92
    assert result["needs_manual_review"] is False


@pytest.mark.asyncio
async def test_classify_paystub_by_filename(martin):
    """Paystub keyword in filename should classify with lower confidence."""
    result = await martin.execute(_make_task("classify_document", {
        "text_content": "",
        "filename": "paystub_jan_2025.pdf",
    }))
    assert result["document_type"] == "paystub"
    assert result["confidence"] == 0.75
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_classify_bank_statement(martin):
    """Bank statement keyword should be detected."""
    result = await martin.execute(_make_task("classify_document", {
        "text_content": "Bank Statement - Account Summary",
    }))
    assert result["document_type"] == "bank_statement"
    assert result["confidence"] == 0.92


@pytest.mark.asyncio
async def test_classify_unknown_document(martin):
    """Unrecognizable document should be classified as unknown."""
    result = await martin.execute(_make_task("classify_document", {
        "text_content": "random content here",
        "filename": "misc.pdf",
    }))
    assert result["document_type"] == "unknown"
    assert result["confidence"] == 0.0
    assert result["needs_manual_review"] is True


@pytest.mark.asyncio
async def test_classify_stores_to_loan(martin):
    """Classification with loan_id should store the document."""
    await martin.execute(_make_task("classify_document", {
        "text_content": "W-2 Wage and Tax Statement",
        "filename": "w2.pdf",
        "loan_id": "LOAN-001",
    }))
    assert "LOAN-001" in martin._document_store
    assert len(martin._document_store["LOAN-001"]) == 1
    assert martin._document_store["LOAN-001"][0]["type"] == "w2"


# --- OCR Validation ---


@pytest.mark.asyncio
async def test_validate_ocr_clean_data(martin):
    """Valid extracted data should pass validation."""
    result = await martin.execute(_make_task("validate_ocr", {
        "extracted_data": {
            "income": 75000,
            "ssn": "123-45-6789",
            "date": "2025-01-15",
        }
    }))
    assert result["valid"] is True
    assert result["issues"] == []
    assert result["fields_checked"] == 3


@pytest.mark.asyncio
async def test_validate_ocr_invalid_ssn(martin):
    """Invalid SSN should be flagged."""
    result = await martin.execute(_make_task("validate_ocr", {
        "extracted_data": {"ssn": "12345"}
    }))
    assert result["valid"] is False
    assert any(i["field"] == "ssn" for i in result["issues"])


@pytest.mark.asyncio
async def test_validate_ocr_invalid_date(martin):
    """Malformed date should be flagged."""
    result = await martin.execute(_make_task("validate_ocr", {
        "extracted_data": {"date": "not-a-date"}
    }))
    assert result["valid"] is False
    assert any(i["field"] == "date" for i in result["issues"])


@pytest.mark.asyncio
async def test_validate_ocr_out_of_range_income(martin):
    """Negative or extreme income should be flagged."""
    result = await martin.execute(_make_task("validate_ocr", {
        "extracted_data": {"income": -5000}
    }))
    assert result["valid"] is False
    assert any(i["field"] == "income" for i in result["issues"])


# --- Fraud Detection ---


@pytest.mark.asyncio
async def test_fraud_no_signals(martin):
    """Clean document metadata should produce low risk."""
    result = await martin.execute(_make_task("detect_fraud", {
        "metadata": {"font_count": 1, "has_layers": False, "resolution_dpi": 300}
    }))
    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"
    assert result["recommendation"] == "pass"
    assert result["signals"] == []


@pytest.mark.asyncio
async def test_fraud_font_inconsistency(martin):
    """Multiple fonts should trigger fraud signal."""
    result = await martin.execute(_make_task("detect_fraud", {
        "metadata": {"font_count": 5}
    }))
    assert result["risk_score"] == 0.3
    assert result["risk_level"] == "medium"
    assert any(s["type"] == "font_inconsistency" for s in result["signals"])


@pytest.mark.asyncio
async def test_fraud_hidden_layers(martin):
    """Hidden PDF layers should trigger high-severity signal."""
    result = await martin.execute(_make_task("detect_fraud", {
        "metadata": {"has_layers": True}
    }))
    assert result["risk_score"] == 0.35
    assert any(s["type"] == "document_layers" for s in result["signals"])
    assert result["recommendation"] == "flag_for_review"


@pytest.mark.asyncio
async def test_fraud_combined_signals(martin):
    """Multiple fraud signals should accumulate risk score."""
    result = await martin.execute(_make_task("detect_fraud", {
        "metadata": {
            "font_count": 5,
            "has_layers": True,
            "creation_date": "2025-01-01",
            "modification_date": "2025-01-15",
            "resolution_dpi": 100,
        }
    }))
    # font(0.3) + layers(0.35) + date_mismatch(0.15) + low_res(0.1) = 0.9
    assert result["risk_score"] == 0.9
    assert result["risk_level"] == "high"
    assert result["recommendation"] == "flag_for_review"
    assert len(result["signals"]) == 4


@pytest.mark.asyncio
async def test_fraud_risk_capped_at_1(martin):
    """Risk score should never exceed 1.0."""
    result = await martin.execute(_make_task("detect_fraud", {
        "metadata": {
            "font_count": 10,
            "has_layers": True,
            "creation_date": "2025-01-01",
            "modification_date": "2025-06-01",
            "resolution_dpi": 50,
        }
    }))
    assert result["risk_score"] <= 1.0


# --- Completeness Audit ---


@pytest.mark.asyncio
async def test_audit_complete_fha_loan(martin):
    """FHA loan with all required docs should be complete."""
    # Pre-populate document store
    martin._document_store["LOAN-FHA"] = [
        {"type": "w2", "filename": "w2.pdf", "confidence": 0.92},
        {"type": "paystub", "filename": "pay.pdf", "confidence": 0.92},
        {"type": "bank_statement", "filename": "bank.pdf", "confidence": 0.92},
        {"type": "tax_return", "filename": "1040.pdf", "confidence": 0.92},
    ]
    result = await martin.execute(_make_task("audit_completeness", {
        "loan_id": "LOAN-FHA",
        "loan_type": "FHA",
    }))
    assert result["complete"] is True
    assert result["missing"] == []
    assert result["required"] == 4
    assert result["received"] == 4


@pytest.mark.asyncio
async def test_audit_missing_docs(martin):
    """Loan missing required docs should list them."""
    martin._document_store["LOAN-INC"] = [
        {"type": "w2", "filename": "w2.pdf", "confidence": 0.92},
    ]
    result = await martin.execute(_make_task("audit_completeness", {
        "loan_id": "LOAN-INC",
        "loan_type": "FHA",
    }))
    assert result["complete"] is False
    assert "paystub" in result["missing"]
    assert "bank_statement" in result["missing"]
    assert "tax_return" in result["missing"]


@pytest.mark.asyncio
async def test_audit_va_loan_fewer_requirements(martin):
    """VA loan requires fewer docs than FHA."""
    martin._document_store["LOAN-VA"] = [
        {"type": "w2", "filename": "w2.pdf", "confidence": 0.92},
        {"type": "paystub", "filename": "pay.pdf", "confidence": 0.92},
        {"type": "bank_statement", "filename": "bank.pdf", "confidence": 0.92},
    ]
    result = await martin.execute(_make_task("audit_completeness", {
        "loan_id": "LOAN-VA",
        "loan_type": "VA",
    }))
    assert result["complete"] is True
    assert result["required"] == 3


# --- Document Audit (Bulk) ---


@pytest.mark.asyncio
async def test_run_document_audit_empty_store(martin):
    """Empty document store should audit cleanly."""
    result = await martin.execute(_make_task("run_document_audit", {}))
    assert result["loans_audited"] == 0
    assert result["incomplete_loans"] == []


@pytest.mark.asyncio
async def test_run_document_audit_mixed(martin):
    """Audit should identify incomplete loans only."""
    martin._document_store["COMPLETE"] = [
        {"type": "w2", "filename": "w2.pdf", "confidence": 0.92},
        {"type": "paystub", "filename": "pay.pdf", "confidence": 0.92},
        {"type": "bank_statement", "filename": "bank.pdf", "confidence": 0.92},
        {"type": "tax_return", "filename": "1040.pdf", "confidence": 0.92},
    ]
    martin._document_store["INCOMPLETE"] = [
        {"type": "w2", "filename": "w2.pdf", "confidence": 0.92},
    ]
    result = await martin.execute(_make_task("run_document_audit", {}))
    assert result["loans_audited"] == 2
    assert len(result["incomplete_loans"]) == 1
    assert result["incomplete_loans"][0]["loan_id"] == "INCOMPLETE"


# --- Unknown Action ---


@pytest.mark.asyncio
async def test_unknown_action_raises(martin):
    """Unknown action should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown MARTIN action"):
        await martin.execute(_make_task("nonexistent_action", {}))
