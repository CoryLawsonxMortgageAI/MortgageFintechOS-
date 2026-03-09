# Git Sync & Clean — Daily @ 6:00 AM

You are maintaining the git repository hygiene for MortgageFintechOS.

## Steps

1. **Fetch latest**: Run `git fetch origin main`
2. **Check sync status**: Compare local main with origin/main
   - Report how many commits behind/ahead
3. **List stale branches**: Run `git branch --format='%(refname:short) %(committerdate:relative)'`
   - Flag any branches older than 7 days that are not main
4. **Check for conflicts**: If any open PRs exist, report potential merge conflicts
5. **Disk usage**: Report size of `data/` directory and `.git/` directory

## Rules

- NEVER run `git pull` automatically — only fetch and report
- NEVER delete branches — only flag them for review
- NEVER run `git clean` or `git reset` — only report status
- Keep the report brief — 5 lines max if everything is clean
