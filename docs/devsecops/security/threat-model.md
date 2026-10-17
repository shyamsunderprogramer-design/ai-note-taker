# Threat Model

> **Role tag:** `devsecops`
> **Owner:** `role-devsecops`
> **Status:** stub — to be expanded

---

## Scope

This threat model covers the ANT (AI Note Taker) monorepo:
Electron desktop, Vite web SPA, React Native mobile, MV3 Chrome
extension, and FastAPI backend.

The threat model is the canonical reference for "what are we
defending against, and how". A new feature PR that introduces a
new attack surface should add a section here.

---

## Assets

1. **User transcripts & audio** — recorded by the desktop
   app, synced to the backend. Considered sensitive (PII,
   confidential conversations, etc.).
2. **API keys** — BYOK (Bring Your Own Key) model. Users store
   their own OpenAI / Anthropic / Google keys in
   `data/user_keys/` (gitignored). Never logged.
3. **Cognitive graph data** — Neo4j-backed knowledge graph of
   extracted entities, skills, companies. Considered PII.
4. **Session tokens** — JWT with `jti` for session tracking.
   Bearer token for the API.
5. **The user's machine** — Electron has full Node.js access;
   the security boundary includes the desktop app not being
   a vector for code execution on the user's machine.

---

## Adversaries

| Adversary | Capability | Primary concern |
|---|---|---|
| **Network eavesdropper** | Reads HTTP traffic on a public Wi-Fi | TLS pinning, HSTS |
| **Compromised npm dep** | RCE on the backend, exfiltrates `data/` | Supply-chain review, SCA |
| **Malicious web content** | XSS in the SPA, steals session cookie | CSP, Trusted Types, HttpOnly cookies |
| **Phishing email** | User enters creds on a fake ANT login page | User education, MFA, no password storage |
| **Insider (collaborator with repo access)** | Reads `data/users.json` | No real data in repo, audit log |
| **Compromised Electron update server** | Pushes malicious auto-update | Code signing, update integrity check |
| **Browser extension attacker** | Uses ANT extension as a foothold | CSP, narrow permissions, no remote code |

---

## Mitigations (summary)

- **Transport**: TLS 1.3+ in prod, HSTS, certificate pinning in
  the mobile app.
- **Auth**: bcrypt (pinned < 4.1 due to passlib 1.7.4
  incompatibility) + JWT with short TTL + jti for session
  revocation.
- **Authz**: per-user resource scoping in every endpoint; no
  global admin endpoints exposed without a separate auth check.
- **Input validation**: Pydantic on all backend endpoints;
  DOMPurify-equivalent on web inputs.
- **CSP**: strict `default-src 'self'`, no `unsafe-eval`, only
  one `unsafe-inline` block remaining (5 pages need per-page
  extraction; see `Phase 6 CSP hardening` memory).
- **Supply chain**: Dependabot weekly, trivy scan on every CI
  build, npm audit on every PR.
- **Browser extension**: MV3 with narrow `host_permissions`,
  no `eval`, no remote code.
- **Audit log**: every admin action and every auth event is
  logged to `data/audit_logs/audit.jsonl` (gitignored).

---

## Open questions / to-do

- [ ] Document the threat model for the new single-session-per-
  user feature (auto-kick on second device login).
- [ ] Expand the data-at-rest threat section (encryption of
  `data/recordings/`, `data/users.json`).
- [ ] Add a section on the LLM provider integrations (what
  happens if a provider leaks prompt content?).
- [ ] Add a section on the Chrome extension update channel.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
