# Changelog

All notable changes to ANT (AI Note Taker) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased] — 2026-06-11

This release adds the **role-based ownership refactor**. It is split into
5 sequential PRs (PR 1 through PR 5); this is the PR-1 entry. See
[`OWNERS.{backend,uiux,devops,qa,devsecops}.md`](OWNERS.backend.md) for the
per-role charters and [`.github/CODEOWNERS`](.github/CODEOWNERS) for the
file-to-role routing.

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
