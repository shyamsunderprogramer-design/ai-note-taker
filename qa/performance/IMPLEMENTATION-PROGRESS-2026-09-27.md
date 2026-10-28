# ANT remediation progress — 2026-09-27

Implementation is in progress, not a release sign-off. Fixes are checked individually before moving on.

| Item | State | Evidence |
|---|---|---|
| ANT-001 isolation | Verified backend/browser foundation | Disposable source/data, sanitized environment, key-server discovery disabled, dedicated ports, no server reuse |
| ANT-002 authentication | Fixed and verified | Live BYOK 500→200; missing/invalid tokens remain 401; 11 additional route modules use shared awaited auth |
| ANT-003 audit database | Fixed and verified | Real SQLite write/read round trip passes; live registration/login no longer logs uninitialized audit manager |
| ANT-004 mock interviews | Fixed and verified | Bounded 1,000-question searchable catalogue; on-demand practice; stable pagination; concurrent health responsive; live first page 13–24 ms |
| ANT-005 streaming | Fixed and verified | Removed global provider mutations; 48 import-order failures cleared; 99 focused tests passed; local Qwen stream completed in 3.282 seconds |
| ANT-006 overlays | Fixed and verified | Shared URL/auth/reconnect lifecycle; both actual file:// pages connected, Live status, no script errors; visible browser left open |
| ANT-007 recording storage | Fixed and verified | Absolute configurable path; clean initialization from different CWD; saved metadata reload; five targeted tests passed |
| ANT-008 API contracts | Main repairs verified; client regression checks ongoing | Conversation CRUD with user isolation; 59 live API tests passed; 164 duplicate route registrations removed and ownership test passes |
| ANT-009 browser harness | Fixed and verified | Isolated clean-URL server and API injection; strict HTTP page checks; job tracker URL fixed; analytics shows unavailable state; 44 Chromium/Firefox tests passed |
| ANT-010 benchmark | Corrected and exercised | Explicit model warmup and timing; 30-minute synthetic speech/local model run: 60/60 answers, 20/20 injected recoveries, no health failures |
| ANT-011 speech | Narrow correction tested | Technical homophones corrected only in unambiguous phrases; financial cash vocabulary preserved; broader live speech checks remain |
| ANT-012 resume measurements | Numeric guard tested | Buffered measurement check, one bounded repair, cancellation cleanup; general factual grounding remains unverified |
| ANT-013 screen context | In progress | Fresh-capture metadata and explicit missing-context errors; typed/spoken failure history saved once; live numbered-question check pending |
| ANT-014 readiness | In progress | Readiness endpoint, truthful optional modules, bounded non-overlapping health polls; targeted tests passed, live check pending |
| ANT-015 onward | Pending | Runtime model limits, complete feature workflows, UI/accessibility, mobile/extension and final release gates |

Backend checkpoint before later API/browser changes: **1,234 passed**, excluding the separately run API suite. This count is not a final result for all subsequent edits.

Live results: [core checks](results/2026-09-27-remediation/live-core.json), [overlays](results/2026-09-27-remediation/overlays.json). Live review: http://127.0.0.1:8047/fix-watch.html.

No release or push performed. Real cloud credentials, external integrations, microphone/meeting capture and graph-backed analytics remain outside these checks. OmniRoute is not connected.

2026-09-28 continuation: long-run evidence is saved in [interview-soak.json](results/2026-09-27-remediation/interview-soak.json). Median end-to-end 4.00 s; p95 4.73 s. Exhausted providers produced an explicit error and the next question completed. This is synthetic file transcription and local inference with injected faults, not a live meeting or cloud-provider test. Some answers still include irrelevant details; numeric checking is not full factual validation.

Latest continuation checks: backend **1,266 passed, 10 warnings** (API integration run remains separate); desktop/web unit checkpoint **87 passed** followed by two additional screen-history tests passing; Vite build passed. Live readiness and liveness-during-module-check passed (3 ms liveness), as did authenticated BYOK and catalogue checks. Browser testing caught an undefined message-options variable and a wrapper dropping metadata; both were fixed and a browser history regression was added. Browser rerun passed across five pages, including the added saved-screen-history workflow. Explicit screen shortcuts now use fresh capture with the common question lifecycle; targeted test passed.

Screen continuation: real OCR + renderer + local Qwen now passes all four controlled-image checks (all numbered questions, ambiguous singular clarification, changed question, fresh metadata). The ambiguous case failed initially and was corrected before inference for clearly numbered questions. **91 desktop/web tests and web build pass** after the final fix. Visible Chromium crashed before loading a page twice; the pipeline check ran headlessly and does not certify native OS capture or a live visual review. Evidence: [checkpoint](results/2026-09-27-remediation/2026-09-28-checkpoint.json), [screen pipeline](results/2026-09-27-remediation/screen-pipeline.json).

## Paused at user request — 2026-09-29

All edits are saved locally. No commit, push, or release was performed.

Latest changes:
- Recovery consistently classifies both `:cloud` and `-cloud` as cloud; installed cloud references cannot bypass disabled cloud-provider settings. Explicit disabled providers are excluded. Desktop provider discovery now has a 3-second deadline.
- Runtime `/models/catalog` combines backend route mappings with installed Ollama metadata. Reports unknown capabilities honestly; distinguishes installed local models from unverified cloud routes. Automatic recovery uses this inventory when available, excludes embedding-only models, and checks image capability. Existing explicit custom selections remain supported. Legacy fallback remains when inventory discovery is unavailable.
- UI labels the former Tokens control as History budget. Local streams expose requested context/output budgets from the final payload; recovery forwards them and the model badge shows them in its tooltip. These are requested budgets, not guaranteed provider capacity.
- Provider/model picker toggles match request selection; cloud references in the installed list are labeled cloud.
- Practice sets distribute remainder questions across categories, returning the requested 1, 3, 5, 7, or 10 questions instead of rounding down.

Verification completed:
- 97 desktop/web unit tests passed; production web build passed.
- 90 focused backend stream/provider/limit tests passed before the runtime catalog addition.
- 44 focused backend catalog/practice/recovery/limits/readiness/route ownership tests passed after the catalog addition (4 warnings).
- Browser recovery passed partial preservation, attribution, quota cooldown, local fallback, exhaustion, visible-stream cancellation and cancellation during buffered resume verification. This browser pass preceded the final runtime catalog/discovery changes; rerun it after resuming.
- Practice count regression reproduced three failures before repair; all seven catalogue tests then passed.

Exact next step: run `qa/performance/live/remediation-check.py --output qa/performance/results/2026-09-27-remediation/live-core.json` against a freshly started isolated backend on 8046. The script now checks `/models/catalog` and the five-question practice set, but those new live checks have NOT been run yet. Then rerun browser recovery with the final build and broaden backend/browser verification. Review inventory discovery latency and unavailable-catalog fallback before declaring ANT-015 complete.

Remaining: finish ANT-015/016 verification; complete the ANT-017 feature workflow matrix, accessibility/layout checks, mobile/extension environment checks, and final live desktop review/release gates. The earlier visible Chromium startup crash is still unresolved. The earlier 30-minute soak is valid for its recorded source hashes, not proof that every subsequent edit was soak-tested.

Relevant logs in temporary storage: `/tmp/ant-model-catalog-tests.log`, `/tmp/ant-model-limits-tests.log`, `/tmp/ant-model-budget-js.log`, `/tmp/ant-model-budget-build.log`, `/tmp/ant-model-budget-recovery.log`, `/tmp/ant-practice-count-before.log`, `/tmp/ant-practice-count-after.log`. Persisted copies are under `results/2026-09-27-remediation/pause-2026-09-29/`.

Keep unrelated dirty/staged changes intact. Do not connect OmniRoute. Personal app data and credentials must remain outside QA.

## Resumed — 2026-10-02 checkpoint

Resumed the September 29 pause. The model catalog and five-question practice set now pass against a freshly isolated backend. All 11 live checks pass; catalog discovery returned 44 entries in 15 ms in the final run.

A discovery latency defect was reproduced with two failing regressions: provider key checks ran sequentially and catalog discovery inherited the ten-second model-manager timeout. Provider/Ollama probes now run concurrently; the catalog's model-list request uses a one-second timeout. Both regressions pass, as do 50 focused backend checks.

Final verification: **1,280 backend tests passed (10 warnings)**; **59 separate live API tests passed**; **97 desktop/web tests passed**; **44 Chromium/Firefox checks passed**; **34 mobile Jest tests passed**; production build and five-page browser smoke passed. Recovery passed the runtime inventory and legacy fallback paths, embedding exclusion, partial preservation, attribution, cooldown, exhaustion, recorded synthetic audio submission, and cancellation during streaming, buffered verification and delayed discovery. A five-second catalog timeout released recovery successfully. Saved-chat search/sort/pagination/deletion and 390px layout checks passed with synthetic conversations.

The first cross-browser run failed: Firefox was missing and nine workers encountered connection resets/loading-state timeouts. Firefox was installed and the full suite passed with two workers. Both logs are preserved. The full backend count before the final discovery fix was 1,278; use the 1,280 result for this checkpoint.

ANT-015/016 are verified for this controlled scope. Next is ANT-017 feature workflows, with remaining ANT-011/012 quality breadth, ANT-018 accessibility/layout, ANT-019 platform checks and ANT-020 final native desktop/release gates still open. A concrete job-tracker gap was found: clicking a card only logs details; it does not open a usable detail view. No feature-completeness or release sign-off is implied.

Details: [model/recovery checkpoint](MODEL-RECOVERY-CHECKPOINT-2026-10-02.md), [feature coverage matrix](FEATURE-WORKFLOWS-2026-10-02.md). Logs and exact source hashes: [persisted continuation evidence](results/2026-09-27-remediation/resume-2026-10-02/checkpoint.json). No commit, push, release, OmniRoute integration or access to personal app data was performed.
