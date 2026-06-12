# Pull Request

<!--
Thanks for contributing to ANT (AI Note Taker)!
Please fill out the template below so reviewers have what they need.
-->

## Role(s) affected

<!--
ANT is organized by 5 roles: backend, uiux, devops, qa, devsecops.
Mark all roles whose owned files this PR touches. CODEOWNERS uses
this to route reviewers. See OWNERS.{role}.md at the repo root for
each role's charter and docs/{role}/README.md for the role's docs.
-->

- [ ] **backend** — FastAPI, services, DB, AI integration, Neo4j (`backend/`)
- [ ] **uiux** — web SPA, mobile, Chrome extension, Electron UI, design (`apps/`, `mobile/`, `electron/features/`)
- [ ] **devops** — deploy, runtime shell, CI, infra, mobile-native build (`Dockerfile`, `k8s/`, `infrastructure/`, `electron/main.js`/`preload.js`/`stealth.js`, `.github/workflows/`)
- [ ] **qa** — tests, fixtures, e2e, performance (`e2e/`, `qa/`, `backend/tests/`, `mobile/__tests__/`, `electron/tests/`)
- [ ] **devsecops** — security, supply chain, secrets, compliance (`.claude/`, `.pre-commit-config.yaml`, `.github/`, `SECURITY.md`, `backend/security/`)

<!--
Per-role checklist — only mark what applies to THIS PR. The auto-review
will route to the role(s) you marked above; their checklist tells the
reviewer what to confirm.
-->

- [ ] **Backend:** `cd backend && pytest tests/ -q` passes; new endpoint updates `docs/backend/api/API_REFERENCE.md`
- [ ] **UI/UX:** `cd apps/web && npx vite build` passes; visual changes have a screenshot or recording; new HTML page added a `vercel.json` rewrite
- [ ] **Devops:** build artifacts verified (Docker / Render / K8s); CHANGELOG entry added; CSP / secret / base-image change flagged
- [ ] **QA:** new / changed behavior has a test; e2e covers the new user flow; DOCUMENTED BUG tests (if touched) are documented in the test docstring
- [ ] **DevSecOps:** no new secrets, supply-chain reviewed, CSP / permissions unchanged (or explicitly justified in PR body)

## Summary

<!--
One or two sentences on what this PR does and why.
Link the relevant issue with "Fixes #123" or "Closes #456".
-->

- **What:**
- **Why:**
- **Fixes / Closes:**

## Type of change

<!-- Mark the relevant options with an "x". -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactor / cleanup (no functional change)
- [ ] CI / CD change
- [ ] Infrastructure (Terraform, K8s, Docker)

## Test plan

<!--
Describe the tests you ran and how to reproduce them.
Include any specific test commands, fixtures, or environments.
-->

- [ ] Backend pytest passes: `cd backend && pytest tests/ -q`
- [ ] Web build passes: `cd apps/web && npm run build`
- [ ] Mobile Jest passes (if mobile changed): `cd mobile && npm test`
- [ ] Electron node:test passes (if electron changed): `cd electron && npm test`
- [ ] E2E smoke passes (if user-facing): `cd e2e && npx playwright test --grep @smoke`
- [ ] Manual testing: describe what you ran

## Checklist

- [ ] My code follows the project's style guide
- [ ] I have added tests for new functionality (or explained why not in the PR description)
- [ ] I have updated the relevant documentation (README, CHANGELOG, `docs/<role>/`)
- [ ] I have added an entry to CHANGELOG.md under `[Unreleased]`
- [ ] I have NOT introduced any new secrets, API keys, or credentials
- [ ] I have verified no `.env`, `*.pem`, or `users.json` files are included
- [ ] My changes generate no new linter warnings
- [ ] Alembic migration is included if I changed a SQLAlchemy model
- [ ] I have read the CONTRIBUTING.md guide
- [ ] If this PR touched a co-owned file (runtime shell, deploy manifest,
      test infra, API contract), the second role's reviewer has been
      tagged in a PR comment

## Screenshots / recordings

<!--
For UI changes: paste a screenshot or short screen recording.
For backend changes: paste a curl output, OpenAPI diff, or test output.
-->

## Related

<!--
Link any related PRs, issues, design docs, or discussion threads.
-->
