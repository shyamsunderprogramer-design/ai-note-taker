# Devops / Release Docs

> **Role tag:** `devops`
> **Charter:** [`OWNERS.devops.md`](../../OWNERS.devops.md)
> **CODEOWNERS routing:** `.github/CODEOWNERS` lines starting with
> `/Dockerfile`, `/docker/`, `/k8s/`, `/infrastructure/`, `/render.yaml`,
> `/vercel.json`, `/Makefile`, `/scripts/`, `/.github/workflows/`,
> `/electron/main.js`, `/electron/preload.js`, `/electron/stealth.js`,
> `/electron/build/`, `/electron/scripts/`, `/electron/package.json`,
> `/package.json`, `/package-lock.json` map to the `role-devops`
> GitHub Team.

This is the docs home for the devops role. Anything about
deployment, runtime shell, CI, infra-as-code, the Electron build,
or release processes lives here.

---

## What's in this folder

| Subfolder / file | What's there |
|---|---|
| [development/](development/) | Local dev: INSTALL, DEVELOPMENT, MIGRATIONS, MOBILE, TROUBLESHOOTING |
| [deployment/](deployment/) | Deploy: DEPLOYMENT_GUIDE, PRODUCTION_CHECKLIST, RELEASE_CHECKLIST, PRODUCTION_READINESS_ANALYSIS, PRODUCTION_TASK_BREAKDOWN |
| [operations/](operations/) | Post-deploy ops runbook (was `docs/OPERATIONS.md`) |
| [docker/](docker/) | Runtime notes for Docker / docker-compose |
| [mobile-native/ios/](mobile-native/ios/) | iOS build / sign / notarize |
| [mobile-native/android/](mobile-native/android/) | Android build / sign / Play Store |

---

## Top-level files (in this folder)

- [`OPERATIONS.md`](operations/OPERATIONS.md) — the on-call runbook
  (moved from `docs/OPERATIONS.md`)

---

## The runtime shell (co-owned)

The Electron runtime is the boundary between the desktop app and
the OS. Three files are co-owned:

- `electron/main.js` — devops owns, backend approves IPC contract
  changes
- `electron/preload.js` — devops owns, backend approves IPC
  contract changes
- `electron/stealth.js` — devops owns, devsecops reviews
  security implications

See `OWNERS.devops.md` for the cross-role review policy.

---

## When to add a doc here

Add a doc here when:

- You're adding a new deploy target (e.g., a new cloud, a new
  Helm chart) → add to `deployment/`
- You're adding a new on-call runbook section → add to
  `operations/`
- You're changing the Docker setup → update `docker/`
- You're shipping a new iOS or Android build pipeline → update
  `mobile-native/`
- You're adding a new dev workflow step → update
  `development/`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
