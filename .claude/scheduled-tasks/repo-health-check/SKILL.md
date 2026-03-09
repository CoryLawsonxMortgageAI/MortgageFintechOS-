# Repo Health Check — Daily @ 7:00 AM

You are monitoring the MortgageFintechOS repository health. Run these checks and produce a concise report:

## Checks

1. **System Health**: Run `python main.py health` — report any agents in ERROR state
2. **System Status**: Run `python main.py status` — flag if queue pending > 50 tasks
3. **Git Status**: Run `git status` — report uncommitted changes or untracked files
4. **Stale Branches**: Run `git branch --list` — flag branches not merged to main
5. **Lint Report**: Run `ruff check . --statistics` — report top 5 lint rule categories
6. **Test Suite**: Run `pytest --tb=short -q` — report pass/fail count

## Output Format

```
MORTGAGEFINTECHOS DAILY HEALTH — [DATE]
========================================
Agents:     [X healthy / Y total]
Queue:      [N pending tasks]
Git:        [clean / N uncommitted files]
Lint:       [N issues across M rules]
Tests:      [X passed, Y failed]
Action Required: [Yes/No — list items if yes]
```

Only flag items that need attention. If everything is green, say so briefly.
