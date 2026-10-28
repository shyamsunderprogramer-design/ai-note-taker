# ANT master remediation plan

Date: 2026-09-27  
Status: Implementation in progress; see IMPLEMENTATION-PROGRESS-2026-09-27.md for verified checkpoints and remaining work.  
Scope: ANT desktop/web/backend plus existing mobile/extension checks. All findings from the final app review and interview soak are included, together with unverified feature workflows. This is a bounded plan for known issues and scoped validation, not a claim that every possible bug can be eliminated.

## Objective

Make the main hands-free interview workflow reliable: accurate transcript → relevant screen/resume/JD context → grounded answer → bounded automatic recovery → correctly saved conversation. Bring the test infrastructure and feature workflows to a state where failures reflect product defects, not stale fixtures or incorrect routing. Keep the app compact and usable while delivering reviewable evidence.

## Scope decisions carried forward

- Do not connect OmniRoute to ANT. Do not integrate kimi-k3-in-c.
- Do not modify the separate AI_Assistant_Job_Applier repository; its malformed resume JSON/layout problem belongs to a different workstream.
- Preserve existing resume/JD separation, compact header access, conversation improvements and hands-free recovery.
- Keep personal chats, uploaded documents, credentials and recordings intact. Use isolated profiles, synthetic fixtures and a configurable temporary data root.
- Preserve unrelated dirty files and staged work. Make focused commits; do not sweep mobile/CI/docs changes into them without reviewing ownership.
- Work through routine implementation and verification continuously. Maintain a short progress log; do not ask permission for each fix. Ask only for a genuine missing credential, OS permission, external integration action or irreversible decision that cannot be resolved from evidence. Continue independent work when an external check is blocked.
- Do not send Slack/email/CRM messages or enable external auto-posting during tests. Use local test doubles for outbound integrations unless separately authorized. Do not weaken auth, ground-truth checks or test assertions to manufacture a pass.

## Baseline and interpretation

| Area | Observed result | How to interpret |
|---|---|---|
| Desktop / web / mobile unit tests | 70 / 5 / 34 passed | Useful regression baseline; not full platform certification |
| Full backend + startup | 1,173 passed / 49 failed / 61 skipped | 48 stream-related failures are import-order dependent; remaining directory failure needs clean-start investigation |
| Focused backend recheck | 68 passed / 1 failed / 2 skipped | Overlaps the full suite; not extra unique passes |
| Isolated API tests | 37 passed / 20 failed / 2 errors | Replaces 59 skipped API cases with observed results |
| Chromium + Firefox E2E | 16 passed / 28 failed | Test server routing and shallow assertions make some results misleading |
| Dedicated browser recovery / history / smoke / build | Passed | Preserve during changes |
| Live tour | 49 screenshots / 617 definitions | Static/runtime duplicates included; not 617 validated workflows |
| Previous 30-minute synthetic run | 60 completed / 20 successful injected recoveries | Wrong 120→12 ms on two turns; cache→cash on six invalidation questions. Timing may include a repeated harness readiness wait |

Baseline references: [final review](FINAL-APP-REVIEW-2026-09-27.md), [interview soak](INTERVIEW-SOAK-2026-09-26.md), [machine-readable work list](results/2026-09-27-remediation-plan.json).

## Execution order and dependencies

Use a single tracked implementation stream with small reviewable batches. No parallel agents are required.

1. **Reliable reproduction:** ANT-001. Persist test commands, isolate storage/auth/ports and capture before-change failures.
2. **Core correctness:** ANT-002, ANT-003, ANT-004. Fix confirmed auth/database/event-loop problems before interpreting feature failures.
3. **Streaming and desktop connections:** ANT-005, ANT-006, ANT-007. Preserve recovery semantics and prove clean startup.
4. **Contracts and test reliability:** ANT-008, ANT-009. Establish registered route ownership and fix requests/assertions without relaxing validation.
5. **Valid performance evidence:** ANT-010, then baseline the corrected pipeline. Do this before optimizing the five-second symptom.
6. **Answer quality:** ANT-011, ANT-012, ANT-013. Validate transcript, factual grounding and screen relevance together, including recovery continuations.
7. **Honest readiness/options:** ANT-014, ANT-015; rerun ANT-016 after every preceding batch.
8. **Feature completeness:** ANT-017, ANT-018, ANT-019. Exercise each scoped workflow on disposable data; record external limitations.
9. **Release verification:** ANT-020. Corrected long-run test, full suites, live walkthrough, final report and scoped commits.

Stop a dependent batch when its prerequisite fails. Investigate that failure, implement the smallest correct repair, and rerun the targeted check before widening tests. An unavailable cloud account must not prevent local work, but cannot be marked tested.

## Work packages

### ANT-001 — Test isolation and evidence (P0)

**Files:** backend/tests/conftest.py; backend/pytest.ini; e2e/playwright.config.js

**Evidence:** Live tests currently require fixed ports and some fixtures can import production state.

**Work:** Provide temporary data root, isolated auth, explicit API URL/ports and deterministic teardown. Make clean-checkout initialization part of the test harness.

**Acceptance:** All tests run without reading .env, writing personal data, or relying on an existing app instance.

### ANT-002 — BYOK authentication coroutine (P0)

**Files:** backend/routes/ollama.py; backend/routes/deps.py

**Evidence:** Confirmed: get_byok_status receives a coroutine because the local auth helper does not await get_current_user.

**Work:** Use the shared awaited auth dependency; audit duplicate wrappers and BYOK configure/delete paths. Preserve all access checks.

**Acceptance:** Valid token returns status without 500; invalid/missing token gets 401/403; no coroutine warnings; user isolation tested.

### ANT-003 — Audit database identity and lifecycle (P0)

**Files:** backend/security/audit.py; backend/core/database.py; backend/core/main.py

**Evidence:** Confirmed divergent import: audit uses database while app/auth use core.database. Logs show uninitialized session_maker.

**Work:** Use one canonical database module/manager and correct startup ordering. Keep missing optional dependency distinct from broken initialization.

**Acceptance:** Register/login/logout audit records persist in the same temporary database; restart reads them; shutdown awaits cleanup; no NoneType session failures.

### ANT-004 — Mock interview event-loop blocking (P0)

**Files:** backend/modules/interview/mock_interview_library.py; backend/routes/interview.py

**Evidence:** Confirmed: first get_all_questions/search can synchronously generate ten million questions; async route calls it directly. Integration calls and following auth fixtures time out.

**Work:** Replace whole-library materialization with bounded pagination/generation or indexed storage; cap work and memory. Offload any remaining blocking generation and prevent concurrent preload duplication. Return truthful counts.

**Acceptance:** Cold and warm list/search/random/practice requests complete within budgets; concurrent health/auth remain responsive; no ten-million-object preload.

### ANT-005 — Streaming function import-order mutation (P0)

**Files:** backend/core/main.py; backend/lib/async_stream.py; backend/routes/ai.py; backend/routes/recovery.py; provider/AI modules

**Evidence:** Confirmed full-suite failures: app import wraps shared sync generators into async generators. Focused recheck passes.

**Work:** Normalize sync/async iteration at the route boundary instead of mutating shared module functions globally. Inventory all consumers, preserve cancellation/close and thread offloading. Update QA adapter loaders if needed.

**Acceptance:** Full backend suite and targeted stream tests pass together and in reverse import order; no event-loop blocking or lost terminal errors; recovery tests remain green.

### ANT-006 — Desktop overlay URL and authentication (P0)

**Files:** apps/web/caption-overlay.html; apps/web/interview-overlay.html; apps/web/js/core/config.js; electron/preload.js

**Evidence:** Confirmed file:// hostname is empty, producing ws://:8000/ws/transcribe.

**Work:** Derive HTTP/WebSocket base from shared configuration, map http/https to ws/wss, and use the existing authenticated WebSocket protocol. Bound reconnects and stop on close/logout.

**Acceptance:** Both real Electron overlays connect on file://; HTTP and HTTPS URL tests pass; unauthenticated connections remain rejected; no listener leaks.

### ANT-007 — Recording storage root (P1)

**Files:** backend/modules/video/recording_manager.py; backend/routes/video.py; backend/tests/test_fix_33_no_stub_recordings.py

**Evidence:** Observed missing directory in clean isolated suite; storage path is relative to process working directory. Import/init timing also needs confirmation.

**Work:** Centralize configurable absolute runtime storage and create directories on manager initialization. Align tests with initialization contract; do not create fake recording files to satisfy assertions.

**Acceptance:** Fresh checkout, root/backend CWD and packaged desktop resolve the same configured root; real synthetic record/list/delete works only in temporary storage.

### ANT-008 — API contract reconciliation (P1)

**Files:** backend/tests/test_api_integration.py; backend/routes/conversations.py; cognitive.py; study.py; interview.py; jobs.py; agents.py; ai.py

**Evidence:** Observed 404/422 and document response-shape mismatches. At least import expects multipart, retrieve expects form, and documents returns pagination metadata.

**Work:** Build route/client/test contract matrix from registered OpenAPI routes. Fix real clients if wrong; update stale tests if wrong; choose one canonical contract and document compatibility. Resolve duplicate inline/router ownership.

**Acceptance:** Every valid request is accepted with schema assertions; malformed inputs still return useful 4xx; all affected API tests pass for the correct reason.

### ANT-009 — Browser routes and weak E2E assertions (P1)

**Files:** e2e/playwright.config.js; e2e/tests/*.spec.js; apps/web/vite.config.js; deployment routing config

**Evidence:** Confirmed plain-file test server returns 404 for extensionless URLs; some tests accept generic 404 headings as successful render.

**Work:** Use production-equivalent frontend routing in tests and explicit deployment rewrites where supported. Assert status, page identity, key controls and no uncaught errors. Test .html desktop navigation separately.

**Acceptance:** All 44 current cross-browser cases pass with real page content; new negative control rejects a 404 page; direct deep links work in supported deployments.

### ANT-010 — Speech benchmark validity (P1)

**Files:** qa/performance/voice/speech.py; qa/performance/pipeline/local.py; new versioned interview soak harness

**Evidence:** Harness investigation: /tmp/ant-interview-soak.py calls transcribe_audio without warmup/model_ready.set; transcribe waits up to five seconds each call. Earlier totals remain observations of that harness, not production latency.

**Work:** Persist a reproducible runner; use real startup/readiness semantics; measure load, readiness wait, speech end, STT, first AI token and completed answer independently. Capture failure states.

**Acceptance:** Cold/warm runs identify readiness cost; corrected 30-minute benchmark can be reproduced; prior report receives an explicit caveat, never silently rewritten as faster results.

### ANT-011 — Technical speech recognition (P1)

**Files:** backend/modules/voice/whisper_handler.py; backend/routes/transcription.py; backend/lib/audio_upload.py

**Evidence:** Observed cache→cash on all six invalidation questions in synthetic run.

**Work:** Evaluate domain vocabulary hints derived from actual resume/JD and recent question context, beam/model settings and confidence-aware correction. Keep original transcript; do not blindly replace cash globally.

**Acceptance:** Held-out cache/cash minimal pairs, technical terms, accents/noise and silence pass agreed thresholds; financial cash questions remain correct; latency measured with corrected harness.

### ANT-012 — Resume-grounded answers and history (P1)

**Files:** apps/web/app.js; backend/modules/ai/ai_router.py; backend/modules/platform/cloud_providers.py; backend/lib/stream_recovery.py

**Evidence:** Observed 120ms→12ms twice and unsupported personal validation/deployment claims; generated history can reinforce errors.

**Work:** Treat resume as authoritative and JD as requirements. Preserve factual spans/metrics; separate facts from generated history; validate high-risk personal claims/numbers and use bounded correction or an honest fallback. Apply identical grounding to continuation.

**Acceptance:** Known wrong-number and invented-certification cases fail before changes and pass after; held-out personal facts/negations/units pass; hypothetical approaches remain allowed; correction attempts bounded.

### ANT-013 — Screen-question freshness and answer scope (P1)

**Files:** apps/web/app.js; electron/main.js; backend/modules/ai/ocr_service.py; screen-context tests

**Evidence:** Observed user confusion and follow-up requests without saved answers; original screenshot absent from saved record. Exact error was not captured.

**Work:** Reproduce with numbered PDF fixtures, multiple screens and refreshed questions. Define singular vs all-visible scope; record non-sensitive capture metadata/status, selected display and request timing. Show unreadable/missing context explicitly. Prefer fresh capture over stale ring data.

**Acceptance:** Single/all-visible questions answer intended content in order; unreadable screens do not invent questions; new questions cancel older output; use latest capture; errors remain inspectable without storing screenshots by default.

### ANT-014 — Backend status and feature readiness (P1)

**Files:** electron/main.js; apps/web/app.js; backend/routes/health.py; backend/core/main.py

**Evidence:** Observed intermittent red health indicator and 81.8% module-health display. Some failures may follow blocked request handlers.

**Work:** Fix blocking causes first. Separate process liveness, readiness and optional feature availability. Use bounded health deadlines, consecutive-failure handling, nonoverlapping polls and honest retry status.

**Acceptance:** Temporary slow response does not claim backend dead; actual crash is detected/restarted; unavailable modules provide actionable status; health responsive during AI/STT/mock load.

### ANT-015 — Model catalog and effective limits (P1)

**Files:** apps/web/app.js; apps/web/index.html; backend/modules/platform/cloud_providers.py; backend/routes/ollama.py

**Evidence:** Observed static and runtime model lists diverge; 1024K UI budget is not proof a provider supports it.

**Work:** Use one runtime catalog with capability/availability metadata; remove or flag stale options only after verification. Respect provider and model toggles, image support, effective context and output limits.

**Acceptance:** UI and request agree on exact model; disabled models never selected; capability mismatches are clear; context UI never promises unsupported limits; custom/local models supported.

### ANT-016 — Recovery and chat-state regression protection (P1)

**Files:** backend/lib/stream_recovery.py; backend/routes/recovery.py; apps/web/app.js; existing recovery/history tests

**Evidence:** Existing recovery and chat tests passed; refactors could regress them.

**Work:** Retain bounded retries, cooldowns, refusal behavior, partial preservation, latest-question ownership, timeout release and accurate model provenance. Add slow discovery, network cut, repeated limits and exhausted local fallback cases.

**Acceptance:** All existing scenarios pass; no stale answer, duplicate partial, false done, endless retry, cross-chat overwrite, or automatic cloud spend outside enabled configuration.

### ANT-017 — Feature workflow completion matrix (P2)

**Files:** Feature HTML/JS pages and matching backend/routes modules; e2e tests

**Evidence:** Many controls were inspected but never exercised end-to-end. Visibility is not workflow completion.

**Work:** For each feature family below, test happy path, invalid input, unavailable backend/model, persistence and cancellation where applicable. Repair broken workflows, show accurate unavailable states for optional dependencies.

**Acceptance:** Every scoped feature has a linked test and explicit pass/fail/external-blocked result. Required core flows cannot be waived as unavailable.

### ANT-018 — UI clarity and accessibility (P2)

**Files:** apps/web/index.html; apps/web/style.css; feature pages; electron shortcut wiring

**Evidence:** Review artifacts expose technical/legacy/hidden options and Mac shortcut labels displaying Ctrl. User will provide design changes after review.

**Work:** Fix functional layout issues, labels, focus/keyboard access, empty/loading/error states and OS-specific shortcut help. Preserve compact resume/JD header and saved-chat improvements. Avoid unrelated redesign.

**Acceptance:** Desktop narrow/large and web small viewport review; all actionable icons labeled; keyboard-only navigation; option values match behavior; no obscured confirmations.

### ANT-019 — Mobile and extension validation (P2)

**Files:** mobile/; apps/ant-chrome-extension/; platform test configs

**Evidence:** Jest and JS syntax passed; physical device/browser capture workflows unverified. Existing unrelated mobile changes are present.

**Work:** Run isolated mobile emulator flows and load extension in a disposable browser profile. Validate auth/API URLs, permissions, recording lifecycle and failure recovery. Do not claim Windows/Linux runtime validation from a Mac.

**Acceptance:** Target-platform results recorded; unsupported/unavailable environments explicitly external-blocked; personal mobile/extension data untouched.

### ANT-020 — Final verification and delivery (P0 release gate)

**Files:** qa/performance/; test configs; CI workflow

**Evidence:** No fully green release evidence yet.

**Work:** Run all scoped suites after fixes, cross-browser and live desktop smoke, corrected 30-minute speech/recovery soak, leak/cancel checks, review UI and compare before/after. Commit only reviewed scope, with rollback references; publish only within authorization.

**Acceptance:** No unresolved core P0/P1 issues; all relevant suites green or explicitly scoped external limitations; known quality failures resolved on held-out cases; final report truthful and reproducible.

## API failure-to-fix matrix

First compare the registered OpenAPI route, actual frontend request and existing test. Duplicate endpoint definitions in `core/main.py` and router modules mean the active route must be checked rather than inferred from a search result.

| Failing tests | Work item / required disposition |
|---|---|
| BYOK status | ANT-002: await authentication; test success and denial |
| Conversation list/create | ANT-008: determine intended backend CRUD vs desktop IPC contract; add real missing API only if required by supported client, otherwise replace obsolete API tests with canonical storage coverage |
| Conversation import | ANT-008: send multipart upload to existing contract; test malformed file explicitly |
| Document list | ANT-008: verify pagination object and entries, not an obsolete bare-list assumption |
| Document retrieve | ANT-008: verify form/query contract and required query |
| Realtime process | ANT-008: trace actual caller and required fields; valid and invalid requests |
| Predict questions/checklist | ANT-008: correct query parameters and required company/role where applicable |
| Performance analyze | ANT-008: match actual analysis payload and resulting schema |
| Study-plan generation | ANT-008: agree on canonical general/personalized generation route and request body |
| Job tracker search | ANT-008: required search input and filters; prove route is not shadowed by dynamic ID route |
| Mock list/random/practice/search | ANT-004 + ANT-008: eliminate blocking preload, then validate route contracts; rerun following auth tests to confirm collateral timeouts stop |
| Collaboration status/messages | ANT-008: valid session identifiers and authorization; no broad anonymous access |
| Web search | ANT-008: required query; controlled unavailable-provider response, no blanket acceptance of errors |
| Resume analyze/compare | ANT-008: actual resume/JD body or form contract, no fabricated success |
| Complexity analysis | ANT-008: required code/text input and useful validation message |

## Feature completion checklist

Each row requires: clear enabled/disabled state; meaningful empty/loading/error states; correct input validation; an actual happy-path operation; cancellation/retry where relevant; persistence after reload where promised; and a linked result. Buttons that only open UI need a navigation assertion; buttons that mutate data require isolated data and a resulting-state assertion.

| Family | Scenarios to complete |
|---|---|
| Account | Synthetic register/login/logout, invalid/expired token, session isolation, recovery; SSO mocked first, live only with configured account |
| Window | Minimize/maximize/close, opacity, keyboard shortcuts, Mac labels, capture protection disclosure, hidden startup in isolated profile |
| Text/voice | Typed prompt, recorded clip, live mic, system audio, silence/noise, repeated start/stop, denied permissions, disconnect and next-question interruption |
| Resume/JD | Supported files, empty/corrupt/oversized file, separate editor save/cancel/remove, persistence, grounding on direct and continued responses |
| Screen/PDF | Fresh capture, selected display, OCR, image fallback, blurry/missing text, single question, all visible questions, page change, relevant vs unrelated screen |
| Answers | Model provenance, copy/read controls, summary, scrolling while streaming, user scroll position, malformed/empty stream, interrupted/exhausted response |
| History | Search all saved messages, pagination, all sort modes, pin/rename/select if exposed, new/open chat, export/import round-trip, cancel/confirm scoped deletion, partial-delete retry |
| AI options | All mode/style/temperature/context options, effective token limit, unavailable/disabled provider and model, custom/local model registration |
| Settings | Every card expands, validates and persists only intended values; restart backend preserves secrets and context; startup toggles reversible |
| Knowledge | Synthetic upload, indexing/retrieval, duplicate/invalid files, dry run vs actual import, remove and reload; no claims of successful indexing if optional service absent |
| Interview tools | Preparation, mock question/answer/skip/next, evaluation, study task completion and persistence, real analytics update from synthetic session |
| Job tracker/resume review | Synthetic application CRUD/search/stages, status persistence, resume analysis with/without JD, versioned page behavior and broken legacy links |
| Graph | Extract/search/filter from synthetic transcript, company/skill views, empty and unavailable graph states |
| Overlays | Both caption and interview plus generic overlay; actual desktop IPC, authentication, reconnect, pause/clear, click-through, close cleanup |
| Voice clone | Synthetic/consented fixture, model availability, create/train/test/cancel/delete in isolated storage; never claim live cloning passed from UI inspection |
| External integrations | Each configured provider tested against a local stub for connect/save/test/disconnect and payload schema. Live destination/account checks explicitly external-blocked until authorized |
| Mobile/extension | Existing automated suites plus emulator/disposable browser workflows, auth/API reachability, permission-denied and recording lifecycle |

## Performance and quality gates

These are proposed release targets for this Mac and measured workload, not promises or blanket requirements for every remote provider. Persist hardware/model versions and exact fixtures with results.

- No uncaught UI exception or invalid WebSocket URL in supported desktop/browser routes.
- Health p95 under 250 ms during ordinary inference and mock-question load; any failure investigated rather than hidden by a longer timeout.
- Warm local first-answer-text p95 at most 2 seconds after the AI request for the agreed short-answer fixtures; cold model load measured separately.
- Corrected speech-end-to-first-useful-text target p95 at most 5 seconds, and speech-end-to-complete-short-answer target p95 at most 10 seconds. Record VAD/segmentation wait separately; if accuracy needs a different tradeoff, report it explicitly instead of silently lowering quality.
- No repeated artificial readiness delay after successful model initialization.
- Known metric/credential hallucination regressions: zero failures in the fixed suite; add held-out resume/JD examples so this is not a hard-coded 120-ms repair. Do not claim a general no-hallucination guarantee.
- Cache/cash minimal pairs: intended technical and financial meanings both retained on held-out speech. Track task relevance and numeric accuracy, not just average word error rate.
- Thirty-minute soak: 60 scheduled turns, ten quota faults and ten mid-answer disconnects, all expected requests reach success or an explicitly expected bounded failure. Separate normal answers, recovered answers and intentionally exhausted cases; no silent drop, stale overwrite, false completion or crash.
- Add a separate all-providers-exhausted case that must finish incomplete promptly; a test requiring success when every provider fails is invalid.
- Measure RSS, model process memory, task/connection counts and CPU where available. No unbounded resource growth across repeated start/stop/cancel; do not infer absence of leaks solely from macOS RSS.

## Test execution and evidence

Run targeted tests for each repaired issue, then the full relevant suite at batch completion. Do not repeatedly rerun expensive unrelated suites without a change or unresolved concern.

```bash
# Backend: run through the isolated harness established in ANT-001.
AINT_Venv/bin/python -m pytest backend/tests backend/core/test_startup.py -q
node --test electron/tests/*.test.js
npm --workspace ant-web test
npm --workspace ant-mobile test -- --runInBand
npm run web:build
npm run e2e:test
```

The command list is not permission to run fixtures against personal production data. ANT-001 must make paths, ports, model downloads, external calls and auth safe before full-suite execution. Run Chromium and Firefox, the dedicated history/recovery/browser-smoke scripts, packaging smoke where supported, and the corrected versioned soak harness. Required checks must not silently skip because a test server was forgotten.

For every work item record: before failure, root cause, files changed, targeted test, wider regression test, artifact path, status and commit. Allowed states: planned, in progress, verified, external-blocked. “Implemented” without evidence is not verified. A workaround that hides a control is not a feature fix unless the feature is explicitly unsupported and clearly communicated.

## Completion and delivery

- All confirmed core defects above repaired, with regression tests and correct behavior under failure.
- Full relevant suites pass together; no new flaky retries, weakened expectations, blanket xfails or skipped required checks.
- Every reviewed feature is either verified with evidence or has a specific external prerequisite recorded. Core chat/voice/context/recovery/history cannot be signed off while blocked.
- Corrected 30-minute performance and quality report compares like-for-like baseline and revised implementation; the earlier harness caveat is prominent.
- Live walkthrough repeated after fixes; compact layout and existing user preferences preserved.
- Deliver the issue matrix, exact test counts, remaining external limitations and scoped commit/rollback references. Installation alone is not deployment; runtime restart and code publication are tracked separately.

## Progress log

- 2026-09-27: Baseline evidence reviewed. Confirmed unawaited BYOK auth lookup, mixed audit DB import, bulk ten-million mock-question preload, import-time stream mutation, and overlay hostname bug. Identified probable repeated readiness wait in the standalone speech harness. Plan created; no product implementation performed in this planning step.
