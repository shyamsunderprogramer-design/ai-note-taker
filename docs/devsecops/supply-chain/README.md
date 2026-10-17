# Supply Chain

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`

---

## What's in this folder

| File | What |
|---|---|
| [dependabot-policy.md](dependabot-policy.md) | The Dependabot triage policy and SLA (stub — to be expanded) |

---

## Tools

| Tool | What it does | Where it runs |
|---|---|---|
| Dependabot | Opens PRs for outdated deps | `.github/dependabot.yml` (co-owned devops + devsecops) |
| `npm audit` | Flags known-vuln npm deps | CI on every PR |
| `pip-audit` | Flags known-vuln PyPI deps | CI on every PR |
| Trivy | Scans Docker image + filesystem for CVEs | `trivy-scan.sh` in CI |
| CodeQL | Static analysis for security issues | `.github/workflows/codeql.yml` (if present) |
| `detect-private-key` (pre-commit) | Catches accidentally committed `*.pem` / `*.key` / `id_rsa` | Pre-commit hook |

---

## SLA for triaging Dependabot PRs

| Severity | Triage SLA | Merge SLA |
|---|---|---|
| Critical (RCE, auth bypass) | same day | 24h |
| High (data leak, privilege escalation) | 3 days | 1 week |
| Medium (DoS, info leak) | 1 week | 2 weeks |
| Low (best practice, hardening) | 2 weeks | next release |

This SLA is enforced by `.github/dependabot.yml` (the `labels`
+ `assignees` block) and the
[`dependabot-policy.md`](dependabot-policy.md) doc.

---

## When to add a doc here

Add a doc here when:

- You're adding a new SCA tool → update the table above
- You're tightening the SLA for a new dep class → update
  `dependabot-policy.md`
- You're documenting a known-watch dep (like bcrypt 5.0.0 +
  passlib 1.7.4) → add a section to `dependabot-policy.md`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
