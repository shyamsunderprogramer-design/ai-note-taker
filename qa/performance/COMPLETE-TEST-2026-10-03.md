# Comprehensive test checkpoint — October 3, 2026

Testing found product failures. This is not release sign-off. Test workloads were stopped after the user reported the live app was unresponsive. The desktop was reopened and Settings open/close and input focus were verified; the exact reported action is still unconfirmed.

## Passing evidence

- Backend: 1,280 tests; desktop/web units: 97; mobile Jest: 34.
- Fresh isolated API integration: 59 passed. An earlier run was interrupted because a document-upload workflow froze its server.
- Chromium/Firefox: final controlled run 44 passed. Initial run: 43 passed, one connection-reset failure. Both logs preserved.
- Production build, five-page browser smoke, recovery and saved-history acceptance passed.
- Thirty-minute synthetic local interview: 60/60 answers, 20/20 injected recoveries, zero health failures. End-to-end median 3.54 seconds, p95 8.25 seconds, maximum 16.67 seconds. Synthetic file transcription, not a microphone/meeting test.
- Synthetic process-only OS loopback audio capture passed with nonzero audio and no helper errors.
- Actual sign-in, seven settings tabs, JD persistence, browser-local study completion, injected microphone denial and 18 page/viewport overflow checks passed in the deeper browser pass (see raw results for exact scope).
- Conversation persistence across server restart and logout-token invalidation passed. These do not imply job/study persistence.

## Confirmed failures

1. Document upload never finishes: the text chunk loop repeats its final overlapping chunk, blocking the async route and even health checks. Isolated server had to be stopped.
2. A second synthetic account can read the first account's job application. Invalid job stages also return success.
3. Jobs disappear after a restart of the same backend/data directory. Missing application is returned as an error object with HTTP 200.
4. Fetching a personalized three-day study plan regenerates a default 30-day plan. Completing tasks reports success without server-side persistence; nonexistent tasks also report success. Browser-local completion works separately.
5. Job creation from the UI fails against configured nondefault API URLs because automatic auth-header injection recognizes only port 8000. Form notes are not submitted, job-card details only log to console, and unavailable backend is presented as an empty job list.
6. The productivity extension does not install with its original manifest. A disposable copy removing only the invalid `careers.*.com` host wildcard installed and opened successfully; original product files were not changed.
7. Job Capture installs, extracts a supported synthetic job page, validates empty input and persists extension storage, but crashes when the active tab URL is unavailable.
8. Accessible-name precheck found unnamed controls on the main and resume-review pages. This is a precheck, not a full accessibility-conformance audit.

## Remaining limits

Native screen capture/OCR and all native overlay/window controls were not completed in this pass. The microphone participation question is pending. Mobile emulators are unavailable (full Xcode/simctl and Android tooling missing). External-account integrations and voice-clone training remain unverified. The real app's earlier long visible wait is not explained by its displayed 3.5-second inference badge.

Raw evidence: [summary](results/2026-10-02-complete/summary.json), [API workflows](results/2026-10-02-complete/api-workflows.json), [restart checks](results/2026-10-02-complete/persistence.json), [browser workflows](results/2026-10-02-complete/browser-workflows.json), [extensions](results/2026-10-02-complete/extensions.json), [soak](results/2026-10-02-complete/interview-soak.json).

No product repairs, commit, push or release performed during this test pass. New files are QA harnesses and evidence. Personal records were not used for destructive tests.
