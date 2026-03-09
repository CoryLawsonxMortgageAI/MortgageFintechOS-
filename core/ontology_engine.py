"""
Palantir AIP-Style Ontology Engine for MortgageFintechOS.
Maps real-world mortgage objects from Total Expert CRM into a semantic
ontology with typed properties, link traversal, action execution,
validation rules, and pipeline analytics.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OBJECT TYPE DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OBJECT_TYPES: dict[str, dict[str, Any]] = {
    "Contact": {
        "primary_key": "id",
        "display_name_template": "{first_name} {last_name}",
        "search_fields": ["first_name", "last_name", "email", "phone"],
        "icon": "user",
        "color": "#58a6ff",
        "properties": {
            "id": {"type": "string", "required": True},
            "first_name": {"type": "string", "required": True},
            "last_name": {"type": "string", "required": True},
            "email": {"type": "string", "indexed": True},
            "phone": {"type": "string"},
            "address": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
            "zip": {"type": "string"},
            "source": {"type": "enum", "values": ["website", "referral", "zillow", "realtor", "social", "cold_call", "walk_in"]},
            "status": {"type": "enum", "values": ["lead", "prospect", "active", "closed", "dead"]},
            "assigned_lo_id": {"type": "string", "link_to": "LoanOfficer"},
            "credit_score": {"type": "integer"},
            "annual_income": {"type": "decimal"},
            "tags": {"type": "array"},
            "custom_fields": {"type": "object"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
    },
    "Loan": {
        "primary_key": "id",
        "display_name_template": "{loan_number} - {loan_type} ${loan_amount}",
        "search_fields": ["loan_number", "property_address"],
        "icon": "dollar-sign",
        "color": "#3fb950",
        "properties": {
            "id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact", "required": True},
            "loan_number": {"type": "string", "indexed": True},
            "loan_type": {"type": "enum", "values": ["FHA", "VA", "CONV", "USDA", "JUMBO"]},
            "loan_amount": {"type": "decimal"},
            "interest_rate": {"type": "decimal"},
            "loan_term": {"type": "integer"},
            "property_address": {"type": "string"},
            "property_type": {"type": "enum", "values": ["single_family", "condo", "townhouse", "multi_family", "manufactured"]},
            "loan_status": {"type": "enum", "values": ["application", "processing", "underwriting", "conditions", "approval", "closing", "funded", "denied"]},
            "ltv": {"type": "decimal"},
            "dti": {"type": "decimal"},
            "credit_score": {"type": "integer"},
            "lock_date": {"type": "date"},
            "lock_expiration": {"type": "date"},
            "closing_date": {"type": "date"},
            "loan_officer_id": {"type": "string", "link_to": "LoanOfficer"},
            "processor_id": {"type": "string"},
            "underwriter_id": {"type": "string"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
    },
    "Document": {
        "primary_key": "id",
        "display_name_template": "{name} ({type})",
        "search_fields": ["name"],
        "icon": "file-text",
        "color": "#d29922",
        "properties": {
            "id": {"type": "string", "required": True},
            "loan_id": {"type": "string", "link_to": "Loan", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact"},
            "name": {"type": "string", "required": True},
            "type": {"type": "enum", "values": ["income", "asset", "credit", "property", "compliance", "identity", "appraisal"]},
            "status": {"type": "enum", "values": ["requested", "received", "reviewed", "approved", "rejected"]},
            "uploaded_at": {"type": "datetime"},
            "reviewed_at": {"type": "datetime"},
            "reviewer_id": {"type": "string"},
            "created_at": {"type": "datetime"},
        },
    },
    "Campaign": {
        "primary_key": "id",
        "display_name_template": "{name}",
        "search_fields": ["name"],
        "icon": "send",
        "color": "#bc8cff",
        "properties": {
            "id": {"type": "string", "required": True},
            "name": {"type": "string", "required": True},
            "type": {"type": "enum", "values": ["email", "sms", "social", "direct_mail"]},
            "status": {"type": "enum", "values": ["draft", "active", "paused", "completed"]},
            "audience_filter": {"type": "object"},
            "content_template": {"type": "string"},
            "scheduled_at": {"type": "datetime"},
            "sent_count": {"type": "integer"},
            "open_rate": {"type": "decimal"},
            "click_rate": {"type": "decimal"},
            "created_at": {"type": "datetime"},
        },
    },
    "Task": {
        "primary_key": "id",
        "display_name_template": "{title}",
        "search_fields": ["title", "description"],
        "icon": "check-square",
        "color": "#f0883e",
        "properties": {
            "id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact"},
            "loan_id": {"type": "string", "link_to": "Loan"},
            "title": {"type": "string", "required": True},
            "description": {"type": "string"},
            "type": {"type": "enum", "values": ["follow_up", "document_request", "condition", "callback", "review", "compliance"]},
            "priority": {"type": "enum", "values": ["low", "medium", "high", "urgent"]},
            "status": {"type": "enum", "values": ["pending", "in_progress", "completed", "cancelled"]},
            "assigned_to": {"type": "string"},
            "due_date": {"type": "date"},
            "completed_at": {"type": "datetime"},
            "created_at": {"type": "datetime"},
        },
    },
    "Communication": {
        "primary_key": "id",
        "display_name_template": "{type}: {subject}",
        "search_fields": ["subject", "body"],
        "icon": "message-square",
        "color": "#79c0ff",
        "properties": {
            "id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact", "required": True},
            "type": {"type": "enum", "values": ["email", "phone", "sms", "in_person"]},
            "direction": {"type": "enum", "values": ["inbound", "outbound"]},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "status": {"type": "enum", "values": ["sent", "delivered", "opened", "replied", "bounced"]},
            "sent_at": {"type": "datetime"},
            "created_at": {"type": "datetime"},
        },
    },
    "LoanOfficer": {
        "primary_key": "id",
        "display_name_template": "{name} (NMLS# {nmls_id})",
        "search_fields": ["name", "email", "nmls_id"],
        "icon": "briefcase",
        "color": "#56d364",
        "properties": {
            "id": {"type": "string", "required": True},
            "name": {"type": "string", "required": True},
            "email": {"type": "string", "indexed": True},
            "phone": {"type": "string"},
            "nmls_id": {"type": "string", "indexed": True},
            "branch": {"type": "string"},
            "active_loans_count": {"type": "integer"},
            "pipeline_volume": {"type": "decimal"},
            "ytd_funded": {"type": "decimal"},
            "status": {"type": "enum", "values": ["active", "inactive", "on_leave"]},
            "created_at": {"type": "datetime"},
        },
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LINK TYPES (Relationships)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LINK_TYPES: dict[str, dict[str, Any]] = {
    "contact_loans": {"from": "Contact", "to": "Loan", "cardinality": "one_to_many", "label": "has loans", "foreign_key": "contact_id"},
    "loan_documents": {"from": "Loan", "to": "Document", "cardinality": "one_to_many", "label": "has documents", "foreign_key": "loan_id"},
    "loan_tasks": {"from": "Loan", "to": "Task", "cardinality": "one_to_many", "label": "has tasks", "foreign_key": "loan_id"},
    "contact_tasks": {"from": "Contact", "to": "Task", "cardinality": "one_to_many", "label": "has tasks", "foreign_key": "contact_id"},
    "contact_communications": {"from": "Contact", "to": "Communication", "cardinality": "one_to_many", "label": "has communications", "foreign_key": "contact_id"},
    "lo_loans": {"from": "LoanOfficer", "to": "Loan", "cardinality": "one_to_many", "label": "manages", "foreign_key": "loan_officer_id"},
    "lo_contacts": {"from": "LoanOfficer", "to": "Contact", "cardinality": "one_to_many", "label": "assigned to", "foreign_key": "assigned_lo_id"},
    "campaign_contacts": {"from": "Campaign", "to": "Contact", "cardinality": "many_to_many", "label": "targets", "foreign_key": "audience_filter"},
    "document_contact": {"from": "Document", "to": "Contact", "cardinality": "many_to_one", "label": "belongs to", "foreign_key": "contact_id"},
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALID STATUS TRANSITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOAN_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "application": ["processing", "denied"],
    "processing": ["underwriting", "denied"],
    "underwriting": ["conditions", "approval", "denied"],
    "conditions": ["underwriting", "approval", "denied"],
    "approval": ["closing", "denied"],
    "closing": ["funded", "denied"],
    "funded": [],
    "denied": ["application"],
}

CONTACT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "lead": ["prospect", "dead"],
    "prospect": ["active", "dead"],
    "active": ["closed", "dead"],
    "closed": ["active"],
    "dead": ["lead"],
}

TASK_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled", "pending"],
    "completed": [],
    "cancelled": ["pending"],
}

DOCUMENT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "requested": ["received"],
    "received": ["reviewed"],
    "reviewed": ["approved", "rejected"],
    "approved": [],
    "rejected": ["requested"],
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ONTOLOGY ACTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ONTOLOGY_ACTIONS: dict[str, dict[str, Any]] = {
    "assign_loan_officer": {
        "object_type": "Contact",
        "description": "Assign a loan officer to a contact",
        "parameters": [
            {"name": "loan_officer_id", "type": "string", "required": True, "description": "ID of the loan officer to assign"},
        ],
        "side_effects": ["update_contact", "create_task", "log_communication"],
        "validation": ["loan_officer_must_exist", "contact_must_be_active"],
        "agent_hint": "DIEGO",
    },
    "update_loan_status": {
        "object_type": "Loan",
        "description": "Move loan to next pipeline stage",
        "parameters": [
            {"name": "new_status", "type": "enum", "values": ["application", "processing", "underwriting", "conditions", "approval", "closing", "funded", "denied"], "required": True},
            {"name": "notes", "type": "string", "required": False, "description": "Transition notes"},
        ],
        "side_effects": ["update_loan", "create_task", "notify_stakeholders"],
        "validation": ["valid_status_transition", "required_documents_present"],
        "agent_hint": "DIEGO",
    },
    "create_follow_up_task": {
        "object_type": "Contact",
        "description": "Create a follow-up task for a contact",
        "parameters": [
            {"name": "title", "type": "string", "required": True},
            {"name": "due_date", "type": "date", "required": True},
            {"name": "priority", "type": "enum", "values": ["low", "medium", "high", "urgent"], "required": False},
            {"name": "assigned_to", "type": "string", "required": False},
        ],
        "side_effects": ["create_task"],
        "validation": [],
        "agent_hint": "JARVIS",
    },
    "request_document": {
        "object_type": "Loan",
        "description": "Request a document from a borrower",
        "parameters": [
            {"name": "document_name", "type": "string", "required": True},
            {"name": "document_type", "type": "enum", "values": ["income", "asset", "credit", "property", "compliance", "identity", "appraisal"], "required": True},
            {"name": "notes", "type": "string", "required": False},
        ],
        "side_effects": ["create_document_request", "create_task", "send_notification"],
        "validation": ["loan_not_funded_or_denied"],
        "agent_hint": "MARTIN",
    },
    "send_campaign": {
        "object_type": "Campaign",
        "description": "Launch a marketing campaign to targeted contacts",
        "parameters": [
            {"name": "audience_filter", "type": "object", "required": True, "description": "Filter criteria for target contacts"},
            {"name": "schedule_at", "type": "datetime", "required": False},
        ],
        "side_effects": ["activate_campaign", "log_campaign_sent"],
        "validation": ["campaign_must_be_draft", "audience_not_empty"],
        "agent_hint": "HERALD",
    },
    "log_call": {
        "object_type": "Contact",
        "description": "Log a phone call with a contact",
        "parameters": [
            {"name": "direction", "type": "enum", "values": ["inbound", "outbound"], "required": True},
            {"name": "subject", "type": "string", "required": True},
            {"name": "body", "type": "string", "required": False},
            {"name": "duration_minutes", "type": "integer", "required": False},
        ],
        "side_effects": ["create_communication", "update_contact_last_activity"],
        "validation": [],
        "agent_hint": "JARVIS",
    },
    "escalate_loan": {
        "object_type": "Loan",
        "description": "Escalate a loan for manager review",
        "parameters": [
            {"name": "reason", "type": "string", "required": True},
            {"name": "escalation_level", "type": "enum", "values": ["supervisor", "manager", "director"], "required": True},
        ],
        "side_effects": ["create_task", "send_notification", "log_escalation"],
        "validation": ["loan_must_be_active"],
        "agent_hint": "DIEGO",
    },
    "verify_income": {
        "object_type": "Loan",
        "description": "Trigger income verification analysis",
        "parameters": [
            {"name": "method", "type": "enum", "values": ["w2_dual_method", "schedule_c", "voe", "bank_statements"], "required": True},
            {"name": "tax_year", "type": "integer", "required": False},
        ],
        "side_effects": ["run_income_analysis", "create_task", "update_loan_dti"],
        "validation": ["income_documents_present"],
        "agent_hint": "NOVA",
    },
    "resolve_condition": {
        "object_type": "Loan",
        "description": "Resolve an underwriting condition",
        "parameters": [
            {"name": "condition_id", "type": "string", "required": True},
            {"name": "resolution_type", "type": "enum", "values": ["document_provided", "loe_drafted", "waived", "cleared"], "required": True},
            {"name": "notes", "type": "string", "required": False},
        ],
        "side_effects": ["update_condition", "create_task", "check_all_conditions_cleared"],
        "validation": ["condition_must_exist", "loan_in_conditions_stage"],
        "agent_hint": "JARVIS",
    },
    "run_security_scan": {
        "object_type": "Loan",
        "description": "Run compliance and fraud security scan on a loan",
        "parameters": [
            {"name": "scan_type", "type": "enum", "values": ["compliance", "fraud", "identity", "full"], "required": True},
        ],
        "side_effects": ["run_scan", "create_report", "flag_issues"],
        "validation": [],
        "agent_hint": "CIPHER",
    },
    "generate_report": {
        "object_type": "LoanOfficer",
        "description": "Generate a performance or pipeline report for a loan officer",
        "parameters": [
            {"name": "report_type", "type": "enum", "values": ["pipeline", "performance", "compliance", "ytd_summary"], "required": True},
            {"name": "date_range", "type": "string", "required": False, "description": "e.g. '2026-01-01:2026-03-01'"},
        ],
        "side_effects": ["generate_report", "store_report"],
        "validation": [],
        "agent_hint": "STORM",
    },
    "classify_document": {
        "object_type": "Document",
        "description": "Auto-classify a document using AI",
        "parameters": [
            {"name": "force_type", "type": "enum", "values": ["income", "asset", "credit", "property", "compliance", "identity", "appraisal"], "required": False},
        ],
        "side_effects": ["update_document_type", "run_ocr_validation"],
        "validation": ["document_must_be_received"],
        "agent_hint": "MARTIN",
    },
    "update_contact_status": {
        "object_type": "Contact",
        "description": "Update a contact's lifecycle status",
        "parameters": [
            {"name": "new_status", "type": "enum", "values": ["lead", "prospect", "active", "closed", "dead"], "required": True},
            {"name": "reason", "type": "string", "required": False},
        ],
        "side_effects": ["update_contact", "log_status_change"],
        "validation": ["valid_contact_status_transition"],
        "agent_hint": "DIEGO",
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PREDICTIVE INTELLIGENCE FORMULAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PIPELINE_STAGE_WEIGHTS: dict[str, float] = {
    "application": 0.10,
    "processing": 0.20,
    "underwriting": 0.40,
    "conditions": 0.60,
    "approval": 0.80,
    "closing": 0.95,
    "funded": 1.00,
    "denied": 0.00,
}

STAGE_RISK_BASELINES: dict[str, dict[str, float]] = {
    "application": {"avg_days": 3, "fallout_rate": 0.25, "doc_completeness": 0.30},
    "processing": {"avg_days": 5, "fallout_rate": 0.15, "doc_completeness": 0.55},
    "underwriting": {"avg_days": 7, "fallout_rate": 0.12, "doc_completeness": 0.75},
    "conditions": {"avg_days": 5, "fallout_rate": 0.08, "doc_completeness": 0.85},
    "approval": {"avg_days": 3, "fallout_rate": 0.03, "doc_completeness": 0.95},
    "closing": {"avg_days": 5, "fallout_rate": 0.02, "doc_completeness": 1.00},
}

PREDICTIVE_FORMULA = {
    "name": "Loan Probability Score (LPS)",
    "formula": "LPS = (W_stage * S) + (W_docs * D) + (W_credit * C) + (W_dti * T) + (W_age * A)",
    "weights": {
        "W_stage": 0.30,
        "W_docs": 0.25,
        "W_credit": 0.20,
        "W_dti": 0.15,
        "W_age": 0.10,
    },
    "variables": {
        "S": "Stage progression score (0.0 - 1.0)",
        "D": "Document completeness ratio (0.0 - 1.0)",
        "C": "Credit score factor: (score - 500) / 350, clamped 0-1",
        "T": "DTI factor: 1 - (dti / 57), clamped 0-1 (FHA max 57%)",
        "A": "Age factor: max(0, 1 - days_in_stage / (2 * avg_days))",
    },
    "risk_thresholds": {
        "low": {"min": 0.70, "max": 1.00, "color": "#3fb950"},
        "medium": {"min": 0.40, "max": 0.70, "color": "#d29922"},
        "high": {"min": 0.20, "max": 0.40, "color": "#f0883e"},
        "critical": {"min": 0.00, "max": 0.20, "color": "#f85149"},
    },
}


class OntologyEngine:
    """Palantir AIP-style ontology engine for mortgage operations."""

    def __init__(self) -> None:
        self._object_types = OBJECT_TYPES
        self._link_types = LINK_TYPES
        self._actions = ONTOLOGY_ACTIONS
        self._object_store: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self._sync_status: dict[str, str] = {}
        self._action_log: list[dict[str, Any]] = []
        self._log = logger.bind(component="ontology_engine")

    # ── Schema Methods ──

    def get_object_types(self) -> dict[str, Any]:
        return {
            name: {
                "primary_key": ot["primary_key"],
                "display_name_template": ot["display_name_template"],
                "search_fields": ot["search_fields"],
                "icon": ot["icon"],
                "color": ot["color"],
                "property_count": len(ot["properties"]),
                "properties": ot["properties"],
            }
            for name, ot in self._object_types.items()
        }

    def get_object_type(self, type_name: str) -> dict[str, Any] | None:
        ot = self._object_types.get(type_name)
        if not ot:
            return None
        return {**ot, "object_count": len(self._object_store.get(type_name, {}))}

    def get_link_types(self) -> dict[str, Any]:
        return dict(self._link_types)

    def get_actions(self) -> dict[str, Any]:
        return dict(self._actions)

    def get_action(self, action_name: str) -> dict[str, Any] | None:
        return self._actions.get(action_name)

    # ── Object CRUD ──

    async def ingest_objects(self, object_type: str, objects: list[dict[str, Any]]) -> dict[str, Any]:
        if object_type not in self._object_types:
            return {"error": f"Unknown object type: {object_type}"}
        pk = self._object_types[object_type]["primary_key"]
        count = 0
        for obj in objects:
            obj_id = str(obj.get(pk, ""))
            if obj_id:
                self._object_store[object_type][obj_id] = obj
                count += 1
        self._sync_status[object_type] = datetime.now(timezone.utc).isoformat()
        self._log.info("objects_ingested", object_type=object_type, count=count)
        return {"ingested": count, "object_type": object_type}

    async def sync_objects(self, object_type: str, te_client: Any, since: str | None = None) -> dict[str, Any]:
        if object_type not in self._object_types:
            return {"error": f"Unknown object type: {object_type}"}
        method_map = {
            "Contact": "sync_all_contacts",
            "Loan": "sync_all_loans",
            "LoanOfficer": "list_loan_officers",
            "Campaign": "list_campaigns",
            "Task": "list_tasks",
            "Communication": "list_communications",
            "Document": "list_documents",
        }
        method_name = method_map.get(object_type)
        if not method_name or not te_client:
            return {"error": f"No sync method for {object_type}"}
        try:
            if method_name.startswith("sync_"):
                result = await getattr(te_client, method_name)(since=since)
            else:
                result = await getattr(te_client, method_name)()
            items = result.get("data", result.get("contacts", result.get("loans", [])))
            if isinstance(items, list):
                return await self.ingest_objects(object_type, items)
            return {"error": "Unexpected response format"}
        except Exception as e:
            self._log.error("sync_failed", object_type=object_type, error=str(e))
            return {"error": str(e)}

    async def get_object(self, object_type: str, object_id: str) -> dict[str, Any] | None:
        return self._object_store.get(object_type, {}).get(object_id)

    async def search_objects(
        self, object_type: str, query: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if object_type not in self._object_types:
            return []
        search_fields = self._object_types[object_type]["search_fields"]
        query_lower = query.lower()
        results = []
        for obj in self._object_store.get(object_type, {}).values():
            for field in search_fields:
                val = str(obj.get(field, "")).lower()
                if query_lower in val:
                    if filters:
                        match = all(obj.get(k) == v for k, v in filters.items())
                        if not match:
                            continue
                    results.append(obj)
                    break
        return results

    async def list_objects(
        self, object_type: str, filters: dict[str, Any] | None = None, page: int = 1, per_page: int = 50
    ) -> dict[str, Any]:
        objects = list(self._object_store.get(object_type, {}).values())
        if filters:
            objects = [o for o in objects if all(o.get(k) == v for k, v in filters.items())]
        total = len(objects)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "data": objects[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    # ── Link Traversal ──

    async def get_linked_objects(self, object_type: str, object_id: str, link_type: str) -> list[dict[str, Any]]:
        link = self._link_types.get(link_type)
        if not link:
            return []
        fk = link["foreign_key"]
        if link["from"] == object_type:
            target_type = link["to"]
            return [
                obj for obj in self._object_store.get(target_type, {}).values()
                if str(obj.get(fk, "")) == object_id
            ]
        elif link["to"] == object_type:
            source_type = link["from"]
            obj = self._object_store.get(object_type, {}).get(object_id)
            if obj and fk in obj:
                source_id = str(obj[fk])
                source_obj = self._object_store.get(source_type, {}).get(source_id)
                return [source_obj] if source_obj else []
        return []

    async def get_object_graph(self, object_type: str, object_id: str, depth: int = 2) -> dict[str, Any]:
        root = await self.get_object(object_type, object_id)
        if not root:
            return {"error": "Object not found"}
        nodes: list[dict[str, Any]] = [{"id": object_id, "type": object_type, "data": root, "depth": 0}]
        edges: list[dict[str, Any]] = []
        visited: set[str] = {f"{object_type}:{object_id}"}
        queue: list[tuple[str, str, int]] = [(object_type, object_id, 0)]

        while queue:
            curr_type, curr_id, curr_depth = queue.pop(0)
            if curr_depth >= depth:
                continue
            for link_name, link_def in self._link_types.items():
                if link_def["from"] == curr_type or link_def["to"] == curr_type:
                    linked = await self.get_linked_objects(curr_type, curr_id, link_name)
                    target_type = link_def["to"] if link_def["from"] == curr_type else link_def["from"]
                    pk = self._object_types[target_type]["primary_key"]
                    for linked_obj in linked:
                        linked_id = str(linked_obj.get(pk, ""))
                        key = f"{target_type}:{linked_id}"
                        if key not in visited:
                            visited.add(key)
                            nodes.append({"id": linked_id, "type": target_type, "data": linked_obj, "depth": curr_depth + 1})
                            edges.append({"from": curr_id, "to": linked_id, "type": link_name, "label": link_def["label"]})
                            queue.append((target_type, linked_id, curr_depth + 1))
        return {"nodes": nodes, "edges": edges, "root": object_id, "root_type": object_type}

    # ── Action Execution ──

    async def validate_action(self, action_name: str, object_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        action = self._actions.get(action_name)
        if not action:
            return {"valid": False, "errors": [f"Unknown action: {action_name}"]}
        errors: list[str] = []
        for param in action["parameters"]:
            if param.get("required") and param["name"] not in parameters:
                errors.append(f"Missing required parameter: {param['name']}")
            if param["name"] in parameters and param["type"] == "enum":
                if parameters[param["name"]] not in param.get("values", []):
                    errors.append(f"Invalid value for {param['name']}: {parameters[param['name']]}")
        obj_type = action["object_type"]
        obj = await self.get_object(obj_type, object_id)
        if not obj:
            errors.append(f"{obj_type} with id {object_id} not found")
        for validation in action.get("validation", []):
            if validation == "valid_status_transition" and obj:
                current = obj.get("loan_status", "")
                new = parameters.get("new_status", "")
                allowed = LOAN_STATUS_TRANSITIONS.get(current, [])
                if new and new not in allowed:
                    errors.append(f"Cannot transition from '{current}' to '{new}'. Allowed: {allowed}")
            elif validation == "valid_contact_status_transition" and obj:
                current = obj.get("status", "")
                new = parameters.get("new_status", "")
                allowed = CONTACT_STATUS_TRANSITIONS.get(current, [])
                if new and new not in allowed:
                    errors.append(f"Cannot transition contact from '{current}' to '{new}'. Allowed: {allowed}")
            elif validation == "loan_not_funded_or_denied" and obj:
                status = obj.get("loan_status", "")
                if status in ("funded", "denied"):
                    errors.append(f"Cannot perform action on {status} loan")
            elif validation == "loan_must_be_active" and obj:
                status = obj.get("loan_status", "")
                if status in ("funded", "denied"):
                    errors.append("Loan is not in an active stage")
            elif validation == "document_must_be_received" and obj:
                if obj.get("status") != "received":
                    errors.append("Document must be in 'received' status to classify")
        return {"valid": len(errors) == 0, "errors": errors}

    async def execute_action(
        self,
        action_name: str,
        object_id: str,
        parameters: dict[str, Any],
        te_client: Any = None,
    ) -> dict[str, Any]:
        validation = await self.validate_action(action_name, object_id, parameters)
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"]}
        action = self._actions[action_name]
        obj_type = action["object_type"]
        result: dict[str, Any] = {
            "action": action_name,
            "object_type": obj_type,
            "object_id": object_id,
            "parameters": parameters,
            "side_effects_executed": [],
            "success": True,
        }
        obj = await self.get_object(obj_type, object_id)
        if action_name == "update_loan_status" and obj:
            obj["loan_status"] = parameters["new_status"]
            obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._object_store[obj_type][object_id] = obj
            result["side_effects_executed"].append("update_loan")
            if te_client:
                await te_client.update_loan(object_id, {"loan_status": parameters["new_status"]})
        elif action_name == "update_contact_status" and obj:
            obj["status"] = parameters["new_status"]
            obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._object_store[obj_type][object_id] = obj
            result["side_effects_executed"].append("update_contact")
            if te_client:
                await te_client.update_contact(object_id, {"status": parameters["new_status"]})
        elif action_name == "assign_loan_officer" and obj:
            obj["assigned_lo_id"] = parameters["loan_officer_id"]
            obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._object_store[obj_type][object_id] = obj
            result["side_effects_executed"].append("update_contact")
            if te_client:
                await te_client.update_contact(object_id, {"assigned_lo_id": parameters["loan_officer_id"]})
        elif action_name == "create_follow_up_task":
            task = {
                "id": str(uuid.uuid4()),
                "contact_id": object_id,
                "title": parameters["title"],
                "type": "follow_up",
                "priority": parameters.get("priority", "medium"),
                "status": "pending",
                "due_date": parameters["due_date"],
                "assigned_to": parameters.get("assigned_to", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._object_store["Task"][task["id"]] = task
            result["created_task_id"] = task["id"]
            result["side_effects_executed"].append("create_task")
            if te_client:
                await te_client.create_task(task)
        elif action_name == "log_call":
            comm = {
                "id": str(uuid.uuid4()),
                "contact_id": object_id,
                "type": "phone",
                "direction": parameters["direction"],
                "subject": parameters["subject"],
                "body": parameters.get("body", ""),
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._object_store["Communication"][comm["id"]] = comm
            result["created_communication_id"] = comm["id"]
            result["side_effects_executed"].append("create_communication")
            if te_client:
                await te_client.log_communication(comm)
        elif action_name == "request_document":
            doc = {
                "id": str(uuid.uuid4()),
                "loan_id": object_id,
                "name": parameters["document_name"],
                "type": parameters["document_type"],
                "status": "requested",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._object_store["Document"][doc["id"]] = doc
            result["created_document_id"] = doc["id"]
            result["side_effects_executed"].append("create_document_request")
        else:
            result["side_effects_executed"].append("generic_action_logged")
        self._action_log.append({
            "action": action_name,
            "object_type": obj_type,
            "object_id": object_id,
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": True,
        })
        self._log.info("action_executed", action=action_name, object_type=obj_type, object_id=object_id)
        return result

    # ── Pipeline Analytics ──

    async def get_pipeline_analytics(self) -> dict[str, Any]:
        loans = list(self._object_store.get("Loan", {}).values())
        if not loans:
            return {"total_loans": 0, "stages": {}, "volume": 0, "avg_lps": 0}
        stages: dict[str, list[dict[str, Any]]] = defaultdict(list)
        total_volume = 0.0
        lps_scores: list[float] = []
        for loan in loans:
            status = loan.get("loan_status", "unknown")
            stages[status].append(loan)
            total_volume += float(loan.get("loan_amount", 0))
            lps = self._compute_lps(loan)
            lps_scores.append(lps)
        stage_summary = {}
        for stage, stage_loans in stages.items():
            stage_volume = sum(float(l.get("loan_amount", 0)) for l in stage_loans)
            stage_summary[stage] = {
                "count": len(stage_loans),
                "volume": stage_volume,
                "avg_lps": round(sum(self._compute_lps(l) for l in stage_loans) / len(stage_loans), 3) if stage_loans else 0,
                "weight": PIPELINE_STAGE_WEIGHTS.get(stage, 0),
                "baseline": STAGE_RISK_BASELINES.get(stage, {}),
            }
        return {
            "total_loans": len(loans),
            "total_volume": total_volume,
            "avg_lps": round(sum(lps_scores) / len(lps_scores), 3) if lps_scores else 0,
            "stages": stage_summary,
            "formula": PREDICTIVE_FORMULA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _compute_lps(self, loan: dict[str, Any]) -> float:
        w = PREDICTIVE_FORMULA["weights"]
        status = loan.get("loan_status", "application")
        s = PIPELINE_STAGE_WEIGHTS.get(status, 0.1)
        d = 0.5
        credit = loan.get("credit_score", 680)
        c = max(0.0, min(1.0, (credit - 500) / 350))
        dti = loan.get("dti", 35)
        t = max(0.0, min(1.0, 1 - (dti / 57)))
        a = 0.7
        lps = (w["W_stage"] * s) + (w["W_docs"] * d) + (w["W_credit"] * c) + (w["W_dti"] * t) + (w["W_age"] * a)
        return round(max(0.0, min(1.0, lps)), 3)

    async def get_loan_funnel(self) -> dict[str, Any]:
        ordered_stages = ["application", "processing", "underwriting", "conditions", "approval", "closing", "funded"]
        funnel = []
        loans = list(self._object_store.get("Loan", {}).values())
        for stage in ordered_stages:
            count = sum(1 for l in loans if l.get("loan_status") == stage)
            volume = sum(float(l.get("loan_amount", 0)) for l in loans if l.get("loan_status") == stage)
            funnel.append({"stage": stage, "count": count, "volume": volume, "weight": PIPELINE_STAGE_WEIGHTS[stage]})
        denied = sum(1 for l in loans if l.get("loan_status") == "denied")
        return {"funnel": funnel, "denied_count": denied, "total": len(loans)}

    async def get_contact_lifecycle(self) -> dict[str, Any]:
        contacts = list(self._object_store.get("Contact", {}).values())
        lifecycle: dict[str, int] = defaultdict(int)
        for c in contacts:
            lifecycle[c.get("status", "unknown")] += 1
        return {"lifecycle": dict(lifecycle), "total": len(contacts)}

    # ── Ontology Graph Export ──

    def export_ontology_graph(self) -> dict[str, Any]:
        nodes = []
        for name, ot in self._object_types.items():
            nodes.append({
                "id": name,
                "type": "object_type",
                "label": name,
                "icon": ot["icon"],
                "color": ot["color"],
                "property_count": len(ot["properties"]),
                "object_count": len(self._object_store.get(name, {})),
            })
        edges = []
        for link_name, link_def in self._link_types.items():
            edges.append({
                "id": link_name,
                "from": link_def["from"],
                "to": link_def["to"],
                "label": link_def["label"],
                "cardinality": link_def["cardinality"],
            })
        return {"nodes": nodes, "edges": edges, "actions": list(self._actions.keys())}

    # ── Status ──

    def get_sync_status(self) -> dict[str, str]:
        return dict(self._sync_status)

    def get_stats(self) -> dict[str, Any]:
        stats: dict[str, int] = {}
        for name in self._object_types:
            stats[name] = len(self._object_store.get(name, {}))
        return {
            "object_counts": stats,
            "total_objects": sum(stats.values()),
            "object_types": len(self._object_types),
            "link_types": len(self._link_types),
            "actions": len(self._actions),
            "action_log_size": len(self._action_log),
            "sync_status": self._sync_status,
            "formula": PREDICTIVE_FORMULA["name"],
        }

    def get_action_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._action_log[-limit:]
