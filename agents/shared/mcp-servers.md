# MCP Servers (planning stub)

> **Status (2026-06-11):** This is a **planning stub**, not an
> implementation. The MCP server infrastructure is not yet built.
> When it is, the contracts documented here will be the source of truth.

---

## What an MCP server is

A **Model Context Protocol (MCP) server** is a process that an AI agent
connects to in order to read/write external state (the filesystem, a
git repo, a database, an API). Each role's agent will connect to a
specific allowlist of MCP servers — no more.

For ANT, the MCP layer is the *permissions boundary* for the AI agents.
An agent's read/write scope in the codebase is enforced by the MCP
server config, not by the agent's good behavior.

---

## Planned MCP servers

| Server | Purpose | Roles allowed |
|---|---|---|
| `fs` | Read/write files in the repo | all (scoped to role's write scope) |
| `git` | Read git history, write to a working branch | all (no force-push, no main push) |
| `gh` | Read PRs / issues, post comments | all (no close/merge without human) |
| `pytest` | Run pytest in `backend/` | backend, qa |
| `alembic` | Run alembic in `backend/` | backend |
| `playwright` | Run e2e in `e2e/` | qa, uiux (for visual review) |
| `jest` | Run mobile tests | qa, uiux |
| `node:test` | Run electron tests | qa, devops |
| `k6` | Run perf scripts | qa |
| `docker` | Build / run containers | devops |
| `kubectl` | Apply / read K8s manifests | devops (apply requires human) |
| `helm` | Template / lint Helm charts | devops |
| `terraform` | init / plan / validate / apply | devops (apply requires human) |
| `gitleaks` | Scan for secrets | devsecops |
| `bandit` | Python security scan | devsecops |
| `pip-audit` | Python dep CVE scan | devsecops |
| `npm audit` | npm dep CVE scan | devsecops |
| `semgrep` | Multi-language static analysis | devsecops |
| `ollama` | Call local Ollama for the agent's own reasoning | all |
| `context7` | Look up library docs | all |

---

## Per-role allowlist (the contract)

For each role, the agent's MCP config restricts which servers it can
call:

### backend
- `fs` (scoped to `backend/` write scope + `agents/backend/MEMORY.md`)
- `git`, `gh` (read-only; write only to its working branch)
- `pytest`, `alembic`
- `ollama`, `context7`

### uiux
- `fs` (scoped to `apps/`, `electron/features/`, `electron/assets/`,
  `assets/design/`, `mobile/src/`, `mobile/{App,index,app.json}`,
  `mobile/package.json`, `agents/uiux/MEMORY.md`)
- `git`, `gh`
- `playwright` (for visual review)
- `jest` (mobile tests)
- `ollama`, `context7`

### devops
- `fs` (scoped to devops write scope + `agents/devops/MEMORY.md`)
- `git`, `gh`
- `docker`, `kubectl`, `helm`, `terraform` (apply requires human)
- `node:test` (electron tests)
- `ollama`, `context7`

### qa
- `fs` (scoped to `e2e/`, `qa/`, test directories + `agents/qa/MEMORY.md`)
- `git`, `gh`
- `pytest`, `playwright`, `jest`, `node:test`, `k6`
- `ollama`, `context7`

### devsecops
- `fs` (scoped to devsecops write scope + `agents/devsecops/MEMORY.md`)
- `git`, `gh`
- `gitleaks`, `bandit`, `pip-audit`, `npm audit`, `semgrep`
- `ollama`, `context7`

---

## How an MCP server is implemented

The MCP layer is **not** in this refactor. When it is built, each server
is a small Python or Node process that:

1. Exposes a JSON-RPC interface over stdio (or TCP)
2. Has its own allowlist of files / commands / endpoints
3. Logs every call to `backend/data/audit_logs/audit.jsonl` (for
   traceability — every agent action is auditable)
4. Returns a structured error when an out-of-scope action is requested
   (the agent then knows it needs to ask a human or another agent)

The implementation choice (Python vs Node) is per-server; some servers
(e.g. `playwright`) are easier in Node, others (e.g. `pytest`) in
Python.

---

## Why MCP and not just a tighter prompt

- A prompt can be ignored. An MCP server returns a hard error.
- A prompt can't enforce "no prod access." An MCP server can refuse to
  accept the request.
- A prompt is one-shot. An MCP server can stream results, paginate, and
  handle long-running ops.
- A prompt can't be audited. An MCP server logs every call to the
  audit log.

This is why ANT's role-ownership refactor includes this *planning*
folder, not just docs: the agents need a real permissions boundary,
not a prompt that says "please be careful."

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
