# DevOps Role — Charter

> **Role tag:** `devops`
> **GitHub team:** `role-devops` (1 member today: `@shyamsunderprogramer-design`)
> **Charter owner:** This file is the canonical answer to "what does devops own?"

---

## What this role owns

Deploy, runtime shell, CI, infra, and the build pipelines. File-level inventory,
in priority order:

### Build & deploy manifests
- `Dockerfile` (root) — backend container image (co-owned with `devsecops`)
- `docker/` — Dockerfiles for sidecars (Neo4j, monitoring)
- `docker-compose.yml` → `docker/`
- `k8s/` — Helm chart + ArgoCD app manifests
- `infrastructure/` — Terraform stacks (AWS, Azure, GCP)
- `render.yaml` — Render.com service definition (co-owned with `devsecops`)
- `vercel.json` — Vercel static-hosting config (co-owned with `devsecops`)

### CI / CD
- `.github/workflows/` — all GitHub Actions workflows
- `.github/dependabot.yml` — co-owned with `devsecops`; devops owns the syntax,
  devsecops owns the supply-chain review
- `Makefile` — repo-helper targets (setup, test, build, docker-up, etc.)
- `scripts/` — repo-helper scripts (PWA icons, dead-imports scanner, etc.)

### Electron runtime shell
- `electron/main.js` — Electron main process (co-owned with `backend` —
  runtime shell is devops, IPC contract is backend)
- `electron/preload.js` — contextBridge / IPC API surface (co-owned with `backend`)
- `electron/stealth.js` — anti-capture / stealth mode (co-owned with `devsecops`)
- `electron/build/` — entitlements, code-signing config
- `electron/scripts/` — icon generation, build helpers
- `electron/package.json` — electron-builder config (this role owns it; lockfile
  bumps and dep conflicts are also devops)
- `electron/BUILD.md` — desktop build instructions

### Workspace plumbing
- Root `package.json` — workspaces, proxy scripts (workspace-dep bumps are
  the per-workspace owner's; lockfile conflicts are devops)
- Root `package-lock.json`

### Mobile native build
- `mobile/ios/`, `mobile/android/` — Xcode project, Gradle config, signing,
  store metadata

---

## What this role reads but doesn't own

| Area | Owner | Why devops cares |
|---|---|---|
| `backend/requirements.txt` | backend + devsecops | devops pins the runtime base image version; devsecops reviews supply-chain risk |
| `apps/web/package.json` | uiux | devops reads but doesn't bump workspace deps |
| `vercel.json` (CSP) | devops + devsecops | devops deploys, devsecops approves attack-surface changes |
| `backend/core/config.py` | backend | devops sets the env-var values in `render.yaml` and `k8s/helm/.../values-*.yaml` |
| `apps/web/vite.config.js` | uiux | devops reads to know the build output paths |
| `electron/features/` | uiux | UI features consume the IPC bridge; devops approves new IPC channels |
| `docs/devops/development/DEVELOPMENT.md` | devops | devops owns this; devops reads it too |
| `docs/devops/deployment/DEPLOYMENT_GUIDE.md` | devops | devops owns + reads |
| `docs/devops/operations/OPERATIONS.md` | devops | devops owns + reads |

---

## What this role delivers

Typical PR outputs from a devops:

- Dockerfile change (with a CHANGELOG note)
- Terraform module update (with a `terraform validate` result)
- K8s Helm chart change (with a `helm template` result)
- New CI job in `.github/workflows/`
- New Makefile target
- Electron build config tweak (`electron/package.json` build, `electron/build/`)
- New repo-helper script in `scripts/`
- Production deploy (with a deploy log + smoke-test result)
- Day-2 ops: log/metric dashboard, alert rule, runbook update

---

## What this role's AI agent has access to

> **Status:** the role-scoped AI agent is a planning stub, not yet wired up.
> See `agents/devops/AGENTS.md` for the scoping plan.

When the agent is online, it will be able to:

- **Read:** every file in the repo (devops needs the full picture)
- **Write:** files in `Dockerfile`, `docker/`, `k8s/`, `infrastructure/`,
  `render.yaml`, `vercel.json`, `Makefile`, `scripts/`, `.github/workflows/`,
  `electron/{main.js,preload.js,stealth.js,build,scripts,package.json,BUILD.md}`,
  root `package.json`, `package-lock.json`
- **Bash:** `docker`, `kubectl`, `helm`, `terraform`, `make`, `npm run`,
  `git`, `gh` (scoped to read-only + the deploy subcommand set)
- **Memory:** `agents/devops/MEMORY.md`

It will **not** have access to:
- Production credentials beyond the deploy-time environment variables
- User data (`users.json`, recordings, audit logs)
- Direct prod DB or Redis access (only via migrations + audit-logged queries)

---

## What this role reviews when it gets a PR

When CODEOWNERS routes a PR to `role-devops`, this role checks:

1. **Build artifacts verified** — Docker image built, Render template renders,
   Helm template renders
2. **CI still green** — the 4 existing jobs (`backend-tests`, `web-build`, `e2e`,
   `security-scan`) pass
3. **CHANGELOG entry added** under `[Unreleased]`
4. **CSP / secret / base-image change flagged** — for any of these,
   `role-devsecops` is also tagged
5. **Dependabot policy respected** — minor/patch grouped, major reviewed
6. **Mobile native build tested** — for iOS/Android changes
7. **No stray `node_modules/`, `dist/`, or `__pycache__/` committed**

---

## How to contact this role

- **Today:** `@shyamsunderprogramer-design` (sole human member of `role-devops`)
- **When collaborators join:** tag the `role-devops` GitHub Team in the PR

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
