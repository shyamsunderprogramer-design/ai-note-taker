# Backend Dev Agent — Persistent Memory

> This file is the `backend` agent's cross-session memory. It starts
> empty and gets populated as the agent accumulates project knowledge.
> Format: one fact per "## YYYY-MM-DD" section.

## How to use this file

- **Add a fact:** append a new dated section with a one-line title and
  a 1-3 sentence body. Link related facts with `[[other-fact-slug]]`.
- **Update a fact:** edit in place; keep the dated section header.
- **Reference a fact:** link to it with `[[fact-slug]]` (the slug is
  the section header, kebab-cased).

## Conventions

- One fact per section.
- Facts should be *project-specific* (not generic Python/FastAPI
  knowledge — that's in the agent's training, not here).
- Facts that other roles need to know should be moved to the appropriate
  role's `MEMORY.md`, not duplicated.

---

<!-- The agent starts with no facts. Add the first fact below. -->
