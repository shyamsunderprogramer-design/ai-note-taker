# DevOps Agent — Persistent Memory

> This file is the `devops` agent's cross-session memory. It starts
> empty and gets populated as the agent accumulates project knowledge.
> Format: one fact per "## YYYY-MM-DD" section.

## How to use this file

- **Add a fact:** append a new dated section with a one-line title and
  a 1-3 sentence body. Link related facts with `[[other-fact-slug]]`.
- **Update a fact:** edit in place; keep the dated section header.

## Conventions

- One fact per section.
- Project-specific (e.g. "the Electron `main.js` sets traffic lights
  off-screen with `trafficLightPosition: { x: -100, y: -100 }` on
  darwin") not generic Docker/K8s knowledge.
- Facts that other roles need should be moved to the appropriate
  role's `MEMORY.md`, not duplicated.

---

<!-- The agent starts with no facts. Add the first fact below. -->
