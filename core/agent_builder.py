"""
No-Code Agent Builder for MortgageFintechOS.
Allows users to create, configure, and deploy custom autonomous agents
without writing code — inspired by Palantir AIP Agent Builder.
Includes DynamicAgent runtime, template library, and guardrail enforcement.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from agents.base import AgentCategory, BaseAgent
from core.task_queue import Task

logger = structlog.get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT DEFINITION SCHEMA DEFAULTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CATEGORY_MAP = {
    "mortgage": AgentCategory.MORTGAGE,
    "engineering": AgentCategory.ENGINEERING,
    "growth": AgentCategory.MORTGAGE,
    "custom": AgentCategory.MORTGAGE,
}

STEP_TYPES = {"llm_call", "api_call", "data_lookup", "condition", "transform", "action"}
TRIGGER_TYPES = {"schedule", "webhook", "event", "manual", "ontology_change"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRE-BUILT TEMPLATES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AGENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "lead_nurture": {
        "name": "Lead Nurture Agent",
        "codename": "NURTURE",
        "description": "Automatically follows up with leads, sends personalized communications based on contact status and loan interest. Monitors lead aging and escalates stale leads.",
        "category": "mortgage",
        "division": "Mortgage Ops",
        "avatar": "target",
        "instructions": {
            "role": "You are an expert mortgage lead nurturing specialist focused on converting leads to active borrowers.",
            "goal": "Maximize lead-to-application conversion rate through timely, personalized follow-ups and intelligent engagement sequencing.",
            "constraints": [
                "Never contact a lead more than 3 times per week",
                "Always personalize communications using contact data",
                "Respect do-not-contact preferences",
                "Escalate leads that have been inactive for 14+ days",
            ],
            "expertise": ["lead scoring", "drip campaigns", "personalization", "conversion optimization"],
            "personality": "Professional, warm, and proactive. Uses data-driven insights to guide outreach timing.",
        },
        "skills": [
            {
                "skill_id": "score_lead",
                "name": "Score Lead",
                "description": "Calculate lead score based on engagement signals and demographic data",
                "trigger": "When a new lead is created or a lead's data is updated",
                "inputs": [{"name": "contact_id", "type": "string", "required": True, "description": "Contact ID to score"}],
                "outputs": [{"name": "score", "type": "integer", "description": "Lead score 0-100"}],
                "steps": [
                    {"step_id": "fetch", "type": "data_lookup", "config": {"object_type": "Contact", "filters": {"id": "{{contact_id}}"}, "fields": ["email", "phone", "source", "status", "credit_score", "annual_income"]}},
                    {"step_id": "analyze", "type": "llm_call", "config": {"system_prompt": "You are a lead scoring expert. Score this lead 0-100 based on their data. Return JSON: {score: int, factors: [str]}.", "user_prompt_template": "Score this lead: {{fetch.result}}", "temperature": 0.2, "max_tokens": 500}},
                    {"step_id": "save", "type": "action", "config": {"ontology_action": "update_contact_status", "parameters": {"new_status": "prospect"}}},
                ],
                "error_handling": "retry",
                "max_retries": 2,
            },
            {
                "skill_id": "follow_up",
                "name": "Send Follow-Up",
                "description": "Send a personalized follow-up communication to a lead",
                "trigger": "Scheduled daily or when lead score exceeds threshold",
                "inputs": [{"name": "contact_id", "type": "string", "required": True, "description": "Contact to follow up with"}],
                "outputs": [{"name": "communication_id", "type": "string", "description": "ID of logged communication"}],
                "steps": [
                    {"step_id": "lookup", "type": "data_lookup", "config": {"object_type": "Contact", "filters": {"id": "{{contact_id}}"}, "fields": ["first_name", "last_name", "email", "source", "tags"]}},
                    {"step_id": "history", "type": "data_lookup", "config": {"object_type": "Communication", "filters": {"contact_id": "{{contact_id}}"}, "fields": ["type", "subject", "sent_at"]}},
                    {"step_id": "draft", "type": "llm_call", "config": {"system_prompt": "Draft a personalized follow-up email. Be professional and warm. Reference their specific situation.", "user_prompt_template": "Contact: {{lookup.result}}\nPrevious communications: {{history.result}}\nDraft a follow-up.", "temperature": 0.7, "max_tokens": 1000}},
                    {"step_id": "send", "type": "action", "config": {"ontology_action": "log_call", "parameters": {"direction": "outbound", "subject": "Follow-up"}}},
                ],
                "error_handling": "skip",
                "max_retries": 1,
            },
        ],
        "triggers": [
            {"type": "schedule", "config": {"hour": 9, "minute": 0}},
            {"type": "event", "config": {"event_type": "contact.created"}},
        ],
        "required_integrations": ["total_expert", "llm"],
        "guardrails": {
            "max_actions_per_hour": 30,
            "require_approval_for": ["send_campaign"],
            "blocked_operations": ["delete_contact", "delete_loan"],
            "data_access_scope": ["Contact", "Communication", "Task"],
        },
    },
    "pipeline_monitor": {
        "name": "Pipeline Monitor Agent",
        "codename": "WATCHDOG",
        "description": "Watches loan status changes, alerts on stalled loans, suggests next actions, and identifies bottlenecks in the mortgage pipeline.",
        "category": "mortgage",
        "division": "Mortgage Ops",
        "avatar": "eye",
        "instructions": {
            "role": "You are a mortgage pipeline monitoring specialist that ensures loans move through the pipeline efficiently.",
            "goal": "Identify stalled loans, predict bottlenecks, and proactively suggest actions to keep the pipeline flowing.",
            "constraints": [
                "Never modify loan data without validation",
                "Alert before auto-escalating",
                "Follow FHA/VA/CONV processing timelines",
            ],
            "expertise": ["pipeline management", "bottleneck detection", "SLA monitoring", "predictive analytics"],
            "personality": "Analytical, precise, and proactive. Focuses on data-driven insights.",
        },
        "skills": [
            {
                "skill_id": "check_stalled",
                "name": "Check Stalled Loans",
                "description": "Identify loans that have been in the same stage longer than expected",
                "trigger": "Every 4 hours",
                "inputs": [],
                "outputs": [{"name": "stalled_loans", "type": "array", "description": "List of stalled loan IDs"}],
                "steps": [
                    {"step_id": "fetch_loans", "type": "data_lookup", "config": {"object_type": "Loan", "filters": {}, "fields": ["id", "loan_number", "loan_status", "loan_type", "updated_at"]}},
                    {"step_id": "analyze", "type": "llm_call", "config": {"system_prompt": "Analyze these loans for stalls. Flag any loan in the same stage for longer than expected. Return JSON with stalled loan IDs and recommended actions.", "user_prompt_template": "Loans: {{fetch_loans.result}}", "temperature": 0.2, "max_tokens": 2000}},
                ],
                "error_handling": "retry",
                "max_retries": 2,
            },
            {
                "skill_id": "pipeline_health",
                "name": "Pipeline Health Report",
                "description": "Generate a comprehensive pipeline health report with risk scores",
                "trigger": "Daily at 7:00 AM",
                "inputs": [],
                "outputs": [{"name": "report", "type": "object", "description": "Pipeline health report"}],
                "steps": [
                    {"step_id": "loans", "type": "data_lookup", "config": {"object_type": "Loan", "filters": {}, "fields": ["loan_status", "loan_amount", "dti", "credit_score", "loan_type"]}},
                    {"step_id": "analyze", "type": "llm_call", "config": {"system_prompt": "Generate a pipeline health report. Include: stage distribution, risk scores per stage, recommendations. Use the LPS formula.", "user_prompt_template": "Pipeline data: {{loans.result}}", "temperature": 0.3, "max_tokens": 3000}},
                ],
                "error_handling": "retry",
                "max_retries": 2,
            },
        ],
        "triggers": [
            {"type": "schedule", "config": {"hour": 7, "minute": 0}},
            {"type": "event", "config": {"event_type": "loan.status_changed"}},
        ],
        "required_integrations": ["total_expert", "llm"],
        "guardrails": {
            "max_actions_per_hour": 20,
            "require_approval_for": ["update_loan_status", "escalate_loan"],
            "blocked_operations": ["delete_loan"],
            "data_access_scope": ["Loan", "Contact", "Task", "Document"],
        },
    },
    "doc_collector": {
        "name": "Document Collector Agent",
        "codename": "COLLECTOR",
        "description": "Tracks missing documents per loan, sends reminders, validates completeness, and ensures all required docs are collected before underwriting.",
        "category": "mortgage",
        "division": "Mortgage Ops",
        "avatar": "folder",
        "instructions": {
            "role": "You are a mortgage document collection specialist ensuring all required documentation is gathered efficiently.",
            "goal": "Achieve 100% document completeness before underwriting submission by proactively tracking and requesting missing documents.",
            "constraints": [
                "Follow document checklists for each loan type (FHA/VA/CONV/USDA/JUMBO)",
                "Send no more than 2 reminders per document per week",
                "Escalate to loan officer if document is 7+ days overdue",
            ],
            "expertise": ["document classification", "FHA/VA/CONV checklists", "OCR validation", "completeness auditing"],
            "personality": "Thorough, organized, and persistent. Methodical in tracking documents.",
        },
        "skills": [
            {
                "skill_id": "check_completeness",
                "name": "Check Document Completeness",
                "description": "Check which documents are missing for a loan",
                "trigger": "When loan enters processing stage",
                "inputs": [{"name": "loan_id", "type": "string", "required": True, "description": "Loan to check"}],
                "outputs": [{"name": "missing_docs", "type": "array", "description": "List of missing documents"}],
                "steps": [
                    {"step_id": "loan", "type": "data_lookup", "config": {"object_type": "Loan", "filters": {"id": "{{loan_id}}"}, "fields": ["loan_type", "loan_status"]}},
                    {"step_id": "docs", "type": "data_lookup", "config": {"object_type": "Document", "filters": {"loan_id": "{{loan_id}}"}, "fields": ["name", "type", "status"]}},
                    {"step_id": "analyze", "type": "llm_call", "config": {"system_prompt": "You are a document completeness expert. Given the loan type, determine which required documents are missing. Return JSON with missing doc names and types.", "user_prompt_template": "Loan: {{loan.result}}\nExisting docs: {{docs.result}}", "temperature": 0.2, "max_tokens": 1500}},
                ],
                "error_handling": "retry",
                "max_retries": 2,
            },
        ],
        "triggers": [
            {"type": "event", "config": {"event_type": "loan.status_changed"}},
            {"type": "schedule", "config": {"hour": 8, "minute": 30}},
        ],
        "required_integrations": ["total_expert", "llm"],
        "guardrails": {
            "max_actions_per_hour": 40,
            "require_approval_for": [],
            "blocked_operations": ["delete_document", "delete_loan"],
            "data_access_scope": ["Loan", "Document", "Contact", "Task"],
        },
    },
    "rate_watch": {
        "name": "Rate Watch Agent",
        "codename": "RATEWATCH",
        "description": "Monitors interest rates, alerts contacts with rate locks expiring, and suggests refinance opportunities based on market conditions.",
        "category": "mortgage",
        "division": "Mortgage Ops",
        "avatar": "trending-up",
        "instructions": {
            "role": "You are a mortgage rate monitoring specialist tracking market conditions and lock expirations.",
            "goal": "Protect borrowers from rate lock expirations and identify refinance opportunities to maximize client value.",
            "constraints": [
                "Never provide rate guarantees",
                "Always include rate lock expiration dates in alerts",
                "Follow TILA-RESPA disclosure requirements",
            ],
            "expertise": ["rate markets", "lock management", "refinance analysis", "TILA-RESPA compliance"],
            "personality": "Alert, data-driven, and communicative. Focuses on timely notifications.",
        },
        "skills": [
            {
                "skill_id": "check_locks",
                "name": "Check Expiring Rate Locks",
                "description": "Find loans with rate locks expiring within 7 days",
                "trigger": "Daily at 6:00 AM",
                "inputs": [],
                "outputs": [{"name": "expiring_locks", "type": "array", "description": "Loans with expiring locks"}],
                "steps": [
                    {"step_id": "loans", "type": "data_lookup", "config": {"object_type": "Loan", "filters": {}, "fields": ["id", "loan_number", "lock_date", "lock_expiration", "interest_rate", "loan_amount", "contact_id"]}},
                    {"step_id": "analyze", "type": "llm_call", "config": {"system_prompt": "Identify loans with rate locks expiring within 7 days. Return JSON with loan details and recommended actions.", "user_prompt_template": "Today's date: {{today}}\nLoans: {{loans.result}}", "temperature": 0.2, "max_tokens": 2000}},
                ],
                "error_handling": "retry",
                "max_retries": 2,
            },
        ],
        "triggers": [{"type": "schedule", "config": {"hour": 6, "minute": 0}}],
        "required_integrations": ["total_expert", "llm"],
        "guardrails": {
            "max_actions_per_hour": 20,
            "require_approval_for": [],
            "blocked_operations": ["delete_loan", "delete_contact"],
            "data_access_scope": ["Loan", "Contact", "Communication"],
        },
    },
    "compliance_checker": {
        "name": "Compliance Checker Agent",
        "codename": "COMPLIANCE",
        "description": "Validates loan data against FHA/VA/CONV requirements, flags issues before underwriting, and ensures regulatory compliance.",
        "category": "mortgage",
        "division": "Mortgage Ops",
        "avatar": "shield",
        "instructions": {
            "role": "You are a mortgage compliance expert specializing in FHA HB 4000.1, VA Lender's Handbook, Fannie Mae and Freddie Mac guidelines.",
            "goal": "Ensure 100% regulatory compliance before loan submission to underwriting. Catch issues early to prevent denials and buybacks.",
            "constraints": [
                "Always cite specific regulation sections when flagging issues",
                "Never approve a loan that violates regulatory requirements",
                "Follow DTI limits: FHA 57%, VA none (compensating factors), CONV 50%",
                "Verify credit score minimums: FHA 580 (3.5% down), VA 620 (lender overlay), CONV 620",
            ],
            "expertise": ["FHA HB 4000.1", "VA Lender's Handbook", "FNMA selling guide", "FHLMC selling guide", "HMDA compliance"],
            "personality": "Meticulous, thorough, and regulatory-focused. No shortcuts on compliance.",
        },
        "skills": [
            {
                "skill_id": "validate_loan",
                "name": "Validate Loan Compliance",
                "description": "Run full compliance check on a loan against applicable guidelines",
                "trigger": "When loan enters underwriting or conditions stage",
                "inputs": [{"name": "loan_id", "type": "string", "required": True, "description": "Loan to validate"}],
                "outputs": [{"name": "issues", "type": "array", "description": "List of compliance issues found"}],
                "steps": [
                    {"step_id": "loan", "type": "data_lookup", "config": {"object_type": "Loan", "filters": {"id": "{{loan_id}}"}, "fields": ["loan_type", "loan_amount", "dti", "ltv", "credit_score", "property_type"]}},
                    {"step_id": "docs", "type": "data_lookup", "config": {"object_type": "Document", "filters": {"loan_id": "{{loan_id}}"}, "fields": ["type", "status"]}},
                    {"step_id": "check", "type": "llm_call", "config": {"system_prompt": "You are a mortgage compliance validator. Check this loan against FHA/VA/CONV guidelines. For each issue, cite the specific regulation section. Return JSON: {compliant: bool, issues: [{field, issue, regulation, severity}]}.", "user_prompt_template": "Loan data: {{loan.result}}\nDocuments: {{docs.result}}", "temperature": 0.1, "max_tokens": 3000}},
                ],
                "error_handling": "abort",
                "max_retries": 1,
            },
        ],
        "triggers": [{"type": "event", "config": {"event_type": "loan.status_changed"}}],
        "required_integrations": ["total_expert", "llm"],
        "guardrails": {
            "max_actions_per_hour": 50,
            "require_approval_for": [],
            "blocked_operations": ["delete_loan", "update_loan_status"],
            "data_access_scope": ["Loan", "Document", "Contact"],
        },
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DYNAMIC AGENT (Runtime for no-code agents)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DynamicAgent(BaseAgent):
    """Runtime agent that executes no-code agent definitions."""

    def __init__(self, definition: dict[str, Any], ontology_engine: Any = None) -> None:
        category = CATEGORY_MAP.get(definition.get("category", "custom"), AgentCategory.MORTGAGE)
        super().__init__(name=definition.get("codename", "CUSTOM"), category=category)
        self._definition = definition
        self._ontology = ontology_engine
        self._action_count = 0
        self._action_window_start = datetime.now(timezone.utc)
        self._execution_log: list[dict[str, Any]] = []
        self._log = logger.bind(agent=definition.get("codename", "CUSTOM"))

    async def execute(self, task: Task) -> dict[str, Any]:
        skill = self._match_skill(task)
        if not skill:
            return {"error": f"No matching skill for task: {task.action}", "agent": self.name}
        self._log.info("executing_skill", skill=skill["name"], task_action=task.action)
        try:
            result = await self._execute_skill(skill, task.payload)
            self._execution_log.append({
                "skill": skill["name"],
                "task": task.action,
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"success": True, "skill": skill["name"], "result": result, "agent": self.name}
        except Exception as e:
            self._log.error("skill_execution_failed", skill=skill["name"], error=str(e))
            self._execution_log.append({
                "skill": skill["name"],
                "task": task.action,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if skill.get("error_handling") == "abort":
                raise
            return {"success": False, "skill": skill["name"], "error": str(e), "agent": self.name}

    async def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": self.status.value,
            "definition_name": self._definition.get("name", ""),
            "skills_count": len(self._definition.get("skills", [])),
            "actions_this_hour": self._action_count,
            "max_actions_per_hour": self._definition.get("guardrails", {}).get("max_actions_per_hour", 50),
            "executions": len(self._execution_log),
            "enabled": self._definition.get("enabled", True),
        }

    def _match_skill(self, task: Task) -> dict[str, Any] | None:
        skills = self._definition.get("skills", [])
        for skill in skills:
            if task.action == skill.get("skill_id") or task.action == skill.get("name"):
                return skill
        if skills:
            return skills[0]
        return None

    async def _execute_skill(self, skill: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        if not self._check_guardrails():
            return {"error": "Rate limit exceeded for this agent"}
        context: dict[str, Any] = {"inputs": inputs}
        results: dict[str, Any] = {}
        for step in skill.get("steps", []):
            step_id = step.get("step_id", "unknown")
            step_result = await self._execute_step(step, context)
            results[step_id] = step_result
            context[step_id] = step_result
        self._action_count += 1
        return results

    async def _execute_step(self, step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        step_type = step.get("type", "")
        config = step.get("config", {})
        if step_type == "llm_call":
            return await self._step_llm_call(config, context)
        elif step_type == "data_lookup":
            return await self._step_data_lookup(config, context)
        elif step_type == "action":
            return await self._step_action(config, context)
        elif step_type == "condition":
            return await self._step_condition(config, context)
        elif step_type == "transform":
            return await self._step_transform(config, context)
        elif step_type == "api_call":
            return await self._step_api_call(config, context)
        return {"error": f"Unknown step type: {step_type}"}

    async def _step_llm_call(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        system_prompt = config.get("system_prompt", "")
        user_template = config.get("user_prompt_template", "")
        user_prompt = self._interpolate_template(user_template, context)
        temperature = config.get("temperature", 0.3)
        max_tokens = config.get("max_tokens", 4096)
        if self._llm:
            response = await self.llm_complete(
                action="dynamic_skill",
                system_prompt=self._build_system_prompt() + "\n\n" + system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return {"result": response}
        return {"result": f"[LLM not available] System: {system_prompt[:100]}... | User: {user_prompt[:100]}..."}

    async def _step_data_lookup(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        object_type = config.get("object_type", "")
        filters = config.get("filters", {})
        resolved_filters = {}
        for k, v in filters.items():
            resolved_filters[k] = self._interpolate_template(str(v), context)
        if self._ontology:
            if "id" in resolved_filters:
                obj = await self._ontology.get_object(object_type, resolved_filters["id"])
                return {"result": obj or {}}
            result = await self._ontology.list_objects(object_type, filters=resolved_filters)
            return {"result": result.get("data", [])}
        return {"result": [], "note": "Ontology not connected"}

    async def _step_action(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        action_name = config.get("ontology_action", "")
        params = config.get("parameters", {})
        resolved_params = {}
        for k, v in params.items():
            resolved_params[k] = self._interpolate_template(str(v), context)
        guardrails = self._definition.get("guardrails", {})
        if action_name in guardrails.get("require_approval_for", []):
            return {"result": "Action requires approval", "action": action_name, "pending_approval": True}
        if action_name in guardrails.get("blocked_operations", []):
            return {"result": "Action is blocked by guardrails", "action": action_name, "blocked": True}
        if self._ontology:
            object_id = context.get("inputs", {}).get("contact_id") or context.get("inputs", {}).get("loan_id", "")
            result = await self._ontology.execute_action(action_name, object_id, resolved_params)
            return {"result": result}
        return {"result": "Ontology not connected", "action": action_name}

    async def _step_condition(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        expression = config.get("expression", "true")
        resolved = self._interpolate_template(expression, context)
        result = resolved.lower() not in ("false", "0", "none", "null", "")
        return {"result": result, "expression": expression}

    async def _step_transform(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        operation = config.get("operation", "passthrough")
        input_field = config.get("input_field", "")
        value = context.get(input_field, {}).get("result", "")
        if operation == "json_parse" and isinstance(value, str):
            try:
                return {"result": json.loads(value)}
            except json.JSONDecodeError:
                return {"result": value}
        return {"result": value}

    async def _step_api_call(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        integration = config.get("integration", "")
        method = config.get("method", "")
        return {"result": f"API call to {integration}.{method}", "note": "External API calls execute via integration layer"}

    def _check_guardrails(self) -> bool:
        now = datetime.now(timezone.utc)
        elapsed = (now - self._action_window_start).total_seconds()
        if elapsed >= 3600:
            self._action_count = 0
            self._action_window_start = now
        max_per_hour = self._definition.get("guardrails", {}).get("max_actions_per_hour", 50)
        return self._action_count < max_per_hour

    def _build_system_prompt(self) -> str:
        instructions = self._definition.get("instructions", {})
        parts = [
            instructions.get("role", "You are an AI agent."),
            f"\nGOAL: {instructions.get('goal', '')}",
        ]
        constraints = instructions.get("constraints", [])
        if constraints:
            parts.append("\nCONSTRAINTS:")
            for c in constraints:
                parts.append(f"- {c}")
        expertise = instructions.get("expertise", [])
        if expertise:
            parts.append(f"\nEXPERTISE: {', '.join(expertise)}")
        personality = instructions.get("personality", "")
        if personality:
            parts.append(f"\nSTYLE: {personality}")
        return "\n".join(parts)

    def _interpolate_template(self, template: str, context: dict[str, Any]) -> str:
        def replacer(match: re.Match[str]) -> str:
            path = match.group(1)
            parts = path.split(".")
            current: Any = context
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part, "")
                else:
                    return match.group(0)
            return str(current) if current else ""
        return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replacer, template)

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info.update({
            "definition_name": self._definition.get("name", ""),
            "description": self._definition.get("description", ""),
            "category": self._definition.get("category", "custom"),
            "division": self._definition.get("division", ""),
            "skills": [s.get("name", "") for s in self._definition.get("skills", [])],
            "triggers": self._definition.get("triggers", []),
            "guardrails": self._definition.get("guardrails", {}),
            "execution_count": len(self._execution_log),
            "dynamic": True,
        })
        return info


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentBuilder:
    """No-code agent builder — create, deploy, and manage custom agents."""

    def __init__(self, ontology_engine: Any = None, data_dir: str = "data") -> None:
        self._definitions: dict[str, dict[str, Any]] = {}
        self._running_agents: dict[str, DynamicAgent] = {}
        self._ontology = ontology_engine
        self._data_dir = data_dir
        self._log = logger.bind(component="agent_builder")

    # ── CRUD ──

    def create_agent(self, definition: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate_definition(definition)
        if not validation["valid"]:
            return {"error": "Invalid definition", "errors": validation["errors"]}
        agent_id = str(uuid.uuid4())
        definition["agent_id"] = agent_id
        definition.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        definition.setdefault("updated_at", datetime.now(timezone.utc).isoformat())
        definition.setdefault("version", 1)
        definition.setdefault("enabled", True)
        self._definitions[agent_id] = definition
        self._log.info("agent_created", agent_id=agent_id, name=definition.get("name", ""))
        return {"agent_id": agent_id, "name": definition.get("name", ""), "created": True}

    def update_agent(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if agent_id not in self._definitions:
            return {"error": f"Agent {agent_id} not found"}
        defn = self._definitions[agent_id]
        for key, value in updates.items():
            if key not in ("agent_id", "created_at"):
                defn[key] = value
        defn["updated_at"] = datetime.now(timezone.utc).isoformat()
        defn["version"] = defn.get("version", 0) + 1
        return {"agent_id": agent_id, "updated": True, "version": defn["version"]}

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._running_agents:
            self._running_agents[agent_id].stop()
            del self._running_agents[agent_id]
        if agent_id in self._definitions:
            del self._definitions[agent_id]
            self._log.info("agent_deleted", agent_id=agent_id)
            return True
        return False

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return self._definitions.get(agent_id)

    def list_agents(self, category: str | None = None) -> list[dict[str, Any]]:
        agents = list(self._definitions.values())
        if category:
            agents = [a for a in agents if a.get("category") == category]
        return [
            {
                "agent_id": a.get("agent_id", ""),
                "name": a.get("name", ""),
                "codename": a.get("codename", ""),
                "category": a.get("category", ""),
                "division": a.get("division", ""),
                "description": a.get("description", ""),
                "enabled": a.get("enabled", True),
                "version": a.get("version", 1),
                "skills_count": len(a.get("skills", [])),
                "triggers_count": len(a.get("triggers", [])),
                "running": a.get("agent_id", "") in self._running_agents,
                "created_at": a.get("created_at", ""),
            }
            for a in agents
        ]

    # ── Lifecycle ──

    async def deploy_agent(self, agent_id: str) -> DynamicAgent | None:
        defn = self._definitions.get(agent_id)
        if not defn:
            return None
        agent = DynamicAgent(defn, ontology_engine=self._ontology)
        agent._ontology = self._ontology
        self._running_agents[agent_id] = agent
        self._log.info("agent_deployed", agent_id=agent_id, codename=defn.get("codename", ""))
        return agent

    async def undeploy_agent(self, agent_id: str) -> bool:
        if agent_id in self._running_agents:
            self._running_agents[agent_id].stop()
            del self._running_agents[agent_id]
            self._log.info("agent_undeployed", agent_id=agent_id)
            return True
        return False

    async def restart_agent(self, agent_id: str) -> DynamicAgent | None:
        await self.undeploy_agent(agent_id)
        return await self.deploy_agent(agent_id)

    def get_running_agent(self, agent_id: str) -> DynamicAgent | None:
        return self._running_agents.get(agent_id)

    # ── Skill Management ──

    def add_skill(self, agent_id: str, skill: dict[str, Any]) -> dict[str, Any]:
        defn = self._definitions.get(agent_id)
        if not defn:
            return {"error": f"Agent {agent_id} not found"}
        skill.setdefault("skill_id", str(uuid.uuid4())[:8])
        defn.setdefault("skills", []).append(skill)
        return {"agent_id": agent_id, "skill_id": skill["skill_id"], "added": True}

    def update_skill(self, agent_id: str, skill_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        defn = self._definitions.get(agent_id)
        if not defn:
            return {"error": f"Agent {agent_id} not found"}
        for skill in defn.get("skills", []):
            if skill.get("skill_id") == skill_id:
                skill.update(updates)
                return {"agent_id": agent_id, "skill_id": skill_id, "updated": True}
        return {"error": f"Skill {skill_id} not found"}

    def remove_skill(self, agent_id: str, skill_id: str) -> bool:
        defn = self._definitions.get(agent_id)
        if not defn:
            return False
        skills = defn.get("skills", [])
        defn["skills"] = [s for s in skills if s.get("skill_id") != skill_id]
        return len(defn["skills"]) < len(skills)

    # ── Templates ──

    def get_templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template_id": tid,
                "name": t["name"],
                "codename": t["codename"],
                "description": t["description"],
                "category": t["category"],
                "skills_count": len(t.get("skills", [])),
                "triggers_count": len(t.get("triggers", [])),
            }
            for tid, t in AGENT_TEMPLATES.items()
        ]

    def create_from_template(self, template_name: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        template = AGENT_TEMPLATES.get(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}
        import copy
        definition = copy.deepcopy(template)
        if overrides:
            for key, value in overrides.items():
                definition[key] = value
        return self.create_agent(definition)

    # ── Validation ──

    def validate_definition(self, definition: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        if not definition.get("name"):
            errors.append("Missing 'name'")
        if not definition.get("codename"):
            errors.append("Missing 'codename'")
        codename = definition.get("codename", "")
        if codename and not codename.isupper():
            errors.append("'codename' must be uppercase")
        category = definition.get("category", "")
        if category and category not in ("mortgage", "engineering", "growth", "custom"):
            errors.append(f"Invalid category: {category}")
        for skill in definition.get("skills", []):
            if not skill.get("name"):
                errors.append("Skill missing 'name'")
            for step in skill.get("steps", []):
                if step.get("type") not in STEP_TYPES:
                    errors.append(f"Invalid step type: {step.get('type')}")
        for trigger in definition.get("triggers", []):
            if trigger.get("type") not in TRIGGER_TYPES:
                errors.append(f"Invalid trigger type: {trigger.get('type')}")
        return {"valid": len(errors) == 0, "errors": errors}

    # ── Persistence ──

    async def save_definitions(self) -> None:
        path = os.path.join(self._data_dir, "agent_definitions.json")
        os.makedirs(self._data_dir, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._definitions, f, indent=2, default=str)
        self._log.info("definitions_saved", count=len(self._definitions), path=path)

    async def load_definitions(self) -> None:
        path = os.path.join(self._data_dir, "agent_definitions.json")
        if os.path.exists(path):
            with open(path) as f:
                self._definitions = json.load(f)
            self._log.info("definitions_loaded", count=len(self._definitions), path=path)

    # ── Export/Import ──

    def export_agent(self, agent_id: str) -> str:
        defn = self._definitions.get(agent_id)
        if not defn:
            return json.dumps({"error": f"Agent {agent_id} not found"})
        return json.dumps(defn, indent=2, default=str)

    def import_agent(self, json_str: str) -> dict[str, Any]:
        try:
            definition = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        definition.pop("agent_id", None)
        return self.create_agent(definition)

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        return {
            "total_definitions": len(self._definitions),
            "running_agents": len(self._running_agents),
            "templates_available": len(AGENT_TEMPLATES),
            "running_agent_ids": list(self._running_agents.keys()),
            "categories": list(set(d.get("category", "") for d in self._definitions.values())),
        }
