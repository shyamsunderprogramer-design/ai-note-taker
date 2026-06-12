# UI/UX Dev Agent — Persistent Memory

> This file is the `uiux` agent's cross-session memory. It starts
> empty and gets populated as the agent accumulates project knowledge.
> Format: one fact per "## YYYY-MM-DD" section.

## How to use this file

- **Add a fact:** append a new dated section with a one-line title and
  a 1-3 sentence body. Link related facts with `[[other-fact-slug]]`.
- **Update a fact:** edit in place; keep the dated section header.
- **Reference a fact:** link to it with `[[fact-slug]]`.

## Conventions

- One fact per section.
- Facts should be *project-specific* (e.g. "the main window has
  traffic lights at x=-100, y=-100") not generic React/CSS knowledge.
- Facts that other roles need should be moved to the appropriate
  role's `MEMORY.md`, not duplicated.

---

<!-- The agent starts with no facts. Add the first fact below. -->
