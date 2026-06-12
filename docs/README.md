# ANT Documentation

> **Reorganized 2026-06-11** to a per-role layout. Pick your
> role below, or browse by topic.

This is the docs home for the ANT (AI Note Taker) monorepo.
The repo itself is split across `backend/`, `electron/`, `apps/`,
`mobile/`, `e2e/`, `qa/`, `agents/`, and several config files
at the root. The role-ownership model that determines who edits
what lives in `OWNERS.*.md` at the repo root and is enforced by
[`.github/CODEOWNERS`](../.github/CODEOWNERS).

This README points at the per-role docs subfolders. Each
subfolder has its own README that goes deeper.

---

## By role

- [Backend dev](backend/README.md) — FastAPI, services, DB,
  AI integration, Neo4j cognitive graph
- [UI/UX dev](uiux/README.md) — Web SPA, mobile, Chrome
  extension, Electron UI, design system
- [Devops / release](devops/README.md) — Deploy, runtime shell,
  CI, infra, Docker, mobile-native build pipelines
- [QA / testing](qa/README.md) — Test strategy, test
  environment, troubleshooting
- [DevSecOps / security](devsecops/README.md) — Threat model,
  supply chain, compliance, audit log policy

## By topic

- [Shared](shared/README.md) — Cross-cutting docs (project
  audit, comprehensive guide, production deep-dive)
- [Business / product](business/README.md) — BYOK, job tools,
  resume builder, plans, speed optimization history
- [Competitive analysis](competitive/README.md) — Competitor
  matrix, Pluely deep-dive
- [Research](research/) — Time-bounded research artifacts
  (kept as-is from before the reorganization)
- [Archive](archive/) — Superseded docs

---

## Per-role charter links

Each role has a charter at the repo root:

- [`OWNERS.backend.md`](../OWNERS.backend.md)
- [`OWNERS.uiux.md`](../OWNERS.uiux.md)
- [`OWNERS.devops.md`](../OWNERS.devops.md)
- [`OWNERS.qa.md`](../OWNERS.qa.md)
- [`OWNERS.devsecops.md`](../OWNERS.devsecops.md)

And an AI-agent scope definition in `agents/`:

- [`agents/backend/AGENTS.md`](../agents/backend/AGENTS.md)
- [`agents/uiux/AGENTS.md`](../agents/uiux/AGENTS.md)
- [`agents/devops/AGENTS.md`](../agents/devops/AGENTS.md)
- [`agents/qa/AGENTS.md`](../agents/qa/AGENTS.md)
- [`agents/devsecops/AGENTS.md`](../agents/devsecops/AGENTS.md)

---

## How to find a specific doc

If you know the doc filename, use GitHub's search (it indexes
all of `docs/`). If you don't:

- **API endpoint** → `backend/api/API_REFERENCE.md`
- **Database schema** → `backend/database/SCHEMA.md`
- **Deploy** → `devops/deployment/DEPLOYMENT_GUIDE.md`
- **Install** → `devops/development/INSTALL.md`
- **Browser extension security** →
  `devsecops/security/BROWSER_EXTENSION_SAFETY.md`
- **Audit log** → `devsecops/compliance/audit-log-policy.md`
- **Test strategy** → `qa/test-strategy.md`
- **Threat model** → `devsecops/security/threat-model.md`
- **Dependabot policy** → `devsecops/supply-chain/dependabot-policy.md`
- **Resume builder** → `business/resume-builder/`
- **Pluely comparison** → `competitive/pluely/`
- **Public security policy** → `devsecops/compliance/SECURITY.md`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
