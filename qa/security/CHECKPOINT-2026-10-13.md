# Repository remediation checkpoint — 2026-10-13

Work continues on `ux-sprint`. The repository is not yet clean; no alerts have been dismissed and query coverage has not been reduced. See [the previous checkpoint](CHECKPOINT-2026-10-12.md) for earlier fixes.

## Hosted results

- d6f0053: CI 38304398776 and CodeQL 38304399206 pass. Fixed search URLs/query parameters resolve the shared-client SSRF alert; the separate Jira alert remains under review.
- 348ab9e: CI 38355892250 and CodeQL 38355892990 pass. The scan reports 146 findings (105 Python, 41 JavaScript, zero Actions), down from 161 before the ingestion/import batch and 494 in the expanded baseline.
- Main still has 50 dependency alerts (1 critical, 27 high, 20 moderate, 2 low), as reported on the last push. Branch fixes require review, merge and a main rescan before those alerts can clear.
- The hosted Bandit report has no high findings. Its four medium findings are trusted-source `exec` calls in three test modules. A wider local scan accidentally included installed voice-runtime dependencies; filtering that report to tracked application source yields zero high/medium and 66 low findings. That does not establish the installed voice runtime's dependency-audit status.

## Reviewed browser batch

- Restoring a saved cloud model now respects the provider's explicit disabled setting, even when a key is available. Six regressions cover enabled/disabled/unset preferences for a hosted provider and Ollama Cloud.
- Resume-review and interview-simulator controllers are explicitly exposed on `window`, matching their HTML button handlers. Removed unused imports/local bindings in browser, extension, desktop and development helper code while retaining constructor initialization, API calls and active capture protection.
- Clean reviewed copy: 15 web tests, 175 desktop tests, production build, all five production-page smoke checks and 44 Chromium/Firefox E2E tests pass. Tests used synthetic data and an isolated backend; no desktop-app relaunch or capture occurred.
- Local evidence: `/tmp/ant-oct13-browser-reviewed-{checks,smoke,e2e}.log`; reviewed copy path is recorded in `/tmp/ant-oct13-browser-reviewed-path`.

## Remaining work

- Review the remaining code-scanning and low-severity Bandit findings, including the Jira custom transport and cross-script JavaScript references.
- Review the pending authentication consolidation: several committed route wrappers call the asynchronous user lookup without awaiting it. Working-tree replacements already use the shared awaited dependency; these need a focused review and clean-source verification before inclusion.
- Other infrastructure edits remain unstaged; the last broad cloud policy scan had 36 failures. No cloud plan/apply, production deployment or main merge has been performed.
- Preserve the existing unrelated working-tree changes. Stage only reviewed files or selected hunks. Lovable website work remains for later.
