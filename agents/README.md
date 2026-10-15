# Role-Scoped AI Agents

> **Status (2026-06-11):** Planning stub. The MCP server + RAG index
> infrastructure is **not** yet built. This folder documents the intent
> and the per-role scoping plan, so that when the infrastructure comes
> online, the agents are ready to spin up.

---

## The pattern

ANT (AI Note Taker) is the only codebase in production with one human
contributor (`@shyamsunderprogramer-design`) but **5 distinct roles** to
represent: `backend`, `uiux`, `devops`, `qa`, `devsecops`. Each role has:

1. A **charter** at the repo root (`OWNERS.<role>.md`) — *what* the role owns
2. A **CODEOWNERS entry** (`.github/CODEOWNERS`) — *who* reviews the role's PRs
3. A **docs home** (`docs/<role>/`) — *where* the role's docs live
4. An **`AGENTS.md`** (this folder) — *how* the role's AI agent is scoped
5. A **`MEMORY.md`** (this folder) — *what* the role's agent remembers across
   sessions

The `AGENTS.md` and `MEMORY.md` are role-scoped: an agent acting as
"role-backend" reads only `agents/backend/AGENTS.md` and writes only to
`agents/backend/MEMORY.md`. The agent has no access to `agents/devops/`
or any other role's memory.

---

## Per-role files

| Role | AGENTS.md | MEMORY.md | Charter |
|---|---|---|---|
| `backend` | [backend/AGENTS.md](backend/AGENTS.md) | [backend/MEMORY.md](backend/MEMORY.md) | [OWNERS.backend.md](../../OWNERS.backend.md) |
| `uiux` | [uiux/AGENTS.md](uiux/AGENTS.md) | [uiux/MEMORY.md](uiux/MEMORY.md) | [OWNERS.uiux.md](../../OWNERS.uiux.md) |
| `devops` | [devops/AGENTS.md](devops/AGENTS.md) | [devops/MEMORY.md](devops/MEMORY.md) | [OWNERS.devops.md](../../OWNERS.devops.md) |
| `qa` | [qa/AGENTS.md](qa/AGENTS.md) | [qa/MEMORY.md](qa/MEMORY.md) | [OWNERS.qa.md](../../OWNERS.qa.md) |
| `devsecops` | [devsecops/AGENTS.md](devsecops/AGENTS.md) | [devsecops/MEMORY.md](devsecops/MEMORY.md) | [OWNERS.devsecops.md](../../OWNERS.devsecops.md) |

---

## Shared infrastructure

When the role-scoped MCP + RAG layer is built, it will live here:

- [shared/mcp-servers.md](shared/mcp-servers.md) — list of MCP servers the
  agents can connect to (filesystem, git, jira, slack, etc.) with the
  per-role allowlist
- [shared/rag-indexes.md](shared/rag-indexes.md) — list of RAG indexes the
  agents can query (per-role docs/, role-owned code, role history, etc.)

---

## How a role's agent is invoked

When a new issue is opened, the user (or a future automation) tags it with
a `role-*` label. The corresponding role's agent is then asked to:

1. Read its `AGENTS.md` (this is the agent's "system prompt" for the session)
2. Read its `MEMORY.md` (prior knowledge accumulated from past sessions)
3. Use the per-role MCP servers + RAG indexes (when they exist)
4. Produce a PR proposal that respects the role's charter + CODEOWNERS entry

The agent's PR is then reviewed by the role's human reviewer (today: the
sole human) and merged or sent back for changes.

---

## Why split by role

- **Context isolation:** a "role-backend" agent doesn't need to know the
  visual design system, the deploy pipeline, or the threat model — it can
  spend all of its context on the FastAPI / SQLAlchemy / AI code.
- **Memory isolation:** a fix to the Alembic migration that "QA remembered"
  is a per-role memory; it doesn't pollute the devops agent's memory of
  render.yaml.
- **Permission isolation:** role-devsecops is the only one that should be
  reading the audit log; role-devops is the only one that should be
  running `terraform apply`; role-qa is the only one that should be
  running `pytest --no-cov` against prod-like data. Splitting the
  agents enforces this at the *agent* level, not just at the *PR review*
  level.

---

## Out of scope (for now)

- Actual MCP server implementation (we plan the contracts in
  [shared/mcp-servers.md](shared/mcp-servers.md))
- Actual RAG index construction (we plan the indexes in
  [shared/rag-indexes.md](shared/rag-indexes.md))
- Per-agent LLM routing / model selection (today: a single model, possibly
  per-role in the future)
- A UI for managing the agents

This is the *seam* for those future changes. The folder + per-role files
are the first step.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
