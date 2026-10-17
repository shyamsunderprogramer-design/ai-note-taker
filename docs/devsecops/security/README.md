# Security

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`

---

## What's in this folder

| File | What |
|---|---|
| [SECURITY_IMPLEMENTATION_SUMMARY.md](SECURITY_IMPLEMENTATION_SUMMARY.md) | What the auth / encryption / rate-limiting code actually does (moved from `docs/security/`) |
| [BROWSER_EXTENSION_SAFETY.md](BROWSER_EXTENSION_SAFETY.md) | The MV3 Chrome extension threat model + mitigations (moved from root) |
| [threat-model.md](threat-model.md) | The repo-wide threat model (stub — to be expanded) |

---

## The implementation / policy split

This folder is the **policy** home. The actual security
implementation lives in `backend/security/` (auth, encryption,
rate limit, audit log writers) and is owned by `backend` for the
implementation and `devsecops` for the policy review.

A change to `backend/security/` requires both roles' approval
(see `.github/CODEOWNERS` co-ownership block).

---

## When to add a doc here

Add a doc here when:

- You're documenting a new attack surface (new endpoint, new
  client platform, new external integration) → add to
  `threat-model.md`
- You're adding a new browser-extension safety rule → update
  `BROWSER_EXTENSION_SAFETY.md`
- You're adding a new compliance control → add to
  `../compliance/`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
