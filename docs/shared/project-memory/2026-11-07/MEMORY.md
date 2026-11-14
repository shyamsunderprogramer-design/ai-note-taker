---
status: completed
branch: main
timestamp: 2026-11-07T19:25:36Z
head: a0db81d952b8365368b2c9785f8ab3c444c169ee
---

# ANT project memory

## Purpose and recall

The user requested project memory to reduce repeated file reads and token consumption. Start with this summary, search the adjacent `file-index.jsonl` for relevant paths or symbols, then read only needed source ranges. Check current git status and changes before relying on this dated snapshot. Do not load the entire index into model context.

This is durable reference material, not permanent model knowledge. It saves future discovery work; retrieved text still consumes context. The local indexer read 977 eligible text files (10,361,104 bytes), extracting symbols, Markdown headings, package scripts, line counts and SHA-256 fingerprints. The model reviewed selected architecture/setup documentation, entry-point excerpts and feature declarations; it did not semantically review every line. This is not a code audit or test result.

Coverage: tracked plus nonignored untracked paths. The inventory has 1,103 entries: 977 indexed text files, 111 excluded binaries, 3 dependency/generated/sensitive exclusions, and 12 missing tracked paths. Ignored dependencies, private environment files, runtime databases, caches and other ignored files were not included. No complete source bodies were copied into the index. `snapshot.json` records counts and the existing dirty working tree.

## Product and architecture

ANT / AI Note Taker is a floating desktop workspace for voice notes, streamed AI answers, screen questions, meeting history, and interview preparation. The root package version at capture is `2.3.0-rc.2`; release claims in README are repository documentation, not independently verified live release state.

| Area | Main paths and responsibility |
| --- | --- |
| Desktop | `electron/main.js` owns windows, native features and IPC; `electron/preload.js` exposes the renderer bridge; `electron/lib/` contains runtime, auth, storage, provider and capture helpers. |
| Shared interface | `apps/web/` is the Vite/vanilla-JavaScript desktop renderer and browser app; `app.js`, `index.html`, `style.css`, `js/` and `css/` contain UI behavior and styling. |
| Backend | `backend/core/main.py` is FastAPI startup and shared endpoints; `core/config.py` configures services; `core/database.py` manages database access; `routes/` separates API features. |
| AI | `backend/routes/ai.py`, `backend/modules/ai/ai_router.py` route conversation/image context to Ollama and configured cloud providers. Auto/race routing can contact multiple providers. |
| Speech | `backend/routes/transcription.py`, `backend/modules/voice/whisper_handler.py`, `apple_speech.py`, system-audio and diarization modules handle uploaded/live audio and transcription. |
| Persistence | SQLite is the default backend database; optional services include PostgreSQL, Redis and Neo4j. `backend/lib/storage_paths.py` handles writable data paths; Electron also owns conversation JSON/settings via `electron/lib/conversation-storage.js`. |
| Other clients | React Native in `mobile/`; extension variants in `apps/ant-chrome-extension/`, `chrome-extension/`, `browser-extension/`, `vscode-extension/`. Desktop release verification does not establish these clients work. |
| Website | `apps/landing/` owns marketing content; `scripts/build-site.mjs` and `vercel.json` support the website at `/` and browser app at `/app`. |
| Operations | `scripts/`, `docker/`, `k8s/`, `infrastructure/`, `.github/workflows/`; `scripts/build_desktop_runtime.py` prepares bundled Python. |
| Verification | `backend/tests/`, `electron/tests/`, `apps/web/tests/`, `mobile/__tests__/`, `e2e/`, and `qa/` hold tests, harnesses and evidence. |

Default local flow: Electron launches FastAPI on loopback port 8000; browser development uses Vite on 5173. Clients use HTTP, streamed responses and audio WebSockets; native features require Electron IPC. Local Whisper transcribes; Ollama or cloud models answer. A remote backend/AI endpoint changes where processing occurs.

## Setup and validation commands

Repository declares Python 3.12 (`.python-version` pins 3.12.15), Node >=22.12 and npm >=10. Source desktop expects `AINT_Venv`; packaged apps use bundled Python. Root npm workspaces include `apps/*`, `electron`, `mobile`, `e2e`, `vendor/*`. Desktop workspace is named `ai-note-taker`, web `ant-web`.

- Install: root `npm ci`; Python requirements are in `backend/requirements*.txt`.
- Desktop: `npm run electron:start`.
- Browser: `npm run web:dev`; backend from `backend/`: `python -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000`.
- Build: `npm run web:build`; combined website `npm run site:build`; desktop runtime preparation precedes platform packaging.
- Unit tests: `npm --workspace ai-note-taker test`, `npm --workspace ant-web test`, `npm run mobile:test -- --runInBand`.
- Backend tests from `backend/`: `python -m pytest core/test_startup.py tests/ --tb=short` after installing test requirements.
- Security: `npm run test:security`. Root `npm test` runs browser E2E, not every suite.
- Browser: `npm run e2e:test`; `e2e/playwright.config.js` uses Chromium and Firefox, isolated frontend 8048/backend 8049, and `ANT_TEST_PYTHON` or local virtualenv Python.

Commands were read from source/docs, not executed during memory capture. No build, test, deploy or provider sign-in was performed.

## Existing working changes and cautions

At capture, `main` already had substantial uncommitted changes. Preserve them; the full pre-save path list is in `snapshot.json`. Recent committed HEAD merged PR #68 for user-scoped jobs/analytics/study routes. Uncommitted work includes:

- Connected ChatGPT/Ollama account answers: `electron/lib/subscription-auth.js`, `subscriptions.js`, `ollama-account.js`, `connected-models.js`, frontend `apps/web/js/subscriptions.js`, styling, tests and `docs/SUBSCRIPTIONS.md`. The docs describe encrypted desktop credentials, trusted-frame IPC, explicit account selection, opt-in cross-account/local fallback and persisted quota pauses. These are source-level implementation descriptions, not proof of live account eligibility or successful sign-in.
- Provider-key persistence: `electron/lib/provider-env.js`, `backend/lib/provider_env.py`, associated tests and configuration. Documented optional private app-data `.env` is passed through `ANT_PROVIDER_ENV_FILE`; do not read or save credential values.
- Note search: `backend/lib/note_search.py`, conversation routes, frontend `NotesSearchController.js`, tests. Symbols include a parser, match finder, ranker and search engine.
- Speech changes: Apple speech, Whisper handling, transcription routes and tests; `qa/performance/TRANSCRIPTION-LATENCY-2026-10-29.md` holds related evidence.
- Role/documentation/artwork reorganization: originals moved toward `assets/design/artwork/`, prototypes toward `assets/design/prototypes/`, reports toward `docs/qa/reports/`; old tracked paths appear deleted. Do not treat these deletions as accidental without checking the move.

Use current manifests and source over older docs when they disagree. `MONOREPO.md` has older platform/build wording; the newer README describes macOS ZIP output. `agents/README.md` describes planned role infrastructure and is dated June 2026; do not infer that its planned services are deployed. GBrain startup reported this worktree unpinned, so do not assume its code search is current.

## Ownership and remaining work

`docs/ROLES.md`, root `OWNERS.*.md` and `.github/CODEOWNERS` map backend, UI/UX, DevOps, QA and DevSecOps ownership. Role-specific instructions and notes live in `agents/<role>/`; they were not modified by this capture.

No application task was requested or performed. Memory capture is complete. Future work should begin from a fresh user request and validate relevant source against this dated index. The index is an append-only snapshot and does not update itself.
