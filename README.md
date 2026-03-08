# MortgageFintechOS

**24/7 Autonomous AI Operating System for Mortgage Lending**

Version 3.0 | Cory Lawson / The Lawson Group

MortgageFintechOS is a production-grade autonomous AI operating system that orchestrates 13 specialized AI agents across 4 divisions, with 9 external service integrations, real-time task dispatch, and regulatory compliance built-in. It runs 24/7 — managing mortgage operations, engineering workflows, security scanning, and developer growth while you sleep.

---

## Architecture

```
+═══════════════════════════════════════════════════════════════════+
│                        MortgageFintechOS v3.0                     │
│                   Autonomous AI Operating System                  │
+═══════════════════════════════════════════════════════════════════+
│                           ORCHESTRATOR                            │
│       Task Queue (Priority FIFO) │ DailyScheduler (11 jobs)      │
│       HealthMonitor │ Watchdog │ StateStore │ Paperclip Gov       │
+───────────┬───────────┬───────────┬───────────────────────────────+
│           │           │           │                               │
│  ┌────────┴────────┐  │  ┌───────┴────────┐  ┌────────────────┐ │
│  │  MORTGAGE OPS   │  │  │   ENGINEERING   │  │  GROWTH OPS    │ │
│  │  DIEGO Pipeline │  │  │  ATLAS FullStack│  │  HUNTER Leads  │ │
│  │  MARTIN DocIntel│  │  │  CIPHER Security│  │  HERALD Content│ │
│  │  NOVA Income/DTI│  │  │  FORGE DevOps   │  │  AMBASSADOR    │ │
│  │  JARVIS Conditns│  │  │  NEXUS CodeQual │  │   Community    │ │
│  └─────────────────┘  │  │  STORM DataEng  │  └────────────────┘ │
│                       │  │  SENTINEL Intel │                      │
│                       │  └────────────────┘                       │
+───────────────────────────────────────────────────────────────────+
│                        INTEGRATIONS (9)                            │
│  GitHub API v3 │ Notion v2025-09-03 │ Google Drive v3 │ Wispr    │
│  LLM Router (OpenAI/Anthropic/OpenRouter) │ Paperclip AI         │
│  GHOST OSINT │ PentAGI │ Browser Automation                      │
+───────────────────────────────────────────────────────────────────+
│               Dashboard (aiohttp:8080) │ 60+ API Endpoints       │
+═══════════════════════════════════════════════════════════════════+
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

### Codebase Engineering (6 Agents)

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| **ATLAS** | Full-Stack Engineering | LLM-powered API generation, feature building with multi-file commits, database migration creation (SQL UP/DOWN), React/TypeScript scaffolding, GitHub branch/commit/PR creation |
| **CIPHER** | Security Engineering | OWASP scanning via GitHub code scanning alerts, SOC2/PCI-DSS/GLBA compliance checking, encryption auditing (AES-256, TLS 1.3), vulnerability patching with CVE tracking, PentAGI integration |
| **FORGE** | DevOps Engineering | GitHub Actions workflow triggering, deployment dispatch with environment selection, rollback via workflow or commit revert, CI/CD pipeline YAML generation, secret rotation tracking |
| **NEXUS** | Code Quality | PR review using real GitHub diff + LLM analysis, test generation (pytest with fixtures/parametrization), tech debt analysis from commit history, SOLID refactoring, review event submission |
| **STORM** | Data Engineering | ETL pipeline generation (extract/transform/load with async patterns), HMDA compliance reporting, ULDD export specification, database query optimization |
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

## Dashboard UI

The web dashboard runs on port 8080 and provides 10 pages:

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

## API Reference (60+ Endpoints)

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/healthz` | Health check |
| `GET` | `/api/status` | Full system status |
| `GET` | `/api/health` | Detailed health report |
| `GET` | `/api/agents` | List all agents |
| `GET` | `/api/queue` | Queue stats + recent tasks |
| `GET` | `/api/schedule` | Scheduled jobs |
| `GET` | `/api/alerts` | Health alerts |
| `POST` | `/api/tasks/submit` | Submit task to agent |
| `GET` | `/api/tasks/{id}` | Task detail + result |
| `GET` | `/api/tasks/results/feed` | Live results feed |

### Notion
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/notion/status` | Configuration status |
| `GET` | `/api/notion/pages` | Query pages |
| `POST` | `/api/notion/pages` | Create page |
| `GET` | `/api/notion/pages/{id}` | Review page (MARTIN classifies) |
| `POST` | `/api/notion/sync-audit` | Audit sync to Notion |

### Google Drive
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/drive/files` | List files in folder |
| `POST` | `/api/drive/import` | Import folder + classify |

### Wispr Flow
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/wispr/webhook` | Receive voice notes |
| `GET` | `/api/wispr/status` | Connection status |

### GitHub Code Ops
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/github/repo` | Repository info |
| `GET` | `/api/github/prs` | List pull requests |
| `GET` | `/api/github/security` | Aggregated security alerts |
| `POST` | `/api/github/security/scan` | Trigger CIPHER scan |
| `GET` | `/api/github/actions` | Recent workflow runs |
| `GET` | `/api/github/commits` | Recent commits |
| `GET` | `/api/github/branches` | List branches |

### Paperclip AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/paperclip/status` | Orchestration status |
| `GET/POST` | `/api/paperclip/tickets` | List/create tickets |
| `POST` | `/api/paperclip/tickets/{id}/approve` | Board approval |
| `POST` | `/api/paperclip/tickets/{id}/reject` | Board rejection |
| `GET` | `/api/paperclip/budgets` | Per-agent budgets |
| `GET` | `/api/paperclip/audit` | Immutable audit log |

### GHOST OSINT
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/ghost/status` | OSINT status |
| `POST` | `/api/ghost/verify` | Borrower verification |
| `GET` | `/api/ghost/search` | Entity search |
| `POST` | `/api/ghost/investigations` | Create investigation |

### PentAGI
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/pentagi/status` | Pentest status |
| `POST` | `/api/pentagi/assess` | Run security assessment |
| `GET` | `/api/pentagi/vulnerabilities` | List vulnerabilities |

### Growth Ops
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

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Runtime | Python | 3.12+ | Core application, async/await, type hints |
| Async | asyncio + aiohttp | 3.9+ | Non-blocking HTTP server/client, REST APIs |
| Config | python-dotenv + pydantic | 1.0+ / 2.5+ | Environment-based config with validation |
| Logging | structlog | 23.2+ | Structured JSON logging with context binding |
| CLI | click | 8.1+ | Command-line interface for daemon startup |
| System | psutil | 5.9+ | CPU, memory, disk metrics for health monitor |
| Auth | google-auth | 2.23+ | Google Drive service account JWT |
| AI (Frontend) | Puter.js | v2 | 500+ LLM models (Claude, GPT, DeepSeek, Kimi K2.5) — no API keys required |
| AI (Backend) | LLM Router | Custom | Multi-provider routing: OpenAI, Anthropic, OpenRouter |
| Frontend | Vanilla JS + HTML5 | ES2022 | Zero-dependency SPA with CSS custom properties |
| Deploy | Vercel | — | Auto-deploy on push, deploy hooks |
| VCS | GitHub API | v3 REST | Code ops, PRs, Actions, security scanning |

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

---

## Key Terms

| Term | Definition |
|------|-----------|
| **Agentic AI** | AI systems that autonomously plan, execute, and adapt without human intervention |
| **Multi-Agent Orchestration** | Central daemon coordinating 13 agents via task queue with cross-agent pipelines |
| **RAG** | Retrieval-Augmented Generation — agents retrieve context before LLM generation |
| **DAG** | Directed Acyclic Graph — task dependency graphs for pipeline execution |
| **OWASP Top 10** | Standard security vulnerability categories for compliance reporting |
| **FHA HB 4000.1** | FHA Single Family Housing Policy Handbook — regulatory reference for income/DTI |
| **HMDA** | Home Mortgage Disclosure Act — regulatory reporting requirement |
| **ULDD** | Uniform Loan Delivery Dataset — Fannie Mae/Freddie Mac delivery format |
| **DTI** | Debt-to-Income ratio — front-end (housing) and back-end (total) |
| **LOE** | Letter of Explanation — documents explaining borrower anomalies |
| **SOC2/PCI-DSS/GLBA** | Security/privacy compliance frameworks for financial services |

---

## Quick Start

### Prerequisites

- Python 3.12+
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

---

## Project Structure

```
MortgageFintechOS-/
  main.py                              Entry point (CLI)
  setup.sh                             Installation script
  requirements.txt                     Python dependencies
  .env.example                         Environment template
  index.html                           Dashboard UI (SPA)

  config/
    settings.py                        Central configuration (dataclass)

  core/
    orchestrator.py                    Central async daemon (lifecycle, dispatch, scheduling)
    task_queue.py                      Priority-based task queue with history

  agents/
    base.py                           Abstract base agent (retry, heartbeat, integration injection)
    diego.py                          DIEGO — Pipeline orchestration
    martin.py                         MARTIN — Document intelligence + fraud detection
    nova.py                           NOVA — Income & DTI analysis (FHA HB 4000.1)
    jarvis.py                         JARVIS — Condition resolution + LOE drafting
    atlas.py                          ATLAS — Full-stack engineering (GitHub code ops)
    cipher.py                         CIPHER — Security engineering (OWASP + PentAGI)
    forge.py                          FORGE — DevOps engineering (GitHub Actions)
    nexus.py                          NEXUS — Code quality (PR review + test gen)
    storm.py                          STORM — Data engineering (ETL + HMDA + ULDD)
    sentinel.py                       SENTINEL — Codebase intelligence + AutoResearch
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
    server.py                         aiohttp web server (60+ endpoints)

  monitoring/
    health_monitor.py                 Agent health & alerting

  schedulers/
    daily_scheduler.py                Cron-like job scheduler

  persistence/
    state_store.py                    Debounced state persistence
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

---

## License

Copyright 2026 Cory Lawson / The Lawson Group. All rights reserved.

---

*MortgageFintechOS v3.0 — 13 Agents, 4 Divisions, 9 Integrations, 24/7 Autonomous Operation*
