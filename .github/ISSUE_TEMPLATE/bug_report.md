---
name: Bug report
about: Report something that's broken or behaving wrong
title: "[bug] "
labels: ["bug", "needs-triage"]
assignees: []
---

## Affected role

<!--
ANT is organized by 5 roles. Pick the role whose owned files contain
the bug — CODEOWNERS routes the issue to that role's GitHub Team.
See OWNERS.{role}.md at the repo root for each role's charter and
docs/{role}/README.md for the role's docs.
-->

- [ ] **backend** — FastAPI, services, DB, AI integration, Neo4j (`backend/`)
- [ ] **uiux** — web SPA, mobile, Chrome extension, Electron UI, design (`apps/`, `mobile/`, `electron/features/`)
- [ ] **devops** — deploy, runtime shell, CI, infra, mobile-native build (`Dockerfile`, `k8s/`, `infrastructure/`, `electron/main.js`/`preload.js`/`stealth.js`, `.github/workflows/`)
- [ ] **qa** — tests, fixtures, e2e, performance (`e2e/`, `qa/`, `backend/tests/`, `mobile/__tests__/`, `electron/tests/`)
- [ ] **devsecops** — security, supply chain, secrets, compliance (`.claude/`, `.pre-commit-config.yaml`, `.github/`, `SECURITY.md`, `backend/security/`)
- [ ] **Unclear / other** — describe in "Additional context"

## Affected area

<!--
File path or feature name. Examples:
  - `backend/routes/agents.py` (backend)
  - `apps/web/app.js` (uiux)
  - `electron/main.js` window-bounds (devops, co-owned with backend)
  - `vercel.json` CSP (devops, co-owned with devsecops)
-->

## Describe the bug

<!-- A clear, concise description of what the bug is. -->

## To reproduce

<!--
Step-by-step instructions to reproduce the behavior.
Include the exact command(s), URL(s), or UI flow.
-->

1. …
2. …
3. …

**Expected behavior:** <!-- What you expected to happen. -->

**Actual behavior:** <!-- What actually happened. -->

## Environment

<!-- Fill in what applies; delete the rest. -->

- **Platform:** <!-- desktop (Electron) / web / mobile (iOS/Android) / CLI / backend -->
- **OS:** <!-- Windows 11 / macOS 14 / Ubuntu 22.04 / iOS 17 / Android 14 -->
- **ANT version:** <!-- e.g., 1.2.3 or commit SHA -->
- **Backend:** <!-- local uvicorn / Render / other -->

## Logs / error output

<!--
Paste the relevant log lines, stack trace, or screenshot.
For backend bugs: `backend/data/audit_logs/audit.jsonl` and Python tracebacks.
For desktop bugs: open DevTools (Ctrl+Shift+I) and copy the console output.
-->

```text
PASTE LOGS HERE
```

## Severity

<!-- Mark one. -->

- [ ] Blocker — can't use the app
- [ ] High — major feature broken
- [ ] Medium — workaround exists
- [ ] Low — minor / cosmetic

## Fix #35 upgrade note

<!--
If you just upgraded from a pre-2.1.0 install AND the bug is
auth-related (login, sessions, security question, password reset,
user account, "users.json not found" errors), please mention it.
Fix #35 migrated user storage from `data/users.json` to a
SQLAlchemy table, and a small number of upgrade edge cases may
not have been covered by the auto-migration.
-->

- [ ] This bug appeared after upgrading from a pre-2.1.0 version
- [ ] This bug is auth / user-account related
- [ ] I've checked `backend/data/.migrated_to_sql` exists (post-upgrade only)
- [ ] I've checked `/auth/login` works with my existing credentials

## Additional context

<!-- Anything else that might help: workaround tried, related issues, etc. -->
