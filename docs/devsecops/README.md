# DevSecOps / Security Docs

> **Role tag:** `devsecops`
> **Charter:** [`OWNERS.devsecops.md`](../../OWNERS.devsecops.md)
> **CODEOWNERS routing:** `.github/CODEOWNERS` lines starting with
> `/.claude/`, `/.pre-commit-config.yaml`,
> `/.github/CODEOWNERS`, `/.github/PULL_REQUEST_TEMPLATE.md`,
> `/.github/ISSUE_TEMPLATE/`, `/.github/dependabot.yml`,
> `/SECURITY.md`, `/backend/security/` map to the
> `role-devsecops` GitHub Team.

This is the docs home for the devsecops role. Threat model,
supply-chain policy, secret rotation, compliance — anything
about the security posture of the project lives here.

---

## What's in this folder

| Subfolder / file | What's there |
|---|---|
| [security/](security/) | Security implementation notes, threat model, browser extension safety |
| [supply-chain/](supply-chain/) | Dependabot policy, dependency review, third-party risk |
| [compliance/](compliance/) | SECURITY.md, audit log policy, regulatory notes |

---

## Top-level files (in this folder)

- (none — all content lives in the subfolders)

---

## Boundary with `backend/security/`

The `backend/security/` folder (in the backend code tree) holds
the **implementation** (auth code, encryption code, rate limit
code). The devsecops role owns the **policy** (what the
implementation should do) and reviews the implementation for
correctness.

In practice:

- `backend/security/auth.py` — owned by `backend` for
  implementation, with `devsecops` as a required reviewer for
  crypto / auth changes
- `docs/devsecops/security/threat-model.md` — owned by
  `devsecops`, references the implementation files

---

## When to add a doc here

Add a doc here when:

- You're documenting a new threat (e.g., a new attack surface
  from a new feature) → add to `security/threat-model.md`
- You're adding a new supply-chain control (e.g., a new SCA
  tool, a new policy) → add to `supply-chain/`
- You're documenting a regulatory requirement (GDPR, SOC 2,
  HIPAA, etc.) → add to `compliance/`
- You're rotating a secret or adding a new secret-management
  workflow → add to `compliance/secret-rotation.md` (if
  present)

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
