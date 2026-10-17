# Compliance

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`

---

## What's in this folder

| File | What |
|---|---|
| [SECURITY.md](SECURITY.md) | The public-facing security policy (moved from repo root) |
| [audit-log-policy.md](audit-log-policy.md) | What gets audited, retention, who can read the log (stub — to be expanded) |

---

## Regulatory scope

ANT is a personal-tool product today. The regulatory bar is
relatively low (no SOC 2, no HIPAA), but we do commit to:

- **GDPR** (if any EU user uses the app): data minimization,
  right to deletion, no third-party tracking.
- **CCPA** (if any California user uses the app): same as
  above, with explicit "do not sell" stance.
- **Children's privacy (COPPA)**: the app is not directed at
  children under 13; we don't knowingly collect data from
  them.

If we add enterprise features later (team plans, SSO, audit
log export), the regulatory bar goes up. Add the relevant docs
when that happens.

---

## When to add a doc here

Add a doc here when:

- You're adding a new regulatory requirement → add a new
  `compliance/<REGULATION>.md`
- You're adding a new audit-log category → update
  `audit-log-policy.md`
- You're changing the data retention window → update
  `audit-log-policy.md` and `SECURITY.md`

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
