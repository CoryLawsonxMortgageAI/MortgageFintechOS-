# Claude Code Loops & Scheduled Tasks — Quick Reference

## Your Machine: HP ProBook 455 (16GB RAM, Ryzen 5 5625U)

**RAM Rule**: Max 2-3 CLI loops active. Stagger Desktop tasks by 30+ min.

---

## CLI /loop Commands (Session-Scoped — Dies on Exit)

### During Active Development
```
/loop 10m run pytest -x --tb=short and ruff check . — report any new failures

/loop 3m run ruff check . --fix --unsafe-fixes and report what was auto-fixed

/loop 15m curl http://localhost:8080/api/healthz and http://localhost:8080/api/status — alert if unhealthy
```

### After Pushing to Main
```
/loop 5m check GitHub Actions with gh run list --limit 3 — tell me when deploy finishes
```

### During PR Review
```
/loop 5m check gh pr checks <PR_NUMBER> — tell me when all checks pass

/loop 10m check gh pr view <PR_NUMBER> --comments — alert me of new feedback
```

### One-Shot Reminders
```
remind me in 30 minutes to check the deployment status

in 1 hour, run the full test suite and report results
```

---

## Detailed Loop Prompts

### Guardian Loop (5-min health watch)

**Command:** `/loop 5m`

**Prompt:**
```
Check MortgageFintechOS health: run `curl -s localhost:8080/api/healthz` and `docker ps --format "{{.Names}}: {{.Status}}"`. Also check RAM with `free -m | awk '/^Mem:/ {print $7}'` — warn if below 4096MB. Only report if something is unhealthy, a container is down, RAM is low, or the API is unreachable. If everything is healthy, say nothing.
```

**Use when:** Any active coding session where the system is running locally.

### PR Review Loop (15-min code review)

**Command:** `/loop 15m`

**Prompt:**
```
Run `gh pr list --repo CoryLawsonxMortgageAI/MortgageFintechOS- --state open --json number,title,createdAt,updatedAt` and check for new or updated PRs since the last check. For any new PRs, fetch the diff with `gh pr diff <number>` and provide a code review summary covering:
- Correctness and logic errors
- Security implications (OWASP top 10)
- Adherence to CLAUDE.md standards: structlog logging, type hints, Decimal for money, docstrings, BaseAgent pattern
- FHA/FNMA citation requirements for mortgage calculations
Do not post reviews to GitHub automatically — present the review for my approval first.
```

**Use when:** Working through a PR queue or expecting collaborator contributions.

### Test Gap Closer (10-min untested module finder)

**Command:** `/loop 10m`

**Prompt:**
```
Scan for modules without test files. Priority order from CLAUDE.md: 1) NOVA income, 2) MARTIN fraud detection, 3) DIEGO pipeline routing. Check if tests/test_nova_income.py, tests/test_martin_document.py, tests/test_diego_pipeline.py exist. For the highest-priority untested module, read the source and outline the test file: fixture definitions, key test cases (happy path, edge cases, error handling), and which Task payloads to test. Do not write files — present the plan for my approval.
```

**Use when:** Dedicated test-writing sessions to close known gaps.

### Auto-Fix Loop (10-min compilation & standards check)

**Command:** `/loop 10m`

**Prompt:**
```
Run `python -m py_compile` against files modified in the working tree (from `git diff --name-only` and `git diff --cached --name-only`). If any compilation errors are found, fix them. Also check modified files for violations of project standards: missing docstrings, missing type hints, use of float for financial values (must be Decimal). Run `ruff check --fix` on modified files. Fix issues automatically and report what was changed.
```

**Use when:** Active bug-fix or refactoring sessions.

### Deployment Watcher (3-min deploy monitor)

**Command:** `/loop 3m`

**Prompt:**
```
Check `gh run list --repo CoryLawsonxMortgageAI/MortgageFintechOS- --limit 1 --json status,conclusion,name,updatedAt` for the latest workflow run. Also check Vercel: `curl -s -o /dev/null -w "%{http_code}" https://mortgage-fintech-os.vercel.app/` and GitHub Pages: `curl -s -o /dev/null -w "%{http_code}" https://corylawsonxmortgageai.github.io/MortgageFintechOS-/`. Report status. If a workflow failed, fetch logs with `gh run view <id> --log-failed` and summarize the error. Stop reporting once deploy succeeds.
```

**Use when:** After pushing to main, waiting for CI/CD to complete.

---

## Desktop Scheduled Tasks (Persistent — Survives Restarts)

| Task | Schedule | What It Does |
|------|----------|--------------|
| `repo-health-check` | Daily 7:00 AM | System health, git status, lint, tests |
| `pr-monitor-autofix` | Hourly | Check PRs, auto-fix lint, report failures |
| `dependency-security-audit` | Monday 3:00 AM | CVE scan, outdated deps, secrets check |
| `git-sync-and-clean` | Daily 6:00 AM | Fetch, sync status, stale branches |
| `system-health-sentinel` | Every 30 min | API health, risk scores, Docker, RAM monitoring |
| `weekly-architecture-review` | Sunday 6:00 AM | Week's changes, agent integrity, gap progress |

### Setup in Claude Code Desktop:
1. Click **Schedule** in the sidebar
2. Click **+ New task**
3. Set name, frequency, and paste the prompt from `.claude/scheduled-tasks/<name>/SKILL.md`

---

## Daily Workflow

```
6:00 AM  — [auto] git-sync-and-clean
7:00 AM  — [auto] repo-health-check
         — Open Claude Code CLI
         — /loop 5m Guardian Loop (health watch)
         — /loop 10m Auto-Fix Loop (during coding)
Hourly   — [auto] pr-monitor-autofix (background)
Every 30 — [auto] system-health-sentinel (silent unless problems)
After push — /loop 3m Deployment Watcher
Evening  — Close CLI (loops auto-stop)
Sunday   — [auto] weekly-architecture-review at 6 AM
Monday   — [auto] dependency-security-audit at 3 AM
```

---

## Resource Rules (16GB RAM Budget)

| Component | Estimated RAM | Notes |
|-----------|--------------|-------|
| OS (Linux/Windows) | 3-4 GB | Base + background services |
| Docker Desktop | 1-2 GB | WSL2 VM overhead |
| PostgreSQL + Redis | 250-500 MB | Database containers |
| MortgageFintechOS app | 200-500 MB | 13 agents + dashboard |
| Claude Code CLI session | 200-400 MB | Active dev session |
| Claude Code Desktop task | 200-400 MB | Per scheduled task |
| **Reserved headroom** | **2-3 GB** | For spikes |

**Constraints:**
1. **Max 1 Desktop scheduled task running simultaneously** — stagger by 30+ min
2. **Max 2-3 CLI loops active** — pick loops matching your current task
3. **Docker ON?** Sequence tests + lint (don't parallelize). ~4.5 GB headroom.
4. **Docker OFF?** Safe to run concurrently. ~6 GB headroom.
5. **Max 50 loops per CLI session** — kill unused ones
6. **CLI loops expire after 3 days** automatically
7. **Desktop tasks run even when CLI is closed** (Desktop app must be open)
8. **Disable Growth Ops agents** during dev: set `GROWTH_OPS_ENABLED=false` in `.env`

---

## Tips

- Use `bash scripts/check-health.sh` for a quick manual health check
- Use `bash scripts/check-health.sh --json` for machine-readable output
- The Guardian Loop calls the same endpoints as the System Health Sentinel — but interactively
- Desktop tasks produce reports in `data/` subdirectories (git-ignored)
