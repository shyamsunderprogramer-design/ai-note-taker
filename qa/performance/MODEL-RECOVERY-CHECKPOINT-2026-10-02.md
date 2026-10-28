# Model discovery and recovery checkpoint — October 2, 2026

The September 29 live-verification checkpoint is complete for the controlled scope below. The overall remediation plan is still in progress.

## Repair

Catalog discovery previously checked eight provider keys sequentially and reused a ten-second Ollama model-list timeout. Either could outlast the browser's five-second discovery deadline. Independent provider/health probes now run concurrently, and the catalog's model-list request has a one-second timeout. Interactive model management retains its existing timeout. Metadata discovery remains bounded to sixteen local models and eight workers; no cloud inference or model download is triggered.

Two new regressions failed before repair and passed afterward. These request timeouts are not a universal end-to-end latency guarantee. The browser deadline still provides fallback if discovery exceeds its budget.

## Verification

| Check | Final result | Scope |
|---|---|---|
| Full isolated backend + startup | 1,280 passed, 10 warnings | Excludes separate API suite |
| Live API integration | 59 passed | Disposable server/account/database |
| Desktop/web unit tests | 97 passed | Existing unit suite |
| Chromium + Firefox | 44 passed | Two workers; real feature pages, mostly smoke coverage |
| Mobile | 34 passed / 5 suites | Jest, not a device/emulator |
| Production web | Build and five-page smoke passed | Existing classic-script build warnings remain |
| Live core checks | 11 passed | Catalog, practice count, readiness, auth and pagination |
| Recovery browser | Passed | Synthetic providers through production recovery endpoint |
| History browser | Passed | Synthetic conversations; search, sort, pagination, keyboard, deletion and 390px layout |

Do not sum overlapping focused and full-suite counts. The earlier full checkpoint had 1,278 passes; the final count includes both new discovery regressions.

The final live catalog returned 44 entries in 15 ms. Liveness during optional-module checks took 4 ms. These are individual local observations, not p95 performance claims.

Recovery coverage includes runtime inventory, embedding exclusion, unavailable-catalog fallback, a full catalog timeout, partial preservation, provider attribution, cooldown, local fallback, exhaustion, synthetic audio submission, and replacement of an older question during streaming, buffered verification and delayed discovery.

The first browser run failed because Firefox was missing and the default nine-worker run hit connection resets/loading-state timeouts. After installing Firefox and explicitly using two workers, all 44 checks passed. Initial failures remain in the evidence folder.

## Reproduction

Run commands from the repository root. Local servers/browser processes require permission outside restricted execution environments.

```sh
AINT_Venv/bin/python qa/performance/backend/isolated.py serve --port 8046
AINT_Venv/bin/python qa/performance/live/remediation-check.py --output qa/performance/results/2026-09-27-remediation/live-core.json
AINT_Venv/bin/python qa/performance/backend/isolated.py test tests/test_api_integration.py -q
AINT_Venv/bin/python qa/performance/backend/isolated.py test tests core/test_startup.py --ignore=tests/test_api_integration.py -q
node --test electron/tests/*.test.js apps/web/tests/*.test.mjs
npm run web:build
AINT_Venv/bin/python qa/performance/live/recovery-server.py
node qa/performance/web/recovery.mjs
node qa/performance/web/browser-smoke.mjs
node qa/performance/web/history-panel.mjs
node node_modules/playwright/cli.js test --config=e2e/playwright.config.js --workers=2 --reporter=line
npm run mobile:test -- --runInBand
```

Run server commands in separate terminals. The direct Playwright command is intentional: the root npm wrapper consumed the supplied worker/reporter arguments instead of forwarding them.

Logs and source hashes are saved in [continuation evidence](results/2026-09-27-remediation/resume-2026-10-02/checkpoint.json). The isolated servers use disposable data and omit personal credentials.

## Still open

See the [feature workflow matrix](FEATURE-WORKFLOWS-2026-10-02.md). Native OS capture, meeting/microphone behavior, live cloud quota/capacity, external integrations, mobile emulators and the latest revision's long-duration soak are not certified by this checkpoint. The original visible-browser crash has not been independently resolved by these headless checks. No commit, push or release was performed.
