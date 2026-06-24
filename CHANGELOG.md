# Changelog

All notable changes to ANT (AI Note Taker) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] — 2026-06-11

This release adds the **role-based ownership refactor**. It is split into
5 sequential PRs (PR 1 through PR 5); PRs 1, 2, 3, 4, and 5 are in this
changelog. See
[`OWNERS.{backend,uiux,devops,qa,devsecops}.md`](OWNERS.backend.md) for the
per-role charters and [`.github/CODEOWNERS`](.github/CODEOWNERS) for the
file-to-role routing.

### Added (PR 5 — root-file link fixes after docs/ move, 2026-06-11)

- **`README.md` Documentation section rewritten** to point at the
  new per-role doc paths. All ~20 broken `docs/<file>.md` links
  replaced with the new `docs/<role>/<file>.md` paths. The
  section is now organized by role (devops / backend / devsecops /
  uiux / qa / business / cross-cutting) and ends with a "per-role
  charters" block linking the 5 `OWNERS.*.md` files.
- **`README.md` Project Structure tree** updated: the `docs/`
  comment block changed from "8 categories" to the new per-role
  layout (5 roles + 5 topics).
- **`README.md`** two one-liners fixed: `docs/SETUP_COGNITIVE_GRAPH.md`
  → `docs/backend/setup/SETUP_COGNITIVE_GRAPH.md`; the
  `BROWSER_EXTENSION_SAFETY.md` and `SECURITY.md` Security
  bullets point at the new `docs/devsecops/...` paths.
- **`CONTRIBUTING.md`** cleaned: the security-contact line had
  malformed link text; fixed. "8 categories" reference updated
  to the new role-based layout. The "new API endpoint →
  `docs/api/API_REFERENCE.md`" example updated to
  `docs/backend/api/API_REFERENCE.md`, with a second example
  for a new design token → `docs/uiux/design-system/README.md`.
- **`MONOREPO.md`** audit-doc link updated to
  `docs/shared/AUDIT_2026-06-05_Project_Audit.md`; a new
  blockquote at the top points readers at `OWNERS.*.md` and
  `.github/CODEOWNERS` for the role-ownership model.

### Migration notes (PR 5)

- All in-repo links to `docs/<file>.md` paths that moved in PR 4
  are now fixed. If a downstream doc (e.g. an external blog post
  or a Slack message) still links at the old path, it will 404
  on github.com; the new `docs/README.md` index is the canonical
  starting point.

### Added (PR 4 — `docs/` reorganization into per-role subfolders, 2026-06-11)- **`docs/` reorganized** into a per-role layout that mirrors the 5
  role charters and the new CODEOWNERS routing. All 56 doc files
  moved via `git mv` (no delete+create) so `git log --follow`
  continues to work. New top-level structure:
  - `docs/backend/` — FastAPI / services / DB / Neo4j cognitive graph
    (`api/`, `architecture/`, `database/`, `modules/`, `setup/`,
    `COGNITIVE_GRAPH_API.md`, `README.md`)
  - `docs/uiux/` — web SPA / mobile / Chrome extension / Electron UI
    / design system (`design-system/`, `components/`,
    `accessibility/`, `README.md`)
  - `docs/devops/` — deploy / runtime shell / CI / infra / Docker /
    mobile-native build (`development/`, `deployment/`,
    `operations/`, `docker/`, `mobile-native/{ios,android}/`,
    `README.md`)
  - `docs/qa/` — test strategy / test environment (`test-strategy.md`,
    `test-environment.md`, `DIY_TEST_GUIDE.md`, `README.md`)
  - `docs/devsecops/` — threat model / supply chain / compliance
    (`security/{README,SECURITY_IMPLEMENTATION_SUMMARY,
    BROWSER_EXTENSION_SAFETY,threat-model}.md`,
    `supply-chain/{README,dependabot-policy}.md`,
    `compliance/{README,SECURITY,audit-log-policy}.md`,
    `README.md`)
  - `docs/shared/` — cross-cutting docs (COMPREHENSIVE_GUIDE,
    AUDIT_2026-06-05, FULL_IMPLEMENTATION_COMPLETE,
    CRITICAL_GAPS_FIXED, PRODUCTION_DEEP_DIVE_2026,
    ANALYSIS_2026-04-07)
  - `docs/business/` — product / business (BYOK, job tools,
    ENTITY_EXTRACTION, PHASE2_PLAN, speed-opt history,
    resume-builder/)
  - `docs/competitive/` — competitor matrix + Pluely deep-dive
  - `docs/archive/` — empty stub, populated as docs are
    superseded
  - `docs/research/` — kept as-is (time-bounded research
    artifacts)
- **`docs/README.md` rewritten** as the new role-based index. Replaces
  the old 8-category layout with a 5-role + 4-topic layout. Each
  role's `README.md` is now the entry point for that role.
- **Two root-level docs moved**: `SECURITY.md` →
  `docs/devsecops/compliance/SECURITY.md`,
  `BROWSER_EXTENSION_SAFETY.md` → `docs/devsecops/security/`.
- **Empty old subfolders removed**: `docs/api/`,
  `docs/architecture/`, `docs/database/`, `docs/development/`,
  `docs/security/`. (No file was deleted; only empty containers
  were `rmdir`'d after their files were `git mv`'d out.)
- **New stub docs** (intentionally short — to be expanded as the
  role matures):
  - `docs/devsecops/security/threat-model.md` — repo-wide
    threat model with assets / adversaries / mitigations
  - `docs/devsecops/supply-chain/dependabot-policy.md` —
    Dependabot triage workflow + SLA, with the known-watch
    `bcrypt 5.0.0 + passlib 1.7.4` block
  - `docs/devsecops/compliance/audit-log-policy.md` — what gets
    audited, retention windows, access control
  - `docs/qa/test-strategy.md` — the layered test strategy (unit
    / e2e / perf / manual) and regression-test convention
  - `docs/qa/test-environment.md` — versions in use + CI
    environment + known gotchas (bcrypt pin, TestClient 405
    workaround, etc.)

### Migration notes (PR 4)

- All doc links that pointed at the old `docs/<file>.md` paths
  need updating. The new `docs/README.md` index is the canonical
  starting point. Root files (`README.md`, `MONOREPO.md`,
  `CONTRIBUTING.md`) will be fixed in PR 5.
- 5 GitHub Teams (`role-backend`, `role-uiux`, `role-devops`,
  `role-qa`, `role-devsecops`) need to be created manually in
  github.com (Settings → Teams) with `@shyamsunderprogramer-design`
  as the sole member. Until then the new CODEOWNERS lines are
  silently ignored by GitHub, but the file is still valid.

### Added (PR 1 — role charters + CODEOWNERS + agents/ scaffold, 2026-06-11)

- **5 `OWNERS.*.md` charter files** at the repo root — one per role
  (`backend`, `uiux`, `devops`, `qa`, `devsecops`). Each charter lists
  the file/dir inventory, the cross-role dependencies, the typical PR
  outputs, the AI-agent scope, and the "do not" list for that role.
- **`agents/` folder** with per-role AI agent scaffolding:
  - `agents/README.md` — explains the role-agent pattern
  - `agents/{backend,uiux,devops,qa,devsecops}/AGENTS.md` — scoped
    instructions for a future role-specific agent
  - `agents/{backend,uiux,devops,qa,devsecops}/MEMORY.md` — role-scoped
    persistent memory (empty stubs, populated as the agent accumulates
    project knowledge)
  - `agents/shared/mcp-servers.md` — planning stub for the future
    MCP-server tool layer (not implemented)
  - `agents/shared/rag-indexes.md` — planning stub for the future
    role-scoped RAG indexes (not implemented)

### Added (PR 3 — qa/ scaffold, 2026-06-11)

- **`qa/` folder** at the repo root — the QA home for test-environment
  artifacts that don't fit next to the code:
  - `qa/README.md` — the test-environment manifest (which Python,
    which Node, which Playwright, which Ollama, etc.); explains
    what goes in `qa/` vs `backend/tests/`, `e2e/tests/`,
    `mobile/__tests__/`, `electron/tests/`
  - `qa/test-plans/README.md` — manual + exploratory test plans
    (the QA substitute for the human's eyes on a real install;
    catches visual / audio / multi-device / onboarding / error-
    message issues that automated tests don't)
  - `qa/fixtures/README.md` — synthetic test data (sample users,
    sample conversations, sample recordings); strict rules on
    "no real user data, no real API keys, no real PII"
  - `qa/performance/README.md` — k6 perf scripts + perf budgets
    (the SLO table for each endpoint; the CI gate that blocks
    PRs that regress a budget)
  - Three empty subfolders ready for the first scripts:
    `qa/test-plans/`, `qa/fixtures/`, `qa/performance/`

### Added (PR 2 — role-aware templates, 2026-06-11)

- **`.github/PULL_REQUEST_TEMPLATE.md` rewritten** with a "Role(s)
  affected" checklist at the top — the 5 roles (`backend` / `uiux` /
  `devops` / `qa` / `devsecops`) with their owned file paths inline so
  the author can pick the right ones. Followed by a per-role checklist
  the reviewer confirms (e.g., "Backend: pytest passes + API ref
  updated", "Devops: CHANGELOG entry + CSP / secret / base-image
  change flagged"). Last section is the original summary / type /
  test plan / checklist, plus one new line: "If this PR touched a
  co-owned file (runtime shell, deploy manifest, test infra, API
  contract), the second role's reviewer has been tagged in a PR
  comment".
- **`.github/ISSUE_TEMPLATE/bug_report.md` edited** to add an
  "Affected role" block at the top — same 5 roles + an "Unclear /
  other" escape. The "Affected area" prompt asks for a file path or
  feature name so the role can route the issue.
- **`.github/ISSUE_TEMPLATE/feature_request.md` edited** to add a
  "Primary role owner" block — same 5 roles + a "Cross-cutting"
  escape (for issues that touch 2+ roles; the body describes which
  secondary roles need to review).
- **`.github/ISSUE_TEMPLATE/question.md` edited** to add a "Role
  context" block — same 5 roles + a "General" escape (for
  project-layout / monorepo / docs-structure questions that aren't
  tied to one role).
- **`.github/dependabot.yml` comment block added** at the top —
  documents the role ownership (devops owns the config, devsecops
  owns the supply-chain review, co-owned in CODEOWNERS last-match
  block), points at `docs/devsecops/supply-chain/README.md` and
  `docs/devsecops/supply-chain/dependabot-policy.md` for the policy
  and triage SLA, and re-flags the known-watch dep
  (`bcrypt 5.0.0 + passlib 1.7.4`). **No config change** — purely
  documentation.

### Changed (PR 1)

- **`.github/CODEOWNERS` rewritten** to map files to role teams
  (`role-backend`, `role-uiux`, `role-devops`, `role-qa`, `role-devsecops`)
  instead of a single owner. Co-owned files (runtime shell, deploy
  manifests, test code, API contract in `apps/web/app.js`) are listed
  at the bottom of the file with multiple owners; GitHub's
  last-match-wins semantics route the PR to all of them. **No code or
  content changed** — the rewrite is purely a routing update.

---

## [2.1.0] - 2026-06-23

This release closes out the **Fix #35 series** — the move from a
JSON-file user store (`backend/data/users.json`) to a proper SQLAlchemy-
backed users table. For existing users, the migration is transparent: on
the first start after upgrading, the app copies every account from the
old file into the database automatically and writes a sticky-note file
(`backend/data/.migrated_to_sql`) so the migration never runs again.
The 5-day UX sprint shipped in v2.0.0 was extended with one in-place
fix in this release: the AI response bubble now renders even if the
Electron IPC store-bridge is unavailable (falls back to `localStorage`),
and the AI race-stream endpoint was hardened against the sync/async
generator mismatch that surfaced under newer FastAPI.

### Added (Fix #35 — 6-commit auth refactor)

- **`backend/core/database.py`** — `DataMigrator` rewritten to copy every
  User column (`security_question`, `hashed_security_answer`,
  `active_session_id/ip/user_agent/started_at`, `on_new_login_pref`,
  `last_login`), not just the original 6. Pre-2.1.0 the migrator silently
  dropped the security-question and active-session fields, which would
  have invalidated every migrated user's security question and forced a
  re-login on first use.
- **`backend/core/database.py`** — `DataMigrator.run_full_migration()` is
  now idempotent via a `backend/data/.migrated_to_sql` sticky-note file.
  `force=True` keyword added so the admin button can re-run on demand.
- **`backend/core/main.py`** — `start_listener()` startup hook now calls
  `DataMigrator.run_full_migration()` after `init_database()`. Wrapped in
  try/except so a migration failure never blocks startup. Both the
  startup hook and the `/admin/migrate` route pass `force=True`
  appropriately.
- **`backend/security/auth.py`** — `UserManager` is now an async shim
  over `core.database.UserRepository`. Module-level
  `from core.database import UserRepository` replaced with a lazy
  `UserManager._repo()` helper to break the circular import that
  appeared once Commit 2's `UserRepository.auth_headers_set_jti` test
  helper started importing back into `security.auth`.
- **`backend/routes/auth.py`** — `await` added to the
  `get_current_user_with_reason(token)` call in `require_authentication`
  (the underlying function became async in Commit 3).
- **`backend/routes/admin.py`** — `/admin/migrate` now passes
  `force=True` so the admin button actually re-runs after the marker is
  set.

### Changed (UX sprint — AI race stream + frontend guard)

- **`apps/web/app.js`** — `streamAIRace` now wraps
  `window.api.storeGet` calls in try/catch with a `localStorage`
  fallback, so the assistant bubble renders even when the Electron IPC
  bridge is unavailable (fixes the "AI response failed" error in some
  preview/dev modes).
- **`backend/core/main.py`** — universal async-generator monkey-patch at
  import time so `async for` over a sync generator (the SSE pattern in
  `routes/ai.py`) works uniformly across all AI provider modules.
- **`backend/routes/ai.py`** — `async for event in …` restored at all
  single-provider fast paths now that the patch makes every stream
  function async-compatible.

### Tests added

- **`backend/tests/test_data_migrator.py`** — 8 tests pinning the
  full-fidelity column copy (AST-level + behavioral), the idempotency
  marker, and the `force=True` bypass.
- **`backend/tests/test_no_json_user_store.py`** — 8 guardrail tests
  that pin the Fix-#35 source-of-truth contract at the AST level: no
  `USERS_FILE`, no `_save_users`/`_load_users`, no `self.users = `
  in-memory dict, no `open('users.json')`, no module-level
  `import json`, and the docstring still mentions SQLAlchemy /
  UserRepository.
- **`backend/tests/conftest.py`** — `auth_headers` fixture converted
  from sync `@pytest.fixture def` calling
  `asyncio.get_event_loop().run_until_complete(...)` (deprecated on
  Python 3.12 main thread, forbidden when pytest-asyncio has a
  running loop) to `@pytest_asyncio.fixture async def`. Adds a
  `tmp_db` fixture for hermetic per-test SQLite databases.
- **`backend/tests/test_fix_34_single_session.py`**,
  **`backend/tests/test_fix_31_user_id_auth.py`**,
  **`backend/tests/test_routes_deps.py`** — repaired to use the async
  `user_manager.create_user()` and the test-only
  `UserRepository.auth_headers_set_jti` helper, with `_setup_db`
  fixtures added so the SQLAlchemy write hits a hermetic per-test
  SQLite DB instead of the dev DB.

### Migration notes

- **No operator action required.** On the first start of v2.1.0, the
  app detects `backend/data/users.json`, copies every user (with all
  fields) into the SQLAlchemy `users` table, and writes
  `backend/data/.migrated_to_sql`. Subsequent starts see the marker
  and skip the migration.
- To re-run the migration manually (e.g. after dropping a fresh
  `users.json` in place), use `POST /admin/migrate` — it now passes
  `force=True`.
- The `backend/data/users.json` file is no longer written to at
  runtime. After confirming the migration succeeded (via
  `/auth/login` working as expected), the file can be archived or
  deleted; it is not read again.

---

## [1.0.0] - 2026-04-05

### Added - Phase 2 Features

#### Real-Time Suggestion Engine (#28)
- Contextual hints during live interviews
- Voice-activated commands ("What did I say about React?")
- Cooldown mechanism to prevent UI spam
- Confidence scoring for suggestion relevance

#### Hybrid Entity Extraction (#29)
- spaCy NER integration (en_core_web_sm)
- Combined rule-based + ML approach
- Confidence weighting system
- >90% extraction accuracy

#### Conversation Analysis (#30)
- Auto-tagging by type (practice, mock, real interview)
- Quality metrics (completeness, technical depth, clarity)
- Focus area detection
- Gap identification

#### Graph Analytics Dashboard (#31)
- Skill progression timeline with Chart.js
- Company comparison heatmap
- Topic network graph with D3.js
- Interview frequency calendar
- Performance trends (improving/declining/stable)

#### Interview Performance Insights (#32)
- STAR method pattern detection
- Code quality scoring
- Speaking pace analysis
- Filler word tracking
- Answer structure assessment

#### Study Plan Generator (#33)
- Spaced repetition scheduling (SM-2 algorithm)
- Weak area identification from cognitive graph
- Resource library (LeetCode, System Design Primer)
- Adaptive difficulty adjustment
- Export to JSON/iCal/Markdown

### Changed
- Enhanced main.py with 25+ new API endpoints
- Improved error handling across all modules
- Better logging for debugging

### Fixed
- Fixed undefined `query_graph()` in realtime_suggestions.py
- Fixed code quality scoring bug in performance_analyzer.py
- Fixed study plan JSON export double parsing
- Fixed iCal export formatting with proper escaping

---

## [0.9.0] - 2026-03-XX

### Added - Phase 1: Cognitive Graph
- Neo4j-powered personal knowledge graph
- Semantic search across interview history
- Entity extraction (companies, skills, topics)
- Company insights and question patterns
- Skill progression tracking
- Interview predictions for major tech companies
- Pre-interview preparation checklists

### Added - Core Features
- Local Whisper speech-to-text
- Real-time streaming transcription
- 10 AI modes (Instant, Auto, Fast, Turbo, etc.)
- Multi-provider AI routing (OpenAI, Anthropic, Google, etc.)
- Floating overlay UI with stealth mode
- Screen capture protection
- Always-on microphone mode
- Session management and history

---

## [0.1.0] - 2026-XX-XX

### Added - Initial Release
- Basic Electron app structure
- Voice recording and transcription
- Simple AI chat interface
- Local storage for conversations

---

## Release Schedule

| Version | Phase | Status |
|---------|-------|--------|
| 1.0.0 | Phase 2 Complete | ✅ Released 2026-04-05 |
| 0.9.0 | Phase 1 Complete | ✅ Released |
| 0.1.0 | MVP | ✅ Released |

## Legend

- **Added** - New features
- **Changed** - Modifications to existing features
- **Deprecated** - Features marked for removal
- **Removed** - Deleted features
- **Fixed** - Bug fixes
- **Security** - Security-related changes
