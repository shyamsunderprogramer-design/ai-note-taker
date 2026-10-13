# Repository remediation checkpoint — 2026-10-13

Work continues on `ux-sprint`. The repository is not yet clean; no alerts have been dismissed and query coverage has not been reduced. See [the previous checkpoint](CHECKPOINT-2026-10-12.md) for earlier fixes.

## Hosted results

- d6f0053: CI 38304398776 and CodeQL 38304399206 pass. Fixed search URLs/query parameters resolve the shared-client SSRF alert; the separate Jira alert remains under review.
- 348ab9e: CI 38355892250 and CodeQL 38355892990 pass. The scan reports 146 findings (105 Python, 41 JavaScript, zero Actions), down from 161 before the ingestion/import batch and 494 in the expanded baseline.
- d069f71: CI 38358275903 and CodeQL 38358275825 pass. The scan reports 121 findings (105 Python, 16 JavaScript, zero Actions) after the reviewed browser batch.
- Main still has 50 dependency alerts (1 critical, 27 high, 20 moderate, 2 low), as reported on the last push. Branch fixes require review, merge and a main rescan before those alerts can clear.
- The hosted Bandit report has no high findings. Its four medium findings are trusted-source `exec` calls in three test modules. A wider local scan accidentally included installed voice-runtime dependencies; filtering that report to tracked application source yields zero high/medium and 66 low findings. That does not establish the installed voice runtime's dependency-audit status.

## Reviewed browser batch

- Restoring a saved cloud model now respects the provider's explicit disabled setting, even when a key is available. Six regressions cover enabled/disabled/unset preferences for a hosted provider and Ollama Cloud.
- Resume-review and interview-simulator controllers are explicitly exposed on `window`, matching their HTML button handlers. Removed unused imports/local bindings in browser, extension, desktop and development helper code while retaining constructor initialization, API calls and active capture protection.
- Clean reviewed copy: 15 web tests, 175 desktop tests, production build, all five production-page smoke checks and 44 Chromium/Firefox E2E tests pass. Tests used synthetic data and an isolated backend; no desktop-app relaunch or capture occurred.
- Local evidence: `/tmp/ant-oct13-browser-reviewed-{checks,smoke,e2e}.log`; reviewed copy path is recorded in `/tmp/ant-oct13-browser-reviewed-path`.

## Reviewed authentication and database diagnostics batch

- Eleven route modules now use the shared authentication dependency, which awaits the user lookup. Their old wrappers could treat an unresolved coroutine as an authenticated user. Regression checks cover missing, invalid and valid tokens, the admin role check and the actual BYOK status endpoint.
- `/health/config` and `/health/db-debug` now require an authenticated admin, including removal from the public-path allowlist. Diagnostic URLs contain only the database dialect and a redaction marker; credentials, query parameters and local paths are not returned.
- The database probe shares verified PostgreSQL TLS settings with normal connections, bounds the connection/query probe to five seconds and disposes its temporary engine on success, failure or cancellation. Errors return HTTP 503 without raw exception details. URL classification uses the scheme, preventing a PostgreSQL password or database name containing `sqlite` from selecting SQLite behavior.
- Clean reviewed source passes 1,463 backend tests (59 skipped, no warnings) and all 44 Chromium/Firefox E2E tests. Focused authentication/TLS/diagnostic checks: 81 passed. Synthetic fixtures and an isolated backend were used; database failure/TLS probes use mocked connections.
- Local evidence: `/tmp/ant-oct13-access-reviewed-{focused,backend,e2e}.log`; export path is recorded in `/tmp/ant-oct13-access-reviewed-path`. Hosted CI and CodeQL results for this batch are pending.

## Remaining work

- Review the remaining code-scanning and low-severity Bandit findings, including the Jira custom transport and cross-script JavaScript references.
- Recheck hosted CI/CodeQL after pushing the authentication and diagnostics batch, then review the remaining source and dependency findings.
- Other infrastructure edits remain unstaged; the last broad cloud policy scan had 36 failures. No cloud plan/apply, production deployment or main merge has been performed.
- Preserve the existing unrelated working-tree changes. Stage only reviewed files or selected hunks. Lovable website work remains for later.
