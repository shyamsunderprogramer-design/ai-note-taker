# DevSecOps Role — Charter

> **Role tag:** `devsecops`
> **GitHub team:** `role-devsecops` (1 member today: `@shyamsunderprogramer-design`)
> **Charter owner:** This file is the canonical answer to "what does DevSecOps own?"

---

## What this role owns

Security, supply chain, secrets, compliance, and threat modeling. File-level
inventory, in priority order:

### Security policy & audit
- `backend/security/` (co-owned with `backend`; see Co-owned section)
  - devsecops owns the *policy* files: `audit.py`, `errors.py`
  - devsecops owns the *threat-model* perspective on `auth.py`, `encryption.py`,
    `rate_limit.py`, `validation.py` (but backend owns the *implementation* of
    those modules)
- `SECURITY.md` (root) — public security policy
- `BROWSER_EXTENSION_SAFETY.md` (root) — Chrome extension threat model

### Threat model & supply chain docs
- `docs/devsecops/security/threat-model.md`
- `docs/devsecops/supply-chain/dependabot-policy.md`
- `docs/devsecops/supply-chain/README.md`
- `docs/devsecops/compliance/audit-log-policy.md`
- `docs/security/SECURITY_IMPLEMENTATION_SUMMARY.md` — moved from
  `docs/security/SECURITY_IMPLEMENTATION_SUMMARY.md`
- `docs/security/BROWSER_EXTENSION_SAFETY.md` — moved from
  `BROWSER_EXTENSION_SAFETY.md` (root)

### Tooling & config
- `.claude/` — Claude Code allowlist, agent scope, project settings
- `.pre-commit-config.yaml` — pre-commit hook definitions
- `.github/CODEOWNERS` — code-ownership routing
- `.github/PULL_REQUEST_TEMPLATE.md` — PR template (role-aware)
- `.github/ISSUE_TEMPLATE/` — bug report, feature request, question templates
- `.github/dependabot.yml` — co-owned with `devops`; devops owns the syntax,
  devsecops owns the supply-chain review

### Compliance
- `docs/devsecops/compliance/SECURITY.md` — moved from `SECURITY.md` (root)

---

## What this role reads but doesn't own

| Area | Owner | Why DevSecOps cares |
|---|---|---|
| `backend/routes/*.py` | backend | DevSecOps reviews for authn/authz bugs, SSRF, injection |
| `backend/security/*.py` | devsecops + backend | DevSecOps owns the policy; backend owns the impl |
| `Dockerfile`, `render.yaml`, `vercel.json` | devops + devsecops | DevSecOps reviews attack-surface changes |
| `backend/requirements*.txt` | backend + devsecops | DevSecOps reviews supply-chain risk on every dep bump |
| `electron/stealth.js` | devops + devsecops | DevSecOps reviews anti-capture mechanisms for bypass risks |
| `apps/web/app.js` (CSP usage) | uiux + backend | DevSecOps reviews for unsafe CSP relaxation |
| `docs/qa/test-strategy.md` | qa | DevSecOps reviews the security-regression section |

---

## What this role delivers

Typical PR outputs from a DevSecOps engineer:

- New threat-model section in `docs/devsecops/security/threat-model.md`
- New supply-chain rule in `docs/devsecops/supply-chain/dependabot-policy.md`
- New audit-log policy in `docs/devsecops/compliance/audit-log-policy.md`
- New secret-rotation runbook in `docs/devsecops/security/`
- Code-review comments on any PR touching auth, encryption, validation
- New pre-commit hook in `.pre-commit-config.yaml`
- New security regression test (in `backend/tests/`)
- Dependabot policy tweak in `.github/dependabot.yml`
- CSP / Permissions-Policy review for any `vercel.json` change
- Supply-chain review on any `requirements.txt` / `package.json` bump

---

## What this role's AI agent has access to

> **Status:** the role-scoped AI agent is a planning stub, not yet wired up.
> See `agents/devsecops/AGENTS.md` for the scoping plan.

When the agent is online, it will be able to:

- **Read:** every file in the repo (DevSecOps needs the full picture)
- **Write:** files in `.claude/`, `.pre-commit-config.yaml`, `.github/CODEOWNERS`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`,
  `.github/dependabot.yml`, `SECURITY.md`, `BROWSER_EXTENSION_SAFETY.md`,
  `docs/devsecops/`
- **Read-only on (for review):** `backend/security/`, `backend/routes/`,
  `Dockerfile`, `render.yaml`, `vercel.json`, `electron/stealth.js`
- **Bash:** gitleaks, bandit, pip-audit, npm audit, semgrep (security scanners only)
- **Memory:** `agents/devsecops/MEMORY.md`

It will **not** have access to:
- Any production credentials (even for "verification")
- Direct prod access (read-only on prod is gated; the agent reads only what
  the audit log + scanner reports)
- The ability to bypass pre-commit hooks

---

## What this role reviews when it gets a PR

When CODEOWNERS routes a PR to `role-devsecops`, this role checks:

1. **No new secrets** — `.env`, `*.pem`, `*.key`, `users.json` not in the diff
2. **Supply-chain reviewed** — every `requirements.txt` / `package.json` bump
   has a changelog URL or known-watch entry
3. **CSP / Permissions-Policy unchanged** — or explicitly justified in the PR body
4. **Authn/authz unchanged or hardened** — no new route without a `Depends(require_authentication)`
5. **Audit log covers the new action** — if the PR adds a new mutating endpoint,
   `audit.py` records it
6. **No new pre-commit bypass** — the `--no-verify` flag is never added
7. **Co-owned files have both approvals** — runtime shell, deploy manifest,
   test infra, API contract — the second role's reviewer is tagged

---

## How to contact this role

- **Today:** `@shyamsunderprogramer-design` (sole human member of `role-devsecops`)
- **When collaborators join:** tag the `role-devsecops` GitHub Team in the PR

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
