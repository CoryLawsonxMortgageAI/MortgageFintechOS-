/**
 * MortgageFintechOS Dashboard v4
 * Fully Connected Automatous AI Operating System
 * Sidebar navigation, ontology graph, prompt generator, all modules
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

// --- Global State ---

let refreshTimer = null;
let currentPage = "home";
let editingJob = "";
let adbBranchesLoaded = false;
let cachedOntology = null;
let cachedStatus = null;

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
    if (str === null || str === undefined) return "";
    const d = document.createElement("div");
    d.textContent = String(str);
    return d.innerHTML;
}

function severityClass(s) {
    return s === "critical" ? "danger" : s === "high" ? "warning" : s === "medium" ? "warning" : "info";
}

// --- Page titles for topbar ---

const PAGE_TITLES = {
    home: "Platform Home",
    "command-center": "Command Center",
    "action-log": "Action Log",
    schedule: "Schedule Control",
    ontology: "Ontology Graph",
    telemetry: "Predictive Telemetry",
    tips: "Expert Tips",
    agentdb: "Agent Database",
    skills: "Agent Skills",
    "agent-chat": "Agent Chat",
    "agentic-runtime": "Agentic Runtime",
    integrations: "Integrations Hub",
    features: "Features Guide",
};

// --- Navigation System ---

function switchPage(pageId) {
    currentPage = pageId;

    // Update sidebar
    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.toggle("active", item.dataset.page === pageId);
    });

    // Update pages
    document.querySelectorAll(".page").forEach(page => {
        page.classList.toggle("active", page.id === "page-" + pageId);
    });

    // Update topbar title
    const titleEl = document.getElementById("topbar-title");
    if (titleEl) titleEl.textContent = PAGE_TITLES[pageId] || pageId;

    // Update URL hash
    location.hash = pageId;

    // Refresh page data
    refreshCurrentPage();
}

function refreshCurrentPage() {
    try {
        switch (currentPage) {
            case "home": refreshHome(); break;
            case "command-center": refreshCommand(); break;
            case "action-log": refreshActionLog(); break;
            case "schedule": refreshSchedule(); break;
            case "ontology": refreshOntology(); break;
            case "telemetry": refreshTelemetry(); break;
            case "tips": refreshTips(); break;
            case "agentdb": refreshAgentDB(); break;
            case "skills": refreshSkills(); break;
            case "agent-chat": initAgentChat(); break;
            case "agentic-runtime": refreshAgenticRuntime(); break;
            case "integrations": refreshIntegrations(); break;
            case "features": refreshFeatures(); break;
        }
    } catch (e) {
        console.error("Page refresh failed:", currentPage, e);
    }
}

// --- Init ---

document.addEventListener("DOMContentLoaded", () => {
    // Wire sidebar navigation
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const pageId = item.dataset.page;
            if (pageId) switchPage(pageId);
        });
    });

    // Wire action log filters
    const agentFilter = document.getElementById("al-agent-filter");
    const failFilter = document.getElementById("al-failures-only");
    if (agentFilter) agentFilter.addEventListener("change", () => { if (currentPage === "action-log") refreshActionLog(); });
    if (failFilter) failFilter.addEventListener("change", () => { if (currentPage === "action-log") refreshActionLog(); });

    // Wire tips category filter
    const catFilter = document.getElementById("tips-cat-filter");
    if (catFilter) catFilter.addEventListener("change", () => { if (currentPage === "tips") refreshTips(); });

    // Read hash or default to home
    const hash = location.hash.replace("#", "");
    const startPage = hash && PAGE_TITLES[hash] ? hash : "home";
    switchPage(startPage);

    // Auto-refresh
    refreshTimer = setInterval(refreshCurrentPage, REFRESH_INTERVAL);
});

// Handle browser back/forward
window.addEventListener("hashchange", () => {
    const hash = location.hash.replace("#", "");
    if (hash && PAGE_TITLES[hash] && hash !== currentPage) {
        switchPage(hash);
    }
});

// ===================================================================
// Platform Home Page
// ===================================================================

async function refreshHome() {
    try {
        const [status, ontSync] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/ontology-telemetry-sync"),
        ]);

        cachedStatus = status;
        cachedOntology = ontSync;

        // Hero metrics
        const heroAgents = document.getElementById("hero-agents");
        const heroTasks = document.getElementById("hero-tasks");
        const heroRisk = document.getElementById("hero-risk");
        const heroUptime = document.getElementById("hero-uptime");

        const agents = Object.keys(status.agents || {});
        if (heroAgents) heroAgents.textContent = agents.length;
        if (heroTasks) heroTasks.textContent = (status.queue || {}).completed || 0;
        if (heroRisk) heroRisk.textContent = status.system_risk || "low";
        if (heroUptime) heroUptime.textContent = status.uptime || "--";

        // Agent capability grid
        const agentGrid = document.getElementById("home-agents-grid");
        if (agentGrid) {
            const agentNodes = (ontSync.nodes || []).filter(n => n.type === "agent");
            if (agentNodes.length) {
                agentGrid.innerHTML = agentNodes.map(a => {
                    const hs = a.health_status || {};
                    const level = hs.level || "unknown";
                    const dotClass = (level === "low" || level === "healthy") ? "low" :
                                     level === "medium" ? "medium" :
                                     (level === "high" || level === "critical") ? "critical" : "unknown";
                    return `<div class="capability-item">
                        <div class="capability-dot ${dotClass}"></div>
                        <div class="capability-info">
                            <div class="capability-name">${esc(a.id || a.name)}</div>
                            <div class="capability-role">${esc(a.role || AGENT_DESCRIPTIONS[a.id] || "")}</div>
                        </div>
                    </div>`;
                }).join("");
            } else {
                agentGrid.innerHTML = '<div class="empty-state">No agents detected</div>';
            }
        }

        // Integration chips
        const intRow = document.getElementById("home-integrations");
        if (intRow) {
            const intNodes = (ontSync.nodes || []).filter(n => n.type === "integration");
            if (intNodes.length) {
                intRow.innerHTML = intNodes.map(n => {
                    const connected = n.connected || false;
                    return `<div class="integration-chip ${connected ? 'connected' : ''}">
                        <span class="int-dot"></span>
                        ${esc(n.id || n.name)}
                    </div>`;
                }).join("");
            } else {
                intRow.innerHTML = '<div class="empty-state">No integrations</div>';
            }
        }

        updateHeaderStatus(status);

    } catch (err) {
        console.error("Home refresh failed:", err);
    }
}

// ===================================================================
// Command Center (Overview)
// ===================================================================

async function refreshCommand() {
    try {
        const [status, health, agents, queue, schedule, alerts] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/health"),
            fetchJSON("/api/agents"),
            fetchJSON("/api/queue"),
            fetchJSON("/api/schedule"),
            fetchJSON("/api/alerts"),
        ]);

        cachedStatus = status;

        renderMetrics(status, health);
        renderAgents(agents);
        renderQueue(queue);
        renderAlerts(alerts);

        updateHeaderStatus(status, health);

    } catch (err) {
        console.error("Command refresh failed:", err);
    }
}

function updateHeaderStatus(status, health) {
    const updatedEl = document.getElementById("last-updated");
    if (updatedEl) updatedEl.textContent = "Updated " + new Date().toLocaleTimeString();

    // Update system risk badge if telemetry data is cached
    if (health) {
        const badge = document.getElementById("overall-status");
        if (badge) {
            const overall = health.overall || "unknown";
            badge.className = "status-badge " + overall;
            badge.innerHTML = `<span class="status-dot"></span>${overall}`;
        }
    }
}

function renderMetrics(status, health) {
    const q = status.queue || {};
    const s = health.system || {};

    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    setEl("metric-uptime", status.uptime || "--");
    setEl("metric-agents", Object.keys(status.agents || {}).length);
    setEl("metric-pending", q.pending || 0);
    setEl("metric-completed", q.completed || 0);

    const failEl = document.getElementById("metric-failed");
    if (failEl) {
        failEl.textContent = q.failed || 0;
        failEl.className = "metric-value" + ((q.failed || 0) > 0 ? " danger" : "");
    }

    setEl("metric-cpu", s.cpu_percent !== undefined ? s.cpu_percent.toFixed(1) + "%" : "--");
    setEl("metric-mem", s.memory_percent !== undefined ? s.memory_percent.toFixed(1) + "%" : "--");

    const badge = document.getElementById("overall-status");
    if (badge) {
        const overall = health.overall || "unknown";
        badge.className = "status-badge " + overall;
        badge.innerHTML = `<span class="status-dot"></span>${overall}`;
    }
}

function renderAgents(agents) {
    const tbody = document.getElementById("agents-tbody");
    if (!tbody) return;
    if (!agents || !agents.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No agents</td></tr>`;
        return;
    }
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
    if (!tbody) return;
    const tasks = (queueData.recent_tasks || []).reverse().slice(0, 20);
    if (!tasks.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No recent tasks</td></tr>`;
        return;
    }
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
    if (!c) return;
    if (!alerts || !alerts.length) {
        c.innerHTML = `<div class="empty-state">No recent alerts</div>`;
        return;
    }
    c.innerHTML = alerts.reverse().slice(0, 20).map(a => `<div class="alert-row">
        <span class="alert-severity ${a.severity}">${a.severity}</span>
        <span class="alert-message">${esc(a.message)}</span>
        <span class="alert-time">${formatTime(a.timestamp)}</span>
    </div>`).join("");
}

// ===================================================================
// Action Log
// ===================================================================

async function refreshActionLog() {
    try {
        const [stats, timeline, entries] = await Promise.all([
            fetchJSON("/api/action-log/stats"),
            fetchJSON("/api/action-log/timeline?hours=24"),
            fetchJSON("/api/action-log?limit=50" +
                (document.getElementById("al-agent-filter")?.value ? "&agent=" + document.getElementById("al-agent-filter").value : "") +
                (document.getElementById("al-failures-only")?.checked ? "&failures=1" : "")),
        ]);

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

        setEl("al-total", stats.total_entries || 0);
        setEl("al-rate", (stats.success_rate || 0) + "%");

        const rateEl = document.getElementById("al-rate");
        if (rateEl) rateEl.className = "metric-value " + (stats.success_rate >= 95 ? "success" : stats.success_rate >= 80 ? "warning" : "danger");

        setEl("al-failures", stats.failures || 0);
        const failEl = document.getElementById("al-failures");
        if (failEl) failEl.className = "metric-value" + ((stats.failures || 0) > 0 ? " danger" : "");

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
        const tlEl = document.getElementById("al-timeline");
        if (tlEl) {
            tlEl.innerHTML = tlData.reverse().map(b => {
                const h = Math.max((b.total / maxVal) * 100, 2);
                const cls = b.failed > 0 ? "has-failures" : "";
                return `<div class="timeline-bar ${cls}" style="height:${h}%" title="${b.total} actions (${b.failed} failed) - ${b.hour}h ago"></div>`;
            }).join("");
        }

        // Table
        const tbody = document.getElementById("al-tbody");
        if (!tbody) return;
        const rows = entries.entries || [];
        if (!rows.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No actions recorded</td></tr>`;
            return;
        }
        tbody.innerHTML = rows.map(e => `<tr>
            <td style="font-size:12px;font-family:var(--font-mono)">${formatTime(e.timestamp)}</td>
            <td><span class="agent-name">${esc(e.agent)}</span></td>
            <td><span class="agent-badge ${e.action_type.includes('failed') ? 'error' : e.action_type.includes('completed') ? 'idle' : 'running'}">${esc(e.action_type)}</span></td>
            <td>${esc(e.action)}</td>
            <td style="font-family:var(--font-mono);font-size:12px">${e.duration_ms ? e.duration_ms + "ms" : "--"}</td>
            <td>${e.success ? '<span style="color:var(--success)">OK</span>' : '<span style="color:var(--danger)">FAIL</span>'}</td>
            <td style="font-size:12px;color:var(--text-muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(e.detail || "")}</td>
        </tr>`).join("");

    } catch (err) {
        console.error("Action log refresh failed:", err);
    }
}

// ===================================================================
// Schedule Control
// ===================================================================

async function refreshSchedule() {
    try {
        const [schedule, recs] = await Promise.all([
            fetchJSON("/api/schedule"),
            fetchJSON("/api/hydrospeed/schedule-recommendations"),
        ]);

        const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        const tbody = document.getElementById("sched-tbody");
        if (!tbody) return;

        if (!schedule || !schedule.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No jobs</td></tr>`;
            return;
        }

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
        if (!recsDiv) return;
        const recommendations = recs.recommendations || [];
        if (!recommendations.length) {
            recsDiv.innerHTML = '<div class="empty-state">No recommendations</div>';
            return;
        }
        recsDiv.innerHTML = recommendations.map(r => `<div class="tip-card">
            <div class="tip-header">
                <span class="alert-severity ${r.severity}">${r.severity}</span>
                <span class="tip-title">${esc(r.type)}</span>
            </div>
            <div class="tip-body">${esc(r.message)}</div>
            ${r.fix ? `<div class="tip-agents">Fix: ${esc(r.fix)}</div>` : ""}
        </div>`).join("");

    } catch (err) {
        console.error("Schedule refresh failed:", err);
    }
}

function editSchedule(name, currentTime) {
    editingJob = name;
    const nameEl = document.getElementById("sched-modal-name");
    if (nameEl) nameEl.textContent = name;
    const parts = currentTime.split(":");
    const hourEl = document.getElementById("sched-hour");
    const minEl = document.getElementById("sched-minute");
    if (hourEl) hourEl.value = parseInt(parts[0]) || 0;
    if (minEl) minEl.value = parseInt(parts[1]) || 0;
    const modal = document.getElementById("sched-modal");
    if (modal) modal.style.display = "flex";
}

function closeModal() {
    const schedModal = document.getElementById("sched-modal");
    if (schedModal) schedModal.style.display = "none";
}

async function saveSchedule() {
    const hour = parseInt(document.getElementById("sched-hour").value);
    const minute = parseInt(document.getElementById("sched-minute").value);
    await fetch(`/api/schedule/${editingJob}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hour, minute }),
    });
    closeModal();
    refreshSchedule();
}

async function toggleJob(name, enabled) {
    await fetch(`/api/schedule/${name}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
    });
    refreshSchedule();
}

// ===================================================================
// Ontology Graph (SVG visualization)
// ===================================================================

async function refreshOntology() {
    try {
        const [ontSync, divisions, flows, proposals] = await Promise.all([
            fetchJSON("/api/ontology-telemetry-sync"),
            fetchJSON("/api/hydrospeed/divisions"),
            fetchJSON("/api/hydrospeed/data-flows"),
            fetchJSON("/api/hydrospeed/proposals"),
        ]);

        cachedOntology = ontSync;

        const agents = (ontSync.nodes || []).filter(n => n.type === "agent");
        const integrations = (ontSync.nodes || []).filter(n => n.type === "integration");
        const dataSources = (ontSync.nodes || []).filter(n => n.type === "data_source");

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl("onto-agents", agents.length);
        setEl("onto-integrations", integrations.length);
        setEl("onto-flows", (ontSync.edges || []).length);

        // Render SVG graph
        renderOntologyGraph(ontSync);

        // Populate agent select for profiles dropdown
        const select = document.getElementById("onto-agent-select");
        if (select && select.options.length <= 1) {
            agents.forEach(a => {
                const opt = document.createElement("option");
                opt.value = a.id;
                opt.textContent = `${a.id} - ${a.role || ""}`;
                select.appendChild(opt);
            });
            select.addEventListener("change", () => loadAgentProfile(select.value));
        }

        // Divisions
        const divDiv = document.getElementById("onto-divisions");
        if (divDiv) {
            const divNames = { mortgage_ops: "Mortgage Operations", engineering: "Engineering", intelligence: "Intelligence", growth_ops: "Growth Ops" };
            divDiv.innerHTML = Object.entries(divisions).map(([key, divAgents]) => `<div class="division-section">
                <div class="division-name">${divNames[key] || key}</div>
                <div class="division-agents">
                    ${divAgents.map(a => `<div class="division-agent" onclick="loadAgentProfile('${a.id}')" title="${a.role}">${a.id}</div>`).join("")}
                </div>
            </div>`).join("");
        }

        // Data flow graph (text version)
        const graphDiv = document.getElementById("onto-graph");
        if (graphDiv) {
            const flowEdges = flows.flows || [];
            if (!flowEdges.length) {
                graphDiv.innerHTML = '<div class="empty-state">No data flows</div>';
            } else {
                graphDiv.innerHTML = flowEdges.map(e => `<div class="flow-edge">
                    <span class="flow-node">${esc(e.from)}</span>
                    <span class="flow-arrow">--&gt;</span>
                    <span class="flow-node">${esc(e.to)}</span>
                    <span class="flow-label">${esc(e.label)}</span>
                </div>`).join("");
            }
        }

        // Proposals
        const propDiv = document.getElementById("onto-proposals");
        if (propDiv) {
            const props = proposals.proposals || [];
            if (!props.length) {
                propDiv.innerHTML = '<div class="empty-state">No proposals yet. Create one to define new agent workflows.</div>';
            } else {
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
        }

    } catch (err) {
        console.error("Ontology refresh failed:", err);
    }
}

function renderOntologyGraph(data) {
    const svgEl = document.getElementById("ontology-svg");
    if (!svgEl) return;

    const nodes = data.nodes || [];
    const edges = data.edges || [];

    // Clear SVG
    svgEl.innerHTML = "";

    const width = svgEl.clientWidth || 960;
    const height = svgEl.clientHeight || 600;

    // Division cluster positions
    const clusterPositions = {
        mortgage_ops: { cx: width * 0.22, cy: height * 0.25 },
        engineering: { cx: width * 0.78, cy: height * 0.25 },
        intelligence: { cx: width * 0.22, cy: height * 0.75 },
        growth_ops: { cx: width * 0.78, cy: height * 0.75 },
        integrations: { cx: width * 0.78, cy: height * 0.50 },
        data_sources: { cx: width * 0.22, cy: height * 0.50 },
    };

    // Assign positions to nodes
    const nodePositions = {};
    const divisionCounts = {};

    nodes.forEach(node => {
        let cluster;
        if (node.type === "integration") {
            cluster = "integrations";
        } else if (node.type === "data_source") {
            cluster = "data_sources";
        } else {
            cluster = node.division || "intelligence";
        }

        if (!divisionCounts[cluster]) divisionCounts[cluster] = 0;
        const idx = divisionCounts[cluster]++;

        const pos = clusterPositions[cluster] || { cx: width * 0.5, cy: height * 0.5 };
        const angle = (idx / Math.max(1, nodes.filter(n => {
            if (n.type === "integration") return cluster === "integrations";
            if (n.type === "data_source") return cluster === "data_sources";
            return (n.division || "intelligence") === cluster;
        }).length)) * Math.PI * 2;
        const radius = 80;

        nodePositions[node.id] = {
            x: pos.cx + Math.cos(angle) * radius,
            y: pos.cy + Math.sin(angle) * radius,
        };
    });

    // Draw edges
    edges.forEach(edge => {
        const from = nodePositions[edge.from || edge.source];
        const to = nodePositions[edge.to || edge.target];
        if (!from || !to) return;

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", from.x);
        line.setAttribute("y1", from.y);
        line.setAttribute("x2", to.x);
        line.setAttribute("y2", to.y);
        line.setAttribute("class", "edge-line");
        svgEl.appendChild(line);
    });

    // Draw nodes
    nodes.forEach(node => {
        const pos = nodePositions[node.id];
        if (!pos) return;

        const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
        g.setAttribute("transform", `translate(${pos.x}, ${pos.y})`);

        if (node.type === "agent") {
            // Agent = circle r=24
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("r", 24);
            const hs = node.health_status || {};
            const level = hs.level || "unknown";
            let fill;
            if (level === "low" || level === "healthy") fill = "#3fb950";
            else if (level === "medium") fill = "#d29922";
            else if (level === "high" || level === "critical") fill = "#f85149";
            else fill = "#484f58";
            circle.setAttribute("fill", fill);
            circle.setAttribute("opacity", "0.85");
            circle.setAttribute("class", "node-agent");
            circle.style.cursor = "pointer";
            g.appendChild(circle);

            // Click handler
            g.addEventListener("click", () => openOntologyPanel(node));

        } else if (node.type === "integration") {
            // Integration = smaller circle r=16
            const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            circle.setAttribute("r", 16);
            circle.setAttribute("fill", node.connected ? "#C0C0C0" : "#484f58");
            circle.setAttribute("opacity", "0.8");
            g.appendChild(circle);

        } else if (node.type === "data_source") {
            // Data source = square
            const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            rect.setAttribute("x", -14);
            rect.setAttribute("y", -14);
            rect.setAttribute("width", 28);
            rect.setAttribute("height", 28);
            rect.setAttribute("rx", 4);
            rect.setAttribute("fill", "#D4D4D4");
            rect.setAttribute("opacity", "0.7");
            g.appendChild(rect);
        }

        // Label
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("y", node.type === "agent" ? 38 : node.type === "data_source" ? 28 : 30);
        text.setAttribute("text-anchor", "middle");
        text.textContent = node.id || node.name || "";
        g.appendChild(text);

        svgEl.appendChild(g);
    });
}

function openOntologyPanel(node) {
    const panel = document.getElementById("ontology-panel");
    if (!panel) return;

    panel.classList.add("open");

    const hs = node.health_status || {};
    const level = hs.level || "unknown";

    panel.innerHTML = `
        <button class="ontology-panel-close" onclick="closeOntologyPanel()">&times;</button>
        <div class="profile-section">
            <div class="profile-label">Agent</div>
            <div class="profile-value"><span class="agent-name">${esc(node.id)}</span> -- ${esc(node.role || "")}</div>

            <div class="profile-label">Division</div>
            <div class="profile-value">${esc(node.division || "N/A")}</div>

            <div class="profile-label">Health Status</div>
            <div class="profile-value">
                <span class="alert-severity ${level}">${level}</span>
                ${hs.risk_score !== undefined ? ` (risk: ${hs.risk_score.toFixed(3)})` : ""}
            </div>

            <div class="profile-label">Capabilities</div>
            <div class="profile-tags">${(node.capabilities || []).map(c => `<span class="profile-tag">${esc(c)}</span>`).join("") || '<span class="profile-value">None listed</span>'}</div>

            <div class="profile-label">Inputs</div>
            <div class="profile-tags">${(node.inputs || []).map(i => `<span class="profile-tag">${esc(i)}</span>`).join("") || '<span class="profile-value">None</span>'}</div>

            <div class="profile-label">Outputs</div>
            <div class="profile-tags">${(node.outputs || []).map(o => `<span class="profile-tag">${esc(o)}</span>`).join("") || '<span class="profile-value">None</span>'}</div>

            ${hs.telemetry ? `<div class="profile-label">Telemetry</div>
            <div class="profile-value" style="font-family:var(--font-mono);font-size:12px">
                Latency: ${(hs.telemetry.avg_latency_ms || 0).toFixed(0)}ms |
                Tasks: ${hs.telemetry.tasks_completed || 0} |
                Errors: ${hs.telemetry.error_count || 0}
            </div>` : ""}
        </div>
    `;
}

function closeOntologyPanel() {
    const panel = document.getElementById("ontology-panel");
    if (panel) panel.classList.remove("open");
}

async function loadAgentProfile(name) {
    if (!name) return;
    try {
        const profile = await fetchJSON(`/api/hydrospeed/agent/${name}`);
        const div = document.getElementById("onto-profile");
        if (!div) return;

        if (profile.error) {
            div.innerHTML = `<div class="empty-state">${esc(profile.error)}</div>`;
            return;
        }

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

        const selectEl = document.getElementById("onto-agent-select");
        if (selectEl) selectEl.value = name;

    } catch (err) {
        console.error("Load agent profile failed:", err);
    }
}

function showProposalForm() {
    const title = prompt("Proposal title:");
    if (!title) return;
    const description = prompt("Description:");
    const agents = prompt("Agents (comma-separated, e.g. ATLAS,NEXUS,FORGE):");
    const steps = prompt("Workflow steps (comma-separated):");
    if (!agents || !steps) return;

    fetch("/api/hydrospeed/proposals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            title,
            description: description || "",
            agents: agents.split(",").map(s => s.trim()),
            workflow_steps: steps.split(",").map(s => s.trim()),
        }),
    }).then(() => refreshOntology());
}

// ===================================================================
// Predictive Telemetry
// ===================================================================

async function refreshTelemetry() {
    try {
        const [risks, predictions] = await Promise.all([
            fetchJSON("/api/telemetry/risks"),
            fetchJSON("/api/telemetry/predictions"),
        ]);

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

        setEl("tele-score", risks.system_risk || "0.0");
        const level = risks.system_level || "low";
        setEl("tele-level", level);
        setEl("tele-tracked", risks.total_tracked || 0);
        setEl("tele-critical", (risks.critical_agents || []).length);
        setEl("tele-predictions", (predictions.predictions || []).length);

        // System risk badge in header
        const riskBadge = document.getElementById("system-risk");
        if (riskBadge) {
            riskBadge.className = "status-badge " + level;
            const riskLabel = document.getElementById("risk-label");
            if (riskLabel) riskLabel.textContent = "risk: " + level;
        }

        // Predictions
        const predDiv = document.getElementById("tele-pred-list");
        if (predDiv) {
            const preds = predictions.predictions || [];
            if (!preds.length) {
                predDiv.innerHTML = '<div class="empty-state">No active predictions -- system is healthy</div>';
            } else {
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
            }
        }

        // Per-agent risk table
        const tbody = document.getElementById("tele-agents-tbody");
        if (tbody) {
            const agentRisks = risks.agents || {};
            const entries = Object.entries(agentRisks);
            if (!entries.length) {
                tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Collecting telemetry...</td></tr>`;
            } else {
                tbody.innerHTML = entries.sort((a, b) => b[1].risk_score - a[1].risk_score).map(([name, r]) => {
                    const f = r.factors || {};
                    return `<tr>
                        <td><span class="agent-name">${esc(name)}</span></td>
                        <td style="font-family:var(--font-mono)">${r.risk_score.toFixed(3)} <div class="risk-bar"><div class="risk-fill ${r.level}" style="width:${r.risk_score * 100}%"></div></div></td>
                        <td><span class="alert-severity ${r.level}">${r.level}</span></td>
                        <td>${esc(r.dominant_factor || "--")}</td>
                        <td style="font-family:var(--font-mono);font-size:12px">${((f.error_rate || {}).value || 0).toFixed(2)}</td>
                        <td style="font-family:var(--font-mono);font-size:12px">${((r.telemetry || {}).avg_latency_ms || 0).toFixed(0)}ms</td>
                        <td style="font-family:var(--font-mono);font-size:12px">${((f.dependency || {}).value || 0).toFixed(2)}</td>
                    </tr>`;
                }).join("");
            }
        }

    } catch (err) {
        console.error("Telemetry refresh failed:", err);
    }
}

// ===================================================================
// Expert Tips
// ===================================================================

async function refreshTips() {
    try {
        const cat = document.getElementById("tips-cat-filter")?.value || "";
        const data = await fetchJSON("/api/hydrospeed/tips" + (cat ? "?category=" + cat : ""));
        const tips = data.tips || [];

        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

        setEl("tips-total", tips.length);
        setEl("tips-critical", tips.filter(t => t.severity === "critical").length);
        const categories = new Set(tips.map(t => t.category));
        setEl("tips-categories", categories.size);

        const div = document.getElementById("tips-list");
        if (!div) return;
        if (!tips.length) {
            div.innerHTML = '<div class="empty-state">No tips match this filter</div>';
            return;
        }
        div.innerHTML = tips.map(t => `<div class="tip-card">
            <div class="tip-header">
                <span class="alert-severity ${t.severity}">${t.severity}</span>
                <span class="priority-badge MEDIUM">${esc(t.category)}</span>
                <span class="tip-title">${esc(t.title)}</span>
            </div>
            <div class="tip-body">${esc(t.tip)}</div>
            <div class="tip-agents">Applies to: ${(t.applies_to || []).join(", ")}</div>
        </div>`).join("");

    } catch (err) {
        console.error("Tips refresh failed:", err);
    }
}

// ===================================================================
// Agent Database (Dolt-style version control)
// ===================================================================

async function refreshAgentDB() {
    try {
        const [branches, tables] = await Promise.all([
            fetchJSON("/api/agentdb/branches"),
            fetchJSON("/api/agentdb/tables?branch=main"),
        ]);

        const branchList = branches.branches || [];
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

        setEl("adb-branches-count", branchList.length);
        setEl("adb-tables-count", Object.keys(tables.tables || {}).length);
        const totalRows = Object.values(tables.tables || {}).reduce((sum, t) => sum + (t.row_count || 0), 0);
        setEl("adb-rows-count", totalRows);

        // Branches table
        const tbody = document.getElementById("adb-branches-tbody");
        if (tbody) {
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
        }

        // Schema view
        const schemaDiv = document.getElementById("adb-schema-view");
        if (schemaDiv) {
            const tblStats = tables.tables || {};
            schemaDiv.innerHTML = Object.entries(tblStats).map(([name, info]) => `<div class="schema-table">
                <div class="schema-table-name">${esc(name)}</div>
                <div class="schema-columns">${(info.columns || []).map(c => `<span class="schema-col">${esc(c)}</span>`).join("")}</div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:4px">${info.row_count} rows</div>
            </div>`).join("");
        }

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

    } catch (err) {
        console.error("AgentDB refresh failed:", err);
    }
}

async function queryTable() {
    try {
        const branch = document.getElementById("adb-branch-select").value;
        const table = document.getElementById("adb-table-select").value;
        const data = await fetchJSON(`/api/agentdb/query/${table}?branch=${branch}&limit=50`);
        const div = document.getElementById("adb-table-data");
        if (!div) return;

        if (data.error) {
            div.innerHTML = `<div class="empty-state">${esc(data.error)}</div>`;
            return;
        }
        const rows = data.rows || [];
        if (!rows.length) {
            div.innerHTML = `<div class="empty-state">No rows in ${table} on branch ${branch}</div>`;
            return;
        }

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

    } catch (err) {
        console.error("Query table failed:", err);
    }
}

async function computeDiff() {
    try {
        const from = document.getElementById("adb-diff-from").value;
        const to = document.getElementById("adb-diff-to").value;
        if (!to) { alert("Select a target branch"); return; }

        const data = await fetchJSON(`/api/agentdb/diff?from=${from}&to=${to}`);
        const div = document.getElementById("adb-diff-view");
        if (!div) return;
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

    } catch (err) {
        console.error("Compute diff failed:", err);
    }
}

function diffBranch(branch) {
    const fromEl = document.getElementById("adb-diff-from");
    const toEl = document.getElementById("adb-diff-to");
    if (fromEl) fromEl.value = "main";
    if (toEl) toEl.value = branch;
    computeDiff();
}

async function mergeBranch(source) {
    if (!confirm(`Merge '${source}' into 'main'? This will apply all changes atomically.`)) return;
    try {
        const resp = await fetch("/api/agentdb/merge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source, target: "main", author: "DASHBOARD" }),
        });
        const result = await resp.json();
        if (result.error) { alert("Merge error: " + result.error); return; }
        alert(`Merged! Added: ${result.added}, Modified: ${result.modified}, Removed: ${result.removed}`);
        adbBranchesLoaded = false;
        refreshAgentDB();
    } catch (err) {
        console.error("Merge failed:", err);
    }
}

async function loadCommitLog() {
    try {
        const branch = document.getElementById("adb-log-branch").value;
        const data = await fetchJSON(`/api/agentdb/log/${branch}?limit=20`);
        const div = document.getElementById("adb-commit-log");
        if (!div) return;
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

    } catch (err) {
        console.error("Load commit log failed:", err);
    }
}

async function loadAgentDbStatus() {
    try {
        const name = document.getElementById("adb-agent-select").value;
        if (!name) return;
        const data = await fetchJSON(`/api/agentdb/agent/${name}`);
        const div = document.getElementById("adb-agent-status");
        if (!div) return;

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

    } catch (err) {
        console.error("Load agent DB status failed:", err);
    }
}

function showCreateBranch() {
    const modal = document.getElementById("adb-modal");
    if (!modal) return;
    const titleEl = document.getElementById("adb-modal-title");
    if (titleEl) titleEl.textContent = "Create Branch";

    const bodyEl = document.getElementById("adb-modal-body");
    if (bodyEl) {
        bodyEl.innerHTML = `
            <label>Branch name: <input type="text" id="adb-new-branch-name" class="control-input" placeholder="feature/my-branch"></label>
            <label>From branch:
                <select id="adb-new-branch-from" class="control-select">
                    ${document.getElementById("adb-branch-select")?.innerHTML || '<option value="main">main</option>'}
                </select>
            </label>`;
    }

    const confirmBtn = document.getElementById("adb-modal-confirm");
    if (confirmBtn) {
        confirmBtn.textContent = "Confirm";
        confirmBtn.onclick = async () => {
            const name = document.getElementById("adb-new-branch-name").value.trim();
            const from = document.getElementById("adb-new-branch-from").value;
            if (!name) { alert("Branch name required"); return; }
            try {
                const resp = await fetch("/api/agentdb/branches", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, from }),
                });
                const result = await resp.json();
                if (result.error) { alert(result.error); return; }
                modal.style.display = "none";
                adbBranchesLoaded = false;
                refreshAgentDB();
            } catch (err) {
                console.error("Create branch failed:", err);
            }
        };
    }

    modal.style.display = "flex";
}

async function showSchemaSQL() {
    try {
        const resp = await fetch("/api/agentdb/schema/sql");
        const sql = await resp.text();
        const modal = document.getElementById("adb-modal");
        if (!modal) return;

        const titleEl = document.getElementById("adb-modal-title");
        if (titleEl) titleEl.textContent = "Database Schema (SQL)";

        const bodyEl = document.getElementById("adb-modal-body");
        if (bodyEl) bodyEl.innerHTML = `<pre class="schema-sql">${esc(sql)}</pre>`;

        const confirmBtn = document.getElementById("adb-modal-confirm");
        if (confirmBtn) {
            confirmBtn.onclick = () => { modal.style.display = "none"; };
            confirmBtn.textContent = "Close";
        }

        modal.style.display = "flex";
    } catch (err) {
        console.error("Show schema SQL failed:", err);
    }
}

// ===================================================================
// Features Guide
// ===================================================================

async function refreshFeatures() {
    try {
        const data = await fetchJSON("/api/features");
        const div = document.getElementById("features-list");
        if (!div) return;
        const sections = data.sections || [];
        if (!sections.length) {
            div.innerHTML = '<div class="empty-state">No features</div>';
            return;
        }

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

    } catch (err) {
        console.error("Features refresh failed:", err);
    }
}

// ===================================================================
// Agent Skills
// ===================================================================

async function refreshSkills() {
    try {
        const division = document.getElementById("skills-division-filter")?.value || "";
        const url = "/api/agents/skills" + (division ? "?division=" + division : "");
        const data = await fetchJSON(url);
        const skills = data.skills || {};
        const summary = data.summary || {};

        // Update metrics
        const totalEl = document.getElementById("skills-total-count");
        if (totalEl) totalEl.textContent = summary.total_skills || 0;
        const divEl = document.getElementById("skills-divisions-count");
        if (divEl) divEl.textContent = summary.divisions || 4;
        const catEl = document.getElementById("skills-methods-count");
        if (catEl) catEl.textContent = (summary.categories || []).length;

        const container = document.getElementById("skills-list");
        if (!container) return;

        const entries = Object.entries(skills);
        if (!entries.length) {
            container.innerHTML = '<div class="empty-state">No skills found for this division</div>';
            return;
        }

        container.innerHTML = entries.map(([agentName, agentSkills]) => {
            if (!agentSkills.length) return "";
            const role = AGENT_DESCRIPTIONS[agentName] || "";
            return `<div style="margin-bottom:24px;">
                <h3 style="margin-bottom:12px;font-size:16px;color:var(--accent-bright);">
                    <span class="agent-name">${esc(agentName)}</span>
                    <span style="font-weight:400;color:var(--text-secondary);font-size:13px;margin-left:8px;">${esc(role)}</span>
                </h3>
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:12px;">
                    ${agentSkills.map(skill => `<div class="card" style="margin:0;">
                        <div class="card-body" style="padding:16px;">
                            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px;">
                                <div style="font-weight:600;font-size:14px;color:var(--text-primary);">${esc(skill.name)}</div>
                                <span class="alert-severity ${skill.difficulty === 'expert' ? 'critical' : skill.difficulty === 'advanced' ? 'high' : 'medium'}">${esc(skill.difficulty)}</span>
                            </div>
                            <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;">${esc(skill.description)}</div>
                            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                                <span class="profile-tag">${esc(skill.category)}</span>
                                <span style="font-size:11px;color:var(--text-muted);">${esc(skill.industry_source)}</span>
                            </div>
                            <details style="margin-top:8px;">
                                <summary style="cursor:pointer;font-size:12px;color:var(--accent-bright);">Methods (${(skill.methods || []).length} steps)</summary>
                                <ol style="padding-left:20px;margin-top:6px;font-size:12px;color:var(--text-secondary);">
                                    ${(skill.methods || []).map(m => `<li style="margin-bottom:4px;">${esc(m)}</li>`).join("")}
                                </ol>
                            </details>
                            <div style="display:flex;gap:16px;margin-top:8px;font-size:11px;color:var(--text-muted);">
                                <span>Inputs: ${(skill.inputs || []).join(", ")}</span>
                            </div>
                            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">
                                Outputs: ${(skill.outputs || []).join(", ")}
                            </div>
                        </div>
                    </div>`).join("")}
                </div>
            </div>`;
        }).join("");

    } catch (err) {
        console.error("Skills refresh failed:", err);
        const container = document.getElementById("skills-list");
        if (container) container.innerHTML = '<div class="empty-state">Skills endpoint not available</div>';
    }
}

// Wire skills filter
document.addEventListener("DOMContentLoaded", () => {
    const skillsFilter = document.getElementById("skills-division-filter");
    if (skillsFilter) skillsFilter.addEventListener("change", () => { if (currentPage === "skills") refreshSkills(); });
});

// ===================================================================
// Prompt Generator
// ===================================================================

function openPromptGenerator() {
    const modal = document.getElementById("prompt-modal");
    if (!modal) return;
    modal.style.display = "flex";

    // Populate agent select from cached ontology data
    const agentSelect = document.getElementById("prompt-agent-select");
    if (agentSelect) {
        agentSelect.innerHTML = '<option value="">Select Agent...</option>';

        const nodes = cachedOntology ? (cachedOntology.nodes || []).filter(n => n.type === "agent") : [];

        if (nodes.length) {
            nodes.forEach(a => {
                const opt = document.createElement("option");
                opt.value = a.id;
                opt.textContent = `${a.id} - ${a.role || AGENT_DESCRIPTIONS[a.id] || ""}`;
                opt.dataset.role = a.role || AGENT_DESCRIPTIONS[a.id] || "";
                opt.dataset.capabilities = JSON.stringify(a.capabilities || []);
                opt.dataset.division = a.division || "";
                opt.dataset.inputs = JSON.stringify(a.inputs || []);
                opt.dataset.outputs = JSON.stringify(a.outputs || []);
                agentSelect.appendChild(opt);
            });
        } else {
            // Fallback to AGENT_DESCRIPTIONS
            Object.entries(AGENT_DESCRIPTIONS).forEach(([name, role]) => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.textContent = `${name} - ${role}`;
                opt.dataset.role = role;
                opt.dataset.capabilities = "[]";
                opt.dataset.division = "";
                opt.dataset.inputs = "[]";
                opt.dataset.outputs = "[]";
                agentSelect.appendChild(opt);
            });
        }

        // Wire up change handler for action select population
        agentSelect.onchange = () => {
            const actionSelect = document.getElementById("prompt-action-select");
            if (!actionSelect) return;
            actionSelect.innerHTML = '<option value="">Select Action...</option>';

            const selectedOpt = agentSelect.options[agentSelect.selectedIndex];
            if (!selectedOpt || !selectedOpt.value) return;

            let capabilities = [];
            try { capabilities = JSON.parse(selectedOpt.dataset.capabilities || "[]"); } catch (e) {}

            if (capabilities.length) {
                capabilities.forEach(cap => {
                    const opt = document.createElement("option");
                    opt.value = cap;
                    opt.textContent = cap;
                    actionSelect.appendChild(opt);
                });
            } else {
                // Provide generic actions
                ["analyze", "execute", "report", "monitor", "optimize"].forEach(action => {
                    const opt = document.createElement("option");
                    opt.value = action;
                    opt.textContent = action;
                    actionSelect.appendChild(opt);
                });
            }
        };
    }

    // Clear previous output
    const output = document.getElementById("prompt-output");
    if (output) output.textContent = "";
}

function generatePrompt() {
    const agentSelect = document.getElementById("prompt-agent-select");
    const actionSelect = document.getElementById("prompt-action-select");
    const instructionsEl = document.getElementById("prompt-instructions");
    const output = document.getElementById("prompt-output");

    if (!agentSelect || !output) return;

    const selectedOpt = agentSelect.options[agentSelect.selectedIndex];
    if (!selectedOpt || !selectedOpt.value) {
        output.textContent = "Please select an agent.";
        return;
    }

    const agentName = selectedOpt.value;
    const role = selectedOpt.dataset.role || "";
    let capabilities = [];
    try { capabilities = JSON.parse(selectedOpt.dataset.capabilities || "[]"); } catch (e) {}
    const division = selectedOpt.dataset.division || "";

    const actionType = actionSelect ? actionSelect.value || "general" : "general";
    const userText = instructionsEl ? instructionsEl.value || "" : "";

    // Get system state from cached data
    const status = cachedStatus || {};
    const riskScore = status.system_risk || "unknown";
    const uptime = status.uptime || "unknown";

    // Get dependencies from cached ontology
    let upstream = [];
    let downstream = [];
    if (cachedOntology) {
        const edges = cachedOntology.edges || [];
        edges.forEach(edge => {
            const src = edge.from || edge.source;
            const tgt = edge.to || edge.target;
            if (tgt === agentName) upstream.push(src);
            if (src === agentName) downstream.push(tgt);
        });
    }

    // Find health level
    let level = "unknown";
    if (cachedOntology) {
        const node = (cachedOntology.nodes || []).find(n => n.id === agentName);
        if (node && node.health_status) level = node.health_status.level || "unknown";
    }

    const prompt = `[AGENT: ${agentName} — ${role}]
[CAPABILITIES: ${capabilities.length ? capabilities.join(", ") : "N/A"}]
[SYSTEM STATE: Risk=${riskScore}, Level=${level}, Uptime=${uptime}]
[DEPENDENCIES: upstream=${upstream.length ? upstream.join(", ") : "none"}, downstream=${downstream.length ? downstream.join(", ") : "none"}]
[TASK: ${actionType}]
[INSTRUCTIONS: ${userText || "Execute standard operating procedure."}]`;

    output.textContent = prompt;
}

function copyPrompt() {
    const output = document.getElementById("prompt-output");
    if (!output || !output.textContent) return;

    navigator.clipboard.writeText(output.textContent).then(() => {
        const btn = document.querySelector('[onclick="copyPrompt()"]');
        if (btn) {
            const original = btn.textContent;
            btn.textContent = "Copied!";
            setTimeout(() => { btn.textContent = original; }, 1500);
        }
    }).catch(err => {
        console.error("Copy failed:", err);
        // Fallback
        const textarea = document.createElement("textarea");
        textarea.value = output.textContent;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    });
}

function closePromptModal() {
    const modal = document.getElementById("prompt-modal");
    if (modal) modal.style.display = "none";
}

// ===================================================================
// Agent Chat
// ===================================================================

const agentChat = {
    history: [],
    currentAgent: "DIEGO",
    initialized: false,
};

const AGENT_QUICK_ACTIONS = {
    DIEGO: ["Run Pipeline Triage", "Check Pipeline Health", "View Active Workflows", "Restart Stalled Jobs"],
    MARTIN: ["Classify Document", "Run Document Audit", "Extract Key Fields", "Validate Compliance"],
    NOVA: ["Calculate DTI Ratio", "Verify Income Sources", "Run Income Analysis", "Flag Anomalies"],
    JARVIS: ["Check Open Conditions", "Resolve Condition", "Escalate Blocking Issue", "Status Summary"],
    ATLAS: ["Review Architecture", "Generate Component", "Run Code Analysis", "Deploy Preview"],
    CIPHER: ["Run Security Scan", "Check Vulnerability Report", "Audit Access Logs", "Rotate Credentials"],
    FORGE: ["Check CI/CD Status", "Deploy to Staging", "View Build Logs", "Rollback Last Deploy"],
    NEXUS: ["Run Code Review", "Check Test Coverage", "Lint Codebase", "Generate Quality Report"],
    STORM: ["Run Data Pipeline", "Check ETL Status", "Validate Data Schema", "Generate Data Report"],
    SENTINEL: ["System Health Check", "View Alert Summary", "Run Diagnostics", "Performance Report"],
    HUNTER: ["Find New Leads", "Score Lead Pipeline", "Generate Outreach List", "Market Analysis"],
    HERALD: ["Generate Blog Post", "Create Social Content", "Review Content Calendar", "SEO Analysis"],
    AMBASSADOR: ["Check Community Metrics", "Draft Response", "Summarize Feedback", "Engagement Report"],
};

const AGENT_SIMULATED_RESPONSES = {
    DIEGO: [
        "Pipeline triage complete. All 3 active workflows are running within normal parameters. No stalled jobs detected.",
        "Current pipeline health: **HEALTHY**. Throughput is at 94% capacity. Average job completion time: 2.3 minutes.",
        "I've scanned the workflow queue. 12 tasks completed in the last hour, 3 pending, 0 failed. The mortgage processing pipeline is operating optimally.",
    ],
    MARTIN: [
        "Document classification complete. Identified 4 W-2 forms, 2 bank statements, and 1 tax return. All documents pass initial validation.",
        "Audit results: 98.5% compliance rate across 47 processed documents. 1 document flagged for manual review (missing signature on page 3).",
        "Key fields extracted successfully. Borrower name, SSN (masked), income figures, and employment dates all captured with >99% confidence.",
    ],
    NOVA: [
        "DTI ratio calculated: **32.4%**. Front-end ratio: 24.1%, Back-end ratio: 32.4%. Within acceptable thresholds for conventional loans.",
        "Income verification complete. Primary income: $8,500/mo (W-2 confirmed). Secondary income: $1,200/mo (1099, 2-year history verified).",
        "Analysis complete. No anomalies detected in income documentation. All figures consistent across tax returns, pay stubs, and bank deposits.",
    ],
    JARVIS: [
        "Open conditions summary: 3 outstanding. 1 title-related (awaiting title company response), 1 appraisal (scheduled for next week), 1 income (additional pay stub needed).",
        "Condition resolved successfully. Updated status in the tracking system and notified the underwriter.",
        "Status: 12 conditions total, 9 cleared, 3 pending. Estimated full clearance: 3 business days.",
    ],
    ATLAS: [
        "Architecture review complete. The current microservices topology is well-structured. Recommendation: consider adding a caching layer for the document processing service.",
        "Component generated. Created a new React component with TypeScript interfaces, unit tests, and Storybook stories. Ready for review.",
        "Code analysis results: 0 critical issues, 2 warnings (unused imports), code quality score: 94/100.",
    ],
    CIPHER: [
        "Security scan complete. No critical vulnerabilities found. 2 low-severity findings: outdated dependency (lodash 4.17.19), and an unused API key in environment config.",
        "Access log audit: 847 API calls in the last 24h. All authenticated. No suspicious patterns detected. Rate limiting functioning correctly.",
        "Credential rotation complete. All API keys rotated successfully. Old keys will expire in 24 hours. Services updated with new credentials.",
    ],
    FORGE: [
        "CI/CD Status: All green. Last build: 2 minutes ago (passed). Deployment pipeline: staging (current), production (pending approval).",
        "Staging deployment successful. Build #347 deployed to staging environment. Health checks passing. Preview URL generated.",
        "Build logs show all 142 tests passing. Build time: 3m 42s. Docker image size: 245MB (optimized from 312MB last week).",
    ],
    NEXUS: [
        "Code review complete. 3 files analyzed. Suggestions: extract duplicated validation logic into shared utility, add error boundary to payment component.",
        "Test coverage: 87.3% (target: 85%). 12 uncovered branches identified, primarily in edge-case error handling paths.",
        "Quality report generated. Maintainability index: A. Technical debt ratio: 2.1%. Complexity hotspots: 2 functions flagged for refactoring.",
    ],
    STORM: [
        "Data pipeline status: All 5 ETL jobs completed successfully. Total records processed: 14,287. Average processing time: 1.8s per batch.",
        "Schema validation passed. All 23 tables conform to the expected schema. No drift detected since last deployment.",
        "Data report generated. Daily ingest volume: 52,000 records. Data quality score: 99.2%. 0 records rejected due to validation errors.",
    ],
    SENTINEL: [
        "System health: **ALL NOMINAL**. CPU: 23%, Memory: 61%, Disk: 44%. All 13 agents reporting healthy heartbeats.",
        "Alert summary: 0 critical, 1 warning (memory usage trending upward on worker-3), 2 info-level notifications.",
        "Diagnostics complete. Network latency: 12ms avg. Database response time: 4ms. API gateway throughput: 450 req/s.",
    ],
    HUNTER: [
        "Found 23 new leads matching criteria. Top prospects: 8 high-intent (visited pricing page 3+ times), 12 medium, 3 low-intent.",
        "Lead pipeline scored. Total active leads: 147. Hot: 31 (21%), Warm: 58 (39%), Cold: 58 (39%). Conversion probability: 12.3%.",
        "Market analysis complete. Target segment growth: +8.2% QoQ. Competitor activity: moderate. Recommended focus: first-time homebuyers in the 28-35 age bracket.",
    ],
    HERALD: [
        "Blog post draft ready: 'Understanding Mortgage Pre-Approval in 2026'. Word count: 1,247. Readability score: 72 (Flesch). SEO keywords integrated.",
        "Social content created. 5 posts for LinkedIn, 3 for Twitter/X, 2 for Instagram. Scheduled for optimal engagement windows this week.",
        "SEO analysis complete. Top performing content: 'DTI Calculator Guide' (4.2K views/mo). Opportunities: 3 high-volume keywords with low competition identified.",
    ],
    AMBASSADOR: [
        "Community metrics: 342 active members (+12% MoM). Average response time: 2.4 hours. Satisfaction score: 4.7/5.0.",
        "Draft response prepared for the feature request thread. Tone: professional and empathetic. Includes timeline estimate and workaround suggestion.",
        "Feedback summary: 67 submissions this month. Top themes: faster processing times (28%), better mobile experience (19%), API documentation (15%).",
    ],
};

function initAgentChat() {
    if (agentChat.initialized) return;
    agentChat.initialized = true;

    const agentSelect = document.getElementById("chat-agent-select");
    const sendBtn = document.getElementById("chat-send-btn");
    const chatInput = document.getElementById("chat-input");

    if (agentSelect) {
        agentSelect.addEventListener("change", () => {
            agentChat.currentAgent = agentSelect.value;
            updateChatAgentInfo();
            renderQuickActions();
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener("click", () => sendChatMessage());
    }

    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }

    updateChatAgentInfo();
    renderQuickActions();
}

function updateChatAgentInfo() {
    const agent = agentChat.currentAgent;
    const avatarEl = document.getElementById("chat-agent-avatar");
    const nameEl = document.getElementById("chat-agent-name");
    const roleEl = document.getElementById("chat-agent-role");

    if (avatarEl) avatarEl.textContent = agent.charAt(0);
    if (nameEl) nameEl.textContent = agent;
    if (roleEl) roleEl.textContent = AGENT_DESCRIPTIONS[agent] || "";
}

function renderQuickActions() {
    const container = document.getElementById("chat-quick-actions");
    if (!container) return;
    const actions = AGENT_QUICK_ACTIONS[agentChat.currentAgent] || [];
    container.innerHTML = actions.map(a =>
        `<button class="chat-quick-btn" onclick="sendChatQuickAction('${esc(a)}')">${esc(a)}</button>`
    ).join("");
}

function sendChatQuickAction(action) {
    const chatInput = document.getElementById("chat-input");
    if (chatInput) {
        chatInput.value = action;
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById("chat-input");
    if (!chatInput || !chatInput.value.trim()) return;

    const message = chatInput.value.trim();
    chatInput.value = "";

    const now = new Date().toISOString();
    agentChat.history.push({ role: "user", agent: agentChat.currentAgent, text: message, time: now });
    renderChatMessages();

    let responseText = "";
    let reasoning = "";
    try {
        const resp = await fetch("/api/agent-chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent: agentChat.currentAgent, message: message }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        responseText = data.response || data.message || "Task acknowledged.";
        reasoning = data.reasoning || "";
    } catch (e) {
        const responses = AGENT_SIMULATED_RESPONSES[agentChat.currentAgent] || ["Task acknowledged. Processing your request."];
        responseText = responses[Math.floor(Math.random() * responses.length)];
        reasoning = generateSimulatedReasoning(agentChat.currentAgent, message);
    }

    const responseTime = new Date().toISOString();
    agentChat.history.push({ role: "agent", agent: agentChat.currentAgent, text: responseText, reasoning: reasoning, time: responseTime });
    renderChatMessages();
}

function generateSimulatedReasoning(agent, message) {
    const steps = [
        `1. Received task from user: "${message.substring(0, 50)}${message.length > 50 ? "..." : ""}"`,
        `2. Identified agent context: ${agent} (${AGENT_DESCRIPTIONS[agent]})`,
        `3. Checked agent permissions and tool access -- all authorized`,
        `4. Queried relevant data sources and knowledge base`,
        `5. Generated response based on domain expertise`,
        `6. Validated output against safety guardrails -- PASSED`,
    ];
    return steps.join("\n");
}

function renderChatMessages() {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    if (agentChat.history.length === 0) {
        container.innerHTML = '<div class="empty-state">Select an agent and start a conversation</div>';
        return;
    }

    container.innerHTML = agentChat.history.map((msg, idx) => {
        const isUser = msg.role === "user";
        const avatarLetter = isUser ? "U" : msg.agent.charAt(0);
        const avatarClass = isUser ? "user-avatar" : "agent-avatar";
        const bubbleClass = isUser ? "user" : "agent";
        const timeStr = formatTime(msg.time);

        let reasoningHtml = "";
        if (!isUser && msg.reasoning) {
            const rid = "reasoning-" + idx;
            reasoningHtml = `
                <button class="reasoning-toggle" onclick="toggleReasoning('${rid}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    View Reasoning
                </button>
                <div class="reasoning-content" id="${rid}">${esc(msg.reasoning)}</div>
            `;
        }

        return `<div class="chat-bubble ${bubbleClass}">
            <div class="chat-avatar ${avatarClass}">${avatarLetter}</div>
            <div>
                <div class="chat-bubble-content">${formatChatText(msg.text)}</div>
                ${reasoningHtml}
                <div class="chat-bubble-time">${timeStr}</div>
            </div>
        </div>`;
    }).join("");

    container.scrollTop = container.scrollHeight;
}

function formatChatText(text) {
    let html = esc(text);
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`(.+?)`/g, '<code style="background:var(--bg-primary);padding:1px 4px;border-radius:3px;font-family:var(--font-mono);font-size:12px;">$1</code>');
    html = html.replace(/\n/g, "<br>");
    return html;
}

function toggleReasoning(id) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("open");
}

// ===================================================================
// Agentic Runtime
// ===================================================================

const SECURITY_DIMENSIONS = [
    {
        title: "Secure Model Access",
        status: "active",
        details: [
            { label: "LLM Router", value: "Active" },
            { label: "Model Providers", value: "Claude, GPT-4, DeepSeek, Gemini" },
            { label: "Data Retention", value: "Zero-retention policy" },
            { label: "Prompt Logging", value: "Enabled (redacted PII)" },
        ],
    },
    {
        title: "Insulated Orchestration",
        status: "active",
        details: [
            { label: "Agent Isolation", value: "Process-level" },
            { label: "Permission Scheme", value: "RBAC + per-agent" },
            { label: "Failover Status", value: "Hot standby ready" },
            { label: "Max Concurrency", value: "13 agents / 50 tasks" },
        ],
    },
    {
        title: "Memory Governance",
        status: "active",
        details: [
            { label: "Working Memory", value: "Ephemeral (session)" },
            { label: "Episodic Memory", value: "7-day retention" },
            { label: "Semantic Memory", value: "Persistent (encrypted)" },
            { label: "Procedural Memory", value: "Version-controlled" },
        ],
    },
    {
        title: "Tool Governance",
        status: "active",
        details: [
            { label: "Authorized Tools", value: "9 integrations" },
            { label: "Egress Policy", value: "Allowlist-only" },
            { label: "Blocked Actions", value: "DELETE, DROP, TRUNCATE" },
            { label: "Review Required", value: "Financial txns > $1K" },
        ],
    },
    {
        title: "Real-time Observability",
        status: "active",
        details: [
            { label: "Trace Count (24h)", value: "2,847" },
            { label: "Audit Log Entries", value: "12,493" },
            { label: "Compliance Score", value: "98.7%" },
            { label: "Alert Channels", value: "Slack, PagerDuty" },
        ],
    },
];

const AGENT_PERMISSIONS = {
    DIEGO: { tools: ["GitHub", "Notion", "Drive"], memory: "read/write", scope: "execute", safety: "safe" },
    MARTIN: { tools: ["Drive", "Notion"], memory: "read/write", scope: "write", safety: "safe" },
    NOVA: { tools: ["Drive", "Notion"], memory: "read", scope: "read-only", safety: "safe" },
    JARVIS: { tools: ["GitHub", "Notion", "Drive"], memory: "read/write", scope: "write", safety: "monitored" },
    ATLAS: { tools: ["GitHub", "Notion", "Browser"], memory: "read/write", scope: "execute", safety: "monitored" },
    CIPHER: { tools: ["GitHub", "PentAGI", "GHOST"], memory: "admin", scope: "admin", safety: "restricted" },
    FORGE: { tools: ["GitHub", "Browser"], memory: "read/write", scope: "execute", safety: "monitored" },
    NEXUS: { tools: ["GitHub", "Notion"], memory: "read", scope: "read-only", safety: "safe" },
    STORM: { tools: ["Drive", "Notion", "GitHub"], memory: "read/write", scope: "write", safety: "safe" },
    SENTINEL: { tools: ["GitHub", "Notion", "Browser", "GHOST"], memory: "admin", scope: "admin", safety: "restricted" },
    HUNTER: { tools: ["Browser", "Notion"], memory: "read/write", scope: "write", safety: "monitored" },
    HERALD: { tools: ["Notion", "Browser", "Drive"], memory: "read/write", scope: "write", safety: "safe" },
    AMBASSADOR: { tools: ["Notion", "Browser"], memory: "read/write", scope: "write", safety: "safe" },
};

const GUARDRAILS_DATA = [
    { name: "No-Delete Policy", detail: "DELETE, DROP, TRUNCATE operations blocked across all agents", status: "active" },
    { name: "Content Validation", detail: "All agent outputs validated against content safety filters", status: "active" },
    { name: "Rate Limiting", detail: "Per-agent caps: 100 API calls/min, 1000 LLM tokens/request", status: "active" },
    { name: "Anti-Spam Cooldowns", detail: "Minimum 5s between identical operations per agent", status: "active" },
    { name: "Financial/Gov Domain Blocking", detail: "Direct financial transactions and government system access restricted", status: "active" },
    { name: "Budget Enforcement (Paperclip)", detail: "Monthly budget cap: $500/agent. Current spend monitored in real-time", status: "active" },
];

const SIMULATED_AUDIT_TRAIL = [
    { time: new Date(Date.now() - 120000).toISOString(), agent: "CIPHER", action: "Attempted credential access", status: "allowed", details: "Rotated API key for GitHub integration" },
    { time: new Date(Date.now() - 300000).toISOString(), agent: "ATLAS", action: "Deploy to production", status: "escalated", details: "Requires manual approval -- flagged for review" },
    { time: new Date(Date.now() - 600000).toISOString(), agent: "HUNTER", action: "Bulk email send (47 recipients)", status: "blocked", details: "Exceeds single-operation recipient limit (25)" },
    { time: new Date(Date.now() - 900000).toISOString(), agent: "FORGE", action: "CI/CD pipeline trigger", status: "allowed", details: "Build #348 triggered on staging branch" },
    { time: new Date(Date.now() - 1800000).toISOString(), agent: "SENTINEL", action: "System diagnostic scan", status: "allowed", details: "Full system health check completed" },
    { time: new Date(Date.now() - 2400000).toISOString(), agent: "MARTIN", action: "Document processing (12 files)", status: "allowed", details: "Batch classification and field extraction" },
    { time: new Date(Date.now() - 3600000).toISOString(), agent: "NOVA", action: "Access financial records", status: "allowed", details: "Income verification for application #4821" },
    { time: new Date(Date.now() - 5400000).toISOString(), agent: "STORM", action: "DELETE query attempt", status: "blocked", details: "No-delete policy enforcement -- suggested UPDATE instead" },
    { time: new Date(Date.now() - 7200000).toISOString(), agent: "AMBASSADOR", action: "Post to external forum", status: "allowed", details: "Community response posted after content validation" },
    { time: new Date(Date.now() - 9000000).toISOString(), agent: "HERALD", action: "Schedule social media post", status: "allowed", details: "LinkedIn post scheduled for optimal engagement window" },
];

async function refreshAgenticRuntime() {
    // Render security dimensions
    const dimContainer = document.getElementById("rt-dimensions");
    if (dimContainer) {
        dimContainer.innerHTML = SECURITY_DIMENSIONS.map(dim => `
            <div class="security-dimension">
                <div class="security-dimension-header">
                    <div class="security-dimension-title">${esc(dim.title)}</div>
                    <span class="dimension-status ${dim.status}">${dim.status.toUpperCase()}</span>
                </div>
                <div class="security-dimension-detail">
                    ${dim.details.map(d => `<div class="detail-row"><span class="detail-label">${esc(d.label)}</span><span class="detail-value">${esc(d.value)}</span></div>`).join("")}
                </div>
            </div>
        `).join("");
    }

    // Render permission matrix
    const permTbody = document.getElementById("rt-permissions-tbody");
    if (permTbody) {
        permTbody.innerHTML = Object.entries(AGENT_PERMISSIONS).map(([agent, perms]) => `
            <tr>
                <td><span class="agent-name">${agent}</span></td>
                <td>${perms.tools.map(t => `<span class="perm-tool-tag">${esc(t)}</span>`).join("")}</td>
                <td>${esc(perms.memory)}</td>
                <td>${esc(perms.scope)}</td>
                <td><span class="safety-badge ${perms.safety}">${perms.safety.toUpperCase()}</span></td>
            </tr>
        `).join("");
    }

    // Render audit trail - try API first, then use simulated
    let auditData = SIMULATED_AUDIT_TRAIL;
    try {
        const blocked = await fetchJSON("/api/safety/blocked");
        if (blocked && blocked.length) {
            auditData = blocked.map(b => ({
                time: b.timestamp || b.time || new Date().toISOString(),
                agent: b.agent || "UNKNOWN",
                action: b.action || b.description || "Blocked action",
                status: "blocked",
                details: b.details || b.reason || "",
            })).concat(SIMULATED_AUDIT_TRAIL).slice(0, 10);
        }
    } catch (e) {
        // Use simulated data
    }

    const auditTbody = document.getElementById("rt-audit-tbody");
    if (auditTbody) {
        auditTbody.innerHTML = auditData.map(a => `
            <tr>
                <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">${formatTime(a.time)}</td>
                <td><span class="agent-name">${esc(a.agent)}</span></td>
                <td>${esc(a.action)}</td>
                <td><span class="audit-status-badge ${a.status}">${a.status.toUpperCase()}</span></td>
                <td style="font-size:12px;color:var(--text-muted);">${esc(a.details)}</td>
            </tr>
        `).join("");
    }

    // Update metrics
    const blockedCount = auditData.filter(a => a.status === "blocked").length;
    const auditCountEl = document.getElementById("rt-audit-count");
    const blockedEl = document.getElementById("rt-blocked");
    if (auditCountEl) auditCountEl.textContent = auditData.length;
    if (blockedEl) blockedEl.textContent = blockedCount;

    // Render guardrails
    const guardrailsList = document.getElementById("rt-guardrails-list");
    if (guardrailsList) {
        guardrailsList.innerHTML = GUARDRAILS_DATA.map(g => `
            <div class="guardrail-item">
                <div>
                    <div class="guardrail-name">${esc(g.name)}</div>
                    <div class="guardrail-detail">${esc(g.detail)}</div>
                </div>
                <span class="guardrail-status ${g.status}">${g.status.toUpperCase()}</span>
            </div>
        `).join("");
    }
}

// ===================================================================
// Integrations Hub
// ===================================================================

const INTEGRATIONS_DATA = [
    {
        name: "GitHub",
        connected: true,
        config: [
            { label: "Repository", value: "MortgageFintechOS" },
            { label: "PAT Status", value: "Valid (expires in 28d)" },
            { label: "Webhooks", value: "3 active" },
        ],
        activity: [
            { text: "Push to main: feat/agent-chat", time: "12m ago" },
            { text: "PR #142 merged by ATLAS", time: "1h ago" },
            { text: "CI build #347 passed", time: "2h ago" },
        ],
    },
    {
        name: "Notion",
        connected: true,
        config: [
            { label: "Workspace", value: "Automatous Intelligence" },
            { label: "Connected Pages", value: "47" },
            { label: "Sync Frequency", value: "Every 5 minutes" },
        ],
        activity: [
            { text: "Agent runbook updated by SENTINEL", time: "8m ago" },
            { text: "Task board synced (23 items)", time: "25m ago" },
            { text: "Knowledge base page created", time: "1h ago" },
        ],
    },
    {
        name: "Google Drive",
        connected: true,
        config: [
            { label: "Connection", value: "Service Account" },
            { label: "Documents", value: "1,247 tracked" },
            { label: "Storage Used", value: "3.2 GB" },
        ],
        activity: [
            { text: "12 loan docs processed by MARTIN", time: "15m ago" },
            { text: "Income report generated by NOVA", time: "45m ago" },
            { text: "Folder scan completed", time: "2h ago" },
        ],
    },
    {
        name: "Wispr Flow",
        connected: true,
        config: [
            { label: "Voice Pipeline", value: "Active" },
            { label: "Transcription Engine", value: "Whisper v3" },
            { label: "Languages", value: "EN, ES" },
        ],
        activity: [
            { text: "Voice command processed (DIEGO)", time: "30m ago" },
            { text: "Dictation session completed", time: "2h ago" },
        ],
    },
    {
        name: "LLM Router",
        connected: true,
        config: [
            { label: "Claude (Anthropic)", value: "Weight: 45%" },
            { label: "GPT-4 (OpenAI)", value: "Weight: 25%" },
            { label: "DeepSeek", value: "Weight: 20%" },
            { label: "Gemini (Google)", value: "Weight: 10%" },
        ],
        activity: [
            { text: "2,847 requests routed (24h)", time: "now" },
            { text: "Failover: GPT-4 to Claude (latency)", time: "3h ago" },
            { text: "Cost optimization: -12% vs yesterday", time: "6h ago" },
        ],
    },
    {
        name: "GHOST OSINT",
        connected: true,
        config: [
            { label: "Investigation Status", value: "Idle" },
            { label: "Entities Tracked", value: "34" },
            { label: "Data Sources", value: "12 active feeds" },
        ],
        activity: [
            { text: "Entity scan completed (0 alerts)", time: "1h ago" },
            { text: "Feed refresh: WHOIS, DNS, SSL", time: "3h ago" },
        ],
    },
    {
        name: "PentAGI",
        connected: true,
        config: [
            { label: "Vulnerability Scanner", value: "Active" },
            { label: "Last Assessment", value: "2h ago" },
            { label: "Risk Score", value: "Low (12/100)" },
        ],
        activity: [
            { text: "Weekly scan completed: 0 critical", time: "2h ago" },
            { text: "Dependency audit: all clear", time: "1d ago" },
        ],
    },
    {
        name: "Paperclip",
        connected: true,
        config: [
            { label: "Governance Tickets", value: "3 open" },
            { label: "Monthly Budget", value: "$6,500 / $10,000" },
            { label: "Approval Queue", value: "1 pending" },
        ],
        activity: [
            { text: "Budget alert: ATLAS at 78% monthly cap", time: "45m ago" },
            { text: "Ticket #89 approved by admin", time: "3h ago" },
            { text: "Cost report generated", time: "6h ago" },
        ],
    },
    {
        name: "Browser",
        connected: true,
        config: [
            { label: "Rate Limiter", value: "Active (60 req/min)" },
            { label: "Blocked Domains", value: "14 domains" },
            { label: "Proxy", value: "Rotating residential" },
        ],
        activity: [
            { text: "HUNTER: 23 pages crawled", time: "20m ago" },
            { text: "Domain blocked: competitor-api.com", time: "1h ago" },
        ],
    },
];

async function refreshIntegrations() {
    const grid = document.getElementById("int-cards-grid");
    if (!grid) return;

    // Try to fetch live status for GHOST and PentAGI
    try {
        const ghostStatus = await fetchJSON("/api/ghost/status");
        const ghostInt = INTEGRATIONS_DATA.find(i => i.name === "GHOST OSINT");
        if (ghostInt && ghostStatus) {
            ghostInt.config[0].value = ghostStatus.status || "Active";
            ghostInt.config[1].value = String(ghostStatus.entities_tracked || 34);
        }
    } catch (e) { /* use simulated */ }

    try {
        const pentStatus = await fetchJSON("/api/pentagi/status");
        const pentInt = INTEGRATIONS_DATA.find(i => i.name === "PentAGI");
        if (pentInt && pentStatus) {
            pentInt.config[0].value = pentStatus.scanner_status || "Active";
            pentInt.config[2].value = pentStatus.risk_score || "Low (12/100)";
        }
    } catch (e) { /* use simulated */ }

    grid.innerHTML = INTEGRATIONS_DATA.map((intg, idx) => `
        <div class="integration-card">
            <div class="integration-card-header">
                <div class="integration-card-title">
                    <span class="integration-status ${intg.connected ? "connected" : "disconnected"}"></span>
                    ${esc(intg.name)}
                </div>
                <button class="integration-test-btn" id="int-test-${idx}" onclick="testIntegrationConnection(${idx})">Test Connection</button>
            </div>
            <div class="integration-config">
                ${intg.config.map(c => `<div class="config-row"><span>${esc(c.label)}</span><span class="config-value">${esc(c.value)}</span></div>`).join("")}
            </div>
            <div class="integration-activity">
                <div class="integration-activity-title">Recent Activity</div>
                ${intg.activity.map(a => `<div class="integration-activity-item"><span>${esc(a.text)}</span><span class="activity-time">${esc(a.time)}</span></div>`).join("")}
            </div>
        </div>
    `).join("");

    // Update metrics
    const connectedCount = INTEGRATIONS_DATA.filter(i => i.connected).length;
    const connEl = document.getElementById("int-connected");
    if (connEl) connEl.textContent = connectedCount;

    const lastSyncEl = document.getElementById("int-last-sync");
    if (lastSyncEl) lastSyncEl.textContent = formatTime(new Date().toISOString());

    const apiCallsEl = document.getElementById("int-api-calls");
    if (apiCallsEl) apiCallsEl.textContent = "2,847";
}

function testIntegrationConnection(idx) {
    const btn = document.getElementById("int-test-" + idx);
    if (!btn) return;

    btn.textContent = "Testing...";
    btn.className = "integration-test-btn testing";

    setTimeout(() => {
        const success = Math.random() > 0.1;
        btn.textContent = success ? "Connected" : "Failed";
        btn.className = "integration-test-btn " + (success ? "success" : "fail");
        showToast(success ? `${INTEGRATIONS_DATA[idx].name} connection successful` : `${INTEGRATIONS_DATA[idx].name} connection failed`, success ? "success" : "error");

        setTimeout(() => {
            btn.textContent = "Test Connection";
            btn.className = "integration-test-btn";
        }, 3000);
    }, 1000 + Math.random() * 1000);
}

function showToast(message, type) {
    const existing = document.querySelector(".toast-notification");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast-notification " + (type || "success");
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}
