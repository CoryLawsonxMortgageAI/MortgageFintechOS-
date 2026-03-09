# PR Monitor & Auto-Fix — Hourly

You are monitoring GitHub PRs and CI for the MortgageFintechOS repository. Auto-fix what you can.

## Steps

1. **List open PRs**: Run `gh pr list --repo CoryLawsonxMortgageAI/MortgageFintechOS-`
2. **Check CI status**: For each open PR, run `gh pr checks <PR_NUMBER>`
3. **Auto-fix lint failures**:
   - If CI fails on ruff lint: run `ruff check . --fix` and commit the fix
   - Only fix lint issues — do not auto-fix test failures without understanding root cause
4. **Report test failures**: If tests are failing, investigate the error and report what needs manual attention
5. **Check deployment**: Run `gh run list --limit 3` — report if latest deploy succeeded or failed

## Rules

- NEVER force-push or rewrite history
- NEVER merge PRs automatically — only fix lint and report
- If a PR has been open > 7 days with no activity, flag it
- Keep output concise — one line per PR
