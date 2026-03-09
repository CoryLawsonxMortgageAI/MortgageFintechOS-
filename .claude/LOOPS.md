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

## Desktop Scheduled Tasks (Persistent — Survives Restarts)

| Task | Schedule | What It Does |
|------|----------|--------------|
| `repo-health-check` | Daily 7:00 AM | System health, git status, lint, tests |
| `pr-monitor-autofix` | Hourly | Check PRs, auto-fix lint, report failures |
| `dependency-security-audit` | Monday 3:00 AM | CVE scan, outdated deps, secrets check |
| `git-sync-and-clean` | Daily 6:00 AM | Fetch, sync status, stale branches |

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
         — /loop 15m monitor localhost health
         — /loop 10m run tests and lint
Hourly   — [auto] pr-monitor-autofix (background)
Evening  — Close CLI (loops auto-stop)
Monday   — [auto] dependency-security-audit at 3 AM
```

---

## Tips

- **Max 50 loops per CLI session** — kill unused ones
- **CLI loops expire after 3 days** automatically
- **Desktop tasks run even when CLI is closed** (Desktop app must be open)
- **Docker ON?** Sequence tests + lint (don't parallelize). ~4.5 GB headroom.
- **Docker OFF?** Safe to run concurrently. ~6 GB headroom.
