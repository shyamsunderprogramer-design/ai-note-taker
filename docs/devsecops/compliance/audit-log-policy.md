# Audit Log Policy

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`
> **Status:** stub — to be expanded

---

## Scope

Every admin action, every auth event (login, logout, refresh,
failed login), and every privileged API call writes a row to
`data/audit_logs/audit.jsonl` (gitignored). This doc covers
**what** is logged, **who** can read it, and **how long** it is
retained.

---

## What is logged

| Event category | Examples | Log level |
|---|---|---|
| Auth | `login.success`, `login.failure`, `logout`, `token.refresh` | info / warn |
| Admin | `user.create`, `user.delete`, `user.role_change` | info |
| Privileged | `keys.list` (admin viewing a user's BYOK keys) | warn |
| Data access | `recording.read` (admin reading a user's transcript) | warn |
| System | `app.start`, `app.shutdown`, `config.change` | info |
| Security | `rate_limit.exceeded`, `csp.violation`, `auth.lockout` | warn / error |

Each row is JSON Lines:

```json
{
  "ts": "2026-06-11T12:34:56.789Z",
  "level": "info",
  "event": "login.success",
  "user_id": "u_abc",
  "ip": "10.0.0.5",
  "user_agent": "Mozilla/5.0 ...",
  "request_id": "req_xyz"
}
```

---

## Retention

- **Default**: 90 days rolling (logrotate weekly, keep 13 weeks).
- **Security events**: 1 year (rate-limit exceeded, lockouts,
  CSP violations).
- **Admin / privileged events**: 2 years (for compliance
  review).

---

## Access control

- The log file is readable only by the `ant` service user
  (UID pinned in the Dockerfile).
- No HTTP endpoint reads the log directly. To inspect, the
  devops role SSHes into the box and `cat`s / `grep`s the file.
- If a future feature needs audit log export, it goes through
  a separate `audit.export` API that requires admin role and
  writes a *new* audit row about the export.

---

## What this doc does not cover

- **Application error logs** (the Python logging output to
  stdout). Those go to the platform's normal log aggregator
  (Cloudwatch / Render logs / etc.) and are not part of the
  audit log.
- **LLM provider request logs** (if a user invokes OpenAI, we
  log the request ID but not the prompt content). That's
  handled in `backend/security/` and tracked separately.

---

## To-do

- [ ] Document the exact log fields the audit JSONL must
  contain (so future contributors know what schema to follow).
- [ ] Add a sample parsing script (`scripts/audit_query.py` —
  not yet written).
- [ ] Decide on log shipping (push to an external SIEM? or
  keep file-based for now?).

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
