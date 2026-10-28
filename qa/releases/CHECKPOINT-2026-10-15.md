# Main integration / release checkpoint — 2026-10-15

The user explicitly authorized integrating the tested application into main and proceeding with the release. Do not ask again for that authorization. Preserve the original workspace's unrelated uncommitted work and both existing histories.

## Pushed source

- PR: https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/25
- Integration branch: `integrate/tested-app-main`.
- History-preserving merge: `49d1e182c9e426c24ee6448765aba50d2d27a5f3`.
- Latest source/security fixes: `b2c214e121b841bbf7fc926a67380fe65a408ba0`.
- Isolated checkout: `/tmp/ant-main-review-2026-10-14`.
- Release source: `7a8552e9f5e9b7b34d3fced57d032c3363e392cb` on `release/v2.3.0-rc.1`, checkout `/tmp/ant-release-2.3.0-rc.1`.
- Remote main remains `2846154dced96f5fb73f85157639934a47001b42`. PR #25 is NOT merged. No release tag or public release has been created. The original workspace remains on ux-sprint.

## Confirmed final validation

- PR CodeQL run 38807967197 succeeded for Python, JavaScript/TypeScript and Actions. The open-alert API for `refs/pull/25/merge` returned no findings after completion.
- CI run 38807967072: backend, web/desktop/mobile, workflow validation and browser E2E jobs all passed. Vercel preview passed. Python audit reports no known vulnerabilities; root npm audit is clean.
- CI security job fails ONLY on one historical secret. This is a real unresolved credential finding, not a scanner crash or a false positive.
- Local integration: 1,647 backend tests passed, 59 skipped; 179 desktop tests, 15 web tests, eight security regressions and production web build passed.
- Release build 38804653301 passed all four native platforms and packaged runtime/sign-in/storage checks. Artifacts are available for darwin-arm64, darwin-x64, linux-x64 and win32-x64, with runtime audit reports. Use these verified native builds; do not distribute the earlier local x64 ZIP with an ARM runtime.

## Remaining credential blocker

The replaced Gitleaks action could not handle a range starting before a root commit. The new checksum-pinned scanner examines both reachable histories and merge resolutions (325 commits / approximately 36.74 MB in hosted CI).

It found a historical Ollama Cloud API key in `backend/.env`, line 10, commit `d854fcbe98d3358b74f80ee9b0247737f8906580`. Its revocation is unverified. The user was asked through an asynchronous question whether it has been revoked; no answer was received before this checkpoint. Do not treat elapsed time as confirmation. Do not print the key or use it to authenticate.

Google and GitHub credentials from that same commit have exact matching GitHub secret-scanning alerts #1 and #2, both resolved with reason `revoked`. Those exact fingerprints are documented as revoked credentials, not false positives. Five additional exact fingerprints are known documentation placeholders. The one unresolved Ollama fingerprint is intentionally NOT ignored.

Evidence is committed in `qa/security/HISTORICAL-SECRETS-2026-10-15.md`. Redacted local reports: `/tmp/ant-main-final-secrets.json`, `/tmp/ant-main-final-security-job.log`. No broad secret-detector exclusions or history rewrites were performed.

## Resume after revocation confirmation

1. Record the evidence for the Ollama revocation. If the user confirms it, document that it is user confirmation rather than an independent provider validation. Add only the exact historic fingerprint `d854fcbe98d3358b74f80ee9b0247737f8906580:backend/.env:generic-api-key:10` to the revoked-credential section of `.gitleaksignore`.
2. Run the pinned complete-history scan, push the reviewed change, and verify fresh CI and CodeQL results for PR #25. Do not bypass the failing security check.
3. Merge normally with the checked head SHA, preserving both histories. Verify remote main and default-branch alert results; the last push still reported the old main's 50 Dependabot alerts, which cannot yet be claimed closed.
4. Preserve the original dirty ux-sprint workspace. Local main has a separate old history; save a backup branch before moving that local ref. Prefer the isolated checkout for main work.
5. Tag verified main as `v2.3.0-rc.1` only if the tag does not exist. The release workflow builds four native targets, verifies the six-installer set, generates SHA256SUMS and creates a draft. Review actual assets before publishing as a prerelease.

Cloud/low-severity and optional voice-runtime review remains pending. Cloud provisioning and deployment notifications require opt-in variables and were not enabled. This work does not certify legacy extensions, live audio/provider behavior, code-signing/notarization or universal screen-capture invisibility.
