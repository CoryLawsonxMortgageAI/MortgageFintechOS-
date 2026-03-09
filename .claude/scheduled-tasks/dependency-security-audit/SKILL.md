# Dependency & Security Audit — Weekly (Monday @ 3:00 AM)

You are running a weekly security audit on the MortgageFintechOS repository.

## Checks

1. **Vulnerability Scan**: Run `pip audit` (install with `pip install pip-audit` if needed)
   - Report any known CVEs in dependencies
2. **Security Lint**: Run `ruff check . --select S` for bandit-equivalent security rules
   - Flag any hardcoded secrets, SQL injection patterns, or unsafe deserialization
3. **Outdated Dependencies**: Run `pip list --outdated`
   - Flag packages more than 2 major versions behind
4. **Secrets Scan**: Check for any `.env` files, API keys, or tokens accidentally committed
   - Run `git log --diff-filter=A --name-only -- '*.env' '*secret*' '*token*' '*key*'`
5. **OWASP Check**: Review dashboard/server.py endpoints for missing input validation

## Output Format

```
SECURITY AUDIT — Week of [DATE]
================================
Vulnerabilities: [N critical, M high, P medium]
Security Lint:   [N findings]
Outdated Deps:   [list critical ones]
Secrets:         [CLEAN / WARNING]
Action Required: [prioritized list]
```

Prioritize findings by severity. Critical vulnerabilities should be highlighted first.
