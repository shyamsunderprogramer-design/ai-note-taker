# Shared Docs

> **Audience:** all roles
> **Owner:** co-owned (no single role)

---

## What's in this folder

These are docs that don't belong to a single role. They're
cross-cutting — they describe the project as a whole, or
capture an audit / analysis that all roles need to read.

| File | What |
|---|---|
| [COMPREHENSIVE_GUIDE.md](COMPREHENSIVE_GUIDE.md) | The big-picture guide to ANT (moved from `docs/`) |
| [FULL_IMPLEMENTATION_COMPLETE.md](FULL_IMPLEMENTATION_COMPLETE.md) | Implementation status snapshot (moved from `docs/`) |
| [CRITICAL_GAPS_FIXED.md](CRITICAL_GAPS_FIXED.md) | Historical record of the most critical bugs and their fixes (moved from `docs/`) |
| [ANALYSIS_2026-04-07_Application_Goals_Competitive_Comparison.md](ANALYSIS_2026-04-07_Application_Goals_Competitive_Comparison.md) | Product goals + competitor comparison from 2026-04-07 (moved from `docs/`) |
| [AUDIT_2026-06-05_Project_Audit.md](AUDIT_2026-06-05_Project_Audit.md) | Project-wide audit from 2026-06-05 (moved from `docs/`) |
| [PRODUCTION_DEEP_DIVE_2026.md](PRODUCTION_DEEP_DIVE_2026.md) | Production-readiness deep dive (moved from `docs/`) |

---

## When to add a doc here

Add a doc here when:

- You're writing a project-wide status / overview / guide that
  no single role owns
- You're capturing the output of a cross-role audit / analysis
- The doc has no clear single-role owner (otherwise it goes
  in `docs/<role>/`)

Avoid using this folder as a "miscellaneous" bin. If a doc
fits a single role, it goes in that role's folder.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
