/**
 * MortgageFintechOS Dashboard v3
 * Fully Connected Autonomous AI Operating System
 * Action Log, Schedule Control, Hydrospeed Ontology, Predictive Telemetry, Expert Tips
 */

const REFRESH_INTERVAL = 5000;

const AGENT_DESCRIPTIONS = {
    DIEGO: "Pipeline Orchestration",
    MARTIN: "Document Intelligence",
    NOVA: "Income & DTI Analysis",
    JARVIS: "Condition Resolution",
    ATLAS: "Full-Stack Engineering",
    CIPHER: "Security Engineering",
    FORGE: "DevOps Engineering",
    NEXUS: "Code Quality",
    STORM: "Data Engineering",
    SENTINEL: "System Intelligence",
    HUNTER: "Lead Generation",
    HERALD: "Content Marketing",
    AMBASSADOR: "Community Engagement",
};

let refreshTimer = null;
let currentTab = "overview";
let editingJob = "";

// --- Utilities ---

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function formatTime(iso) {
    if (!iso) return "--";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatRelative(iso) {
    if (!iso) return "--";
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return diff + "s ago";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    return Math.floor(diff / 3600) + "h ago";
}

function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

function severityClass(s) {
    return s === "critical" ? "danger" : s === "high" ? "warning" : s === "medium" ? "warning" : "info";
}

// --- Tab Navigation ---

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            const tab = btn.dataset.tab;
            document.getElementById("tab-" + tab).classList.add("active");
            currentTab = tab;
            refreshTab(tab);
        });
    });
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_INTERVAL);
});

// --- Main Refresh ---

async function refresh() {
    try {
        const [status, health, agents, queue, schedule, alerts] = await Promise.all([
            fetchJSON("/api/status"), fetchJSON("/api/health"),
            fetchJSON("/api/agents"), fetchJSON("/api/queue"),
            fetchJSON("/api/schedule"), fetchJSON("/api/alerts"),
        ]);

        renderMetrics(status, health);
        renderAgents(agents);
        renderQueue(queue);
        renderAlerts(alerts);

        document.getElementById("last-updated").textContent = "Updated " + new Date().toLocaleTimeString();

        // Refresh active tab
        refreshTab(currentTab);

    } catch (err) {
        console.error("Refresh failed:", err);
        document.getElementById("last-updated").textContent = "Connection error";
    }
}

async function refreshTab(tab) {
    try {
        if (tab === "action-log") await refreshActionLog();
        if (tab === "schedule") await refreshSchedule();
        if (tab === "ontology") await refreshOntology();
        if (tab === "telemetry") await refreshTelemetry();
        if (tab === "tips") await refreshTips();
        if (tab === "features") await refreshFeatures();
    } catch (e) { console.error("Tab refresh failed:", tab, e); }
}

// --- Overview Renderers ---

function renderMetrics(status, health) {
    const q = status.queue || {};
    const s = health.system || {};
    document.getElementById("metric-uptime").textContent = status.uptime || "--";
    document.getElementById("metric-agents").textContent = Object.keys(status.agents || {}).length;
    document.getElementById("metric-pending").textContent = q.pending || 0;
    document.getElementById("metric-completed").textContent = q.completed || 0;
    const failEl = document.getElementById("metric-failed");
    failEl.textContent = q.failed || 0;
    failEl.className = "metric-value" + ((q.failed || 0) > 0 ? " danger" : "");
    document.getElementById("metric-cpu").textContent = s.cpu_percent !== undefined ? s.cpu_percent.toFixed(1) + "%" : "--";
    document.getElementById("metric-mem").textContent = s.memory_percent !== undefined ? s.memory_percent.toFixed(1) + "%" : "--";

    const badge = document.getElementById("overall-status");
    const overall = health.overall || "unknown";
    badge.className = "status-badge " + overall;
    badge.innerHTML = `<span class="status-dot"></span>${overall}`;
}

function renderAgents(agents) {
    const tbody = document.getElementById("agents-tbody");
    if (!agents || !agents.length) { tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No agents</td></tr>`; return; }
    tbody.innerHTML = agents.map(a => `<tr>
        <td><span class="agent-name">${esc(a.name)}</span></td>
        <td>${esc(AGENT_DESCRIPTIONS[a.name] || "--")}</td>
        <td><span class="agent-badge ${a.status}">${a.status}</span></td>
        <td style="font-family:var(--font-mono)">${a.tasks_completed}</td>
        <td style="font-family:var(--font-mono);${a.error_count > 0 ? "color:var(--danger);font-weight:700" : ""}">${a.error_count}</td>
        <td style="font-size:12px;color:var(--text-muted)">${formatRelative(a.last_heartbeat)}</td>
    </tr>`).join("");
}

function renderQueue(queueData) {
    const tbody = document.getElementById("queue-tbody");
    const tasks = (queueData.recent_tasks || []).reverse().slice(0, 20);
    if (!tasks.length) { tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No recent tasks</td></tr>`; return; }
    tbody.innerHTML = tasks.map(t => `<tr>
        <td style="font-family:var(--font-mono);font-size:12px">${esc(t.id)}</td>
        <td><span class="agent-name">${esc(t.agent)}</span></td>
        <td>${esc(t.action)}</td>
        <td><span class="priority-badge ${t.priority}">${t.priority}</span></td>
        <td><span class="agent-badge ${t.status}">${t.status}</span></td>
    </tr>`).join("");
}

function renderAlerts(alerts) {
    const c = document.getElementById("alerts-container");
    if (!alerts || !alerts.length) { c.innerHTML = `<div class="empty-state">No recent alerts</div>`; return; }
    c.innerHTML = alerts.reverse().slice(0, 20).map(a => `<div class="alert-row">
        <span class="alert-severity ${a.severity}">${a.severity}</span>
        <span class="alert-message">${esc(a.message)}</span>
        <span class="alert-time">${formatTime(a.timestamp)}</span>
    </div>`).join("");
}

// --- Action Log ---

async function refreshActionLog() {
    const [stats, timeline, entries] = await Promise.all([
        fetchJSON("/api/action-log/stats"),
        fetchJSON("/api/action-log/timeline?hours=24"),
        fetchJSON("/api/action-log?limit=50" +
            (document.getElementById("al-agent-filter")?.value ? "&agent=" + document.getElementById("al-agent-filter").value : "") +
            (document.getElementById("al-failures-only")?.checked ? "&failures=1" : "")),
    ]);

    document.getElementById("al-total").textContent = stats.total_entries || 0;
    document.getElementById("al-rate").textContent = (stats.success_rate || 0) + "%";
    const rateEl = document.getElementById("al-rate");
    rateEl.className = "metric-value " + (stats.success_rate >= 95 ? "success" : stats.success_rate >= 80 ? "warning" : "danger");
    document.getElementById("al-failures").textContent = stats.failures || 0;
    const failEl = document.getElementById("al-failures");
    failEl.className = "metric-value" + ((stats.failures || 0) > 0 ? " danger" : "");

    // Populate agent filter
    const select = document.getElementById("al-agent-filter");
    if (select && select.options.length <= 1 && stats.agent_breakdown) {
        Object.keys(stats.agent_breakdown).sort().forEach(name => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = name;
            select.appendChild(opt);
        });
    }

    // Timeline
    const tlData = timeline.timeline || [];
    const maxVal = Math.max(...tlData.map(b => b.total), 1);
    document.getElementById("al-timeline").innerHTML = tlData.reverse().map(b => {
        const h = Math.max((b.total / maxVal) * 100, 2);
        const cls = b.failed > 0 ? "has-failures" : "";
        return `<div class="timeline-bar ${cls}" style="height:${h}%" title="${b.total} actions (${b.failed} failed) - ${b.hour}h ago"></div>`;
    }).join("");

    // Table
    const tbody = document.getElementById("al-tbody");
    const rows = entries.entries || [];
    if (!rows.length) { tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No actions recorded</td></tr>`; return; }
    tbody.innerHTML = rows.map(e => `<tr>
        <td style="font-size:12px;font-family:var(--font-mono)">${formatTime(e.timestamp)}</td>
        <td><span class="agent-name">${esc(e.agent)}</span></td>
        <td><span class="agent-badge ${e.action_type.includes('failed') ? 'error' : e.action_type.includes('completed') ? 'idle' : 'running'}">${esc(e.action_type)}</span></td>
        <td>${esc(e.action)}</td>
        <td style="font-family:var(--font-mono);font-size:12px">${e.duration_ms ? e.duration_ms + "ms" : "--"}</td>
        <td>${e.success ? '<span style="color:var(--success)">OK</span>' : '<span style="color:var(--danger)">FAIL</span>'}</td>
        <td style="font-size:12px;color:var(--text-muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(e.detail || "")}</td>
    </tr>`).join("");
}

// Wire up action log filters
document.addEventListener("DOMContentLoaded", () => {
    const agentFilter = document.getElementById("al-agent-filter");
    const failFilter = document.getElementById("al-failures-only");
    if (agentFilter) agentFilter.addEventListener("change", () => refreshTab("action-log"));
    if (failFilter) failFilter.addEventListener("change", () => refreshTab("action-log"));
});

// --- Schedule Control ---

async function refreshSchedule() {
    const [schedule, recs] = await Promise.all([
        fetchJSON("/api/schedule"),
        fetchJSON("/api/hydrospeed/schedule-recommendations"),
    ]);

    const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const tbody = document.getElementById("sched-tbody");
    if (!schedule || !schedule.length) { tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No jobs</td></tr>`; return; }

    tbody.innerHTML = schedule.map(j => {
        let sched = "";
        if (j.interval_minutes) sched = `Every ${j.interval_minutes}m`;
        else if (j.day_of_week !== null && j.day_of_week !== undefined) sched = `${DAYS[j.day_of_week]} ${j.run_time || ""}`;
        else sched = `Daily ${j.run_time || ""}`;
        const dot = j.enabled ? '<span class="schedule-enabled"></span>' : '<span class="schedule-disabled"></span>';
        return `<tr>
            <td>${dot}</td>
            <td>${esc(j.name)}</td>
            <td class="schedule-time">${sched}</td>
            <td style="font-size:12px;color:var(--text-muted)">${j.last_run ? formatRelative(j.last_run) : "Never"}</td>
            <td>
                <button class="btn btn-sm" onclick="editSchedule('${esc(j.name)}','${j.run_time || "00:00:00"}')">Edit</button>
                <button class="btn btn-sm ${j.enabled ? 'btn-danger' : 'btn-primary'}" onclick="toggleJob('${esc(j.name)}',${!j.enabled})">${j.enabled ? "Disable" : "Enable"}</button>
            </td>
        </tr>`;
    }).join("");

    // Recommendations
    const recsDiv = document.getElementById("sched-recommendations");
    const recommendations = recs.recommendations || [];
    if (!recommendations.length) { recsDiv.innerHTML = '<div class="empty-state">No recommendations</div>'; return; }
    recsDiv.innerHTML = recommendations.map(r => `<div class="tip-card">
        <div class="tip-header">
            <span class="alert-severity ${r.severity}">${r.severity}</span>
            <span class="tip-title">${esc(r.type)}</span>
        </div>
        <div class="tip-body">${esc(r.message)}</div>
        ${r.fix ? `<div class="tip-agents">Fix: ${esc(r.fix)}</div>` : ""}
    </div>`).join("");
}

function editSchedule(name, currentTime) {
    editingJob = name;
    document.getElementById("sched-modal-name").textContent = name;
    const parts = currentTime.split(":");
    document.getElementById("sched-hour").value = parseInt(parts[0]) || 0;
    document.getElementById("sched-minute").value = parseInt(parts[1]) || 0;
    document.getElementById("sched-modal").style.display = "flex";
}

function closeModal() { document.getElementById("sched-modal").style.display = "none"; }

async function saveSchedule() {
    const hour = parseInt(document.getElementById("sched-hour").value);
    const minute = parseInt(document.getElementById("sched-minute").value);
    await fetch(`/api/schedule/${editingJob}/update`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ hour, minute }),
    });
    closeModal();
    refreshTab("schedule");
}

async function toggleJob(name, enabled) {
    await fetch(`/api/schedule/${name}/toggle`, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ enabled }),
    });
    refreshTab("schedule");
}

// --- Hydrospeed Ontology ---

async function refreshOntology() {
    const [ontology, divisions, flows, proposals] = await Promise.all([
        fetchJSON("/api/hydrospeed/ontology"),
        fetchJSON("/api/hydrospeed/divisions"),
        fetchJSON("/api/hydrospeed/data-flows"),
        fetchJSON("/api/hydrospeed/proposals"),
    ]);

    const agents = (ontology.nodes || []).filter(n => n.type === "agent");
    const integrations = (ontology.nodes || []).filter(n => n.type === "integration");
    document.getElementById("onto-agents").textContent = agents.length;
    document.getElementById("onto-integrations").textContent = integrations.length;
    document.getElementById("onto-flows").textContent = (ontology.edges || []).length;

    // Populate agent select
    const select = document.getElementById("onto-agent-select");
    if (select && select.options.length <= 1) {
        agents.forEach(a => {
            const opt = document.createElement("option");
            opt.value = a.id;
            opt.textContent = `${a.id} - ${a.role}`;
            select.appendChild(opt);
        });
        select.addEventListener("change", () => loadAgentProfile(select.value));
    }

    // Divisions
    const divDiv = document.getElementById("onto-divisions");
    const divNames = { mortgage_ops: "Mortgage Operations", engineering: "Engineering", intelligence: "Intelligence", growth_ops: "Growth Ops" };
    divDiv.innerHTML = Object.entries(divisions).map(([key, agents]) => `<div class="division-section">
        <div class="division-name">${divNames[key] || key}</div>
        <div class="division-agents">
            ${agents.map(a => `<div class="division-agent" onclick="loadAgentProfile('${a.id}')" title="${a.role}">${a.id}</div>`).join("")}
        </div>
    </div>`).join("");

    // Data flow graph
    const graphDiv = document.getElementById("onto-graph");
    const flowEdges = flows.flows || [];
    if (!flowEdges.length) { graphDiv.innerHTML = '<div class="empty-state">No data flows</div>'; return; }
    graphDiv.innerHTML = flowEdges.map(e => `<div class="flow-edge">
        <span class="flow-node">${esc(e.from)}</span>
        <span class="flow-arrow">--&gt;</span>
        <span class="flow-node">${esc(e.to)}</span>
        <span class="flow-label">${esc(e.label)}</span>
    </div>`).join("");

    // Proposals
    const propDiv = document.getElementById("onto-proposals");
    const props = proposals.proposals || [];
    if (!props.length) { propDiv.innerHTML = '<div class="empty-state">No proposals yet. Create one to define new agent workflows.</div>'; return; }
    propDiv.innerHTML = props.map(p => `<div class="tip-card">
        <div class="tip-header">
            <span class="alert-severity ${p.priority}">${p.priority}</span>
            <span class="tip-title">${esc(p.title)}</span>
            <span style="font-size:11px;color:var(--text-muted)">${p.id}</span>
        </div>
        <div class="tip-body">${esc(p.description)}</div>
        <div class="tip-agents">Agents: ${p.agents.join(", ")} | Steps: ${p.workflow_steps.length} | Status: ${p.status}</div>
    </div>`).join("");
}

async function loadAgentProfile(name) {
    if (!name) return;
    const profile = await fetchJSON(`/api/hydrospeed/agent/${name}`);
    const div = document.getElementById("onto-profile");
    if (profile.error) { div.innerHTML = `<div class="empty-state">${esc(profile.error)}</div>`; return; }

    const p = profile.profile || {};
    div.innerHTML = `<div class="profile-section">
        <div class="profile-label">Agent</div>
        <div class="profile-value"><span class="agent-name">${esc(p.id)}</span> -- ${esc(p.role)} (${esc(p.division || "")})</div>

        <div class="profile-label">Capabilities</div>
        <div class="profile-tags">${(p.capabilities || []).map(c => `<span class="profile-tag">${esc(c)}</span>`).join("")}</div>

        <div class="profile-label">Inputs</div>
        <div class="profile-tags">${(p.inputs || []).map(i => `<span class="profile-tag">${esc(i)}</span>`).join("")}</div>

        <div class="profile-label">Outputs</div>
        <div class="profile-tags">${(p.outputs || []).map(o => `<span class="profile-tag">${esc(o)}</span>`).join("")}</div>

        <div class="profile-label">Dependencies (upstream)</div>
        <div class="profile-value">${(profile.dependencies || []).join(", ") || "None"}</div>

        <div class="profile-label">Dependents (downstream)</div>
        <div class="profile-value">${(profile.dependents || []).join(", ") || "None"}</div>

        <div class="profile-label">Expert Tips for ${esc(p.id)}</div>
        ${(profile.tips || []).map(t => `<div class="tip-card" style="padding:8px 0">
            <div class="tip-header"><span class="alert-severity ${t.severity}">${t.severity}</span><span class="tip-title">${esc(t.title)}</span></div>
            <div class="tip-body">${esc(t.tip)}</div>
        </div>`).join("")}
    </div>`;

    document.getElementById("onto-agent-select").value = name;
}

function showProposalForm() {
    const title = prompt("Proposal title:");
    if (!title) return;
    const description = prompt("Description:");
    const agents = prompt("Agents (comma-separated, e.g. ATLAS,NEXUS,FORGE):");
    const steps = prompt("Workflow steps (comma-separated):");
    if (!agents || !steps) return;

    fetch("/api/hydrospeed/proposals", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            title, description: description || "",
            agents: agents.split(",").map(s => s.trim()),
            workflow_steps: steps.split(",").map(s => s.trim()),
        }),
    }).then(() => refreshTab("ontology"));
}

// --- Predictive Telemetry ---

async function refreshTelemetry() {
    const [risks, predictions] = await Promise.all([
        fetchJSON("/api/telemetry/risks"),
        fetchJSON("/api/telemetry/predictions"),
    ]);

    document.getElementById("tele-score").textContent = risks.system_risk || "0.0";
    const level = risks.system_level || "low";
    document.getElementById("tele-level").textContent = level;
    document.getElementById("tele-tracked").textContent = risks.total_tracked || 0;
    document.getElementById("tele-critical").textContent = (risks.critical_agents || []).length;
    document.getElementById("tele-predictions").textContent = (predictions.predictions || []).length;

    // System risk badge in header
    const riskBadge = document.getElementById("system-risk");
    riskBadge.className = "status-badge " + level;
    document.getElementById("risk-label").textContent = "risk: " + level;

    // Predictions
    const predDiv = document.getElementById("tele-pred-list");
    const preds = predictions.predictions || [];
    if (!preds.length) { predDiv.innerHTML = '<div class="empty-state">No active predictions -- system is healthy</div>'; return; }
    predDiv.innerHTML = preds.map(p => `<div class="prediction-card ${p.level === 'critical' ? 'critical' : ''}">
        <div class="prediction-header">
            <div><span class="agent-name">${esc(p.agent)}</span> <span class="alert-severity ${p.level}">${p.level}</span></div>
            <span style="font-size:12px;color:var(--text-muted)">Confidence: ${(p.confidence * 100).toFixed(0)}%</span>
        </div>
        <div class="prediction-text">${esc(p.prediction)}</div>
        <div class="prediction-solutions">
            ${(p.solutions || []).map(s => `<div style="margin-top:4px">- [${s.severity}] ${esc(s.action)}</div>`).join("")}
        </div>
    </div>`).join("");

    // Per-agent risk table
    const tbody = document.getElementById("tele-agents-tbody");
    const agentRisks = risks.agents || {};
    const entries = Object.entries(agentRisks);
    if (!entries.length) { tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Collecting telemetry...</td></tr>`; return; }
    tbody.innerHTML = entries.sort((a, b) => b[1].risk_score - a[1].risk_score).map(([name, r]) => {
        const f = r.factors || {};
        return `<tr>
            <td><span class="agent-name">${esc(name)}</span></td>
            <td style="font-family:var(--font-mono)">${r.risk_score.toFixed(3)} <div class="risk-bar"><div class="risk-fill ${r.level}" style="width:${r.risk_score * 100}%"></div></div></td>
            <td><span class="alert-severity ${r.level}">${r.level}</span></td>
            <td>${esc(r.dominant_factor || "--")}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${((f.error_rate||{}).value||0).toFixed(2)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${((r.telemetry||{}).avg_latency_ms||0).toFixed(0)}ms</td>
            <td style="font-family:var(--font-mono);font-size:12px">${((f.dependency||{}).value||0).toFixed(2)}</td>
        </tr>`;
    }).join("");
}

// --- Expert Tips ---

async function refreshTips() {
    const cat = document.getElementById("tips-cat-filter")?.value || "";
    const data = await fetchJSON("/api/hydrospeed/tips" + (cat ? "?category=" + cat : ""));
    const tips = data.tips || [];

    document.getElementById("tips-total").textContent = tips.length;
    document.getElementById("tips-critical").textContent = tips.filter(t => t.severity === "critical").length;
    const categories = new Set(tips.map(t => t.category));
    document.getElementById("tips-categories").textContent = categories.size;

    const div = document.getElementById("tips-list");
    if (!tips.length) { div.innerHTML = '<div class="empty-state">No tips match this filter</div>'; return; }
    div.innerHTML = tips.map(t => `<div class="tip-card">
        <div class="tip-header">
            <span class="alert-severity ${t.severity}">${t.severity}</span>
            <span class="priority-badge MEDIUM">${esc(t.category)}</span>
            <span class="tip-title">${esc(t.title)}</span>
        </div>
        <div class="tip-body">${esc(t.tip)}</div>
        <div class="tip-agents">Applies to: ${(t.applies_to || []).join(", ")}</div>
    </div>`).join("");
}

document.addEventListener("DOMContentLoaded", () => {
    const catFilter = document.getElementById("tips-cat-filter");
    if (catFilter) catFilter.addEventListener("change", () => refreshTab("tips"));
});

// --- Features Guide ---

async function refreshFeatures() {
    const data = await fetchJSON("/api/features");
    const div = document.getElementById("features-list");
    const sections = data.sections || [];
    if (!sections.length) { div.innerHTML = '<div class="empty-state">No features</div>'; return; }

    div.innerHTML = sections.map(s => `<div class="feature-card">
        <div class="feature-title">${esc(s.title)}</div>
        <div class="feature-desc">${esc(s.description)}</div>
        <div class="feature-meta">
            <div>
                <div class="feature-meta-label">Technology</div>
                <div class="feature-meta-value">${esc(s.tech)}</div>
            </div>
            <div>
                <div class="feature-meta-label">How to Use</div>
                <div class="feature-meta-value">${esc(s.how_to_use)}</div>
            </div>
        </div>
        ${s.agents ? `<div style="margin-top:12px">
            <div class="feature-meta-label">Agents</div>
            <div class="profile-tags">${s.agents.map(a => `<span class="profile-tag" title="${a.division}: ${a.actions.join(', ')}">${a.name}</span>`).join("")}</div>
        </div>` : ""}
    </div>`).join("");
}
