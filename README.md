# MortgageFintechOS

**24/7 Autonomous AI Operating System for Mortgage Lending**

Version 1.0.0 | Cory Lawson / The Lawson Group

---

## Overview

MortgageFintechOS is an autonomous AI operating system that runs 24/7 to manage mortgage lending operations. It replaces manual processes with four specialized AI agents orchestrated by a central daemon with scheduling, health monitoring, and GitHub integration.

---

## Architecture

```
+--------------------------------------------------------------+
|                      MortgageFintechOS                       |
|                  Autonomous AI Operating System               |
+--------------------------------------------------------------+
|                        Orchestrator                           |
|            Task Queue | Scheduler | Health Monitor            |
+----------+-----------+-----------+---------------------------+
|  DIEGO   |  MARTIN   |   NOVA    |         JARVIS            |
| Pipeline | Document  | Income &  |       Condition            |
| Orchestr | Intellig  |   DTI     |       Resolution           |
+----------+-----------+-----------+---------------------------+
|              GitHub Integration | Alert System                |
+--------------------------------------------------------------+
|          PostgreSQL  |  Redis  |  Docker / Systemd            |
+--------------------------------------------------------------+
```

---

## AI Agents

| Agent | Role | Key Capabilities |
|-------|------|-----------------|
| DIEGO | Pipeline Orchestration | Loan triage (FHA/VA/Conv/USDA), stage tracking, priority assignment, pipeline health |
| MARTIN | Document Intelligence | Classification, OCR validation, fraud detection, completeness audit |
| NOVA | Income & DTI Analysis | W-2 dual-method (HB 4000.1 II.A.5.b), Schedule C (II.A.4.c.ii), DTI grid (II.A.4.b), Collections 5% rule (II.A.4.d.v) |
| JARVIS | Condition Resolution | LOE drafting, condition-to-document mapping, compliance citations (FHA/FNMA/FHLMC) |

---

## Scheduled Operations

| Time | Agent | Operation |
|------|-------|-----------|
| 06:00 | MARTIN | Document Audit |
| 06:30 | NOVA | Income Recalculation |
| 07:00 | DIEGO | Pipeline Health Check |
| Hourly | System | Queue Health Check |
| Weekly | DIEGO | Pipeline Report |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- PostgreSQL 15+ (optional)
- Redis 7+ (optional)

### Install

```bash
git clone https://github.com/CoryLawsonxMortgageAI/MortgageFintechOS-.git
cd MortgageFintechOS-
cp .env.example .env
# Edit .env with your settings

# Option 1: Direct install
./setup.sh install

# Option 2: Docker
cd docker && docker-compose up -d
```

### Commands

```bash
python main.py start       # Start the autonomous system
python main.py status      # Show system status
python main.py health      # Run health checks
python main.py schedule    # View scheduled tasks
python main.py agents      # List registered agents
```

### Systemd Deployment

```bash
sudo ./setup.sh install
sudo ./setup.sh configure
sudo ./setup.sh start
sudo ./setup.sh status
sudo ./setup.sh logs
```

---

## Project Structure

```
MortgageFintechOS-/
  main.py                        Entry point (CLI)
  setup.sh                       Installation script
  requirements.txt               Python dependencies
  .env.example                   Environment template
  config/
    settings.py                  Central configuration
  core/
    orchestrator.py              Central async daemon
    task_queue.py                Priority-based task queue
  agents/
    base.py                      Abstract base agent
    diego.py                     DIEGO - Pipeline orchestration
    martin.py                    MARTIN - Document intelligence
    nova.py                      NOVA - Income & DTI analysis
    jarvis.py                    JARVIS - Condition resolution
  schedulers/
    daily_scheduler.py           Cron-like task scheduler
  integrations/
    github_client.py             GitHub API integration
  monitoring/
    health_monitor.py            Agent health & alerting
  docker/
    Dockerfile                   Container image
    docker-compose.yml           Full stack deployment
    mortgagefintechos.service    Systemd unit file
```

---

## FHA Compliance

All calculations cite specific FHA Handbook 4000.1 sections:

- **W-2 Dual-Method**: II.A.5.b
- **Schedule C Self-Employment**: II.A.4.c.ii
- **DTI Ratios & Compensating Factors**: II.A.4.b
- **Collections 5% Rule**: II.A.4.d.v

---

## Configuration

Set environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection | postgresql://localhost:5432/mortgageos |
| REDIS_URL | Redis connection | redis://localhost:6379 |
| GITHUB_TOKEN | GitHub API token | (required for GitHub integration) |
| GITHUB_REPO | Target repository | CoryLawsonxMortgageAI/MortgageFintechOS- |
| LOG_LEVEL | Logging level | INFO |
| AGENT_RETRY_COUNT | Max task retries | 3 |

---

## License

Copyright 2026 Cory Lawson / The Lawson Group. All rights reserved.
