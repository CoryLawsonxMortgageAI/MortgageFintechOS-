# CLAUDE.md — MortgageFintechOS Project Context

## Project Identity

**MortgageFintechOS** is a 24/7 autonomous AI operating system for mortgage lending, built by Cory Lawson (Producing Branch Manager at Geneva Financial LLC / The Lawson Group, NMLS 891785). It orchestrates 13 specialized AI agents across origination, underwriting, compliance, security, growth, and intelligence operations.

**Repository**: `CoryLawsonxMortgageAI/MortgageFintechOS-` (PUBLIC, main branch)

## Architecture

The system follows a layered async daemon architecture:

**Core Layer** — `core/orchestrator.py` is the central daemon managing agent lifecycle, task dispatch, scheduling, health monitoring, and state persistence. It includes a watchdog loop with crash-loop detection and graceful degradation. `core/task_queue.py` is a priority-based async queue with full persistence and history.

**Agent Layer** — 13 agents inherit from `agents/base.py` (BaseAgent), which enforces the execute/health_check contract, retry logic with exponential backoff, and state persistence hooks. Agents are organized into four divisions:

Mortgage Ops: DIEGO (pipeline orchestration), MARTIN (document intelligence), NOVA (income/DTI), JARVIS (condition resolution).
Engineering: ATLAS (full-stack), CIPHER (security), FORGE (devops), NEXUS (code quality), STORM (data engineering).
Intelligence: SENTINEL (research/autoresearch).
Growth Ops: HUNTER (lead discovery), HERALD (content), AMBASSADOR (engagement).

**Integration Layer** — 9 async clients in `integrations/`: GitHub (full API v3 with security scanning), Notion, Google Drive, Wispr Flow, LLM Router (OpenAI/Claude/OpenRouter), Paperclip AI (agent governance), GHOST OSINT, PentAGI, Browser automation.

**Monitoring Layer** — `monitoring/` contains: health_monitor (heartbeats, queue depth, error rates), action_log (append-only agent action log), telemetry (5-factor EWMA risk scoring), hydrospeed (26-node ontology graph).

**Persistence Layer** — `persistence/state_store.py` (atomic JSON writes with debounced flushing), `persistence/agent_database.py` (Dolt-inspired version-controlled DB).

**Dashboard** — `dashboard/server.py` serves 54+ REST API endpoints via aiohttp. Static frontends deploy to Vercel, GitHub Pages, and Netlify.

## Code Standards

All Python code uses Python 3.11+ with modern type hints (dict[str, Any], list[str] | None unions). Use structlog for all logging with bound contextual loggers. Every module begins with a docstring. Every agent method has a type-hinted return signature.

Financial calculations MUST use Decimal with explicit ROUND_HALF_UP rounding. Never use float for money.

All mortgage calculations MUST cite the relevant FHA HB 4000.1 section: W-2 Dual-Method (II.A.5.b), Schedule C (II.A.4.c.ii), DTI/Compensating Factors (II.A.4.b), Collections 5% Rule (II.A.4.d.v). Also reference FNMA Selling Guide and FHLMC Guide where applicable.

## Agent Pattern

Every agent follows this structure:

```python
class XAgent(BaseAgent):
    def __init__(self, max_retries: int = 3):
        super().__init__(name="X", max_retries=max_retries)

    async def execute(self, task: Task) -> dict[str, Any]:
        handlers = {"action_name": self._action_handler, ...}
        handler = handlers.get(task.action)
        if not handler:
            raise ValueError(f"Unknown X action: {task.action}")
        return await handler(task.payload)

    async def health_check(self) -> dict[str, Any]: ...
    def _get_state(self) -> dict[str, Any]: ...
    def _restore_state(self, data: dict[str, Any]) -> None: ...
```

New agents must: inherit BaseAgent, implement execute/health_check, register in `core/orchestrator.py _register_default_agents()`, export from `agents/__init__.py`, and add REST endpoints in `dashboard/server.py`.

## API Pattern

Dashboard endpoints follow this pattern:

```python
async def _handle_endpoint(self, request: web.Request) -> web.Response:
    data = await self._do_something()
    return web.json_response(data, dumps=_json_dumps)
```

POST endpoints for task submission use `await self.orchestrator.submit_task(agent, action, payload, priority)`.

## Deployment

**Vercel**: https://mortgage-fintech-os.vercel.app — Auto-deploys from main. Config: `vercel.json` with `{"outputDirectory":"public","cleanUrls":true}`.

**GitHub Pages**: https://corylawsonxmortgageai.github.io/MortgageFintechOS-/

**Docker**: `cd docker && docker-compose up -d` — Runs app + PostgreSQL 15 + Redis 7.

**Systemd**: `sudo ./setup.sh install && sudo ./setup.sh configure && sudo ./setup.sh start`

## UI Preferences

Default to high-contrast, monochromatic themes: black backgrounds, white/grey text, silver accents. Professional institutional feel. Fonts: Instrument Sans + IBM Plex Mono. Avoid colorful palettes.

## Custom Claude Skills

The project includes 4 custom skills for Claude:

`loan-officer-strategic-tool` — Reverse-engineered DU/LP scoring algorithms for mortgage approval probability analysis. Run via Python scripts in the skill's scripts/ directory.

`mortgage-underwriting` — Full 4 C's analysis with conditional approval memorandum generation. Uses templates and reference materials.

`refinance-payment-summary` — Branded PDF refinance comparison documents for Geneva Financial / The Lawson Group.

`hiring-manager-interview` — Conducts structured technical interviews and produces institutional-grade scorecards with 8-dimension rubric grading.

## Known Gaps (from Interview Assessment, March 2026)

No automated test suite. Priority: add pytest with fixtures covering NOVA income calculations, MARTIN fraud detection, and DIEGO pipeline routing.

No linting/type-checking enforcement. Priority: add ruff.toml and mypy configuration.

No API authentication on dashboard endpoints. Priority: add JWT or API key auth before any production deployment with real borrower data.

No input validation/schema enforcement on REST endpoints. Priority: add pydantic models for request bodies.

## Environment Variables

DATABASE_URL, REDIS_URL, GITHUB_TOKEN, GITHUB_REPO, LOG_LEVEL, AGENT_RETRY_COUNT, AGENT_HEARTBEAT_INTERVAL, ENCRYPTION_KEY, DASHBOARD_PORT, DASHBOARD_HOST, DATA_DIR, NOTION_TOKEN, NOTION_DATABASE_ID, GDRIVE_FOLDER_ID, WISPR_SECRET.
