# Weekly Architecture Review — Sunday @ 6:00 AM

You are performing a weekly architecture review of MortgageFintechOS. This produces a structured report of the week's changes and verifies system integrity.

## Checks

1. **Week's Changes**: Run `git log --oneline --since="7 days ago"`
   - Summarize: N commits, key areas changed, contributors

2. **Agent Registration Integrity**:
   - Read `core/orchestrator.py` — find `_register_default_agents()`
   - Verify all 13 agents are registered: DIEGO, MARTIN, NOVA, JARVIS, ATLAS, CIPHER, FORGE, NEXUS, STORM, SENTINEL, HUNTER, HERALD, AMBASSADOR
   - Read `agents/__init__.py` — verify exports match registered agents

3. **Dashboard Endpoint Count**: Count route definitions in `dashboard/server.py`
   - Report total endpoints and any new ones added this week

4. **Scheduler Integration**: Verify `schedulers/daily_scheduler.py` job definitions align with `config/settings.py` timing defaults

5. **Known Gaps Progress** (from CLAUDE.md):
   - Test coverage: count test files in `tests/` and total test functions
   - Linting: check if `ruff.toml` or `pyproject.toml` has ruff config
   - Type checking: check if `mypy` config exists
   - API auth: check if any auth middleware exists in `dashboard/server.py`
   - Input validation: check for pydantic model usage in endpoint handlers

6. **Code Diff Summary**: Run `git diff --stat HEAD~20..HEAD` (or week's equivalent)
   - Report files with most changes

## Output

Write a Markdown report to `data/weekly-reviews/{YYYY-MM-DD}.md`:

```markdown
# Weekly Architecture Review — {DATE}

## Summary
- Commits this week: N
- Files changed: N
- Key areas: [list]

## Agent Registration: [PASS/FAIL]
[Details if fail]

## Dashboard Endpoints: N total
[New endpoints this week]

## Known Gaps Status
| Gap | Status | Progress |
|-----|--------|----------|
| Test suite | [X/13 agents covered] | [trend] |
| Linting | [configured/missing] | |
| Type checking | [configured/missing] | |
| API auth | [present/missing] | |
| Input validation | [present/missing] | |

## Recommendations
[Prioritized list of 3-5 items]
```

## Rules

- NEVER modify any files except writing the report to `data/weekly-reviews/`
- NEVER push to git, merge branches, or create PRs
- Keep the report concise — 1 page max
