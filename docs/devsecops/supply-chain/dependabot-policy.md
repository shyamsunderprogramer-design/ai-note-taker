# Dependabot Policy

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`
> **Status:** stub — to be expanded

---

## What this doc covers

The Dependabot configuration in `.github/dependabot.yml` is
co-owned by `role-devops` (config) and `role-devsecops` (security
implications). This doc is the **policy** half — what to do when
a Dependabot PR opens, how fast, and what's blocked.

The Dependabot config itself is in
[`.github/dependabot.yml`](../../../.github/dependabot.yml).

---

## Triage workflow

1. **Open PR** — Dependabot opens a PR with severity labels.
2. **Label triage** — apply the matching `severity/*` label and
   assign to the role team that owns the affected dep:
   - `backend/*` deps (Python, Alembic) → `role-backend`
   - `uiux/*` deps (React, Vite) → `role-uiux`
   - `devops/*` deps (Docker, K8s) → `role-devops`
   - Cross-cutting (root `package.json`, transitive) →
     `role-devsecops`
3. **Check the changelog** — does the bump have a known-
   breaking change? If yes, the PR is "needs review" not "auto-
   merge".
4. **Check the supply-chain risk** — first-time-from-this-
   publisher? Weird version skip? Unusual release time?
   Devsecops gets a second look.
5. **Run the test suite** — every Dependabot PR must pass CI
   before merge. If CI is red, the dep bump gets pinned or
   reverted.
6. **Merge** — squash, with the `dependabot` commit trailer
   preserved.

---

## Auto-merge policy

Deps are eligible for auto-merge if **all** of these are true:

- Patch or minor version bump (no major)
- Dep is in the "trusted" list
  (see [`trusted-deps.md`](trusted-deps.md) — TODO)
- CI is green
- No `breaking-change` label
- No security advisory (npm audit / pip-audit clean)
- PR is < 7 days old

Major bumps are **never** auto-merged.

---

## Known-watch deps

### `bcrypt 5.0.0` + `passlib 1.7.4` (CRITICAL)

- **Issue**: passlib 1.7.4 does not work with bcrypt 5.0.0.
  Every user registration silently fails (returns 500).
- **Current mitigation**: `bcrypt<4.1` is pinned in
  `backend/requirements.txt`.
- **Long-term fix**: migrate off passlib to a maintained
  alternative (e.g., `bcrypt` directly, or `argon2-cffi`).
- **Triage rule**: do **not** allow a Dependabot PR that bumps
  `bcrypt` to 5.x or `passlib` to 1.8.x until the migration
  lands. If Dependabot opens such a PR, close it with a comment
  pointing at this doc.
- **Regression test**: a live smoke test (not a unit test) caught
  this; see `bcrypt-passlib-incompatibility-2026-06-07` memory.

---

## SLA recap

| Severity | Triage | Merge |
|---|---|---|
| Critical | same day | 24h |
| High | 3 days | 1 week |
| Medium | 1 week | 2 weeks |
| Low | 2 weeks | next release |

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
