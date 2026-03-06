/**
 * MortgageFintechOS Dashboard
 * Real-time monitoring for AIOS Kernel with 9 AI agents.
 */

const REFRESH_INTERVAL = 5000;

const OPS_AGENTS = ["DIEGO", "MARTIN", "NOVA", "JARVIS"];
const CODING_AGENTS = ["ATLAS", "CIPHER", "FORGE", "NEXUS", "STORM"];

const AGENT_DESCRIPTIONS = {
    DIEGO: "Pipeline Orchestration",
    MARTIN: "Document Intelligence",
    NOVA: "Income & DTI Analysis",
    JARVIS: "Condition Resolution",
    ATLAS: "Full-Stack Engineering",
    CIPHER: "Security Engineering",
    FORGE: "CI/CD & DevOps",
    NEXUS: "Code Quality & Review",
    STORM: "Data Engineering",
};

let refreshTimer = null;

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

function formatTime(isoString) {
    if (!isoString) return "\u2014";
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatRelative(isoString) {
    if (!isoString) return "\u2014";
    const d = new Date(isoString);
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return diff + "s ago";
    if (diff < 3600) return Math.floor(diff / 60) + "m ago";
    return Math.floor(diff / 3600) + "h ago";
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// --- Render functions ---

function renderMetrics(status, health, kernel) {
    const queue = status.queue || {};
    const system = health.system || {};

    document.getElementById("metric-uptime").textContent = status.uptime || "\u2014";
    document.getElementById("metric-agents").textContent = Object.keys(status.agents || {}).length;
    document.getElementById("metric-pending").textContent = queue.pending || 0;
    document.getElementById("metric-completed").textContent = queue.completed || 0;
    document.getElementById("metric-pipelines").textContent = kernel.total_pipeline_triggers || 0;

    const failedEl = document.getElementById("metric-failed");
    failedEl.textContent = queue.failed || 0;
    failedEl.className = "metric-value" + ((queue.failed || 0) > 0 ? " danger" : "");

    const cpuEl = document.getElementById("metric-cpu");
    const memEl = document.getElementById("metric-mem");
    cpuEl.textContent = system.cpu_percent !== undefined ? system.cpu_percent.toFixed(1) + "%" : "\u2014";
    memEl.textContent = system.memory_percent !== undefined ? system.memory_percent.toFixed(1) + "%" : "\u2014";

    // Overall status badge
    const badge = document.getElementById("overall-status");
    const overall = health.overall || "unknown";
    badge.className = "status-badge " + overall;
    badge.innerHTML = `<span class="status-dot"></span>${overall}`;
}

function renderKernel(kernel) {
    const grid = document.getElementById("kernel-grid");
    const agents = kernel.agents || {};

    if (Object.keys(agents).length === 0) {
        grid.innerHTML = `<div class="empty-state">No kernel agents</div>`;
        return;
    }

    const versionEl = document.getElementById("kernel-version");
    if (versionEl) versionEl.textContent = `v${kernel.kernel_version || "1.0.0"}`;

    grid.innerHTML = Object.entries(agents)
        .map(([name, info]) => `
            <div class="kernel-agent${info.suspended ? ' suspended' : ''}">
                <div class="kernel-agent-name">${escapeHtml(name)}</div>
                <div class="kernel-agent-priority ${info.priority}">${info.priority}</div>
                <div class="kernel-agent-slots">${info.active_tasks}/${info.max_concurrent} slots</div>
            </div>
        `)
        .join("");
}

function renderAgentTable(agents, names, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    const filtered = (agents || []).filter((a) => names.includes(a.name));

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No agents</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered
        .map(
            (a) => `
        <tr>
            <td><span class="agent-name">${escapeHtml(a.name)}</span></td>
            <td>${escapeHtml(AGENT_DESCRIPTIONS[a.name] || "\u2014")}</td>
            <td><span class="agent-badge ${a.status}">${a.status}</span></td>
            <td style="font-family:var(--font-mono)">${a.tasks_completed}</td>
            <td style="font-family:var(--font-mono);${a.error_count > 0 ? "color:var(--danger);font-weight:700" : ""}">${a.error_count}</td>
        </tr>`
        )
        .join("");
}

function renderDependencyGraph(kernel) {
    const container = document.getElementById("dependency-graph");
    const deps = kernel.dependency_graph || [];

    if (deps.length === 0) {
        container.innerHTML = `<div class="empty-state">No dependencies</div>`;
        return;
    }

    container.innerHTML = deps
        .map(
            (d) => `
        <div class="dep-row">
            <span class="dep-agent">${escapeHtml(d.upstream)}</span>
            <span class="dep-action">${escapeHtml(d.trigger)}</span>
            <span class="dep-arrow">\u2192</span>
            <span class="dep-agent">${escapeHtml(d.downstream)}</span>
            <span class="dep-action">${escapeHtml(d.target)}</span>
        </div>`
        )
        .join("");
}

function renderSchedule(jobs) {
    const tbody = document.getElementById("schedule-tbody");
    const countEl = document.getElementById("schedule-count");
    if (countEl) countEl.textContent = (jobs || []).length;

    if (!jobs || jobs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No scheduled jobs</td></tr>`;
        return;
    }

    const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    tbody.innerHTML = jobs
        .map((j) => {
            let schedule = "";
            if (j.interval_minutes) {
                schedule = `Every ${j.interval_minutes}m`;
            } else if (j.day_of_week !== null && j.day_of_week !== undefined) {
                schedule = `${DAYS[j.day_of_week]} ${j.run_time || ""}`;
            } else {
                schedule = `Daily ${j.run_time || ""}`;
            }
            const statusDot = j.enabled
                ? `<span class="schedule-enabled"></span>`
                : `<span class="schedule-disabled"></span>`;
            return `
            <tr>
                <td>${statusDot}</td>
                <td>${escapeHtml(j.name)}</td>
                <td class="schedule-time">${schedule}</td>
                <td style="font-size:11px;color:var(--text-muted)">${j.last_run ? formatRelative(j.last_run) : "Never"}</td>
            </tr>`;
        })
        .join("");
}

function renderAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    if (!alerts || alerts.length === 0) {
        container.innerHTML = `<div class="empty-state">No recent alerts</div>`;
        return;
    }
    container.innerHTML = alerts
        .reverse()
        .slice(0, 20)
        .map(
            (a) => `
        <div class="alert-row">
            <span class="alert-severity ${a.severity}">${a.severity}</span>
            <span class="alert-message">${escapeHtml(a.message)}</span>
            <span class="alert-time">${formatTime(a.timestamp)}</span>
        </div>`
        )
        .join("");
}

function renderQueue(queueData) {
    const tbody = document.getElementById("queue-tbody");
    const tasks = queueData.recent_tasks || [];
    if (tasks.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No recent tasks</td></tr>`;
        return;
    }
    tbody.innerHTML = tasks
        .reverse()
        .slice(0, 25)
        .map(
            (t) => `
        <tr>
            <td style="font-family:var(--font-mono);font-size:11px">${escapeHtml(t.id)}</td>
            <td><span class="agent-name">${escapeHtml(t.agent)}</span></td>
            <td>${escapeHtml(t.action)}</td>
            <td><span class="priority-badge ${t.priority}">${t.priority}</span></td>
            <td><span class="agent-badge ${t.status}">${t.status}</span></td>
        </tr>`
        )
        .join("");
}

// --- Main refresh loop ---

async function refresh() {
    try {
        const [status, health, agents, queue, schedule, alerts, kernel] = await Promise.all([
            fetchJSON("/api/status"),
            fetchJSON("/api/health"),
            fetchJSON("/api/agents"),
            fetchJSON("/api/queue"),
            fetchJSON("/api/schedule"),
            fetchJSON("/api/alerts"),
            fetchJSON("/api/kernel"),
        ]);

        renderMetrics(status, health, kernel);
        renderKernel(kernel);
        renderAgentTable(agents, OPS_AGENTS, "ops-agents-tbody");
        renderAgentTable(agents, CODING_AGENTS, "coding-agents-tbody");
        renderDependencyGraph(kernel);
        renderSchedule(schedule);
        renderAlerts(alerts);
        renderQueue(queue);

        document.getElementById("last-updated").textContent =
            "Updated " + new Date().toLocaleTimeString();
    } catch (err) {
        console.error("Dashboard refresh failed:", err);
        document.getElementById("last-updated").textContent = "Connection error";
    }
}

// Start auto-refresh
document.addEventListener("DOMContentLoaded", () => {
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_INTERVAL);
});
