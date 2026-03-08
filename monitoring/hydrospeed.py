"""Hydrospeed Ontology Engine for MortgageFintechOS.

Live ontology that maps agent relationships, data flows, integration
dependencies, and operational patterns. Inspired by enterprise-grade
decision intelligence platforms. Provides real-time graph visualization
data and agent proposals based on codebase analysis.
"""

from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# --- Ontology Graph Definition ---
# Nodes represent agents, integrations, data sources, and outputs.
# Edges represent data flows, dependencies, and communication paths.

AGENT_ONTOLOGY = {
    "nodes": [
        # Mortgage Operations Division
        {"id": "DIEGO", "type": "agent", "division": "mortgage_ops", "label": "DIEGO", "role": "Pipeline Orchestration",
         "capabilities": ["pipeline_triage", "stage_tracking", "priority_routing", "health_monitoring"],
         "inputs": ["loan_applications", "wispr_notes", "pipeline_data"],
         "outputs": ["pipeline_reports", "stage_updates", "github_issues"]},
        {"id": "MARTIN", "type": "agent", "division": "mortgage_ops", "label": "MARTIN", "role": "Document Intelligence",
         "capabilities": ["document_classification", "completeness_audit", "text_extraction", "compliance_check"],
         "inputs": ["drive_documents", "wispr_notes", "uploaded_files"],
         "outputs": ["classifications", "audit_reports", "notion_pages"]},
        {"id": "NOVA", "type": "agent", "division": "mortgage_ops", "label": "NOVA", "role": "Income & DTI Analysis",
         "capabilities": ["income_calculation", "dti_analysis", "employment_verification", "self_employed_analysis"],
         "inputs": ["w2_docs", "paystubs", "tax_returns", "bank_statements"],
         "outputs": ["income_reports", "dti_ratios", "notion_results"]},
        {"id": "JARVIS", "type": "agent", "division": "mortgage_ops", "label": "JARVIS", "role": "Condition Resolution",
         "capabilities": ["condition_tracking", "loe_drafting", "compliance_verification", "condition_clearing"],
         "inputs": ["underwriting_conditions", "loan_data", "wispr_notes"],
         "outputs": ["loe_documents", "condition_updates", "compliance_reports"]},

        # Engineering Division
        {"id": "ATLAS", "type": "agent", "division": "engineering", "label": "ATLAS", "role": "Full-Stack Engineering",
         "capabilities": ["api_generation", "feature_building", "database_migrations", "component_scaffolding"],
         "inputs": ["feature_requests", "api_specs", "codebase"],
         "outputs": ["github_code", "pull_requests", "branches"]},
        {"id": "CIPHER", "type": "agent", "division": "engineering", "label": "CIPHER", "role": "Security Engineering",
         "capabilities": ["owasp_scanning", "compliance_auditing", "encryption_audit", "vulnerability_patching"],
         "inputs": ["github_security_alerts", "codebase", "cve_databases"],
         "outputs": ["security_reports", "patch_prs", "compliance_results"]},
        {"id": "FORGE", "type": "agent", "division": "engineering", "label": "FORGE", "role": "DevOps Engineering",
         "capabilities": ["deployment", "rollback", "pipeline_creation", "secret_rotation"],
         "inputs": ["deployment_requests", "workflow_configs"],
         "outputs": ["workflow_runs", "deployment_status", "rotation_issues"]},
        {"id": "NEXUS", "type": "agent", "division": "engineering", "label": "NEXUS", "role": "Code Quality",
         "capabilities": ["pr_review", "test_generation", "debt_analysis", "refactoring"],
         "inputs": ["pull_requests", "source_code", "commit_history"],
         "outputs": ["reviews", "test_files", "refactored_code"]},
        {"id": "STORM", "type": "agent", "division": "engineering", "label": "STORM", "role": "Data Engineering",
         "capabilities": ["etl_building", "hmda_reporting", "uldd_export", "query_optimization"],
         "inputs": ["loan_data", "regulatory_requirements"],
         "outputs": ["etl_pipelines", "hmda_reports", "uldd_exports"]},

        # Intelligence Division
        {"id": "SENTINEL", "type": "agent", "division": "intelligence", "label": "SENTINEL", "role": "System Intelligence",
         "capabilities": ["anomaly_detection", "pattern_analysis", "threat_assessment"],
         "inputs": ["system_metrics", "agent_logs", "health_data"],
         "outputs": ["intelligence_reports", "threat_alerts"]},

        # Growth Ops Division
        {"id": "HUNTER", "type": "agent", "division": "growth_ops", "label": "HUNTER", "role": "Lead Generation",
         "capabilities": ["github_scanning", "hn_scanning", "reddit_scanning", "lead_scoring"],
         "inputs": ["web_sources", "social_platforms"],
         "outputs": ["scored_leads", "prospect_profiles"]},
        {"id": "HERALD", "type": "agent", "division": "growth_ops", "label": "HERALD", "role": "Content Marketing",
         "capabilities": ["content_generation", "seo_optimization", "social_posts"],
         "inputs": ["market_data", "product_features", "leads"],
         "outputs": ["blog_posts", "social_content", "newsletters"]},
        {"id": "AMBASSADOR", "type": "agent", "division": "growth_ops", "label": "AMBASSADOR", "role": "Community Engagement",
         "capabilities": ["community_monitoring", "engagement_responses", "relationship_building"],
         "inputs": ["community_signals", "leads", "content"],
         "outputs": ["engagement_metrics", "relationships", "referrals"]},

        # Integration Nodes
        {"id": "github", "type": "integration", "label": "GitHub", "role": "Code & Issues"},
        {"id": "notion", "type": "integration", "label": "Notion", "role": "Knowledge Base"},
        {"id": "gdrive", "type": "integration", "label": "Google Drive", "role": "Document Source"},
        {"id": "wispr", "type": "integration", "label": "Wispr Flow", "role": "Voice Input"},
        {"id": "llm", "type": "integration", "label": "LLM Router", "role": "AI Intelligence"},
        {"id": "ghost", "type": "integration", "label": "GHOST OSINT", "role": "Entity Verification"},
        {"id": "pentagi", "type": "integration", "label": "PentAGI", "role": "Security Testing"},
        {"id": "paperclip", "type": "integration", "label": "Paperclip", "role": "Cost Governance"},
        {"id": "browser", "type": "integration", "label": "Browser", "role": "Web Scraping"},

        # Data Source Nodes
        {"id": "loan_apps", "type": "data_source", "label": "Loan Applications"},
        {"id": "borrower_docs", "type": "data_source", "label": "Borrower Documents"},
        {"id": "voice_notes", "type": "data_source", "label": "Voice Notes"},
        {"id": "codebase", "type": "data_source", "label": "Repository Code"},
    ],
    "edges": [
        # Mortgage workflow chain
        {"from": "loan_apps", "to": "DIEGO", "type": "data_flow", "label": "ingests"},
        {"from": "borrower_docs", "to": "MARTIN", "type": "data_flow", "label": "classifies"},
        {"from": "MARTIN", "to": "NOVA", "type": "dependency", "label": "classified docs"},
        {"from": "NOVA", "to": "JARVIS", "type": "dependency", "label": "income/dti results"},
        {"from": "DIEGO", "to": "MARTIN", "type": "orchestration", "label": "triggers audit"},

        # Voice flow
        {"from": "voice_notes", "to": "wispr", "type": "data_flow", "label": "transcribes"},
        {"from": "wispr", "to": "MARTIN", "type": "routing", "label": "routes notes"},
        {"from": "wispr", "to": "DIEGO", "type": "routing", "label": "routes notes"},

        # Drive flow
        {"from": "gdrive", "to": "MARTIN", "type": "data_flow", "label": "imports docs"},

        # Engineering → GitHub
        {"from": "ATLAS", "to": "github", "type": "writes", "label": "creates code"},
        {"from": "CIPHER", "to": "github", "type": "reads_writes", "label": "scans + patches"},
        {"from": "FORGE", "to": "github", "type": "writes", "label": "triggers CI/CD"},
        {"from": "NEXUS", "to": "github", "type": "reads_writes", "label": "reviews PRs"},
        {"from": "STORM", "to": "github", "type": "writes", "label": "commits configs"},

        # Notion sync
        {"from": "MARTIN", "to": "notion", "type": "writes", "label": "audit reports"},
        {"from": "NOVA", "to": "notion", "type": "writes", "label": "income results"},
        {"from": "CIPHER", "to": "notion", "type": "writes", "label": "security reports"},

        # LLM usage
        {"from": "llm", "to": "ATLAS", "type": "powers", "label": "code generation"},
        {"from": "llm", "to": "CIPHER", "type": "powers", "label": "security analysis"},
        {"from": "llm", "to": "FORGE", "type": "powers", "label": "pipeline YAML"},
        {"from": "llm", "to": "NEXUS", "type": "powers", "label": "code review"},
        {"from": "llm", "to": "STORM", "type": "powers", "label": "data analysis"},

        # Growth Ops
        {"from": "browser", "to": "HUNTER", "type": "powers", "label": "web scraping"},
        {"from": "browser", "to": "HERALD", "type": "powers", "label": "content research"},
        {"from": "browser", "to": "AMBASSADOR", "type": "powers", "label": "engagement"},
        {"from": "HUNTER", "to": "HERALD", "type": "dependency", "label": "leads"},
        {"from": "HERALD", "to": "AMBASSADOR", "type": "dependency", "label": "content"},

        # Intelligence
        {"from": "SENTINEL", "to": "ghost", "type": "reads", "label": "entity data"},
        {"from": "SENTINEL", "to": "pentagi", "type": "reads", "label": "vuln data"},

        # Governance
        {"from": "paperclip", "to": "ATLAS", "type": "governs", "label": "cost control"},
        {"from": "paperclip", "to": "CIPHER", "type": "governs", "label": "cost control"},
        {"from": "paperclip", "to": "FORGE", "type": "governs", "label": "cost control"},
    ],
}

# --- Expert Tips & Proposals ---

EXPERT_TIPS = [
    {
        "category": "scheduling",
        "severity": "high",
        "title": "Stagger Resource-Heavy Jobs",
        "tip": "CIPHER security scan (03:00) and Drive import (05:30) both make many API calls. Keep them 2+ hours apart to avoid rate limiting. Current schedule is correctly staggered.",
        "applies_to": ["CIPHER", "MARTIN"],
    },
    {
        "category": "scheduling",
        "severity": "medium",
        "title": "Run Drive Import Before Document Audit",
        "tip": "Drive import (05:30) runs before MARTIN audit (06:00) so new documents are available for classification. This dependency is correctly ordered.",
        "applies_to": ["MARTIN"],
    },
    {
        "category": "scheduling",
        "severity": "medium",
        "title": "Chain Income Recalc After Audit",
        "tip": "NOVA income recalculation (06:30) runs after MARTIN audit (06:00) so newly classified W-2s and paystubs are available. Keep this ordering.",
        "applies_to": ["NOVA", "MARTIN"],
    },
    {
        "category": "cost_optimization",
        "severity": "high",
        "title": "Batch LLM Calls During Off-Peak",
        "tip": "Engineering agents (ATLAS, CIPHER, FORGE, NEXUS, STORM) use LLM for code generation. Schedule heavy code gen tasks during off-peak hours (22:00-06:00) when API costs are lower and rate limits less contended.",
        "applies_to": ["ATLAS", "CIPHER", "FORGE", "NEXUS", "STORM"],
    },
    {
        "category": "cost_optimization",
        "severity": "medium",
        "title": "Use Paperclip Budget Controls",
        "tip": "Set daily token budgets per agent via Paperclip. Recommended: ATLAS 50K tokens/day, CIPHER 30K, NEXUS 40K. This prevents runaway LLM costs from recursive code generation.",
        "applies_to": ["ATLAS", "CIPHER", "NEXUS"],
    },
    {
        "category": "safety",
        "severity": "critical",
        "title": "Deletion Guardrails Are Active",
        "tip": "Two-layer deletion blocking is permanently enabled. GitHubClient blocks delete_branch/delete_file at the API layer. BaseAgent.safe_github() blocks any method containing 'delete'. No override exists. Monitor /api/safety/blocked for attempted violations.",
        "applies_to": ["ATLAS", "CIPHER", "FORGE", "NEXUS", "STORM"],
    },
    {
        "category": "safety",
        "severity": "high",
        "title": "Review PR Merges Manually",
        "tip": "NEXUS can post reviews and FORGE can merge PRs. Consider requiring human approval before auto-merge. Use GitHub branch protection rules as an additional guardrail.",
        "applies_to": ["NEXUS", "FORGE"],
    },
    {
        "category": "monitoring",
        "severity": "high",
        "title": "Watch Error Rate Threshold",
        "tip": "Health monitor triggers alerts when error rate exceeds 10% over 5 minutes. If you see repeated failures from one agent, check its integration credentials (GitHub token, Notion API key, etc.).",
        "applies_to": ["ALL"],
    },
    {
        "category": "monitoring",
        "severity": "medium",
        "title": "Heartbeat Timeout = 60 Seconds",
        "tip": "Agents must heartbeat within 60 seconds or they are flagged as hung. LLM-heavy agents (ATLAS, NEXUS) may need longer timeouts if generating large code blocks. Increase heartbeat_timeout_seconds in settings if you see false positives.",
        "applies_to": ["ATLAS", "NEXUS"],
    },
    {
        "category": "workflow",
        "severity": "high",
        "title": "Unified Document Pipeline",
        "tip": "Optimal flow: Google Drive import -> MARTIN classifies -> NOVA analyzes income docs -> JARVIS tracks conditions -> DIEGO updates pipeline. Wire Wispr voice notes to MARTIN first for classification before routing to specialized agents.",
        "applies_to": ["DIEGO", "MARTIN", "NOVA", "JARVIS"],
    },
    {
        "category": "workflow",
        "severity": "medium",
        "title": "Engineering Agent Chain",
        "tip": "Recommended code workflow: ATLAS creates feature branch + code -> NEXUS reviews PR -> FORGE triggers CI -> CIPHER scans security -> NEXUS approves. Automate this by submitting tasks in sequence.",
        "applies_to": ["ATLAS", "NEXUS", "FORGE", "CIPHER"],
    },
    {
        "category": "scaling",
        "severity": "medium",
        "title": "Growth Ops Independent Pipeline",
        "tip": "HUNTER, HERALD, AMBASSADOR run independently on browser client. They do not block mortgage ops or engineering. Keep their tasks at LOW priority to avoid starving critical loan processing.",
        "applies_to": ["HUNTER", "HERALD", "AMBASSADOR"],
    },
    {
        "category": "scaling",
        "severity": "low",
        "title": "Queue Backlog Threshold",
        "tip": "Alert fires when queue exceeds 50 pending tasks. If you regularly hit this, consider increasing agent concurrency or adding task deduplication for repeated schedule triggers.",
        "applies_to": ["ALL"],
    },
    {
        "category": "resilience",
        "severity": "high",
        "title": "Watchdog Auto-Recovery",
        "tip": "The watchdog checks subsystems every 30 seconds. If dispatch, scheduler, or health monitor crash, they auto-restart. After 5 crashes in 5 minutes, the system enters degraded mode and creates a critical GitHub issue. Check orchestrator logs for 'subsystem_crash_loop'.",
        "applies_to": ["ALL"],
    },
    {
        "category": "resilience",
        "severity": "medium",
        "title": "State Persistence on Shutdown",
        "tip": "Agent state, task queue, and scheduler state are persisted every 5 seconds and on graceful shutdown. Use SIGTERM (not SIGKILL) to ensure state is saved. Task queue history survives restarts.",
        "applies_to": ["ALL"],
    },
    {
        "category": "deployment",
        "severity": "high",
        "title": "Use Process Supervisor in Production",
        "tip": "Run with systemd, Docker, or supervisord for automatic restart on crash. Example: systemd with Restart=always and RestartSec=5. The internal watchdog handles subsystem recovery, but the process itself needs external supervision.",
        "applies_to": ["ALL"],
    },
    {
        "category": "deployment",
        "severity": "medium",
        "title": "Set All Integration Tokens",
        "tip": "Agents gracefully degrade when integrations are missing (they return placeholder results instead of crashing). But for full autonomous operation, set: GITHUB_TOKEN, NOTION_API_TOKEN, GOOGLE_SERVICE_ACCOUNT_JSON, and at least one LLM key (ANTHROPIC_API_KEY recommended).",
        "applies_to": ["ALL"],
    },
    {
        "category": "compliance",
        "severity": "critical",
        "title": "GLBA/SOC2 Data Handling",
        "tip": "Mortgage data is subject to GLBA. Never log PII in action logs. MARTIN document classification should sanitize borrower names before writing to Notion or GitHub. CIPHER compliance_check audits this automatically.",
        "applies_to": ["MARTIN", "CIPHER", "NOVA"],
    },
]


class HydrospeedEngine:
    """Live ontology engine that maps agent relationships and generates proposals."""

    def __init__(self) -> None:
        self._log = logger.bind(component="hydrospeed")
        self._proposals: list[dict[str, Any]] = []

    def get_ontology(self) -> dict[str, Any]:
        """Return the full ontology graph for visualization."""
        return {
            "version": "1.0.0",
            "engine": "Hydrospeed",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **AGENT_ONTOLOGY,
        }

    def get_agent_profile(self, agent_name: str) -> dict[str, Any]:
        """Get detailed profile for a specific agent from the ontology."""
        for node in AGENT_ONTOLOGY["nodes"]:
            if node["id"] == agent_name:
                # Find connected edges
                incoming = [e for e in AGENT_ONTOLOGY["edges"] if e["to"] == agent_name]
                outgoing = [e for e in AGENT_ONTOLOGY["edges"] if e["from"] == agent_name]
                tips = [t for t in EXPERT_TIPS if agent_name in t.get("applies_to", []) or "ALL" in t.get("applies_to", [])]
                return {
                    "profile": node,
                    "incoming_edges": incoming,
                    "outgoing_edges": outgoing,
                    "tips": tips,
                    "dependencies": [e["from"] for e in incoming if e["type"] == "dependency"],
                    "dependents": [e["to"] for e in outgoing if e["type"] == "dependency"],
                }
        return {"error": f"Agent {agent_name} not found in ontology"}

    def get_expert_tips(self, category: str = "", agent: str = "") -> list[dict[str, Any]]:
        """Get expert tips filtered by category and/or agent."""
        tips = EXPERT_TIPS
        if category:
            tips = [t for t in tips if t["category"] == category]
        if agent:
            tips = [t for t in tips if agent in t.get("applies_to", []) or "ALL" in t.get("applies_to", [])]
        return tips

    def get_divisions(self) -> dict[str, Any]:
        """Get agents grouped by division."""
        divisions: dict[str, list[dict[str, Any]]] = {}
        for node in AGENT_ONTOLOGY["nodes"]:
            if node["type"] == "agent":
                div = node.get("division", "other")
                if div not in divisions:
                    divisions[div] = []
                divisions[div].append(node)
        return divisions

    def create_proposal(
        self, title: str, description: str, agents: list[str],
        workflow_steps: list[str], priority: str = "medium",
    ) -> dict[str, Any]:
        """Create an agent workflow proposal."""
        proposal = {
            "id": f"prop-{len(self._proposals) + 1:04d}",
            "title": title,
            "description": description,
            "agents": agents,
            "workflow_steps": workflow_steps,
            "priority": priority,
            "status": "proposed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._proposals.append(proposal)
        self._log.info("proposal_created", id=proposal["id"], title=title)
        return proposal

    def list_proposals(self) -> list[dict[str, Any]]:
        return list(self._proposals)

    def get_data_flows(self) -> list[dict[str, Any]]:
        """Get all data flow paths for visualization."""
        return [e for e in AGENT_ONTOLOGY["edges"] if e["type"] == "data_flow"]

    def get_schedule_recommendations(self, current_schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Analyze current schedule and recommend improvements."""
        recommendations = []

        # Check for resource conflicts
        time_slots: dict[str, list[str]] = {}
        for job in current_schedule:
            rt = job.get("run_time", "")
            if rt:
                hour = rt.split(":")[0]
                if hour not in time_slots:
                    time_slots[hour] = []
                time_slots[hour].append(job["name"])

        for hour, jobs in time_slots.items():
            if len(jobs) > 2:
                recommendations.append({
                    "type": "conflict",
                    "severity": "warning",
                    "message": f"Hour {hour}:00 has {len(jobs)} jobs ({', '.join(jobs)}). Consider spreading them out to reduce API contention.",
                    "jobs": jobs,
                })

        # Check dependency ordering
        dep_pairs = [
            ("drive_auto_import", "document_audit", "Drive import must run before MARTIN audit"),
            ("document_audit", "income_recalculation", "Audit should complete before income recalc"),
            ("security_scan", "notion_audit_sync", "Security scan results should sync to Notion"),
        ]
        job_times = {j["name"]: j.get("run_time", "") for j in current_schedule}
        for before, after, reason in dep_pairs:
            if before in job_times and after in job_times:
                if job_times[before] > job_times[after]:
                    recommendations.append({
                        "type": "dependency",
                        "severity": "high",
                        "message": f"{before} ({job_times[before]}) should run BEFORE {after} ({job_times[after]}). {reason}",
                        "fix": f"Move {before} earlier or {after} later",
                    })

        if not recommendations:
            recommendations.append({
                "type": "ok",
                "severity": "info",
                "message": "Current schedule looks well-ordered. No conflicts detected.",
            })

        return recommendations
