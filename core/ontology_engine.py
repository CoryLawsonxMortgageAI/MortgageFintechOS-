"""Palantir AIP-style Ontology Engine for MortgageFintechOS.

Models real-world mortgage objects (from Total Expert CRM) as ontology
object types with properties, links, and actions -- mirroring Palantir
Foundry's Ontology layer.  Every entity in the mortgage lifecycle
(Contact, Loan, Document, Campaign, Task, Communication, LoanOfficer)
is a first-class ontology object with typed properties, directional
link types, executable actions, and validation rules.
"""

from __future__ import annotations

import asyncio
import copy
import re
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Sequence

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Property type helpers
# ---------------------------------------------------------------------------

_PYTHON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "decimal": (float, Decimal),  # type: ignore[dict-item]
    "boolean": bool,
    "date": (str, date),  # type: ignore[dict-item]
    "datetime": (str, datetime),  # type: ignore[dict-item]
    "array": list,
    "enum": str,
}

# ============================================================================
# OBJECT TYPE DEFINITIONS
# ============================================================================

OBJECT_TYPES: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------------
    "Contact": {
        "primary_key": "id",
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
            "source": {
                "type": "enum",
                "values": [
                    "website",
                    "referral",
                    "zillow",
                    "realtor",
                    "social",
                    "cold_call",
                    "walk_in",
                ],
            },
            "status": {
                "type": "enum",
                "values": ["lead", "prospect", "active", "closed", "dead"],
            },
            "assigned_lo_id": {"type": "string", "link_to": "LoanOfficer"},
            "credit_score": {"type": "integer"},
            "annual_income": {"type": "decimal"},
            "tags": {"type": "array"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
        "display_name": "{{first_name}} {{last_name}}",
        "search_fields": ["first_name", "last_name", "email", "phone"],
    },
    # ------------------------------------------------------------------
    # Loan
    # ------------------------------------------------------------------
    "Loan": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact", "required": True},
            "loan_number": {"type": "string", "indexed": True},
            "loan_type": {
                "type": "enum",
                "values": ["FHA", "VA", "CONV", "USDA", "JUMBO"],
            },
            "loan_amount": {"type": "decimal"},
            "interest_rate": {"type": "decimal"},
            "loan_term": {"type": "integer"},
            "property_address": {"type": "string"},
            "property_type": {
                "type": "enum",
                "values": [
                    "single_family",
                    "condo",
                    "townhouse",
                    "multi_family",
                    "manufactured",
                ],
            },
            "loan_status": {
                "type": "enum",
                "values": [
                    "application",
                    "processing",
                    "underwriting",
                    "conditions",
                    "approval",
                    "closing",
                    "funded",
                    "denied",
                ],
            },
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
        "display_name": "{{loan_number}} - {{loan_type}} ${{loan_amount}}",
        "search_fields": ["loan_number", "property_address"],
    },
    # ------------------------------------------------------------------
    # Document
    # ------------------------------------------------------------------
    "Document": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "loan_id": {"type": "string", "link_to": "Loan", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact"},
            "document_type": {
                "type": "enum",
                "values": [
                    "pay_stub",
                    "w2",
                    "tax_return",
                    "bank_statement",
                    "appraisal",
                    "title_report",
                    "insurance",
                    "purchase_agreement",
                    "disclosure",
                    "closing_docs",
                    "id_verification",
                    "other",
                ],
            },
            "name": {"type": "string", "required": True},
            "file_url": {"type": "string"},
            "file_size": {"type": "integer"},
            "mime_type": {"type": "string"},
            "status": {
                "type": "enum",
                "values": [
                    "requested",
                    "uploaded",
                    "under_review",
                    "approved",
                    "rejected",
                    "expired",
                ],
            },
            "expiration_date": {"type": "date"},
            "reviewed_by": {"type": "string"},
            "review_notes": {"type": "string"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
        "display_name": "{{name}} ({{document_type}})",
        "search_fields": ["name", "document_type"],
    },
    # ------------------------------------------------------------------
    # Campaign
    # ------------------------------------------------------------------
    "Campaign": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "name": {"type": "string", "required": True},
            "campaign_type": {
                "type": "enum",
                "values": [
                    "email",
                    "sms",
                    "direct_mail",
                    "social",
                    "multi_channel",
                ],
            },
            "status": {
                "type": "enum",
                "values": [
                    "draft",
                    "scheduled",
                    "active",
                    "paused",
                    "completed",
                    "cancelled",
                ],
            },
            "target_audience": {
                "type": "enum",
                "values": [
                    "all_leads",
                    "new_leads",
                    "stale_leads",
                    "past_clients",
                    "refi_candidates",
                    "pre_approved",
                    "custom",
                ],
            },
            "subject": {"type": "string"},
            "body_template": {"type": "string"},
            "scheduled_date": {"type": "datetime"},
            "sent_count": {"type": "integer"},
            "open_count": {"type": "integer"},
            "click_count": {"type": "integer"},
            "response_count": {"type": "integer"},
            "conversion_count": {"type": "integer"},
            "created_by": {"type": "string", "link_to": "LoanOfficer"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
        "display_name": "{{name}} ({{campaign_type}})",
        "search_fields": ["name", "subject"],
    },
    # ------------------------------------------------------------------
    # Task
    # ------------------------------------------------------------------
    "Task": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "description": {"type": "string"},
            "task_type": {
                "type": "enum",
                "values": [
                    "follow_up",
                    "document_review",
                    "appraisal_order",
                    "title_order",
                    "condition_clear",
                    "disclosure_send",
                    "closing_prep",
                    "quality_check",
                    "general",
                ],
            },
            "priority": {
                "type": "enum",
                "values": ["low", "medium", "high", "urgent"],
            },
            "status": {
                "type": "enum",
                "values": [
                    "pending",
                    "in_progress",
                    "blocked",
                    "completed",
                    "cancelled",
                ],
            },
            "assigned_to": {"type": "string", "link_to": "LoanOfficer"},
            "contact_id": {"type": "string", "link_to": "Contact"},
            "loan_id": {"type": "string", "link_to": "Loan"},
            "due_date": {"type": "date"},
            "completed_at": {"type": "datetime"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
        "display_name": "{{title}} [{{priority}}]",
        "search_fields": ["title", "description"],
    },
    # ------------------------------------------------------------------
    # Communication
    # ------------------------------------------------------------------
    "Communication": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "contact_id": {"type": "string", "link_to": "Contact", "required": True},
            "loan_id": {"type": "string", "link_to": "Loan"},
            "channel": {
                "type": "enum",
                "values": ["email", "phone", "sms", "in_person", "video", "chat"],
            },
            "direction": {
                "type": "enum",
                "values": ["inbound", "outbound"],
            },
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "duration_seconds": {"type": "integer"},
            "outcome": {
                "type": "enum",
                "values": [
                    "connected",
                    "voicemail",
                    "no_answer",
                    "callback_requested",
                    "info_provided",
                    "appointment_set",
                    "application_started",
                    "not_interested",
                ],
            },
            "loan_officer_id": {"type": "string", "link_to": "LoanOfficer"},
            "campaign_id": {"type": "string", "link_to": "Campaign"},
            "sentiment": {
                "type": "enum",
                "values": ["positive", "neutral", "negative"],
            },
            "created_at": {"type": "datetime"},
        },
        "display_name": "{{channel}} - {{direction}} ({{outcome}})",
        "search_fields": ["subject", "body"],
    },
    # ------------------------------------------------------------------
    # LoanOfficer
    # ------------------------------------------------------------------
    "LoanOfficer": {
        "primary_key": "id",
        "properties": {
            "id": {"type": "string", "required": True},
            "first_name": {"type": "string", "required": True},
            "last_name": {"type": "string", "required": True},
            "email": {"type": "string", "indexed": True, "required": True},
            "phone": {"type": "string"},
            "nmls_id": {"type": "string", "indexed": True},
            "branch": {"type": "string"},
            "region": {"type": "string"},
            "role": {
                "type": "enum",
                "values": [
                    "loan_officer",
                    "senior_lo",
                    "team_lead",
                    "branch_manager",
                    "regional_manager",
                ],
            },
            "status": {
                "type": "enum",
                "values": ["active", "inactive", "on_leave"],
            },
            "max_pipeline": {"type": "integer"},
            "current_pipeline_count": {"type": "integer"},
            "ytd_funded_count": {"type": "integer"},
            "ytd_funded_volume": {"type": "decimal"},
            "avg_cycle_days": {"type": "decimal"},
            "pull_through_rate": {"type": "decimal"},
            "created_at": {"type": "datetime"},
            "updated_at": {"type": "datetime"},
        },
        "display_name": "{{first_name}} {{last_name}} (NMLS {{nmls_id}})",
        "search_fields": ["first_name", "last_name", "email", "nmls_id"],
    },
}

# ============================================================================
# LINK TYPE DEFINITIONS
# ============================================================================

LINK_TYPES: dict[str, dict[str, Any]] = {
    "contact_loans": {
        "from": "Contact",
        "to": "Loan",
        "cardinality": "one_to_many",
        "foreign_key": "contact_id",
        "label": "has loans",
        "reverse_label": "belongs to contact",
    },
    "loan_documents": {
        "from": "Loan",
        "to": "Document",
        "cardinality": "one_to_many",
        "foreign_key": "loan_id",
        "label": "has documents",
        "reverse_label": "attached to loan",
    },
    "loan_tasks": {
        "from": "Loan",
        "to": "Task",
        "cardinality": "one_to_many",
        "foreign_key": "loan_id",
        "label": "has tasks",
        "reverse_label": "for loan",
    },
    "contact_tasks": {
        "from": "Contact",
        "to": "Task",
        "cardinality": "one_to_many",
        "foreign_key": "contact_id",
        "label": "has tasks",
        "reverse_label": "for contact",
    },
    "contact_communications": {
        "from": "Contact",
        "to": "Communication",
        "cardinality": "one_to_many",
        "foreign_key": "contact_id",
        "label": "has communications",
        "reverse_label": "with contact",
    },
    "loan_officer_loans": {
        "from": "LoanOfficer",
        "to": "Loan",
        "cardinality": "one_to_many",
        "foreign_key": "loan_officer_id",
        "label": "manages",
        "reverse_label": "managed by",
    },
    "loan_officer_contacts": {
        "from": "LoanOfficer",
        "to": "Contact",
        "cardinality": "one_to_many",
        "foreign_key": "assigned_lo_id",
        "label": "assigned to",
        "reverse_label": "assigned officer",
    },
    "campaign_contacts": {
        "from": "Campaign",
        "to": "Contact",
        "cardinality": "many_to_many",
        "junction_key": "campaign_contact_targets",
        "label": "targets",
        "reverse_label": "targeted by",
    },
    "loan_communications": {
        "from": "Loan",
        "to": "Communication",
        "cardinality": "one_to_many",
        "foreign_key": "loan_id",
        "label": "has communications",
        "reverse_label": "regarding loan",
    },
    "loan_officer_tasks": {
        "from": "LoanOfficer",
        "to": "Task",
        "cardinality": "one_to_many",
        "foreign_key": "assigned_to",
        "label": "assigned tasks",
        "reverse_label": "assigned to officer",
    },
    "contact_documents": {
        "from": "Contact",
        "to": "Document",
        "cardinality": "one_to_many",
        "foreign_key": "contact_id",
        "label": "has documents",
        "reverse_label": "belongs to contact",
    },
    "campaign_communications": {
        "from": "Campaign",
        "to": "Communication",
        "cardinality": "one_to_many",
        "foreign_key": "campaign_id",
        "label": "generated communications",
        "reverse_label": "from campaign",
    },
}

# ============================================================================
# VALID STATUS TRANSITIONS
# ============================================================================

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
    "dead": ["lead", "prospect"],
}

DOCUMENT_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "requested": ["uploaded", "expired"],
    "uploaded": ["under_review"],
    "under_review": ["approved", "rejected"],
    "approved": ["expired"],
    "rejected": ["uploaded"],
    "expired": ["requested"],
}

TASK_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["blocked", "completed", "cancelled"],
    "blocked": ["in_progress", "cancelled"],
    "completed": [],
    "cancelled": ["pending"],
}

CAMPAIGN_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["scheduled", "cancelled"],
    "scheduled": ["active", "cancelled"],
    "active": ["paused", "completed"],
    "paused": ["active", "cancelled"],
    "completed": [],
    "cancelled": [],
}

# ============================================================================
# ONTOLOGY ACTIONS
# ============================================================================

ONTOLOGY_ACTIONS: dict[str, dict[str, Any]] = {
    # --- Contact actions ---
    "assign_loan_officer": {
        "object_type": "Contact",
        "parameters": [
            {"name": "loan_officer_id", "type": "string", "required": True},
        ],
        "side_effects": ["update_contact", "create_task", "log_communication"],
        "validation": ["loan_officer_must_exist", "contact_must_be_active_or_prospect"],
        "description": "Assign a loan officer to a contact",
    },
    "update_contact_status": {
        "object_type": "Contact",
        "parameters": [
            {
                "name": "new_status",
                "type": "enum",
                "values": ["lead", "prospect", "active", "closed", "dead"],
                "required": True,
            },
            {"name": "reason", "type": "string"},
        ],
        "side_effects": ["update_contact", "log_communication"],
        "validation": ["valid_contact_status_transition"],
        "description": "Update a contact's lifecycle status",
    },
    "create_follow_up_task": {
        "object_type": "Contact",
        "parameters": [
            {"name": "title", "type": "string", "required": True},
            {"name": "description", "type": "string"},
            {"name": "due_date", "type": "date", "required": True},
            {
                "name": "priority",
                "type": "enum",
                "values": ["low", "medium", "high", "urgent"],
            },
            {"name": "assigned_to", "type": "string"},
        ],
        "side_effects": ["create_task"],
        "validation": ["contact_must_exist"],
        "description": "Create a follow-up task for a contact",
    },
    "log_call": {
        "object_type": "Contact",
        "parameters": [
            {
                "name": "direction",
                "type": "enum",
                "values": ["inbound", "outbound"],
                "required": True,
            },
            {"name": "duration_seconds", "type": "integer"},
            {
                "name": "outcome",
                "type": "enum",
                "values": [
                    "connected",
                    "voicemail",
                    "no_answer",
                    "callback_requested",
                    "info_provided",
                    "appointment_set",
                    "application_started",
                    "not_interested",
                ],
                "required": True,
            },
            {"name": "notes", "type": "string"},
        ],
        "side_effects": ["log_communication", "create_task"],
        "validation": ["contact_must_exist"],
        "description": "Log a phone call with a contact",
    },
    # --- Loan actions ---
    "update_loan_status": {
        "object_type": "Loan",
        "parameters": [
            {
                "name": "new_status",
                "type": "enum",
                "values": [
                    "application",
                    "processing",
                    "underwriting",
                    "conditions",
                    "approval",
                    "closing",
                    "funded",
                    "denied",
                ],
                "required": True,
            },
            {"name": "notes", "type": "string"},
        ],
        "side_effects": ["update_loan", "create_task", "notify_stakeholders"],
        "validation": ["valid_loan_status_transition", "required_documents_present"],
        "description": "Move loan to next pipeline stage",
    },
    "lock_rate": {
        "object_type": "Loan",
        "parameters": [
            {"name": "interest_rate", "type": "decimal", "required": True},
            {"name": "lock_days", "type": "integer", "required": True},
            {"name": "lock_date", "type": "date"},
        ],
        "side_effects": ["update_loan", "notify_stakeholders", "log_communication"],
        "validation": ["loan_must_be_in_pipeline", "rate_within_bounds"],
        "description": "Lock the interest rate on a loan",
    },
    "escalate_loan": {
        "object_type": "Loan",
        "parameters": [
            {
                "name": "reason",
                "type": "enum",
                "values": [
                    "stalled_pipeline",
                    "lock_expiring",
                    "compliance_issue",
                    "borrower_complaint",
                    "underwriting_exception",
                ],
                "required": True,
            },
            {"name": "escalate_to", "type": "string"},
            {"name": "notes", "type": "string"},
        ],
        "side_effects": ["create_task", "notify_stakeholders", "log_communication"],
        "validation": ["loan_must_exist"],
        "description": "Escalate a loan for management review",
    },
    "set_closing_date": {
        "object_type": "Loan",
        "parameters": [
            {"name": "closing_date", "type": "date", "required": True},
            {"name": "notes", "type": "string"},
        ],
        "side_effects": ["update_loan", "create_task", "notify_stakeholders"],
        "validation": ["loan_must_be_approved_or_closing", "closing_date_in_future"],
        "description": "Set or update the closing date for a loan",
    },
    # --- Document actions ---
    "request_document": {
        "object_type": "Loan",
        "parameters": [
            {
                "name": "document_type",
                "type": "enum",
                "values": [
                    "pay_stub",
                    "w2",
                    "tax_return",
                    "bank_statement",
                    "appraisal",
                    "title_report",
                    "insurance",
                    "purchase_agreement",
                    "disclosure",
                    "closing_docs",
                    "id_verification",
                    "other",
                ],
                "required": True,
            },
            {"name": "name", "type": "string", "required": True},
            {"name": "due_date", "type": "date"},
            {"name": "notes", "type": "string"},
        ],
        "side_effects": ["create_document", "create_task", "notify_stakeholders"],
        "validation": ["loan_must_exist"],
        "description": "Request a document from the borrower",
    },
    "review_document": {
        "object_type": "Document",
        "parameters": [
            {
                "name": "decision",
                "type": "enum",
                "values": ["approved", "rejected"],
                "required": True,
            },
            {"name": "review_notes", "type": "string"},
            {"name": "reviewed_by", "type": "string", "required": True},
        ],
        "side_effects": ["update_document", "create_task", "notify_stakeholders"],
        "validation": ["document_must_be_under_review"],
        "description": "Approve or reject an uploaded document",
    },
    # --- Campaign actions ---
    "send_campaign": {
        "object_type": "Campaign",
        "parameters": [
            {"name": "target_contact_ids", "type": "array"},
            {"name": "scheduled_date", "type": "datetime"},
        ],
        "side_effects": [
            "update_campaign",
            "create_communications",
            "link_campaign_contacts",
        ],
        "validation": ["campaign_must_be_draft_or_scheduled", "has_recipients"],
        "description": "Send or schedule a marketing campaign",
    },
    "pause_campaign": {
        "object_type": "Campaign",
        "parameters": [
            {"name": "reason", "type": "string"},
        ],
        "side_effects": ["update_campaign"],
        "validation": ["campaign_must_be_active"],
        "description": "Pause an active campaign",
    },
    # --- Task actions ---
    "complete_task": {
        "object_type": "Task",
        "parameters": [
            {"name": "completion_notes", "type": "string"},
        ],
        "side_effects": ["update_task", "check_loan_conditions"],
        "validation": ["task_must_be_in_progress_or_pending"],
        "description": "Mark a task as completed",
    },
    "reassign_task": {
        "object_type": "Task",
        "parameters": [
            {"name": "new_assignee_id", "type": "string", "required": True},
            {"name": "reason", "type": "string"},
        ],
        "side_effects": ["update_task", "notify_stakeholders"],
        "validation": ["task_not_completed", "assignee_must_exist"],
        "description": "Reassign a task to a different team member",
    },
}

# ============================================================================
# ONTOLOGY ENGINE
# ============================================================================


class OntologyValidationError(Exception):
    """Raised when an action or object fails ontology validation."""


class OntologyEngine:
    """Palantir AIP-style Ontology Engine.

    Models mortgage domain objects as first-class ontology types with
    properties, link traversal, executable actions, and pipeline analytics.
    """

    def __init__(self) -> None:
        self._object_types: dict[str, dict[str, Any]] = copy.deepcopy(OBJECT_TYPES)
        self._link_types: dict[str, dict[str, Any]] = copy.deepcopy(LINK_TYPES)
        self._actions: dict[str, dict[str, Any]] = copy.deepcopy(ONTOLOGY_ACTIONS)

        # In-memory object store keyed by (object_type, object_id)
        self._object_store: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        # Many-to-many junction tables
        self._junction_store: dict[str, list[dict[str, str]]] = defaultdict(list)
        # Sync timestamps
        self._sync_status: dict[str, datetime] = {}
        # Action execution log
        self._action_log: list[dict[str, Any]] = []

        logger.info("ontology_engine.initialized", object_types=list(self._object_types.keys()))

    # -----------------------------------------------------------------------
    # Schema introspection
    # -----------------------------------------------------------------------

    def get_object_types(self) -> dict[str, dict[str, Any]]:
        """Return all registered object type definitions."""
        return copy.deepcopy(self._object_types)

    def get_object_type(self, type_name: str) -> dict[str, Any]:
        """Return schema definition for a single object type."""
        if type_name not in self._object_types:
            raise KeyError(f"Unknown object type: {type_name}")
        return copy.deepcopy(self._object_types[type_name])

    def get_link_types(self) -> dict[str, dict[str, Any]]:
        """Return all link type definitions."""
        return copy.deepcopy(self._link_types)

    def get_actions(self) -> dict[str, dict[str, Any]]:
        """Return all registered action definitions."""
        return copy.deepcopy(self._actions)

    def get_action(self, action_name: str) -> dict[str, Any]:
        """Return definition for a single action."""
        if action_name not in self._actions:
            raise KeyError(f"Unknown action: {action_name}")
        return copy.deepcopy(self._actions[action_name])

    # -----------------------------------------------------------------------
    # Display-name rendering
    # -----------------------------------------------------------------------

    def render_display_name(self, object_type: str, obj: dict[str, Any]) -> str:
        """Render the display name template for an object instance."""
        schema = self._object_types.get(object_type)
        if not schema:
            return str(obj.get("id", ""))
        template: str = schema.get("display_name", "{{id}}")
        def _replacer(match: re.Match) -> str:
            key = match.group(1)
            val = obj.get(key, "")
            return str(val) if val is not None else ""
        return re.sub(r"\{\{(\w+)\}\}", _replacer, template)

    # -----------------------------------------------------------------------
    # Property validation
    # -----------------------------------------------------------------------

    def validate_object(self, object_type: str, obj: dict[str, Any]) -> list[str]:
        """Validate an object dict against its schema. Returns list of errors."""
        schema = self._object_types.get(object_type)
        if not schema:
            return [f"Unknown object type: {object_type}"]

        errors: list[str] = []
        props = schema["properties"]

        # Check required fields
        for prop_name, prop_def in props.items():
            if prop_def.get("required") and prop_name not in obj:
                errors.append(f"Missing required property: {prop_name}")

        # Check types and enum constraints
        for prop_name, value in obj.items():
            if prop_name not in props:
                continue
            prop_def = props[prop_name]
            prop_type = prop_def["type"]

            if value is None:
                continue

            if prop_type == "enum":
                allowed = prop_def.get("values", [])
                if value not in allowed:
                    errors.append(
                        f"Invalid enum value for {prop_name}: {value}. "
                        f"Allowed: {allowed}"
                    )
            else:
                expected = _PYTHON_TYPE_MAP.get(prop_type)
                if expected and not isinstance(value, expected):
                    errors.append(
                        f"Invalid type for {prop_name}: expected {prop_type}, "
                        f"got {type(value).__name__}"
                    )

        return errors

    # -----------------------------------------------------------------------
    # Object CRUD
    # -----------------------------------------------------------------------

    async def sync_objects(
        self,
        object_type: str,
        te_client: Any,
        since: Optional[datetime] = None,
    ) -> int:
        """Sync objects of a given type from Total Expert CRM.

        Parameters
        ----------
        object_type:
            One of the registered object types.
        te_client:
            A Total Expert API client with a ``get_<type>s()`` method.
        since:
            If provided, only sync records updated after this timestamp.

        Returns
        -------
        int
            Number of objects synced.
        """
        if object_type not in self._object_types:
            raise KeyError(f"Unknown object type: {object_type}")

        method_name = f"get_{object_type.lower()}s"
        fetch_fn = getattr(te_client, method_name, None)
        if fetch_fn is None:
            logger.warning(
                "ontology_engine.sync_no_method",
                object_type=object_type,
                method=method_name,
            )
            return 0

        try:
            kwargs: dict[str, Any] = {}
            if since:
                kwargs["updated_since"] = since.isoformat()
            records = await fetch_fn(**kwargs)
        except Exception as exc:
            logger.error(
                "ontology_engine.sync_error",
                object_type=object_type,
                error=str(exc),
            )
            return 0

        pk = self._object_types[object_type]["primary_key"]
        count = 0
        for record in records:
            obj_id = str(record.get(pk, ""))
            if not obj_id:
                continue
            self._object_store[object_type][obj_id] = record
            count += 1

        self._sync_status[object_type] = datetime.now(timezone.utc)
        logger.info(
            "ontology_engine.sync_complete",
            object_type=object_type,
            count=count,
        )
        return count

    async def get_object(self, object_type: str, object_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single object by type and ID."""
        if object_type not in self._object_types:
            raise KeyError(f"Unknown object type: {object_type}")
        obj = self._object_store.get(object_type, {}).get(object_id)
        if obj is None:
            return None
        return copy.deepcopy(obj)

    async def put_object(self, object_type: str, obj: dict[str, Any]) -> str:
        """Insert or update an object in the store. Returns the object ID."""
        if object_type not in self._object_types:
            raise KeyError(f"Unknown object type: {object_type}")

        pk = self._object_types[object_type]["primary_key"]
        obj_id = obj.get(pk)
        if not obj_id:
            obj_id = str(uuid.uuid4())
            obj[pk] = obj_id

        errors = self.validate_object(object_type, obj)
        if errors:
            raise OntologyValidationError(
                f"Validation failed for {object_type}: {'; '.join(errors)}"
            )

        now = datetime.now(timezone.utc).isoformat()
        if "created_at" not in obj:
            obj["created_at"] = now
        obj["updated_at"] = now

        self._object_store[object_type][str(obj_id)] = obj
        logger.info(
            "ontology_engine.put_object",
            object_type=object_type,
            object_id=obj_id,
        )
        return str(obj_id)

    async def delete_object(self, object_type: str, object_id: str) -> bool:
        """Remove an object from the store."""
        store = self._object_store.get(object_type, {})
        if object_id in store:
            del store[object_id]
            logger.info(
                "ontology_engine.delete_object",
                object_type=object_type,
                object_id=object_id,
            )
            return True
        return False

    async def search_objects(
        self,
        object_type: str,
        query: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Full-text search across search_fields of an object type."""
        if object_type not in self._object_types:
            raise KeyError(f"Unknown object type: {object_type}")

        schema = self._object_types[object_type]
        search_fields: list[str] = schema.get("search_fields", [])
        query_lower = query.lower()

        results: list[dict[str, Any]] = []
        for obj in self._object_store.get(object_type, {}).values():
            # Apply text search
            matched = False
            for field in search_fields:
                val = obj.get(field)
                if val and query_lower in str(val).lower():
                    matched = True
                    break
            if not matched:
                continue

            # Apply filters
            if filters and not self._matches_filters(obj, filters):
                continue

            results.append(copy.deepcopy(obj))

        return results

    async def list_objects(
        self,
        object_type: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """List objects with optional filtering and pagination."""
        if object_type not in self._object_types:
            raise KeyError(f"Unknown object type: {object_type}")

        all_objects = list(self._object_store.get(object_type, {}).values())

        if filters:
            all_objects = [o for o in all_objects if self._matches_filters(o, filters)]

        total = len(all_objects)
        start = (page - 1) * per_page
        end = start + per_page
        page_objects = [copy.deepcopy(o) for o in all_objects[start:end]]

        return {
            "object_type": object_type,
            "objects": page_objects,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        }

    @staticmethod
    def _matches_filters(obj: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if an object matches all filter conditions."""
        for key, value in filters.items():
            if key.endswith("__in"):
                field = key[:-4]
                if obj.get(field) not in value:
                    return False
            elif key.endswith("__gte"):
                field = key[:-5]
                if obj.get(field) is None or obj.get(field) < value:
                    return False
            elif key.endswith("__lte"):
                field = key[:-5]
                if obj.get(field) is None or obj.get(field) > value:
                    return False
            elif key.endswith("__ne"):
                field = key[:-4]
                if obj.get(field) == value:
                    return False
            elif key.endswith("__contains"):
                field = key[:-10]
                obj_val = obj.get(field)
                if not obj_val or value not in obj_val:
                    return False
            else:
                if obj.get(key) != value:
                    return False
        return True

    # -----------------------------------------------------------------------
    # Link traversal (Palantir-style)
    # -----------------------------------------------------------------------

    def _find_link_types_for(
        self, object_type: str, link_type: Optional[str] = None,
    ) -> list[tuple[str, dict[str, Any], bool]]:
        """Find link definitions involving an object type.

        Returns list of (link_name, link_def, is_reverse).
        """
        results: list[tuple[str, dict[str, Any], bool]] = []
        for name, ldef in self._link_types.items():
            if link_type and name != link_type:
                continue
            if ldef["from"] == object_type:
                results.append((name, ldef, False))
            elif ldef["to"] == object_type:
                results.append((name, ldef, True))
        return results

    async def get_linked_objects(
        self,
        object_type: str,
        object_id: str,
        link_type: str,
    ) -> list[dict[str, Any]]:
        """Traverse a single link type from an object, returning linked objects."""
        obj = await self.get_object(object_type, object_id)
        if obj is None:
            return []

        links = self._find_link_types_for(object_type, link_type)
        if not links:
            raise KeyError(
                f"No link type '{link_type}' found for object type '{object_type}'"
            )

        results: list[dict[str, Any]] = []
        for _name, ldef, is_reverse in links:
            if ldef.get("cardinality") == "many_to_many":
                results.extend(
                    await self._traverse_many_to_many(
                        ldef, object_type, object_id, is_reverse
                    )
                )
            else:
                results.extend(
                    await self._traverse_foreign_key(
                        ldef, object_type, object_id, is_reverse
                    )
                )

        return results

    async def _traverse_foreign_key(
        self,
        ldef: dict[str, Any],
        source_type: str,
        source_id: str,
        is_reverse: bool,
    ) -> list[dict[str, Any]]:
        """Traverse a one-to-many link via foreign key."""
        fk = ldef["foreign_key"]

        if not is_reverse:
            # Forward: source is "from" side. Find "to" objects where fk == source_id
            target_type = ldef["to"]
            return [
                copy.deepcopy(o)
                for o in self._object_store.get(target_type, {}).values()
                if str(o.get(fk, "")) == source_id
            ]
        else:
            # Reverse: source is "to" side. Look up fk on source object.
            source_obj = self._object_store.get(source_type, {}).get(source_id)
            if not source_obj:
                return []
            parent_id = source_obj.get(fk)
            if not parent_id:
                return []
            target_type = ldef["from"]
            parent = self._object_store.get(target_type, {}).get(str(parent_id))
            return [copy.deepcopy(parent)] if parent else []

    async def _traverse_many_to_many(
        self,
        ldef: dict[str, Any],
        source_type: str,
        source_id: str,
        is_reverse: bool,
    ) -> list[dict[str, Any]]:
        """Traverse a many-to-many link via junction store."""
        junction_key = ldef.get("junction_key", "")
        junctions = self._junction_store.get(junction_key, [])

        if not is_reverse:
            target_type = ldef["to"]
            target_ids = [
                j["to_id"] for j in junctions if j.get("from_id") == source_id
            ]
        else:
            target_type = ldef["from"]
            target_ids = [
                j["from_id"] for j in junctions if j.get("to_id") == source_id
            ]

        results: list[dict[str, Any]] = []
        store = self._object_store.get(target_type, {})
        for tid in target_ids:
            obj = store.get(tid)
            if obj:
                results.append(copy.deepcopy(obj))
        return results

    async def add_many_to_many_link(
        self,
        link_type: str,
        from_id: str,
        to_id: str,
    ) -> None:
        """Add a many-to-many association."""
        ldef = self._link_types.get(link_type)
        if not ldef:
            raise KeyError(f"Unknown link type: {link_type}")
        junction_key = ldef.get("junction_key")
        if not junction_key:
            raise ValueError(f"Link type '{link_type}' is not many-to-many")
        self._junction_store[junction_key].append(
            {"from_id": from_id, "to_id": to_id}
        )

    async def get_object_graph(
        self,
        object_type: str,
        object_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Build a subgraph around an object, following links up to *depth* levels.

        Returns a structure with ``root``, ``nodes``, and ``edges`` suitable
        for graph visualization.
        """
        root = await self.get_object(object_type, object_id)
        if root is None:
            return {"root": None, "nodes": [], "edges": []}

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        root_key = f"{object_type}:{object_id}"
        nodes[root_key] = {
            "object_type": object_type,
            "object_id": object_id,
            "display_name": self.render_display_name(object_type, root),
            "data": root,
        }

        frontier: list[tuple[str, str, int]] = [(object_type, object_id, 0)]
        visited: set[str] = {root_key}

        while frontier:
            cur_type, cur_id, cur_depth = frontier.pop(0)
            if cur_depth >= depth:
                continue

            all_links = self._find_link_types_for(cur_type)
            for link_name, ldef, is_reverse in all_links:
                try:
                    linked = await self.get_linked_objects(cur_type, cur_id, link_name)
                except KeyError:
                    continue

                target_type = ldef["to"] if not is_reverse else ldef["from"]
                pk = self._object_types[target_type]["primary_key"]

                for linked_obj in linked:
                    linked_id = str(linked_obj.get(pk, ""))
                    linked_key = f"{target_type}:{linked_id}"

                    if linked_key not in nodes:
                        nodes[linked_key] = {
                            "object_type": target_type,
                            "object_id": linked_id,
                            "display_name": self.render_display_name(
                                target_type, linked_obj
                            ),
                            "data": linked_obj,
                        }

                    label = ldef.get("reverse_label" if is_reverse else "label", link_name)
                    edge = {
                        "link_type": link_name,
                        "from": f"{cur_type}:{cur_id}",
                        "to": linked_key,
                        "label": label,
                    }
                    edges.append(edge)

                    if linked_key not in visited:
                        visited.add(linked_key)
                        frontier.append((target_type, linked_id, cur_depth + 1))

        return {
            "root": root_key,
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    # -----------------------------------------------------------------------
    # Action validation
    # -----------------------------------------------------------------------

    async def validate_action(
        self,
        action_name: str,
        object_id: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate action parameters and preconditions.

        Returns ``{"valid": True}`` or ``{"valid": False, "errors": [...]}``.
        """
        action_def = self._actions.get(action_name)
        if not action_def:
            return {"valid": False, "errors": [f"Unknown action: {action_name}"]}

        errors: list[str] = []
        object_type = action_def["object_type"]

        # Check required parameters
        for param_def in action_def.get("parameters", []):
            pname = param_def["name"]
            if param_def.get("required") and pname not in parameters:
                errors.append(f"Missing required parameter: {pname}")
            elif pname in parameters:
                val = parameters[pname]
                if param_def.get("type") == "enum":
                    allowed = param_def.get("values", [])
                    if val not in allowed:
                        errors.append(
                            f"Invalid value for {pname}: {val}. Allowed: {allowed}"
                        )

        # Check object exists
        obj = await self.get_object(object_type, object_id)
        if obj is None:
            errors.append(f"{object_type} {object_id} not found")
            return {"valid": False, "errors": errors}

        # Run named validation rules
        for rule in action_def.get("validation", []):
            rule_errors = self._run_validation_rule(rule, action_name, obj, parameters)
            errors.extend(rule_errors)

        return {"valid": len(errors) == 0, "errors": errors}

    def _run_validation_rule(
        self,
        rule: str,
        action_name: str,
        obj: dict[str, Any],
        parameters: dict[str, Any],
    ) -> list[str]:
        """Execute a single named validation rule."""
        errors: list[str] = []

        if rule == "valid_loan_status_transition":
            current = obj.get("loan_status", "")
            new = parameters.get("new_status", "")
            allowed = LOAN_STATUS_TRANSITIONS.get(current, [])
            if new and new not in allowed:
                errors.append(
                    f"Invalid loan status transition: {current} -> {new}. "
                    f"Allowed transitions from '{current}': {allowed}"
                )

        elif rule == "valid_contact_status_transition":
            current = obj.get("status", "")
            new = parameters.get("new_status", "")
            allowed = CONTACT_STATUS_TRANSITIONS.get(current, [])
            if new and new not in allowed:
                errors.append(
                    f"Invalid contact status transition: {current} -> {new}. "
                    f"Allowed transitions from '{current}': {allowed}"
                )

        elif rule == "required_documents_present":
            new_status = parameters.get("new_status", "")
            if new_status in ("underwriting", "closing"):
                loan_id = str(obj.get("id", ""))
                docs = self._object_store.get("Document", {})
                loan_docs = [
                    d for d in docs.values()
                    if str(d.get("loan_id", "")) == loan_id
                    and d.get("status") == "approved"
                ]
                if not loan_docs:
                    errors.append(
                        f"No approved documents found for loan {loan_id}. "
                        f"Cannot transition to {new_status}."
                    )

        elif rule == "loan_officer_must_exist":
            lo_id = parameters.get("loan_officer_id", "")
            if lo_id and lo_id not in self._object_store.get("LoanOfficer", {}):
                errors.append(f"Loan officer {lo_id} not found")

        elif rule == "contact_must_be_active_or_prospect":
            status = obj.get("status", "")
            if status not in ("lead", "prospect", "active"):
                errors.append(
                    f"Contact status is '{status}'; must be lead, prospect, or active "
                    f"to assign a loan officer"
                )

        elif rule == "contact_must_exist":
            pass  # Already checked object existence above

        elif rule == "loan_must_exist":
            pass

        elif rule == "loan_must_be_in_pipeline":
            status = obj.get("loan_status", "")
            pipeline_statuses = [
                "application", "processing", "underwriting",
                "conditions", "approval", "closing",
            ]
            if status not in pipeline_statuses:
                errors.append(
                    f"Loan status is '{status}'; must be in active pipeline to lock rate"
                )

        elif rule == "rate_within_bounds":
            rate = parameters.get("interest_rate")
            if rate is not None and (rate < 0.5 or rate > 20.0):
                errors.append(
                    f"Interest rate {rate} is out of bounds (0.5% - 20.0%)"
                )

        elif rule == "loan_must_be_approved_or_closing":
            status = obj.get("loan_status", "")
            if status not in ("approval", "closing"):
                errors.append(
                    f"Loan status is '{status}'; must be 'approval' or 'closing' "
                    f"to set closing date"
                )

        elif rule == "closing_date_in_future":
            cd = parameters.get("closing_date")
            if cd:
                if isinstance(cd, str):
                    try:
                        cd = date.fromisoformat(cd)
                    except ValueError:
                        errors.append(f"Invalid closing date format: {cd}")
                        return errors
                if isinstance(cd, date) and cd <= date.today():
                    errors.append("Closing date must be in the future")

        elif rule == "document_must_be_under_review":
            status = obj.get("status", "")
            if status != "under_review":
                errors.append(
                    f"Document status is '{status}'; must be 'under_review' to review"
                )

        elif rule == "campaign_must_be_draft_or_scheduled":
            status = obj.get("status", "")
            if status not in ("draft", "scheduled"):
                errors.append(
                    f"Campaign status is '{status}'; must be 'draft' or 'scheduled' to send"
                )

        elif rule == "campaign_must_be_active":
            status = obj.get("status", "")
            if status != "active":
                errors.append(
                    f"Campaign status is '{status}'; must be 'active' to pause"
                )

        elif rule == "has_recipients":
            target_ids = parameters.get("target_contact_ids", [])
            if not target_ids:
                # Allow sending to all contacts if no explicit list
                pass

        elif rule == "task_must_be_in_progress_or_pending":
            status = obj.get("status", "")
            if status not in ("pending", "in_progress"):
                errors.append(
                    f"Task status is '{status}'; must be 'pending' or 'in_progress' to complete"
                )

        elif rule == "task_not_completed":
            status = obj.get("status", "")
            if status in ("completed", "cancelled"):
                errors.append(
                    f"Task status is '{status}'; cannot reassign completed/cancelled tasks"
                )

        elif rule == "assignee_must_exist":
            new_id = parameters.get("new_assignee_id", "")
            if new_id and new_id not in self._object_store.get("LoanOfficer", {}):
                errors.append(f"Assignee (LoanOfficer) {new_id} not found")

        else:
            logger.warning("ontology_engine.unknown_validation_rule", rule=rule)

        return errors

    # -----------------------------------------------------------------------
    # Action execution
    # -----------------------------------------------------------------------

    async def execute_action(
        self,
        action_name: str,
        object_id: str,
        parameters: dict[str, Any],
        te_client: Any = None,
    ) -> dict[str, Any]:
        """Execute an ontology action with validation and side-effects.

        Returns an execution result dict with ``status``, ``action``,
        ``object_id``, ``side_effects_executed``, and optionally ``errors``.
        """
        validation = await self.validate_action(action_name, object_id, parameters)
        if not validation["valid"]:
            logger.warning(
                "ontology_engine.action_validation_failed",
                action=action_name,
                object_id=object_id,
                errors=validation["errors"],
            )
            return {
                "status": "validation_failed",
                "action": action_name,
                "object_id": object_id,
                "errors": validation["errors"],
            }

        action_def = self._actions[action_name]
        object_type = action_def["object_type"]

        executed_effects: list[str] = []
        effect_results: dict[str, Any] = {}

        for effect in action_def.get("side_effects", []):
            try:
                result = await self._execute_side_effect(
                    effect, action_name, object_type, object_id, parameters, te_client
                )
                executed_effects.append(effect)
                effect_results[effect] = result
            except Exception as exc:
                logger.error(
                    "ontology_engine.side_effect_error",
                    effect=effect,
                    action=action_name,
                    error=str(exc),
                )
                effect_results[effect] = {"error": str(exc)}

        # Log the action
        log_entry = {
            "action": action_name,
            "object_type": object_type,
            "object_id": object_id,
            "parameters": parameters,
            "side_effects": executed_effects,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._action_log.append(log_entry)

        logger.info(
            "ontology_engine.action_executed",
            action=action_name,
            object_type=object_type,
            object_id=object_id,
            side_effects=executed_effects,
        )

        return {
            "status": "success",
            "action": action_name,
            "object_type": object_type,
            "object_id": object_id,
            "side_effects_executed": executed_effects,
            "effect_results": effect_results,
        }

    async def _execute_side_effect(
        self,
        effect: str,
        action_name: str,
        object_type: str,
        object_id: str,
        parameters: dict[str, Any],
        te_client: Any,
    ) -> dict[str, Any]:
        """Execute a single side-effect from an action."""

        if effect == "update_contact":
            obj = self._object_store.get("Contact", {}).get(object_id)
            if obj:
                if action_name == "assign_loan_officer":
                    obj["assigned_lo_id"] = parameters.get("loan_officer_id")
                elif action_name == "update_contact_status":
                    obj["status"] = parameters.get("new_status")
                obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"updated": True}

        elif effect == "update_loan":
            obj = self._object_store.get("Loan", {}).get(object_id)
            if obj:
                if action_name == "update_loan_status":
                    obj["loan_status"] = parameters.get("new_status")
                elif action_name == "lock_rate":
                    obj["interest_rate"] = parameters.get("interest_rate")
                    lock_date_val = parameters.get("lock_date", date.today().isoformat())
                    obj["lock_date"] = lock_date_val
                    lock_days = parameters.get("lock_days", 30)
                    if isinstance(lock_date_val, str):
                        ld = date.fromisoformat(lock_date_val)
                    else:
                        ld = lock_date_val
                    from datetime import timedelta
                    obj["lock_expiration"] = (ld + timedelta(days=lock_days)).isoformat()
                elif action_name == "set_closing_date":
                    obj["closing_date"] = parameters.get("closing_date")
                obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"updated": True}

        elif effect == "update_document":
            obj = self._object_store.get("Document", {}).get(object_id)
            if obj:
                if action_name == "review_document":
                    obj["status"] = parameters.get("decision")
                    obj["review_notes"] = parameters.get("review_notes", "")
                    obj["reviewed_by"] = parameters.get("reviewed_by", "")
                obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"updated": True}

        elif effect == "update_campaign":
            obj = self._object_store.get("Campaign", {}).get(object_id)
            if obj:
                if action_name == "send_campaign":
                    obj["status"] = "active"
                    sd = parameters.get("scheduled_date")
                    if sd:
                        obj["status"] = "scheduled"
                        obj["scheduled_date"] = sd
                elif action_name == "pause_campaign":
                    obj["status"] = "paused"
                obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"updated": True}

        elif effect == "update_task":
            obj = self._object_store.get("Task", {}).get(object_id)
            if obj:
                if action_name == "complete_task":
                    obj["status"] = "completed"
                    obj["completed_at"] = datetime.now(timezone.utc).isoformat()
                elif action_name == "reassign_task":
                    obj["assigned_to"] = parameters.get("new_assignee_id")
                obj["updated_at"] = datetime.now(timezone.utc).isoformat()
            return {"updated": True}

        elif effect == "create_task":
            task_id = str(uuid.uuid4())
            task: dict[str, Any] = {
                "id": task_id,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if action_name == "create_follow_up_task":
                task.update({
                    "title": parameters.get("title", "Follow up"),
                    "description": parameters.get("description", ""),
                    "task_type": "follow_up",
                    "priority": parameters.get("priority", "medium"),
                    "due_date": parameters.get("due_date"),
                    "contact_id": object_id,
                    "assigned_to": parameters.get("assigned_to"),
                })
            elif action_name == "assign_loan_officer":
                task.update({
                    "title": "New contact assigned - initial outreach",
                    "task_type": "follow_up",
                    "priority": "high",
                    "contact_id": object_id,
                    "assigned_to": parameters.get("loan_officer_id"),
                })
            elif action_name == "update_loan_status":
                new_status = parameters.get("new_status", "")
                task.update({
                    "title": f"Loan status changed to {new_status} - review next steps",
                    "task_type": "general",
                    "priority": "medium",
                    "loan_id": object_id,
                })
            elif action_name == "escalate_loan":
                task.update({
                    "title": f"ESCALATION: {parameters.get('reason', 'unknown')}",
                    "task_type": "general",
                    "priority": "urgent",
                    "loan_id": object_id,
                    "assigned_to": parameters.get("escalate_to"),
                })
            elif action_name == "request_document":
                task.update({
                    "title": f"Document requested: {parameters.get('name', '')}",
                    "task_type": "document_review",
                    "priority": "high",
                    "loan_id": object_id,
                    "due_date": parameters.get("due_date"),
                })
            elif action_name == "review_document":
                decision = parameters.get("decision", "")
                if decision == "rejected":
                    task.update({
                        "title": "Re-upload required: document rejected",
                        "task_type": "document_review",
                        "priority": "high",
                    })
            elif action_name == "set_closing_date":
                task.update({
                    "title": f"Closing prep for {parameters.get('closing_date', '')}",
                    "task_type": "closing_prep",
                    "priority": "high",
                    "loan_id": object_id,
                })
            elif action_name == "log_call":
                outcome = parameters.get("outcome", "")
                if outcome == "callback_requested":
                    task.update({
                        "title": "Callback requested by contact",
                        "task_type": "follow_up",
                        "priority": "high",
                        "contact_id": object_id,
                    })
                else:
                    return {"created": False, "reason": "no task needed for this outcome"}
            else:
                task["title"] = f"Auto-generated task for {action_name}"

            self._object_store["Task"][task_id] = task
            return {"created": True, "task_id": task_id}

        elif effect == "create_document":
            doc_id = str(uuid.uuid4())
            doc = {
                "id": doc_id,
                "loan_id": object_id,
                "document_type": parameters.get("document_type"),
                "name": parameters.get("name", "Untitled Document"),
                "status": "requested",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._object_store["Document"][doc_id] = doc
            return {"created": True, "document_id": doc_id}

        elif effect == "log_communication":
            comm_id = str(uuid.uuid4())
            comm: dict[str, Any] = {
                "id": comm_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if action_name == "log_call":
                comm.update({
                    "contact_id": object_id,
                    "channel": "phone",
                    "direction": parameters.get("direction", "outbound"),
                    "duration_seconds": parameters.get("duration_seconds"),
                    "outcome": parameters.get("outcome"),
                    "body": parameters.get("notes", ""),
                })
            elif action_name == "assign_loan_officer":
                comm.update({
                    "contact_id": object_id,
                    "channel": "email",
                    "direction": "outbound",
                    "subject": "Loan officer assigned",
                    "outcome": "info_provided",
                })
            elif action_name == "lock_rate":
                loan = self._object_store.get("Loan", {}).get(object_id, {})
                comm.update({
                    "contact_id": loan.get("contact_id", ""),
                    "loan_id": object_id,
                    "channel": "email",
                    "direction": "outbound",
                    "subject": "Rate lock confirmation",
                    "outcome": "info_provided",
                })
            else:
                comm.update({
                    "contact_id": object_id if object_type == "Contact" else "",
                    "channel": "email",
                    "direction": "outbound",
                    "subject": f"Notification: {action_name}",
                })

            self._object_store["Communication"][comm_id] = comm
            return {"created": True, "communication_id": comm_id}

        elif effect == "create_communications":
            target_ids = parameters.get("target_contact_ids", [])
            created: list[str] = []
            for cid in target_ids:
                comm_id = str(uuid.uuid4())
                self._object_store["Communication"][comm_id] = {
                    "id": comm_id,
                    "contact_id": cid,
                    "channel": "email",
                    "direction": "outbound",
                    "campaign_id": object_id,
                    "subject": "Campaign message",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                created.append(comm_id)
            campaign = self._object_store.get("Campaign", {}).get(object_id, {})
            if campaign:
                campaign["sent_count"] = len(created)
            return {"created": True, "count": len(created)}

        elif effect == "link_campaign_contacts":
            target_ids = parameters.get("target_contact_ids", [])
            for cid in target_ids:
                await self.add_many_to_many_link("campaign_contacts", object_id, cid)
            return {"linked": len(target_ids)}

        elif effect == "notify_stakeholders":
            # In production this would send emails / push notifications.
            logger.info(
                "ontology_engine.notify_stakeholders",
                action=action_name,
                object_id=object_id,
            )
            return {"notified": True}

        elif effect == "check_loan_conditions":
            # After completing a task, check if all loan conditions are met
            task = self._object_store.get("Task", {}).get(object_id, {})
            loan_id = task.get("loan_id")
            if loan_id:
                open_tasks = [
                    t for t in self._object_store.get("Task", {}).values()
                    if t.get("loan_id") == loan_id
                    and t.get("status") not in ("completed", "cancelled")
                ]
                return {
                    "loan_id": loan_id,
                    "open_tasks_remaining": len(open_tasks),
                    "all_conditions_met": len(open_tasks) == 0,
                }
            return {"checked": False, "reason": "task has no loan_id"}

        else:
            logger.warning("ontology_engine.unknown_side_effect", effect=effect)
            return {"executed": False, "reason": f"unknown side effect: {effect}"}

    # -----------------------------------------------------------------------
    # Pipeline analytics (Palantir-style)
    # -----------------------------------------------------------------------

    async def get_pipeline_analytics(self) -> dict[str, Any]:
        """Compute top-level pipeline metrics across all loans and contacts."""
        loans = list(self._object_store.get("Loan", {}).values())
        contacts = list(self._object_store.get("Contact", {}).values())
        tasks = list(self._object_store.get("Task", {}).values())

        # Loan status distribution
        loan_by_status: dict[str, int] = defaultdict(int)
        total_volume = 0.0
        for loan in loans:
            status = loan.get("loan_status", "unknown")
            loan_by_status[status] += 1
            amt = loan.get("loan_amount")
            if amt is not None:
                total_volume += float(amt)

        # Contact status distribution
        contact_by_status: dict[str, int] = defaultdict(int)
        for contact in contacts:
            contact_by_status[contact.get("status", "unknown")] += 1

        # Task metrics
        open_tasks = sum(1 for t in tasks if t.get("status") in ("pending", "in_progress", "blocked"))
        overdue_tasks = 0
        today_str = date.today().isoformat()
        for t in tasks:
            if t.get("status") in ("pending", "in_progress") and t.get("due_date"):
                if str(t["due_date"]) < today_str:
                    overdue_tasks += 1

        # LO workload
        officers = list(self._object_store.get("LoanOfficer", {}).values())
        lo_pipeline: dict[str, int] = {}
        for lo in officers:
            lo_id = lo.get("id", "")
            count = sum(
                1 for ln in loans
                if ln.get("loan_officer_id") == lo_id
                and ln.get("loan_status") not in ("funded", "denied")
            )
            lo_pipeline[lo_id] = count

        return {
            "total_loans": len(loans),
            "total_contacts": len(contacts),
            "total_pipeline_volume": total_volume,
            "loan_status_distribution": dict(loan_by_status),
            "contact_status_distribution": dict(contact_by_status),
            "open_tasks": open_tasks,
            "overdue_tasks": overdue_tasks,
            "lo_pipeline_counts": lo_pipeline,
        }

    async def get_loan_funnel(self) -> dict[str, Any]:
        """Compute a loan pipeline funnel with counts and conversion rates."""
        loans = list(self._object_store.get("Loan", {}).values())
        stages = [
            "application",
            "processing",
            "underwriting",
            "conditions",
            "approval",
            "closing",
            "funded",
        ]
        stage_counts: dict[str, int] = {s: 0 for s in stages}
        denied_count = 0

        for loan in loans:
            status = loan.get("loan_status", "")
            if status == "denied":
                denied_count += 1
            elif status in stage_counts:
                stage_counts[status] += 1

        # Build funnel with conversion rates
        funnel: list[dict[str, Any]] = []
        prev_count: Optional[int] = None
        for stage in stages:
            count = stage_counts[stage]
            entry: dict[str, Any] = {"stage": stage, "count": count}
            if prev_count is not None and prev_count > 0:
                entry["conversion_rate"] = round(count / prev_count * 100, 1)
            else:
                entry["conversion_rate"] = 100.0
            funnel.append(entry)
            prev_count = count

        # Pull-through rate: funded / total
        total = len(loans)
        funded = stage_counts.get("funded", 0)
        pull_through = round(funded / total * 100, 1) if total > 0 else 0.0

        return {
            "funnel": funnel,
            "denied_count": denied_count,
            "total_loans": total,
            "funded_count": funded,
            "pull_through_rate": pull_through,
        }

    async def get_contact_lifecycle(self) -> dict[str, Any]:
        """Analyze the contact lifecycle with conversion metrics."""
        contacts = list(self._object_store.get("Contact", {}).values())
        stages = ["lead", "prospect", "active", "closed"]

        stage_counts: dict[str, int] = {s: 0 for s in stages}
        dead_count = 0
        source_dist: dict[str, int] = defaultdict(int)

        for contact in contacts:
            status = contact.get("status", "")
            if status == "dead":
                dead_count += 1
            elif status in stage_counts:
                stage_counts[status] += 1
            source = contact.get("source", "unknown")
            source_dist[source] += 1

        lifecycle: list[dict[str, Any]] = []
        prev: Optional[int] = None
        for stage in stages:
            count = stage_counts[stage]
            entry: dict[str, Any] = {"stage": stage, "count": count}
            if prev is not None and prev > 0:
                entry["conversion_rate"] = round(count / prev * 100, 1)
            else:
                entry["conversion_rate"] = 100.0
            lifecycle.append(entry)
            prev = count

        total = len(contacts)
        closed = stage_counts.get("closed", 0)

        return {
            "lifecycle": lifecycle,
            "dead_count": dead_count,
            "total_contacts": total,
            "closed_count": closed,
            "close_rate": round(closed / total * 100, 1) if total > 0 else 0.0,
            "source_distribution": dict(source_dist),
        }

    # -----------------------------------------------------------------------
    # Ontology graph export (for visualization / UI rendering)
    # -----------------------------------------------------------------------

    def export_ontology_graph(self) -> dict[str, Any]:
        """Export the ontology schema as a graph of nodes and edges.

        Each object type becomes a node; each link type becomes an edge.
        Useful for rendering the schema in a UI (e.g., D3, vis.js).
        """
        nodes: list[dict[str, Any]] = []
        for type_name, type_def in self._object_types.items():
            prop_names = list(type_def["properties"].keys())
            nodes.append({
                "id": type_name,
                "label": type_name,
                "properties": prop_names,
                "primary_key": type_def["primary_key"],
                "display_name_template": type_def.get("display_name", ""),
                "search_fields": type_def.get("search_fields", []),
                "object_count": len(self._object_store.get(type_name, {})),
            })

        edges: list[dict[str, Any]] = []
        for link_name, link_def in self._link_types.items():
            edges.append({
                "id": link_name,
                "from": link_def["from"],
                "to": link_def["to"],
                "label": link_def.get("label", link_name),
                "reverse_label": link_def.get("reverse_label", ""),
                "cardinality": link_def.get("cardinality", "one_to_many"),
            })

        action_nodes: list[dict[str, Any]] = []
        for act_name, act_def in self._actions.items():
            action_nodes.append({
                "id": act_name,
                "object_type": act_def["object_type"],
                "description": act_def.get("description", ""),
                "parameters": [p["name"] for p in act_def.get("parameters", [])],
            })

        return {
            "object_types": nodes,
            "link_types": edges,
            "actions": action_nodes,
        }

    # -----------------------------------------------------------------------
    # Status / stats
    # -----------------------------------------------------------------------

    def get_sync_status(self) -> dict[str, Any]:
        """Return last sync timestamps for each object type."""
        return {
            otype: ts.isoformat() for otype, ts in self._sync_status.items()
        }

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for the ontology store."""
        counts: dict[str, int] = {}
        for type_name in self._object_types:
            counts[type_name] = len(self._object_store.get(type_name, {}))

        return {
            "object_type_count": len(self._object_types),
            "link_type_count": len(self._link_types),
            "action_count": len(self._actions),
            "object_counts": counts,
            "total_objects": sum(counts.values()),
            "action_log_entries": len(self._action_log),
            "junction_entries": sum(
                len(v) for v in self._junction_store.values()
            ),
            "sync_status": self.get_sync_status(),
        }

    def get_action_log(
        self, limit: int = 50, action_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return recent action execution log entries."""
        entries = self._action_log
        if action_filter:
            entries = [e for e in entries if e.get("action") == action_filter]
        return list(reversed(entries[-limit:]))
