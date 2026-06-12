# Backend Dev Docs

> **Role tag:** `backend`
> **Charter:** [`OWNERS.backend.md`](../../OWNERS.backend.md)
> **CODEOWNERS routing:** `.github/CODEOWNERS` lines starting with
> `/backend/` map to the `role-backend` GitHub Team.

This is the docs home for everything `backend` dev owns. If you're
adding a new endpoint, schema, or AI integration, the doc that explains
it lives somewhere under here.

---

## What's in this folder

| Subfolder | What's there |
|---|---|
| [api/](api/) | REST + WebSocket endpoint reference |
| [architecture/](architecture/) | File layout, package boundaries, data flow |
| [database/](database/) | Every SQLAlchemy model + Alembic migration |
| [setup/](setup/) | Tooling setup (Neo4j, etc.) |
| [modules/](modules/) | Per-module deep dives (the 7 internal modules) |

---

## Top-level files

- [`COGNITIVE_GRAPH_API.md`](COGNITIVE_GRAPH_API.md) — the cognitive-graph
  endpoint deep-dive (Neo4j query patterns, response shapes)

---

## How this folder is organized

The subfolders mirror the role's owned code:

- `backend/api/...`  ↔  `backend/routes/...`
- `backend/database/...`  ↔  `backend/core/database.py` + `backend/migrations/...`
- `backend/architecture/...`  ↔  the full backend file layout
- `backend/modules/...`  ↔  `backend/modules/<module>/...`
- `backend/setup/...`  ↔  tooling setup (Neo4j, etc.)

If you're writing a doc about a `backend/routes/auth.py` endpoint, it
goes in `backend/api/`. If you're writing a doc about a SQLAlchemy
model, it goes in `backend/database/`.

---

## When to add a doc here

Add a doc here when:

- You're adding a new HTTP endpoint → update `backend/api/API_REFERENCE.md`
- You're adding a new SQLAlchemy model → update `backend/database/SCHEMA.md`
- You're adding a new AI provider → update `backend/api/API_REFERENCE.md` and
  add a deep-dive to `backend/modules/` if the integration is non-trivial
- You're adding a new internal module → add `backend/modules/<module>/README.md`
- You're changing the file layout → update `backend/architecture/PROJECT_STRUCTURE.md`

For full design changes (cross-cutting), add or update
`backend/architecture/TECHNICAL_SPECIFICATION.md`.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
