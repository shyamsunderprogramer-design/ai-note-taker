# DevSecOps Agent — Persistent Memory

> This file is the `devsecops` agent's cross-session memory. It starts
> empty and gets populated as the agent accumulates project knowledge.
> Format: one fact per "## YYYY-MM-DD" section.

## How to use this file

- **Add a fact:** append a new dated section with a one-line title and
  a 1-3 sentence body. Link related facts with `[[other-fact-slug]]`.
- **Update a fact:** edit in place; keep the dated section header.

## Conventions

- One fact per section.
- Project-specific (e.g. "bcrypt 5.0.0 + passlib 1.7.4 = no user can
  register; pin `bcrypt<4.1` until passlib is migrated off") not generic
  security knowledge.
- Facts that other roles need should be moved to the appropriate
  role's `MEMORY.md`, not duplicated.

---

<!-- The agent starts with no facts. Add the first fact below. -->
