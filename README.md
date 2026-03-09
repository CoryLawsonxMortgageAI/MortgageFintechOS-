# MortgageFintechOS

**24/7 Automatous AI Operating System for Mortgage Lending**

Version 4.0 | Cory Lawson / The Lawson Group | NMLS 891785

[![CI — Lint & Test](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/actions/workflows/ci.yml/badge.svg)](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/actions/workflows/ci.yml)
[![Deploy to GitHub Pages](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/actions/workflows/deploy-pages.yml)

MortgageFintechOS is a production-grade automatous AI operating system that orchestrates 13 specialized AI agents across 4 divisions, with 9 external service integrations, 90 REST API endpoints, real-time task dispatch, and regulatory compliance built-in. It runs 24/7 — managing mortgage operations, engineering workflows, security scanning, and developer growth autonomously.

**Live Dashboards:**
- **Vercel**: https://mortgage-fintech-os.vercel.app
- **GitHub Pages**: https://corylawsonxmortgageai.github.io/MortgageFintechOS-/

---

## Architecture

```
+═══════════════════════════════════════════════════════════════════════════+
│                        MortgageFintechOS v4.0                            │
│                     Automatous AI Operating System                       │
+═══════════════════════════════════════════════════════════════════════════+
│                             ORCHESTRATOR                                 │
│     Task Queue (Priority FIFO)  │  DailyScheduler (11 jobs)             │
│     HealthMonitor │ Watchdog │ StateStore │ Paperclip Governance         │
│     ActionLog │ Telemetry (EWMA) │ Hydrospeed Ontology (26 nodes)       │
+──────────┬──────────┬──────────┬─────────────────────────────────────────+
│          │          │          │                                          │
│  ┌───────┴───────┐  │  ┌──────┴────────┐  ┌──────────────┐  ┌────────┐ │
│  │ MORTGAGE OPS  │  │  │  ENGINEERING   │  │  GROWTH OPS  │  │ INTEL  │ │
│  │ DIEGO Pipeline│  │  │ ATLAS FullStack│  │ HUNTER Leads │  │SENTINEL│ │
│  │ MARTIN DocInt │  │  │ CIPHER Security│  │ HERALD Contnt│  │Research│ │
│  │ NOVA Income   │  │  │ FORGE DevOps  │  │ AMBASSADOR   │  └────────┘ │
│  │ JARVIS Conds  │  │  │ NEXUS Quality │  │  Community   │             │
│  └───────────────┘  │  │ STORM DataEng │  └──────────────┘             │
│                      │  └───────────────┘                               │
+─────────────────────────────────────────────────────────────────────────+
│                       INTEGRATIONS (9 Services)                          │
│  GitHub API v3 │ Notion v2025-09-03 │ Google Drive v3 │ Wispr Flow     │
│  LLM Router (OpenAI/Anthropic/OpenRouter) │ Paperclip AI Governance    │
│  GHOST OSINT │ PentAGI │ Browser Automation                            │
+─────────────────────────────────────────────────────────────────────────+
│                      MONITORING & PERSISTENCE                            │
│  HealthMonitor │ ActionLog │ Telemetry (5-factor EWMA) │ Hydrospeed    │
│  StateStore (debounced JSON) │ AgentDB (Dolt-style version control)    │
+─────────────────────────────────────────────────────────────────────────+
│  Dashboard (aiohttp:8080) │ 90 API Endpoints │ 12 UI Pages            │
│  CI/CD: GitHub Actions (ruff + pytest + mypy) │ Vercel │ GitHub Pages  │
+═══════════════════════════════════════════════════════════════════════════+
```

---

## AI Agents — 13 Agents / 4 Divisions

### Mortgage Operations (4 Agents)

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **DIEGO** | Pipeline Orchestration | Loan triage (FHA/VA/CONV/USDA/JUMBO), stage progression (application → funding), priority assignment, bottleneck detection, pipeline health reporting |
| **MARTIN** | Document Intelligence | Classification (W2/paystub/bank/tax/license/title/appraisal), OCR validation, fraud detection (font inconsistency, hidden layers, date mismatches), GHOST OSINT borrower verification, completeness auditing |
| **NOVA** | Income & DTI Analysis | W-2 dual-method per FHA HB 4000.1 II.A.5.b, Schedule C self-employment (2-year average + depreciation add-back), DTI with compensating factors, collections 5% rule per II.A.4.d.v, income trending |
| **JARVIS** | Condition Resolution | LOE template generation (employment gap, large deposit, credit inquiry), condition-to-document mapping, compliance citations (FHA/FNMA/FHLMC), condition lifecycle tracking |

### Codebase Engineering (5 Agents)

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **ATLAS** | Full-Stack Engineering | LLM-powered API generation, feature building with multi-file commits, database migration creation (SQL UP/DOWN), React/TypeScript scaffolding, GitHub branch/commit/PR creation |
| **CIPHER** | Security Engineering | OWASP scanning via GitHub code scanning alerts, SOC2/PCI-DSS/GLBA compliance checking, encryption auditing (AES-256, TLS 1.3), vulnerability patching with CVE tracking, PentAGI integration |
| **FORGE** | DevOps Engineering | GitHub Actions workflow triggering, deployment dispatch with environment selection, rollback via workflow or commit revert, CI/CD pipeline YAML generation, secret rotation tracking |
| **NEXUS** | Code Quality | PR review using real GitHub diff + LLM analysis, test generation (pytest with fixtures/parametrization), tech debt analysis from commit history, SOLID refactoring, review event submission |
| **STORM** | Data Engineering | ETL pipeline generation (extract/transform/load with async patterns), HMDA compliance reporting, ULDD export specification, database query optimization |

### Intelligence (1 Agent)

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **SENTINEL** | Codebase Intelligence | Codebase scanning (structure/commits/branches), technology trend analysis, reverse engineering, build plan generation, AutoResearch (Karpathy-style ML experiments), deep security audit |

### Growth Ops — Autonomous 24/7 (3 Agents)

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **HUNTER** | Dev Lead Discovery | GitHub trending/topic scanning, Hacker News frontpage monitoring, Reddit subreddit scanning, keyword-weighted lead scoring (mortgage/fintech/AI-agent), tier ranking (hot/warm/cold), Notion sync |
| **HERALD** | Build-in-Public Content | LLM-powered content generation (tweets, threads, dev.to articles, changelogs, LinkedIn posts), content calendar scheduling (Mon=milestone, Tue/Thu=thread, Wed=article, Fri=changelog), multi-template system |
| **AMBASSADOR** | Community Engagement | Rate-limited GitHub starring/commenting (25/day max), per-user engagement caps (3/week), anti-spam cooldowns, LLM-generated value-adding responses, blocked domain guardrails (financial/gov sites) |

---

## External Integrations (9 Services)

| Service | Version/Protocol | Purpose |
|---------|-----------------|---------|
| **GitHub API** | v3 REST | Full code operations: repo CRUD, branch management, PRs (create/review/merge), GitHub Actions (trigger/monitor/cancel), security scanning (code scanning/Dependabot/secret scanning) |
| **Notion API** | v2025-09-03 | Knowledge base + audit trail. `data_source_id` parent (v2025 concept). Page CRUD, block management, search, agent result auto-sync |
| **Google Drive API** | v3 | Document source for borrower docs. Service account JWT auth. File listing, download, Google Docs export, batch folder import with MARTIN classification |
| **Wispr Flow** | Webhook | Voice-to-text transcription. HMAC-SHA256 signature validation. Keyword-based agent routing with confidence scoring |
| **LLM Router** | Multi-provider | Intelligent routing: OpenAI, Anthropic (Claude Sonnet 4.6), OpenRouter. Task-based routing matrix with agent-specific overrides and automatic fallback |
| **Paperclip AI** | Custom | Enterprise orchestration with Board approval governance. Per-agent budgets ($300-800/mo), auto-pause at 100%, immutable audit log |
| **GHOST OSINT** | REST API | Entity investigation for fraud detection. Entity creation/search, relationship mapping, OSINT lookups (email/phone/domain/person), borrower verification |
| **PentAGI** | REST API | Autonomous penetration testing. 111+ security tools. Vulnerability scanning, attack surface analysis, report generation |
| **Browser Automation** | HTTP + Sessions | Headless client for Growth Ops. Token-bucket rate limiter, blocked domain guardrails, per-platform action budgets, persistent sessions, fingerprint rotation |

---

## Monitoring & Observability

| System | Module | Purpose |
|--------|--------|---------|
| **Health Monitor** | `monitoring/health_monitor.py` | Agent heartbeats (60s timeout), queue backlog detection (>50 tasks), error rate tracking (10% threshold over 5m window), system metrics via psutil |
| **Action Log** | `monitoring/action_log.py` | Append-only agent action log with timeline views and per-agent statistics |
| **Predictive Telemetry** | `monitoring/telemetry.py` | 5-factor EWMA risk scoring per agent: error rate, response time, queue depth, heartbeat lag, task failure rate. Cascade failure prediction |
| **Hydrospeed Ontology** | `monitoring/hydrospeed.py` | 26-node knowledge graph mapping agents, integrations, and data flows. Schedule optimization recommendations, improvement proposals |
| **Watchdog** | `core/orchestrator.py` | Crash loop detection for subsystems (5+ crashes in 5 min → degraded mode). Auto-restart with 30s polling. GitHub issue creation for crash loops |

---

## Persistence

| System | Module | Purpose |
|--------|--------|---------|
| **State Store** | `persistence/state_store.py` | Atomic JSON writes with debounced flushing. Agent state, task queue, and budgets survive restarts |
| **Agent Database** | `persistence/agent_database.py` | Dolt-inspired version-controlled database with Git-style branching, diff, merge, and commit log. Per-agent status tracking |

---

## Scheduled Operations (11 Jobs)

| Time | Agent | Operation | Priority |
|------|-------|-----------|----------|
| 02:00 | HUNTER | Dev lead sweep (GitHub + HN + Reddit) | LOW |
| 03:00 | CIPHER | Security scan (code scanning + Dependabot + secrets) | HIGH |
| 05:30 | System | Google Drive folder import (new borrower docs) | MEDIUM |
| 06:00 | MARTIN | Document audit (classification + fraud check) | MEDIUM |
| 06:30 | NOVA | Income recalculation (W-2 + Schedule C) | MEDIUM |
| 07:00 | DIEGO | Pipeline health check (bottleneck detection) | HIGH |
| 07:30 | System | Notion audit sync (push results to knowledge base) | MEDIUM |
| 08:00 | HERALD | Daily content generation (calendar-driven) | LOW |
| 10:00 | AMBASSADOR | Community engagement (rate-limited outreach) | LOW |
| Hourly | System | Queue health check | — |
| Weekly (Mon 08:00) | DIEGO | Pipeline report (GitHub + stakeholders) | LOW |

---

## Claude Code Automation Layer

MortgageFintechOS includes a comprehensive Claude Code automation layer for external monitoring, CI/CD, and development workflow optimization. This operates independently from the internal DailyScheduler — providing a redundant "meta-monitoring" layer.

### Session-Start Hook

Runs automatically when opening Claude Code in this repo. Validates:
- OS type (Linux/WSL/macOS), Python version, RAM usage
- Docker container status (postgres, redis, app)
- Dashboard reachability (localhost:8080)
- Dev tools (ruff, pytest), git branch, .env presence

### Desktop Scheduled Tasks (6 Persistent)

| Task | Schedule | Purpose |
|------|----------|---------|
| `git-sync-and-clean` | Daily 6:00 AM | Fetch, sync status, stale branch detection |
| `repo-health-check` | Daily 7:00 AM | System health, git status, lint, tests |
| `pr-monitor-autofix` | Hourly | Check PRs, auto-fix lint failures |
| `system-health-sentinel` | Every 30 min | API health, EWMA risk scores, Docker, RAM |
| `weekly-architecture-review` | Sunday 6:00 AM | Week's changes, agent integrity, gap progress |
| `dependency-security-audit` | Monday 3:00 AM | CVE scan, outdated deps, secrets check |

Task prompts stored in `.claude/scheduled-tasks/<name>/SKILL.md`.

### CLI Loop Prompts (5 Session-Scoped)

| Loop | Interval | Purpose |
|------|----------|---------|
| Guardian | 5 min | Silent health watch — only reports problems |
| PR Review | 15 min | Code review against CLAUDE.md standards |
| Test Gap Closer | 10 min | Find untested modules, suggest test structure |
| Auto-Fix | 10 min | py_compile + ruff fix on modified files |
| Deployment Watcher | 3 min | GitHub Actions + Vercel + Pages status |

Full prompts in `.claude/LOOPS.md`.

### Shared Health Utility

```bash
bash scripts/check-health.sh          # Human-readable report
bash scripts/check-health.sh --json   # Machine-readable JSON
```

---

## Dashboard UI (12 Pages)

The web dashboard runs on port 8080 with 90 API endpoints:

| Page | Purpose |
|------|---------|
| **Office Floor** | KPIs, task assignment, agent status tables, activity log |
| **Office Manager** | AIOS Kernel supervision, pipeline dependency visualization |
| **Live Monitor** | Real-time agent swim lanes with progress bars, execution streaming, live metrics |
| **AI Chat** | Multi-model chat via Puter.js (500+ LLMs, no API keys) |
| **Intelligence Reports** | Auto-generated reports from agent tasks |
| **Model Discovery** | Neural self-learning model ranking engine with benchmark scoring |
| **Paperclip AI** | Enterprise ticket lifecycle, Board approval, budget tracking, org chart, audit log |
| **Code Workspace** | GitHub integration, AutoResearch (Karpathy-style), Edge Agents (SubZeroClaw) |
| **Knowledge Hub** | Open Notebook (NotebookLM alternative), Notion, Wispr Flow, Google Drive |
| **Growth Ops** | HUNTER leads, HERALD content queue, AMBASSADOR engagement stats |
| **Tech Stack** | Complete technology reference, architecture patterns, key terms glossary |
| **Connections** | Vercel deploy, Telegram bot, GHOST OSINT, PentAGI, Security Operations Center |

---

## API Reference (90 Endpoints)

### Core (11)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/healthz` | Health check |
| `GET` | `/api/status` | Full system status |
| `GET` | `/api/health` | Detailed health report |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/agents/skills` | Agent skills manifest |
| `GET` | `/api/queue` | Queue stats + recent tasks |
| `GET` | `/api/schedule` | Scheduled jobs |
| `GET` | `/api/alerts` | Health alerts |
| `POST` | `/api/tasks/submit` | Submit task to agent |
| `GET` | `/api/tasks/{id}` | Task detail + result |
| `GET` | `/api/tasks/results/feed` | Live results feed |

### Notion (5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notion/status` | Configuration status |
| `GET` | `/api/notion/pages` | Query pages |
| `POST` | `/api/notion/pages` | Create page |
| `GET` | `/api/notion/pages/{id}` | Review page (MARTIN classifies) |
| `POST` | `/api/notion/sync-audit` | Audit sync to Notion |

### Google Drive (2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/drive/files` | List files in folder |
| `POST` | `/api/drive/import` | Import folder + classify |

### Wispr Flow (2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/wispr/webhook` | Receive voice notes |
| `GET` | `/api/wispr/status` | Connection status |

### GitHub Code Ops (7)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/github/repo` | Repository info |
| `GET` | `/api/github/prs` | List pull requests |
| `GET` | `/api/github/security` | Aggregated security alerts |
| `POST` | `/api/github/security/scan` | Trigger CIPHER scan |
| `GET` | `/api/github/actions` | Recent workflow runs |
| `GET` | `/api/github/commits` | Recent commits |
| `GET` | `/api/github/branches` | List branches |

### Paperclip AI (11)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/paperclip/health` | Health check |
| `GET` | `/api/paperclip/status` | Orchestration status |
| `GET/POST` | `/api/paperclip/tickets` | List/create tickets |
| `POST` | `/api/paperclip/tickets/{id}/approve` | Board approval |
| `POST` | `/api/paperclip/tickets/{id}/reject` | Board rejection |
| `POST` | `/api/paperclip/tickets/{id}/start` | Start work |
| `POST` | `/api/paperclip/tickets/{id}/complete` | Mark complete |
| `GET` | `/api/paperclip/budgets` | Per-agent budgets |
| `POST` | `/api/paperclip/budgets/{agent}/set` | Set budget |
| `POST` | `/api/paperclip/budgets/{agent}/reset` | Reset budget |
| `GET` | `/api/paperclip/audit` | Immutable audit log |

### GHOST OSINT (4)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/ghost/status` | OSINT status |
| `POST` | `/api/ghost/verify` | Borrower verification |
| `GET` | `/api/ghost/search` | Entity search |
| `POST` | `/api/ghost/investigations` | Create investigation |

### PentAGI (3)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pentagi/status` | Pentest status |
| `POST` | `/api/pentagi/assess` | Run security assessment |
| `GET` | `/api/pentagi/vulnerabilities` | List vulnerabilities |

### Growth Ops (8)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/growth/status` | All Growth Ops agent status |
| `POST` | `/api/growth/sweep` | Full sweep (HUNTER + HERALD + AMBASSADOR) |
| `POST` | `/api/growth/hunter/scan` | Trigger HUNTER scan |
| `GET` | `/api/growth/hunter/leads` | Scored lead rankings |
| `POST` | `/api/growth/herald/generate` | Generate content |
| `GET` | `/api/growth/herald/queue` | Content queue |
| `POST` | `/api/growth/ambassador/engage` | Trigger engagement |
| `GET` | `/api/growth/ambassador/stats` | Engagement metrics |

### Action Log (3)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/action-log` | Full action log |
| `GET` | `/api/action-log/stats` | Per-agent statistics |
| `GET` | `/api/action-log/timeline` | Timeline view |

### Schedule Control (2)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/schedule/{job}/update` | Update job timing |
| `POST` | `/api/schedule/{job}/toggle` | Enable/disable job |

### Hydrospeed Ontology (8)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/hydrospeed/ontology` | Full 26-node ontology graph |
| `GET` | `/api/hydrospeed/agent/{name}` | Agent ontology node |
| `GET` | `/api/hydrospeed/tips` | Optimization tips |
| `GET` | `/api/hydrospeed/divisions` | Division breakdown |
| `GET` | `/api/hydrospeed/data-flows` | Data flow map |
| `GET` | `/api/hydrospeed/schedule-recommendations` | Schedule optimization |
| `POST` | `/api/hydrospeed/proposals` | Create improvement proposal |
| `GET` | `/api/hydrospeed/proposals` | List proposals |

### Telemetry (5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/telemetry/risks` | All agent risk scores |
| `GET` | `/api/telemetry/risks/{agent}` | Per-agent risk score |
| `GET` | `/api/telemetry/predictions` | Failure predictions |
| `GET` | `/api/telemetry/cascade/{agent}` | Cascade failure analysis |
| `GET` | `/api/telemetry/context` | Full telemetry context |

### Agent Database (14)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/agentdb/schema` | Database schema |
| `GET` | `/api/agentdb/schema/sql` | SQL CREATE statements |
| `GET` | `/api/agentdb/branches` | List branches |
| `POST` | `/api/agentdb/branches` | Create branch |
| `DELETE` | `/api/agentdb/branches/{branch}` | Delete branch |
| `GET` | `/api/agentdb/tables` | List tables |
| `GET` | `/api/agentdb/query/{table}` | Query table |
| `POST` | `/api/agentdb/insert/{table}` | Insert row |
| `POST` | `/api/agentdb/update/{table}/{id}` | Update row |
| `GET` | `/api/agentdb/diff` | Branch diff |
| `POST` | `/api/agentdb/merge` | Merge branches |
| `POST` | `/api/agentdb/reset` | Reset branch |
| `GET` | `/api/agentdb/log/{branch}` | Commit log |
| `GET` | `/api/agentdb/agent/{agent}` | Agent status record |

### Other (5)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/safety/blocked` | Blocked domains list |
| `GET` | `/api/ontology-telemetry-sync` | Ontology + telemetry sync |
| `GET` | `/api/features` | Feature guide |
| `GET` | `/` | Dashboard index |
| `GET` | `/static/*` | Static file serving |

---

## Test Suite

59 tests across 4 test files, with CI enforcement via GitHub Actions (ruff + pytest + mypy).

| File | Tests | Coverage Area |
|------|-------|--------------|
| `tests/test_nova_income.py` | 13 | W-2 dual-method, Schedule C, DTI ratios, compensating factors, collections 5% rule |
| `tests/test_martin_document.py` | 20 | Document classification, OCR validation, fraud detection (font/layers/dates), completeness audit |
| `tests/test_diego_pipeline.py` | 20 | Loan triage (FHA/VA/CONV/USDA), stage progression, priority assignment, pipeline health |
| `tests/test_task_queue.py` | 6 | Enqueue/dequeue, completion history, retry logic, serialization |

```bash
pytest -v --tb=short          # Run all tests
ruff check .                  # Lint check
mypy agents/ core/ monitoring/ --ignore-missing-imports  # Type check
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Runtime | Python | 3.11+ | Core application, async/await, type hints |
| Async | asyncio + aiohttp | 3.9+ | Non-blocking HTTP server/client, REST APIs |
| Config | python-dotenv + pydantic | 1.0+ / 2.5+ | Environment-based config with validation |
| Logging | structlog | 23.2+ | Structured JSON logging with context binding |
| CLI | click | 8.1+ | Command-line interface for daemon startup |
| System | psutil | 5.9+ | CPU, memory, disk metrics for health monitor |
| Auth | google-auth | 2.23+ | Google Drive service account JWT |
| AI (Frontend) | Puter.js | v2 | 500+ LLM models (Claude, GPT, DeepSeek, Kimi K2.5) — no API keys |
| AI (Backend) | LLM Router | Custom | Multi-provider routing: OpenAI, Anthropic, OpenRouter |
| Frontend | Vanilla JS + HTML5 | ES2022 | Zero-dependency SPA with CSS custom properties |
| Lint | ruff | 0.3+ | 12 linter rules (E, F, W, I, N, UP, S, B, A, C4, SIM) |
| Test | pytest + pytest-asyncio | 8.0+ / 0.23+ | Async test suite with fixtures |
| Type Check | mypy | 1.8+ | Static type analysis |
| Deploy | Vercel | — | Auto-deploy on push to main |
| Deploy | GitHub Pages | — | Static dashboard hosting |
| CI/CD | GitHub Actions | — | Lint + test + type check on push/PR |
| VCS | GitHub API | v3 REST | Code ops, PRs, Actions, security scanning |
| Database | PostgreSQL | 15+ | Primary datastore (Docker) |
| Cache | Redis | 7+ | Task queue caching (Docker) |

---

## Architecture Patterns

| Pattern | Description |
|---------|-------------|
| **Agent Registry** | Orchestrator maintains agent dictionary. Dynamic registration, health monitoring, integration injection |
| **Priority Task Queue** | FIFO with 4 priority levels (CRITICAL/HIGH/MEDIUM/LOW). Retry with exponential backoff (2^n seconds). History tracking for audit |
| **Watchdog Supervision** | Crash loop detection for subsystems. Auto-restart with 30s polling. GitHub issue creation after 5+ crashes in 5 minutes |
| **State Persistence** | Debounced writes to disk via StateStore. Agent state, task queue, and budgets survive restarts |
| **Integration Injection** | Agents receive integration clients post-registration. Decoupled, testable, swappable |
| **LLM Routing Matrix** | Task category → optimal model mapping. Agent-specific overrides. Automatic fallback chains |
| **Board Governance** | Paperclip AI: ticket lifecycle (open → approved → in_progress → completed). Per-agent budgets with auto-pause |
| **Rate-Limited Automation** | Token-bucket rate limiter per domain. Blocked domains (financial/gov). Per-platform hourly action budgets |
| **Version-Controlled Data** | Dolt-inspired AgentDB with Git-style branching, diff, merge, and commit log |
| **Predictive Telemetry** | 5-factor EWMA risk scoring with cascade failure prediction and auto-alerting |
| **Ontology-Driven Optimization** | 26-node Hydrospeed knowledge graph mapping agents, integrations, and data flows for schedule optimization |
| **External Meta-Monitoring** | Claude Code automation layer monitors the system from outside — providing redundant health checks independent of the internal scheduler |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- PostgreSQL 15+ (optional)
- Redis 7+ (optional)

### Installation

```bash
git clone https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-.git
cd MortgageFintechOS-
cp .env.example .env
# Edit .env with your API keys and configuration

# Install dependencies
pip install -r requirements.txt

# Start the autonomous system
python main.py start

# Or via Docker
cd docker && docker-compose up -d
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub API token for code ops | Yes |
| `GITHUB_REPO` | Target repository | Yes |
| `NOTION_API_TOKEN` | Notion integration token (v2025-09-03) | No |
| `NOTION_DATABASE_ID` | Notion database ID | No |
| `NOTION_DATA_SOURCE_ID` | Notion data source ID (v2025) | No |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Drive service account path | No |
| `GOOGLE_DRIVE_FOLDER_ID` | Default Drive folder | No |
| `WISPR_WEBHOOK_SECRET` | Wispr Flow webhook HMAC secret | No |
| `OPENAI_API_KEY` | OpenAI API key for LLM Router | No |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM Router | No |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM Router | No |
| `GHOST_API_KEY` | GHOST OSINT API key | No |
| `PENTAGI_API_KEY` | PentAGI API key | No |
| `GROWTH_OPS_ENABLED` | Enable Growth Ops agents (default: true) | No |
| `DASHBOARD_PORT` | Dashboard port (default: 8080) | No |
| `ENCRYPTION_KEY` | AES-256 encryption key | No |

---

## Project Structure

```
MortgageFintechOS-/
  main.py                              Entry point (CLI)
  setup.sh                             Installation script
  requirements.txt                     Python dependencies (12 packages)
  pyproject.toml                       Ruff + pytest + mypy configuration
  .env.example                         Environment template

  config/
    settings.py                        Central configuration (40+ env vars, dataclass)

  core/
    orchestrator.py                    Central async daemon (730 LOC — lifecycle, dispatch, watchdog)
    task_queue.py                      Priority-based task queue with history

  agents/
    base.py                           Abstract base agent (retry, heartbeat, integration injection)
    diego.py                          DIEGO — Pipeline orchestration (5 actions)
    martin.py                         MARTIN — Document intelligence + fraud detection (5 actions)
    nova.py                           NOVA — Income & DTI analysis, FHA HB 4000.1 (4 actions)
    jarvis.py                         JARVIS — Condition resolution + LOE drafting (5 actions)
    atlas.py                          ATLAS — Full-stack engineering, GitHub code ops (5 actions)
    cipher.py                         CIPHER — Security engineering, OWASP + PentAGI (5 actions)
    forge.py                          FORGE — DevOps engineering, GitHub Actions (4 actions)
    nexus.py                          NEXUS — Code quality, PR review + test gen (4 actions)
    storm.py                          STORM — Data engineering, ETL + HMDA + ULDD (4 actions)
    sentinel.py                       SENTINEL — Codebase intelligence + AutoResearch (5 actions)
    hunter.py                         HUNTER — Dev lead discovery (24/7 autonomous)
    herald.py                         HERALD — Build-in-public content creation
    ambassador.py                     AMBASSADOR — Community engagement with guardrails

  integrations/
    github_client.py                  GitHub API v3 (code ops, PRs, Actions, security)
    notion_client.py                  Notion API v2025-09-03 (data_source_id)
    gdrive_client.py                  Google Drive API v3 (service account JWT)
    wispr_client.py                   Wispr Flow webhook receiver
    llm_router.py                     Multi-LLM router (OpenAI/Anthropic/OpenRouter)
    paperclip_service.py              Enterprise orchestration + governance
    ghost_client.py                   GHOST OSINT CRM (entity investigation)
    pentagi_client.py                 PentAGI autonomous pentesting
    browser_client.py                 Browser automation (rate-limited, guardrails)

  dashboard/
    server.py                         aiohttp web server (90 endpoints, 1400+ LOC)
    static/                           Frontend assets

  monitoring/
    health_monitor.py                 Agent health, heartbeats, queue backlog, error rates
    action_log.py                     Append-only agent action log
    telemetry.py                      5-factor EWMA risk scoring + cascade prediction
    hydrospeed.py                     26-node ontology graph + schedule optimization

  schedulers/
    daily_scheduler.py                Cron-like job scheduler (11 jobs, missed job recovery)

  persistence/
    state_store.py                    Debounced atomic JSON state persistence
    agent_database.py                 Dolt-inspired version-controlled DB (Git-style branching)

  tests/
    conftest.py                       Shared fixtures (W-2, Schedule C, DTI, sample task)
    test_nova_income.py               13 tests — income calculations + FHA compliance
    test_martin_document.py           20 tests — document intelligence + fraud detection
    test_diego_pipeline.py            20 tests — pipeline routing + stage management
    test_task_queue.py                6 tests — queue operations + persistence

  scripts/
    check-health.sh                   Shared health check utility (human + JSON output)

  skills/
    hiring-manager-interview/         Structured interview + 8-dimension scorecard

  public/
    index.html                        Main dashboard SPA
    orchestration.html                Orchestration map visualization
    ontology.html                     Hydrospeed ontology explorer

  docker/
    Dockerfile                        Python 3.11 container
    docker-compose.yml                App + PostgreSQL 15 + Redis 7
    mortgagefintechos.service          Systemd service unit

  .claude/
    hooks/session-start.sh            Environment validation hook
    scheduled-tasks/                  6 persistent monitoring task prompts
    LOOPS.md                          CLI loop + scheduling reference
    settings.json                     Claude Code hook configuration

  .github/workflows/
    ci.yml                            Lint (ruff) + test (pytest) + type check (mypy)
    deploy-pages.yml                  GitHub Pages deployment
```

---

## FHA Compliance

All mortgage calculations cite specific FHA Handbook 4000.1 sections:

| Regulation | Section | Agent |
|-----------|---------|-------|
| W-2 Dual-Method Income | II.A.5.b | NOVA |
| Schedule C Self-Employment | II.A.4.c.ii | NOVA |
| DTI Ratios & Compensating Factors | II.A.4.b | NOVA |
| Collections 5% Rule | II.A.4.d.v | NOVA |
| Document Classification | II.A | MARTIN |
| Condition Mapping | Various | JARVIS |
| HMDA Reporting | Reg C | STORM |
| ULDD Delivery | FNMA/FHLMC specs | STORM |

---

## Security

| Layer | Implementation |
|-------|---------------|
| **Code Scanning** | GitHub code scanning alerts → CIPHER OWASP mapping |
| **Dependency Scanning** | Dependabot alerts → CIPHER compliance check |
| **Secret Scanning** | GitHub secret scanning → CIPHER alert management |
| **Penetration Testing** | PentAGI autonomous pentesting (111+ tools) |
| **OSINT** | GHOST OSINT entity investigation + borrower verification |
| **Encryption** | AES-256 at rest, TLS 1.3 in transit, CIPHER audit |
| **Compliance** | SOC2 Type II, PCI-DSS, GLBA Safeguards Rule |
| **Governance** | Paperclip AI Board approval + per-agent budget enforcement |
| **Watchdog** | Crash loop detection with auto-GitHub issue creation |
| **CI/CD** | ruff security rules (S linter), mypy type checking, weekly dependency audit |

---

## Open Pull Requests

| PR | Branch | Feature |
|----|--------|---------|
| [#12](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/pull/12) | — | Pre-configure Vercel deploy hook URL for one-click redeploy |
| [#9](https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-/pull/9) | `claude/autonomous-ai-operating-system-ad2L3` | Telegram bot, X.com integration, knowledge reference system |

---

## Key Terms

| Term | Definition |
|------|-----------|
| **Automatous AI** | AI systems that autonomously plan, execute, and adapt without human intervention — self-governing and self-sustaining |
| **Multi-Agent Orchestration** | Central daemon coordinating 13 agents via task queue with cross-agent pipelines |
| **RAG** | Retrieval-Augmented Generation — agents retrieve context before LLM generation |
| **DAG** | Directed Acyclic Graph — task dependency graphs for pipeline execution |
| **EWMA** | Exponentially Weighted Moving Average — predictive risk scoring for agent health |
| **OWASP Top 10** | Standard security vulnerability categories for compliance reporting |
| **FHA HB 4000.1** | FHA Single Family Housing Policy Handbook — regulatory reference for income/DTI |
| **HMDA** | Home Mortgage Disclosure Act — regulatory reporting requirement |
| **ULDD** | Uniform Loan Delivery Dataset — Fannie Mae/Freddie Mac delivery format |
| **DTI** | Debt-to-Income ratio — front-end (housing) and back-end (total) |
| **LOE** | Letter of Explanation — documents explaining borrower anomalies |
| **SOC2/PCI-DSS/GLBA** | Security/privacy compliance frameworks for financial services |

---

## License

Copyright 2026 Cory Lawson / The Lawson Group. All rights reserved.

---

*MortgageFintechOS v4.0 — 13 Agents, 4 Divisions, 9 Integrations, 90 API Endpoints, 59 Tests, 24/7 Automatous Operation*
