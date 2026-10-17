# RAG Indexes (planning stub)

> **Status (2026-06-11):** This is a **planning stub**, not an
> implementation. The RAG index infrastructure is not yet built.
> When it is, the indexes documented here will be the source of truth.

---

## What a RAG index is

A **Retrieval-Augmented Generation (RAG) index** is a pre-computed
embedding of a corpus of documents, stored in a vector database. An AI
agent queries the index to find relevant context (chunks of docs,
code, history) and feeds those chunks into its prompt.

For ANT, the RAG layer is the agent's *long-term memory*. The agent's
own short-term memory is the conversation; the RAG index is everything
it should "remember" about the project.

---

## Planned RAG indexes

| Index | Corpus | Roles allowed |
|---|---|---|
| `code-backend` | All source in `backend/` (chunked by function) | backend, devsecops (read-only) |
| `code-uiux` | All source in `apps/`, `electron/features/`, `mobile/src/` | uiux, devsecops |
| `code-devops` | All source in `docker/`, `k8s/`, `infrastructure/`, `Makefile`, `scripts/`, `.github/workflows/`, `electron/{main,preload,stealth}.{js,...}` | devops, devsecops |
| `code-qa` | All test files in `e2e/`, `qa/`, `backend/tests/`, `mobile/__tests__/`, `electron/tests/` | qa, all (for context) |
| `code-devsecops` | All files in `.claude/`, `.pre-commit-config.yaml`, `backend/security/`, `docs/devsecops/`, `SECURITY.md`, `BROWSER_EXTENSION_SAFETY.md` | devsecops |
| `docs-backend` | `docs/backend/` | all (read-only) |
| `docs-uiux` | `docs/uiux/` | all (read-only) |
| `docs-devops` | `docs/devops/` | all (read-only) |
| `docs-qa` | `docs/qa/` | all (read-only) |
| `docs-devsecops` | `docs/devsecops/`, `docs/security/` | all (read-only) |
| `docs-shared` | `docs/shared/`, `docs/README.md` | all (read-only) |
| `docs-business` | `docs/business/` | all (read-only) |
| `docs-competitive` | `docs/competitive/` | all (read-only) |
| `docs-research` | `docs/research/` | all (read-only) |
| `git-history` | All `git log` entries (commit messages + diffs) | all (read-only) |
| `issues-prs` | All GitHub issues + PRs (past and open) | all (read-only) |
| `changelog` | All entries in `CHANGELOG.md` | all (read-only) |
| `agents-shared` | All `agents/*/MEMORY.md` + `agents/shared/*.md` | the matching role + devsecops (for audit) |

---

## Per-role allowlist (the contract)

### backend
- `code-backend` (full), `code-devsecops` (read-only)
- `docs-backend`, `docs-shared`, `docs-business` (read-only)
- `git-history`, `issues-prs`, `changelog` (read-only)
- `agents/backend/MEMORY.md` (read + write)

### uiux
- `code-uiux` (full), `code-devsecops` (read-only)
- `docs-uiux`, `docs-shared`, `docs-business` (read-only)
- `git-history`, `issues-prs`, `changelog` (read-only)
- `agents/uiux/MEMORY.md` (read + write)

### devops
- `code-devops` (full), `code-devsecops` (read-only)
- `code-backend`, `code-uiux`, `code-qa` (read-only, for deploy context)
- `docs-devops`, `docs-shared`, `docs-business` (read-only)
- `git-history`, `issues-prs`, `changelog` (read-only)
- `agents/devops/MEMORY.md` (read + write)

### qa
- `code-qa` (full), `code-backend`/`code-uiux`/`code-devops`/`code-devsecops` (read-only)
- `docs-qa`, `docs-shared`, `docs-business` (read-only)
- `git-history`, `issues-prs`, `changelog` (read-only)
- `agents/qa/MEMORY.md` (read + write)

### devsecops
- `code-devsecops` (full)
- `code-backend`, `code-uiux`, `code-devops`, `code-qa` (read-only)
- `docs-devsecops`, `docs-security`, `docs-shared` (read-only)
- `git-history`, `issues-prs`, `changelog` (read-only)
- `agents/devsecops/MEMORY.md` (read + write)
- `agents-shared` (read-only, for cross-role audit)

---

## How a RAG index is built

A RAG index is built by:

1. **Chunking:** split the corpus into ~500-token chunks (typically
   paragraph- or function-level)
2. **Embedding:** encode each chunk with an embedding model (e.g.
   `text-embedding-3-small`, `nomic-embed-text`, or a local model)
3. **Storage:** store the embeddings + the source metadata in a vector
   database (Chroma, Qdrant, Pinecone, or a SQLite-backed custom impl)
4. **Re-index:** on every commit, re-embed changed files (incremental)
5. **Re-embed fully:** on a weekly schedule, do a full re-embed to
   catch drift

The index is **read-only** for the agent — it never writes to the
index. The index is a *cache* of the codebase.

---

## Why role-scoped indexes (not one global index)

- **Context precision:** a backend agent searching for "the migration
  workflow" finds `backend/migrations/` first, not Electron's
  `electron-builder` config
- **Permissions:** a QA agent doesn't need access to the threat model
  docs (devsecops-only) to write a test
- **Memory isolation:** the `agents/backend/MEMORY.md` is only in the
  backend agent's index; the devops agent's memory of `render.yaml`
  doesn't pollute the backend agent's view

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
