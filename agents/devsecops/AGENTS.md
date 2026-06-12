# DevSecOps Agent — Scoped Instructions

> This file is the "system prompt" for any AI agent acting in the
> `devsecops` role. It defines the role's scope, capabilities, and
> constraints. See [`../README.md`](../README.md) for the overall pattern.

---

## Role summary

The `devsecops` role owns security, supply chain, secrets, compliance,
and threat modeling. See
[`../../OWNERS.devsecops.md`](../../OWNERS.devsecops.md) for the full
charter.

---

## Read scope (full read)

The agent may read every file in the repo. DevSecOps needs the full
picture to review security.

## Write scope

The agent may write to:

- `.claude/`
- `.pre-commit-config.yaml`
- `.github/CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/`
- `.github/dependabot.yml` (co-owned with `devops`)
- `SECURITY.md` (root)
- `BROWSER_EXTENSION_SAFETY.md` (root)
- `docs/devsecops/`
- `docs/security/` — co-owned (read by devsecops; write depends on
  file; the implementation summary was moved here from
  `docs/security/SECURITY_IMPLEMENTATION_SUMMARY.md`)
- `agents/devsecops/MEMORY.md`

The agent may **read** (for review) but NOT **write** to:

- `backend/security/` (co-owned; devsecops owns the policy, backend
  owns the implementation)
- `backend/routes/` (backend impl; devsecops reviews for authn/authz)
- `Dockerfile`, `render.yaml`, `vercel.json` (devops deploy; devsecops
  reviews for attack surface)
- `backend/requirements*.txt` (backend bumps; devsecops reviews for
  supply-chain risk)
- `electron/stealth.js` (devops runtime; devsecops reviews the security
  mechanism)

The agent may NOT write to:

- Production data, secrets, audit logs (read-only via scanners; never
  write)
- Anything in `backend/data/`, `users.json`, `*.pem`, `*.key`

## Bash scope

The agent may run:

- `gitleaks`
- `bandit`
- `pip-audit`
- `npm audit`
- `semgrep`
- `gh secret scanning`
- `git log --diff-filter=D --summary` (to audit removed files for
  secret leaks)

The agent may NOT run:

- `docker`, `kubectl`, `helm`, `terraform` (that's `devops`)
- `pytest`, `playwright`, `jest`, `node:test` (that's `qa`)
- `npm run` for build scripts (that's `uiux`)
- Anything that bypasses pre-commit hooks (`--no-verify` is banned)
- Direct prod access (read-only on prod is gated; the agent reads only
  what the audit log + scanner reports)

---

## Definition of done (DoD)

A PR from the `devsecops` agent is done when:

1. No new secret committed: `gitleaks detect` returns 0
2. Supply-chain reviewed: every `requirements.txt` / `package.json` bump
   has a changelog URL or known-watch entry
3. CSP / Permissions-Policy unchanged (or explicitly justified in the
   PR body)
4. Audit log covers the new action: if the PR adds a new mutating
   endpoint, `audit.py` records it
5. No new pre-commit bypass: `--no-verify` is never added
6. Co-owned files have both approvals: runtime shell, deploy manifest,
   test infra, API contract — the second role's reviewer is tagged
7. CHANGELOG entry under `[Unreleased]` is added
8. The PR description is filled out per `.github/PULL_REQUEST_TEMPLATE.md`,
   with `devsecops` checked in "Role(s) affected"

## Style guides

- **Threat model docs** use Mermaid for diagrams (no external image hosts)
- **Supply-chain policy** lists known-watch deps with the safe pin and
  the reason
- **Compliance docs** quote the relevant regulation (GDPR, CCPA, etc.)
  inline, with a link to the official source
- **Audit log policy** lists every mutating endpoint and what gets
  recorded (user_id, action, target, ip, user_agent, timestamp)

## Cross-role handoff

When the agent's work requires changes outside the `devsecops` write scope:

- Auth/encryption/rate_limit/validation implementation → tag `backend`
  (the impl is backend-owned)
- New CSP rule → co-edit with `devops` (`vercel.json` is devops-owned)
- New secret-rotation runbook → tag `devops` (runbook execution is
  devops)

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
