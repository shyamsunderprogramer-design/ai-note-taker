# Security Policy

Thank you for taking the time to responsibly disclose security issues in ANT (AI Note Taker). We take reports seriously and aim to respond quickly.

## Supported Versions

The following versions of ANT receive security updates:

| Version | Supported          | Notes |
|---------|--------------------|-------|
| 2.1.x   | ✅ Yes             | Current stable. Fix #35 series (auth refactor, JSON → SQL migration). |
| 2.0.x   | ⚠️ Critical fixes only | Receives patches for HIGH/CRITICAL CVEs in shipped deps; no new features. |
| 1.0.x   | ❌ No              | End-of-life. The JSON user store (`data/users.json`) is still active on this branch — upgrade to 2.1.0 for the SQLAlchemy-backed store and the auto-migration. |
| < 1.0   | ❌ No              | Pre-release. |

## Reporting a Vulnerability

**Please do not file public GitHub issues for security issues.**

Use one of these private channels instead:

1. **GitHub Security Advisories** (preferred) — [Open a private security advisory](https://github.com/shyamsunderprogramer-design/ai-note-taker/security/advisories/new). This routes the report to maintainers without disclosing it publicly until a fix is ready.
2. **Email** — `dev@ainotetaker.com`. Use PGP if you have it (key on request). Encrypted reports help us triage faster.

### What to include

A good report has:

- **Description** — what the vulnerability is and what an attacker could do with it
- **Affected component** — backend route / Electron main / web renderer / dependency / etc.
- **Reproduction steps** — minimal steps to trigger the issue
- **Environment** — OS, app version (`Help → About` in the desktop app), and any relevant config
- **Impact assessment** — your guess at severity (we'll verify)
- **Suggested fix** (optional) — if you have one, attach a patch or PR

### What to expect

| Step | Timeline |
|------|----------|
| Acknowledgement | within 72 hours |
| Triage + severity rating | within 7 days |
| Patch for HIGH/CRITICAL | within 30 days |
| Patch for MEDIUM/LOW | best-effort, next minor release |
| Public disclosure | coordinated with reporter; default 90 days after report |

We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure): we won't publicly disclose until a fix is released (or 90 days have passed, whichever comes first), and we'll credit you in the release notes and the GitHub Security Advisory unless you ask to remain anonymous.

## Scope

The following are **in scope**:

- The ANT backend (FastAPI, `backend/`) — auth, SQL injection, path traversal, etc.
- The Electron desktop shell (`electron/`) — IPC bridge, sandbox escapes, preload leaks
- The web renderer (`apps/web/`) — XSS, content injection, prototype pollution
- Dependencies with **known CVEs** that ship in our installer (we track Dependabot alerts)
- Cryptographic / authentication issues — JWT validation, password hashing, session handling
- The users.json → SQL migration path (Fix #35) — anything that could corrupt user data

The following are **out of scope**:

- Issues in dependencies that we don't ship (e.g. dev-only deps)
- Social engineering of maintainers
- Rate limiting on unauthenticated endpoints (we have rate limits but they're not the focus)
- Self-XSS (you can't XSS yourself)
- "ANT does X" without a specific exploitable bug

## Security Hall of Fame

We thank the following reporters:

- _No reports yet — be the first._

## Architecture Notes

For researchers who want to understand the threat model:

- **Authentication:** JWT with HS256, 8-hour access tokens, 7-day refresh tokens, **single-session enforcement** (Fix #34) — a 2nd-device login invalidates the 1st device's tokens.
- **Password storage:** bcrypt via `passlib` (bcrypt<4.1 pinned in `requirements-security.txt` due to a known passlib issue with newer bcrypt).
- **User store:** SQLAlchemy-backed `users` table (Fix #35). The legacy `data/users.json` is read **once** on first boot after upgrade and then never touched — see `backend/core/database.py` → `DataMigrator` for the migration path.
- **Electron security:** context isolation enabled, `nodeIntegration: false`, `sandbox: true` for the renderer; the preload script (`electron/preload.js`) exposes a narrow IPC bridge via `contextBridge.exposeInMainWorld`.
- **macOS hardened runtime:** enabled by default with entitlements for microphone, screen capture (off by default), and outbound network.

See also:

- [`docs/devsecops/SECURITY.md`](docs/devsecops/SECURITY.md) — the full security architecture doc
- [`docs/devsecops/THREAT_MODEL.md`](docs/devsecops/THREAT_MODEL.md) — threat model
- [`docs/devsecops/AUDIT_*.md`](docs/devsecops/) — periodic audit reports