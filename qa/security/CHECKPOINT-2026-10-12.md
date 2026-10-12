# Repository remediation checkpoint — 2026-10-12

Work continues on `ux-sprint`; the whole repository is not yet clean. No alerts were dismissed or query coverage reduced.

## Hosted baseline

- CI run 38255373262 passes backend, web, security and Chromium/Firefox E2E on 3c33957.
- CodeQL run 38038466821 succeeds on the same commit: 287 open branch findings, down from the expanded 494-finding baseline. Two SSRF transport-model findings remain under review.

## Reviewed application batch

- Voice subprocess cleanup runs in `finally`. Timeout and cancellation tests launch a real child process and verify it is reaped; partial voice registrations are removed on unsuccessful creation.
- Removed dead local assignments and duplicate standard-library imports, preserving authentication and connection-check calls. Other feature edits in shared files are not staged.
- Optional AI import failures emit static debug diagnostics. Standard-library logging initializes normally in the voice module.
- Transcription debug logs record character counts, not spoken content. Removed an obsolete test requiring a dead 45-word variable; existing VAD boundary tests remain.
- The standalone backend launcher defaults to 127.0.0.1. Remote binding requires an explicit --host; both behaviors are tested.
- Starlette's supported httpx2 client is pinned in test requirements. Application network transports continue using httpx.

## Validation

- Clean reviewed source: 1,338 backend tests passed, 59 skipped, no warnings after the test-client update. Workspace source before the final import cleanup: 1,381 passed, 59 skipped.
- Full disposable Python test environment: zero known dependency vulnerabilities, including the new httpx2/httpcore2 packages.
- Backend Bandit application scan: zero high/medium findings; 70 low findings still require review.
- Syntax and undefined-name checks pass for the duplicate-import changes.

## Infrastructure and remaining scope

Infrastructure changes remain in the working tree for a separate review. Azure's retired Monitor log-profile resource was replaced by subscription diagnostic settings and storage lifecycle retention; a removed block preserves existing resources when retiring the old state entry. Azure validation now reports zero errors and warnings. No cloud plan, apply or deployment was performed.

Remaining CodeQL findings, low-severity Bandit findings and cloud security checks are unfinished. Branch fixes do not clear main-branch alerts until reviewed changes are merged and rescanned. Lovable is reserved for later website work.

## Database, network and webhook follow-up

- Hosted CI 38257905482 passes all four jobs on d049035. CodeQL 38257878473 succeeds and reports 245 open branch findings, down from 287.
- Manual review found PostgreSQL TLS contexts with certificate/hostname verification disabled. Initialization now uses verified TLS, supports DATABASE_SSL_CA_FILE for private CAs, preserves non-SSL query options, and fails before connecting when CA configuration is invalid. Database logs no longer print connection URLs. Existing servers with private/self-signed certificates must configure their trusted CA before restarting; see docs/backend/DATABASE_TLS.md.
- Local-use NAT64 (64:ff9b:1::/48) is rejected despite older Python classification. Literal URL, sync DNS and async DNS regressions verify no connection occurs. All 37 network tests pass.
- API-key loading preserves task cancellation and fails safely on decrypt errors; raw exception contents are not logged. Six database TLS/key-loading cases pass.
- Webhook management requires authentication and isolates subscriptions by owner. Signing secrets are accepted in JSON bodies instead of query strings, IDs use full UUIDs, listing omits secrets, and test responses describe a preview rather than claiming delivery. Six webhook access/control regressions pass; no webhook requests were sent externally.
- Alembic's dynamically loaded metadata and entry points are explicitly exported; the real Alembic loader still finds all three revisions and the correct head. Dead warmup/cache/event-log state was removed after checking repository consumers.
- Final clean reviewed backend suite: 1,356 passed, 59 skipped, no warnings. Updated Bandit: zero high/medium findings and 69 low findings requiring review.

The follow-up needs a hosted run and CodeQL rescan after push. Remaining infrastructure and scanner findings are still unfinished.
