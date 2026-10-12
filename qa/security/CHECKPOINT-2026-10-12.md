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
