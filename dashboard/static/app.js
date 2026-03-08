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
        if (tab === "agentdb") await refreshAgentDB();
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

// --- Agent Database (Dolt-style version control) ---

let adbBranchesLoaded = false;

async function refreshAgentDB() {
    const [branches, tables] = await Promise.all([
        fetchJSON("/api/agentdb/branches"),
        fetchJSON("/api/agentdb/tables?branch=main"),
    ]);

    const branchList = branches.branches || [];
    document.getElementById("adb-branches-count").textContent = branchList.length;
    document.getElementById("adb-tables-count").textContent = Object.keys((tables.tables || {})).length;
    const totalRows = Object.values(tables.tables || {}).reduce((sum, t) => sum + (t.row_count || 0), 0);
    document.getElementById("adb-rows-count").textContent = totalRows;

    // Branches table
    const tbody = document.getElementById("adb-branches-tbody");
    tbody.innerHTML = branchList.map(b => {
        const lastMsg = b.last_commit ? esc(b.last_commit.message).slice(0, 40) : "--";
        const lastTime = b.last_commit ? formatRelative(b.last_commit.timestamp) : "--";
        const actions = b.name === "main"
            ? '<span style="color:var(--text-muted);font-size:12px">protected</span>'
            : `<button class="btn btn-sm" onclick="mergeBranch('${esc(b.name)}')">Merge</button>
               <button class="btn btn-sm" onclick="diffBranch('${esc(b.name)}')">Diff</button>`;
        return `<tr>
            <td><span class="agent-name">${esc(b.name)}</span></td>
            <td style="font-size:12px;color:var(--text-muted)">${esc(b.parent || "--")}</td>
            <td style="font-family:var(--font-mono)">${b.commits}</td>
            <td style="font-family:var(--font-mono)">${b.total_rows}</td>
            <td style="font-size:12px" title="${lastMsg}">${lastTime}</td>
            <td>${actions}</td>
        </tr>`;
    }).join("");

    // Schema view
    const schemaDiv = document.getElementById("adb-schema-view");
    const tblStats = tables.tables || {};
    schemaDiv.innerHTML = Object.entries(tblStats).map(([name, info]) => `<div class="schema-table">
        <div class="schema-table-name">${esc(name)}</div>
        <div class="schema-columns">${(info.columns || []).map(c => `<span class="schema-col">${esc(c)}</span>`).join("")}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">${info.row_count} rows</div>
    </div>`).join("");

    // Populate branch selects
    if (!adbBranchesLoaded) {
        const selects = ["adb-branch-select", "adb-diff-from", "adb-diff-to", "adb-log-branch"];
        selects.forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            sel.innerHTML = "";
            if (id === "adb-diff-to") {
                sel.innerHTML = '<option value="">Select branch...</option>';
            }
            branchList.forEach(b => {
                const opt = document.createElement("option");
                opt.value = b.name;
                opt.textContent = b.name;
                sel.appendChild(opt);
            });
        });

        // Agent select
        const agentSel = document.getElementById("adb-agent-select");
        if (agentSel && agentSel.options.length <= 1) {
            Object.keys(AGENT_DESCRIPTIONS).forEach(name => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.textContent = name + " - " + AGENT_DESCRIPTIONS[name];
                agentSel.appendChild(opt);
            });
        }
        adbBranchesLoaded = true;
    }
}

async function queryTable() {
    const branch = document.getElementById("adb-branch-select").value;
    const table = document.getElementById("adb-table-select").value;
    const data = await fetchJSON(`/api/agentdb/query/${table}?branch=${branch}&limit=50`);
    const div = document.getElementById("adb-table-data");

    if (data.error) { div.innerHTML = `<div class="empty-state">${esc(data.error)}</div>`; return; }
    const rows = data.rows || [];
    if (!rows.length) { div.innerHTML = `<div class="empty-state">No rows in ${table} on branch ${branch}</div>`; return; }

    const cols = Object.keys(rows[0]);
    div.innerHTML = `<div style="overflow-x:auto"><table>
        <thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map(r => `<tr>${cols.map(c => {
            let val = r[c];
            if (typeof val === "object" && val !== null) val = JSON.stringify(val).slice(0, 80);
            return `<td style="font-size:12px;font-family:var(--font-mono);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(String(val ?? ""))}</td>`;
        }).join("")}</tr>`).join("")}
        </tbody>
    </table></div>
    <div style="font-size:12px;color:var(--text-muted);padding:8px">Showing ${rows.length} of ${data.total} rows on <b>${esc(branch)}</b></div>`;
}

async function computeDiff() {
    const from = document.getElementById("adb-diff-from").value;
    const to = document.getElementById("adb-diff-to").value;
    if (!to) { alert("Select a target branch"); return; }

    const data = await fetchJSON(`/api/agentdb/diff?from=${from}&to=${to}`);
    const div = document.getElementById("adb-diff-view");
    const diffs = data.diffs || [];

    if (!diffs.length) {
        div.innerHTML = `<div class="empty-state">No differences between ${esc(from)} and ${esc(to)}</div>`;
        return;
    }

    div.innerHTML = `<div style="font-size:12px;color:var(--text-muted);padding:8px 0">${diffs.length} change(s)</div>` +
        diffs.map(d => {
            const typeClass = d.diff_type === "added" ? "diff-added" : d.diff_type === "removed" ? "diff-removed" : "diff-modified";
            const icon = d.diff_type === "added" ? "+" : d.diff_type === "removed" ? "-" : "~";
            const detail = d.diff_type === "added"
                ? JSON.stringify(d.to_row || {}).slice(0, 120)
                : d.diff_type === "removed"
                ? JSON.stringify(d.from_row || {}).slice(0, 120)
                : `FROM: ${JSON.stringify(d.from_row || {}).slice(0, 60)} TO: ${JSON.stringify(d.to_row || {}).slice(0, 60)}`;
            return `<div class="diff-entry ${typeClass}">
                <span class="diff-icon">${icon}</span>
                <span class="diff-table">${esc(d.table)}</span>
                <span class="diff-id">${esc((d.row_id || "").slice(0, 8))}</span>
                <span class="diff-detail">${esc(detail)}</span>
            </div>`;
        }).join("");
}

function diffBranch(branch) {
    document.getElementById("adb-diff-from").value = "main";
    document.getElementById("adb-diff-to").value = branch;
    computeDiff();
}

async function mergeBranch(source) {
    if (!confirm(`Merge '${source}' into 'main'? This will apply all changes atomically.`)) return;
    const resp = await fetch("/api/agentdb/merge", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ source, target: "main", author: "DASHBOARD" }),
    });
    const result = await resp.json();
    if (result.error) { alert("Merge error: " + result.error); return; }
    alert(`Merged! Added: ${result.added}, Modified: ${result.modified}, Removed: ${result.removed}`);
    adbBranchesLoaded = false;
    refreshTab("agentdb");
}

async function loadCommitLog() {
    const branch = document.getElementById("adb-log-branch").value;
    const data = await fetchJSON(`/api/agentdb/log/${branch}?limit=20`);
    const div = document.getElementById("adb-commit-log");
    const commits = data.commits || [];

    if (!commits.length || commits[0]?.error) {
        div.innerHTML = `<div class="empty-state">No commits on ${esc(branch)}</div>`;
        return;
    }

    div.innerHTML = commits.map(c => `<div class="commit-entry">
        <div class="commit-header">
            <span class="commit-id">${esc((c.id || "").slice(0, 8))}</span>
            <span class="commit-author">${esc(c.author)}</span>
            <span class="commit-time">${formatRelative(c.timestamp)}</span>
        </div>
        <div class="commit-message">${esc(c.message)}</div>
    </div>`).join("");
}

async function loadAgentDbStatus() {
    const name = document.getElementById("adb-agent-select").value;
    if (!name) return;
    const data = await fetchJSON(`/api/agentdb/agent/${name}`);
    const div = document.getElementById("adb-agent-status");

    if (data.error) {
        div.innerHTML = `<div class="empty-state">${esc(data.error)}</div>`;
        return;
    }

    const state = data.state || {};
    const ops = data.recent_operations || [];
    const diffs = data.diffs || [];
    const commits = data.recent_commits || [];

    div.innerHTML = `
        <div class="agent-db-status">
            <div class="adb-stat-section">
                <div class="adb-stat-title">Branch: <span class="agent-name">${esc(data.branch)}</span></div>
                <div class="adb-stat-row">
                    <span>Pending changes: <b>${data.pending_changes}</b></span>
                    <span>Status: <span class="agent-badge ${state.status || 'idle'}">${state.status || "unknown"}</span></span>
                    <span>Tasks: ${state.tasks_completed || 0} completed, ${state.tasks_failed || 0} failed</span>
                    <span>Health: ${(state.health_score || 1.0).toFixed(2)}</span>
                </div>
            </div>

            ${diffs.length ? `<div class="adb-stat-section">
                <div class="adb-stat-title">Pending Diffs (${diffs.length})</div>
                ${diffs.slice(0, 10).map(d => {
                    const tc = d.diff_type === "added" ? "diff-added" : d.diff_type === "removed" ? "diff-removed" : "diff-modified";
                    return `<div class="diff-entry ${tc}">
                        <span class="diff-icon">${d.diff_type === "added" ? "+" : d.diff_type === "removed" ? "-" : "~"}</span>
                        <span class="diff-table">${esc(d.table)}</span>
                        <span class="diff-id">${esc((d.row_id || "").slice(0, 8))}</span>
                    </div>`;
                }).join("")}
                ${diffs.length > 10 ? `<div style="font-size:12px;color:var(--text-muted)">...and ${diffs.length - 10} more</div>` : ""}
                <button class="btn btn-sm btn-primary" style="margin-top:8px" onclick="mergeBranch('${esc(data.branch)}')">Merge to main</button>
            </div>` : ""}

            ${ops.length ? `<div class="adb-stat-section">
                <div class="adb-stat-title">Recent Operations</div>
                <table><thead><tr><th>Action</th><th>Status</th><th>Duration</th><th>Time</th></tr></thead>
                <tbody>${ops.map(o => `<tr>
                    <td>${esc(o.action)}</td>
                    <td><span class="agent-badge ${o.status === 'completed' ? 'idle' : 'error'}">${o.status}</span></td>
                    <td style="font-family:var(--font-mono);font-size:12px">${o.duration_ms ? o.duration_ms + "ms" : "--"}</td>
                    <td style="font-size:12px;color:var(--text-muted)">${formatRelative(o.created_at)}</td>
                </tr>`).join("")}</tbody></table>
            </div>` : ""}

            ${commits.length ? `<div class="adb-stat-section">
                <div class="adb-stat-title">Recent Commits</div>
                ${commits.slice(0, 5).map(c => `<div class="commit-entry">
                    <span class="commit-id">${esc((c.id || "").slice(0, 8))}</span>
                    <span class="commit-message">${esc(c.message)}</span>
                    <span class="commit-time">${formatRelative(c.timestamp)}</span>
                </div>`).join("")}
            </div>` : ""}
        </div>`;
}

function showCreateBranch() {
    const modal = document.getElementById("adb-modal");
    document.getElementById("adb-modal-title").textContent = "Create Branch";
    document.getElementById("adb-modal-body").innerHTML = `
        <label>Branch name: <input type="text" id="adb-new-branch-name" class="control-input" placeholder="feature/my-branch"></label>
        <label>From branch:
            <select id="adb-new-branch-from" class="control-select">
                ${(document.getElementById("adb-branch-select")?.innerHTML || '<option value="main">main</option>')}
            </select>
        </label>`;
    document.getElementById("adb-modal-confirm").onclick = async () => {
        const name = document.getElementById("adb-new-branch-name").value.trim();
        const from = document.getElementById("adb-new-branch-from").value;
        if (!name) { alert("Branch name required"); return; }
        const resp = await fetch("/api/agentdb/branches", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ name, from }),
        });
        const result = await resp.json();
        if (result.error) { alert(result.error); return; }
        modal.style.display = "none";
        adbBranchesLoaded = false;
        refreshTab("agentdb");
    };
    modal.style.display = "flex";
}

async function showSchemaSQL() {
    const resp = await fetch("/api/agentdb/schema/sql");
    const sql = await resp.text();
    const modal = document.getElementById("adb-modal");
    document.getElementById("adb-modal-title").textContent = "Database Schema (SQL)";
    document.getElementById("adb-modal-body").innerHTML = `<pre class="schema-sql">${esc(sql)}</pre>`;
    document.getElementById("adb-modal-confirm").onclick = () => { modal.style.display = "none"; };
    document.getElementById("adb-modal-confirm").textContent = "Close";
    modal.style.display = "flex";
}
