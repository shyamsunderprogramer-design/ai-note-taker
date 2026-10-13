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

Hosted follow-up: CI 38260850651 passes all four jobs on 0ca9a01; CodeQL 38260686153 succeeds and reports 224 open branch findings. Remaining infrastructure and scanner findings are still unfinished.

## Browser cleanup and keyboard access

- Removed verified unused browser helpers and local bindings after checking repository consumers; retained active live-question and streaming helpers.
- Enter preserves native activation for information/settings buttons and links. On focused Live helper/recording controls during a unified session, Enter still requests assistance without stopping listening. Typed questions remain independent of listening.
- Added page language, input/select labels, a skip link, visible keyboard focus and 24px hit areas around small header icons. The app keeps its existing visual theme; light/dark OS preference does not force a new theme.
- Clean reviewed export: 175 desktop tests, 5 web tests, production build and all five production-page smoke checks pass. Chromium/Firefox E2E: 44 passed using isolated backend data and local ports. Smoke checks cover real Enter activation, Escape/focus restoration and the skip link. Corrected old smoke assumptions about gentle scrolling and typed Enter rather than changing those existing behaviors.
- Axe WCAG 2.2 confirmation: zero violations in four combinations (390x844 and 1440x900, each with light/dark OS preference); synthetic-data screenshots manually inspected. Private evidence: /var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-ui-security-JCDHQf. No desktop-app capture, relaunch or live user backend was used.

This browser batch requires its own hosted CI and CodeQL confirmation after push. Repository remediation is not complete.

## Recording deletion and database error handling

- Browser commit 98546ec: hosted CI 38265886930 passes all four jobs; CodeQL 38265887891 succeeds, with 205 open branch findings.
- Recording deletion removes media before metadata, retains the session when filesystem deletion fails, and tolerates already absent files so retries can finish. It no longer reports success with retained recording files.
- The deletion endpoint returns real HTTP 500/503 responses with structured errors. The shared error_response helper currently returns a dictionary and ignores its status_code argument; other endpoints using that helper still require review.
- Database initialization and cleanup/secret-decode diagnostics use static messages, preserving original exceptions to callers without copying connection secrets into logs.
- Clean staged export: 1,364 backend tests passed, 59 skipped, no warnings. Recording retry/media/metadata and real endpoint status regressions pass. Bandit: zero high/medium, 66 low findings remain.
- Pre-existing storage-directory changes were preserved and excluded from this commit. No files belonging to real recordings or deployed databases were deleted during testing.

Repository remediation remains ongoing: 205 scanner findings before this batch, shared error-response status handling, low-severity Bandit findings and cloud template checks are not yet complete.

## Shared HTTP error contract

- CodeQL rescan 38266945392 succeeds on 0dab86f: 201 open branch findings. CI 38266945129 was still running when this checkpoint was written.
- Fixed the shared error_response helper to return JSONResponse with the requested status and JSON-compatible encoded details. The existing structured error body is preserved; optional extra fields support Ollama's empty models list without replacing the error object.
- Reviewed all tracked backend callers: direct returns, four dictionary unions (main/route Ollama handlers) and three nested recording responses. Unions and nested responses now use the supported helper interface.
- Tests verify actual HTTP statuses 400/401/403/404/409/413/422/429/500/502/503, content type, datetime/UUID details and extra-field behavior through FastAPI.
- Clean reviewed source: 1,376 backend tests passed, 59 skipped, no warnings. Full workspace: 1,421 passed, 59 skipped. Isolated Chromium/Firefox E2E: 44 passed.
- Success response behavior is unchanged. API consumers now receive actual failures instead of HTTP 200 containing an error body; callers should already handle response.ok/status. No production deployment or main merge was performed.

Outstanding: remaining CodeQL findings, low Bandit findings, cloud templates and main-branch dependency alerts.

## Verified import cleanup

- Removed 21 unused bindings from agent orchestration/coaching, entity extraction, question-library compatibility, voice transcription, CRM encryption, and request validation/rate limiting. Imported modules still initialize normally; active classes, helpers and compatibility names remain. Whole-repository consumer searches found no callers of the removed bindings.
- Ruff F401 confirmation passes on the ten changed files. Clean reviewed backend suite: 1,376 passed, 59 skipped, no warnings. No tests were weakened or security-query coverage changed.
- Shared HTTP error batch is pushed as cf64484; its hosted CI/CodeQL were pending at this checkpoint. Further CodeQL, low Bandit and infrastructure remediation remains outstanding.

## Azure configuration review

- Hosted application batches all pass CI and CodeQL: 0dab86f (CI 38266945129), cf64484 (38267597720), 84c8718 (38268956588). CodeQL 38268958114 succeeds on 84c8718 and reports 185 open branch findings.
- Azure Kubernetes/Helm providers use kubelogin Entra tokens with local AKS accounts disabled, replacing incompatible certificate credentials. Deployment RBAC is scoped to the cluster and ordered before Helm; empty optional admin groups are filtered. The Azure CLI/automation identity must match the AzureRM principal. Live authentication/role propagation was not tested.
- Retired hardcoded AKS 1.29 becomes an optional validated version input; new clusters can use the service default. Input checks accept 1.35/1.35.7 and report validation errors for invalid values. Service/DNS addresses now avoid the existing 10.0.0.0/8 VNet. Existing-cluster service-range changes may require replacement; deployment/migration review is required before applying.
- Updated deprecated storage HTTPS and subnet policy arguments. Replaced retired Monitor log profiles with subscription diagnostics using supported categories and a 365-day base-blob lifecycle policy. A removed block retains the old resource; check existing diagnostics to avoid duplicate collection/cost. No snapshot/version cleanup was added.
- Exact staged Azure configuration: Terraform validation returns zero errors and warnings using installed AzureRM 3.117.1/Kubernetes 2.38.0/Helm 2.17.0 providers. Documentation covers kubelogin prerequisites and migration limits. No cloud plan, apply or deployment was run.
- Other AWS/Azure/GCP hardening edits remain unstaged and unfinished; the last wider cloud policy scan still has 36 failures. This validation does not prove a deployment works or the cloud templates are fully hardened.

Remaining work includes 185 CodeQL findings, 66 low Bandit findings, other cloud checks and main-branch dependency alerts. The repository is not yet clean.

## Browser success/failure states

- Model-download acknowledgments say download started, not completed. HTTP/body errors retain the model input and restore controls for retry. Suggestion accept/dismiss requests check HTTP status before changing the card. Four failure/acknowledgment regressions pass.
- Removed seven verified uncalled legacy browser helpers/maps and six dead local bindings/empty-loop entries, retaining current chat history rendering, code-copy delegation, live question cutting and streaming updates. Updated two test source-extraction boundaries after removing legacy helpers; behavior assertions are unchanged.
- Clean reviewed source: 9 web tests, 175 desktop tests, production build, five production-page smoke checks and 44 Chromium/Firefox E2E tests pass. Workspace includes additional pre-existing tests (13 web, 176 desktop), also passing after boundary updates. No live backend/user recordings or desktop captures were used.
- Azure source batch is pushed as 918aa69; CI/CodeQL confirmation pending. Other cloud hardening edits remain unstaged.

Remaining scanner, infrastructure and main-branch dependency work is not complete.

## Fixed search URLs and client cleanup

- Hosted CI 38279237238 passes all four jobs on 47f8782; CodeQL 38279237449 succeeds and reports 168 open branch findings. Azure CI 38276125560 and CodeQL 38276125146 also pass on 918aa69.
- The Python SARIF report traces the shared-client partial SSRF finding to Brave search query/count interpolation in both search endpoints. Both now use the fixed provider URL and HTTPX query parameters; result counts are validated from 1 through 20. Fourteen isolated regressions verify special characters, embedded URLs, parameter boundaries and rejection of invalid counts before any provider request.
- Removed unused mobile imports and unused desktop IPC/platform/timer state. Kept Electron's app import: the tray Exit callback uses it. Existing mobile/desktop suites passed (34/176 cases); an additional undefined-name check passes for the reviewed desktop file. This cleanup does not change capture-protection behavior.
- Jira's separate partial SSRF finding remains under investigation. Its HTTPS-only URL validation and DNS-to-numeric-address connection guard are retained. No alerts were dismissed or query models added to hide the findings.

The two search files contain other pre-existing feature work; only the reviewed query-parameter/count changes are staged. Other code-scanning findings, infrastructure checks and main-branch dependency alerts remain unfinished.

## Document ingestion retries and stable question banks

- d6f0053 passes hosted CI 38304398776 and CodeQL 38304399206. The shared HTTP-client SSRF alert is resolved; 161 branch findings remain, including the separate Jira finding.
- Document imports mark content as loaded only after successful storage or an already-existing result. Failed QA/PDF imports remain retryable. Temporary staging now handles CI/CD categories, Windows-style paths and long Unicode filenames inside a private directory, preserves the text extension, and cleans derived sidecar files. Cleanup errors return a failure without logging source text, filenames or raw exceptions.
- Question-bank initialization copies the bulk coding/design lists before adding expansion questions. Repeated construction no longer grows the shared data or duplicates the resulting indexes; optional bank import failures emit static debug diagnostics.
- Removed verified unused imports in nine analytics, graph, authentication, voice and AI route modules after checking tracked Python consumers. The shared AI route file retains unrelated unstaged feature changes.
- Clean reviewed backend suite: 1,402 passed, 59 skipped, no warnings. Twelve ingestion/question-bank regressions cover failed-import retries, deduplication after success, confined staging, sidecar cleanup, failure reporting and stable repeated initialization. Undefined-name checks pass for the reviewed modules.

The Jira scanner review, other quality/security findings, cloud checks and main-branch dependency alerts are still outstanding. No main merge or production deployment has occurred.
