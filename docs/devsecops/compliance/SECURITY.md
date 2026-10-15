# ─────────────────────────────────────────────────────────────────────
# ANT (AI Note Taker) — Security policy
#
# If you find a security vulnerability, please follow responsible
# disclosure: do NOT open a public GitHub issue. Email the maintainer
# directly (see MAINTAINERS) or use GitHub's "Report content" feature
# on the affected file / issue / PR.
#
# We aim to acknowledge security reports within 48 hours and to ship
# a fix within 7 days for critical issues. Credit is given in the
# CHANGELOG once a fix lands (unless you prefer to stay anonymous).
# ─────────────────────────────────────────────────────────────────────

# Reporting a Vulnerability

If you discover a security vulnerability in ANT (AI Note Taker), please
help us fix it responsibly.

**DO:**

- Email the maintainer directly (see [MAINTAINERS](#maintainers))
- Include reproduction steps and the affected version / commit
- Give us a reasonable window to investigate and patch before
  disclosing publicly (90 days is the standard)

**DO NOT:**

- Open a public GitHub issue for security bugs
- Exploit the vulnerability beyond what's needed to demonstrate it
- Access or modify other users' data

## MAINTAINERS

Current active maintainer:

- Shyam Sunder Daggupati — see `Profile.pdf` in the repo root or the
  GitHub profile linked from the project's homepage

If multiple maintainers are listed in `MAINTAINERS.md` (when that file
exists), any of them can be contacted.

## What we protect

ANT is a privacy-first product. The security bar is high because:

- **Transcription runs locally** — no STT data leaves the device, ever
- **Screen-capture protection** uses OS-level APIs (Windows
  `WS_EX_FROMLEARN`, macOS screen capture kit) — we treat these as
  load-bearing
- **BYOK (Bring Your Own Key)** — user-supplied cloud API keys are
  encrypted at rest with `ENCRYPTION_KEY` and never logged
- **JWT auth** — `JWT_SECRET_KEY` is required for stable tokens
  across restarts; the system refuses to fall back to a random
  ephemeral secret in production

## Supported versions

| Version | Supported          |
|---------|--------------------|
| main    | ✅ active dev      |
| latest release tag | ✅ security fixes backported |
| older release tags | ❌ no longer maintained |

We do not maintain long-term-support branches. The latest release
tag is the only one that receives security patches; everyone else
is expected to upgrade.

## Security-relevant prior work

See [`../../shared/AUDIT_2026-06-05_Project_Audit.md`](../../shared/AUDIT_2026-06-05_Project_Audit.md)
for the project-wide security audit (3 pre-existing bugs pinned as
DOCUMENTED BUG tests, all known) and [`../security/SECURITY_IMPLEMENTATION_SUMMARY.md`](../security/SECURITY_IMPLEMENTATION_SUMMARY.md)
for the security module reference.
