# Published testing prerelease — 2026-10-17

The authorized main integration and testing release are complete. [ANT v2.3.0-rc.1](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/tag/v2.3.0-rc.1) was published on October 17, 2026 at 20:09:13 UTC. The user confirmed removing the earlier exposed Ollama key and retaining the replacement used by ANT. Revocation is recorded as user confirmation, not independent provider validation.

## Current GitHub status

- New public testing prerelease: [v2.3.0-rc.1](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/tag/v2.3.0-rc.1), release ID `416025668`. The API confirms `draft: false`, `prerelease: true`, and seven uploaded assets (six installers plus checksums). Stable Latest remains [v2.2.0](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/tag/v2.2.0), as intended. The existing v2.2.1 and v2.2.3 entries remain drafts.
- [PR #25](https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/25) was merged normally on October 17 at 19:31:43 UTC after every check passed for head `14b2ec17bff1a1a91e5049d8bccf7261846d705d`. PR CI: 39060390838; CodeQL: 39060390824; zero open PR CodeQL findings.
- Remote main is now `b16e551331a6387286ff754de0accc7ef7d9d7f4`. Its tree exactly matches the tested PR head, and both original histories are confirmed ancestors. Main CI 39062856695 and CodeQL 39062856718 passed. Security workflow 39062856782 also completed, but its advisory cloud/low-severity results are not all clean; do not equate a green workflow with zero findings.
- Main has no open CodeQL findings. The final queries returned 62 Bandit and 77 Checkov findings. Dependabot's open count fell from 50 to 16 (one critical, nine high, six medium); do not claim that all dependency alerts are closed. The sampled AnyIO and urllib3 alerts still referenced older state although current manifests pin their exact first-patched versions, `4.14.2` and `2.8.0`. Other remaining alerts were not individually reconciled in this release task. Fresh CI and native-build dependency audits passed.
- Local old main `5b4055cb6d996959a90a555389fa85171eac7b3b` is preserved as `backup/main-before-integration-2026-10-17`. The isolated checkout `/tmp/ant-main-review-2026-10-14` is now on main. The original workspace remains on ux-sprint with its pre-existing uncommitted work preserved.
- Annotated tag `v2.3.0-rc.1` points to verified main `b16e551331a6387286ff754de0accc7ef7d9d7f4`; its tag-object SHA is `5fe72daa2bf6ea26433e9acbed976ab664373c63`. Final native [release build 39063676159](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/39063676159) passed on all four platforms and assembled the verified draft. Only artifacts from this tagged build were published.

## Published asset verification

All four native jobs passed JavaScript and bundled Python dependency audits, actual packaged-runtime imports, backend health, registration, login and writable user-data storage checks. Final runtime reports contain 95 dependencies on Apple Silicon, 97 on Intel Mac, 95 on Linux and 134 on Windows, with zero reported vulnerabilities on every platform.

The exact published installer set is:

- `ANT-Setup-2.3.0-rc.1-win-x64.exe`
- `ANT-2.3.0-rc.1-win-x64.exe`
- `ANT-2.3.0-rc.1-linux-x86_64.AppImage`
- `ANT-2.3.0-rc.1-linux-amd64.deb`
- `ANT-2.3.0-rc.1-mac-arm64.zip`
- `ANT-2.3.0-rc.1-mac-x64.zip`

Downloaded `SHA256SUMS.txt`, verified its own GitHub upload digest, and matched every installer checksum against GitHub's independently reported SHA256 upload digest. Verified positive asset sizes, completed upload states, exact installer coverage, and release notes matching the reviewed source. Installer payloads were not downloaded locally during this verification. After publication, repeated digest verification and confirmed the same release ID, asset IDs, sizes, hashes and notes were preserved.

Final evidence is under `/tmp/ant-final-rc-1-review/`: checksum manifest, `asset-verification.json`, `published-asset-verification.json`, `runtime-audit-summary.json`, and all four `runtime-audits/` reports. Draft and public metadata snapshots are `/tmp/ant-rc-1-release-draft.json` and `/tmp/ant-rc-1-release-published.json`. The verifier is `/tmp/ant-verify-rc-assets-2026-10-17.py`.

The release remains a testing candidate. The published notes disclose absent Apple notarization/Windows publisher signing, target-device audio/provider testing requirements, and remaining cloud-template, low-severity and optional-runtime review. Cloud provisioning and deployment-notification opt-ins were not enabled.

## Earlier native build evidence reviewed

[Release build 38804653301](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/38804653301) passed on all four platforms at release-branch commit `7a8552e9f5e9b7b34d3fced57d032c3363e392cb`. Each platform passed its actual packaged-runtime and sign-in checks. All four installer artifact groups remain available.

Downloaded and inspected the existing build's bundled-runtime audit reports:

| Platform | Dependencies in report | Reported vulnerabilities |
| --- | ---: | ---: |
| Apple Silicon Mac | 95 | 0 |
| Intel Mac | 97 | 0 |
| Linux x64 | 95 | 0 |
| Windows x64 | 134 | 0 |

Reports are under `/tmp/ant-release-resume-2026-10-17/runtime-audits/`. These are the October 15 build reports, not new October 17 vulnerability scans. This earlier review is superseded for publication by the final tagged-build verification above.

## Credential revocation and completed integration

The historical Ollama Cloud key from `d854fcbe98d3358b74f80ee9b0247737f8906580:backend/.env:generic-api-key:10` is recorded as revoked based on user confirmation. Commit `14b2ec17bff1a1a91e5049d8bccf7261846d705d` added only that exact historical exception and updated the evidence. The local full-history scan passed: 324 commits, approximately 29.36 MB, zero unexcepted findings. Reports: `/tmp/ant-revocation-2026-10-17-gitleaks.{log,json}`. Fresh PR and main CI, including secret scans, passed, and integration is complete.

All release steps are complete: fresh PR and main checks, history-preserving merge, four native tagged builds, packaged-runtime checks, draft review, checksum verification and public prerelease publication. Broader security review remains unfinished as recorded above; do not claim the entire repository is free of findings.

The user subsequently explicitly asked to delete the exposed key first and finish the release. This authorizes revoking that credential, but is not confirmation that it has been revoked. A value-only comparison, without printing either credential, found that the original workspace's configured Ollama key differs from the historical exposed key. Neither isolated release/integration checkout has `backend/.env`, and that file is absent from the current tracked release source. Do not delete the different replacement key.

No Ollama browser-session handle was found through the available connector. macOS denied Apple Events access to Google Chrome with error `-1743`, preventing account automation. Opened `https://ollama.com/settings/keys` in the user's browser and asked the user to revoke the exposed old key and confirm. The user subsequently confirmed: “i removed erlier one now is present i used in ant”. No provider key was deleted by the agent, and no Git history was rewritten. No further revocation confirmation is needed.

## REA request

REA was already installed and configured before this request. The existing user skill is `/Users/shyamsunderd/.agents/skills/reverse-engineer-anything/SKILL.md`; all seven installed files exactly match the bundled skill in `rea-agents@6.5.0`. Its version is 42. The existing Codex MCP registration uses `npx -y rea-agents@6.5.0 mcp`. The scoped doctor check passed for Node and Codex registration and reports the skill aligned. No duplicate installation or configuration change was needed.

REA tools are not connected in this active session; restart/reconnection is needed to load the existing MCP registration. Native decompilation engines are absent, which does not prevent REA's static JavaScript/Electron workflows. Use REA when shipped-artifact or runtime evidence helps, as requested, and normal repository tools for source analysis. No REA target analysis was performed.

## Repository homepage update — 2026-10-17

- User requested the new release on the main GitHub repository page. Published the README release callout, six direct installer links and SHA256SUMS.txt in PR #52: https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/52.
- Documentation commit: `20d9542ac213875dd4f1a8af47e65b6d68ce7662`; main merge: `c0e077b0ecc7170895355e2c84f65727bbf2896c` at 22:08:36 UTC.
- Only README.md changed. Corrected stale v2.1.0 download text and macOS DMG instructions; documented current ZIP assets and macOS 14 minimum.
- PR CI `39073549375` and CodeQL `39073549342` passed. All seven asset URLs matched the published release. GitHub Markdown rendering and the actual public repository homepage were verified. Published README exactly matches the reviewed file.
- Release `v2.3.0-rc.1` remains a public testing prerelease at the original `b16e551` tag target with seven assets. The right-hand stable Latest label remains v2.2.0; the new download section is visible on the repository homepage.
- Evidence: `/tmp/ant-homepage-published-readme-2026-10-17.md`, `/tmp/ant-homepage-public-2026-10-17.html`, `/tmp/ant-homepage-release-2026-10-17.json`.

## Latest sidebar selection — 2026-10-17 (supersedes earlier sidebar status)

- User clarified that they want the right-hand Releases/Latest box to show the new version. Set release 416025668 (`v2.3.0-rc.1`) to `prerelease=false` and `make_latest=true`; GitHub requires a regular release for that box.
- Confirmed the latest-release API returns `v2.3.0-rc.1`. A real Playwright browser verified the sidebar text `ANT 2.3.0-rc.1`, `Latest`, and the current publication age; screenshot: `/tmp/ant-latest-sidebar-2026-10-17.png`.
- RC tag, original tag target, publication timestamp and all seven asset IDs, names, sizes, digests and URLs are unchanged. The release notes retain the testing candidate limitations and explain Latest selection. The previous v2.2.0 release is retained.
- README and source release notes aligned through PR #53: https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/53. Main merge `ae8f71542726f5df52ad2ea5044f3e42fd7f789c` at 2026-10-17T23:01:20Z; documentation head `be95331e56bef6af8b43232026d583355c126b21`.
- CI `39076711387` and CodeQL `39076711391` passed. Published README exactly matches the reviewed file; source release notes exactly match the updated release body. No application code or binaries changed.
- Evidence: `/tmp/ant-latest-before-2026-10-17.json`, `/tmp/ant-latest-after-2026-10-17.json`, `/tmp/ant-latest-docs-merge-2026-10-17.json`, `/tmp/ant-latest-published-readme-2026-10-17.md`.

## README refresh and architecture image — 2026-10-17 local time

- Completed the user's requested README rewrite and architecture image in PR #54: https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/54. Documentation head `8007a42a1894666160a0dea2483b22405995b725`; main merge `adc9a0124179fc88ea78ee6fa66ad9e76fe41773` at 2026-10-18T02:12:50Z.
- Updated downloads, source requirements and commands, local/cloud data flow, current project layout, privacy limitations and troubleshooting. Removed obsolete readiness claims. The user's macOS verification warning is addressed with Apple's per-app Open Anyway instructions; the existing release is still ad-hoc signed and not notarized.
- Added `docs/architecture/overview.svg`, its 2560 × 1920 PNG preview, a source-map guide and a renderer using the existing Playwright dependency. The diagram includes Electron's direct history/settings storage and the optional cloud AI route.
- Verified all seven download URLs against published assets, relative links and anchors, npm commands and version pins, SVG contents, JavaScript syntax, GitHub Markdown output and visual rendering. Published README exactly matches the reviewed file.
- PR CI `39088868235` and CodeQL `39088868227` passed. Main CI `39089283760` and CodeQL `39089283759` also passed. Main CD remained skipped under existing opt-in settings.
- A real browser confirmed the new README and architecture image on public main at desktop and mobile sizes. Evidence: `/tmp/ant-readme-pr54-merge.json`, `/tmp/ant-readme-published-2026-10-17.md`, `/tmp/ant-readme-main-verification.json`, `/tmp/ant-readme-main-desktop.png`, `/tmp/ant-readme-main-architecture.png`, `/tmp/ant-readme-main-mobile.png`.
- Work was isolated in `/tmp/ant-release-homepage-2026-10-17`. The original workspace's dirty README draft and application work were preserved. No application binaries, release assets or security settings were changed.

## macOS warning: distribution fix pending Apple credentials

- User explicitly requested fixing the Apple verification warning in the release itself. Do not treat the README workaround as completion of this request.
- Confirmed the existing release configuration has `identity: "-"`, `hardenedRuntime: false`, `notarize: false`, and ad-hoc signing of the Python runtime. No code-signing identities were found in the local keychain, including an unsandboxed check. GitHub reports zero repository Actions secrets. No standard signing/notarization environment variables are present.
- On 2026-10-18 the user answered “nope” to whether they have an active Apple Developer Program membership. Enrollment and signing credentials remain the external blocker. PR #55 was rechecked and remains open, draft and unmerged. Never request credential values in chat.
- Prepared draft PR #55: https://github.com/shyamsunderprogramer-design/ai-note-taker/pull/55, branch `fix/macos-notarized-release`, head `47f9d8aa61f78443acc91451dc307adb88ec0aca`, based on main `adc9a0124179fc88ea78ee6fa66ad9e76fe41773`.
- Separate release config requires Developer ID distribution signing, Hardened Runtime, Apple notarization and five credential environment variables. The runtime hook signs Mach-O files with the same imported identity/keychain as the outer app, a secure timestamp and a matching Apple team. Local ad-hoc builds are preserved.
- The workflow verifies the app extracted from the actual ZIP using codesign, stapler and Gatekeeper, exercises its packaged runtime/authentication, and checks the signature again before uploading. Python bytecode writes are disabled for these checks. Missing credentials or failed verification stop Mac release jobs.
- Credential setup guide: `docs/devops/deployment/MACOS_SIGNING.md` on the PR branch. Required GitHub secret names: `MAC_CSC_LINK`, `MAC_CSC_KEY_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`. `.p12` and `.p8` are now ignored on that branch.
- Validation: 187 desktop tests passed, including 8 signing tests; 6 Python release-verification tests passed; 8 dependency/security regression tests passed. The pinned electron-builder 26.15.3 loaded and schema-validated the config with fixture credentials, without submitting to Apple. A native codesign smoke passed for the preserved ad-hoc path. PR CI `39092672336`, CodeQL `39092672314`, and Vercel all passed.
- Actual Developer ID signing/notarization and both native Mac release builds remain unverified because credentials are absent. The PR intentionally remains draft and unmerged. No new tag, binaries or release publication occurred. Existing `v2.3.0-rc.1` downloads still display the verification warning.
- Next: obtain membership/credential setup through the user's Apple account and GitHub secret store, run the release workflow on the signing branch, resolve real notarization issues, verify both Mac ZIPs and first launch, then prepare and publish a new version with matching metadata/checksums. Do not overwrite the existing release or call it notarized retroactively.
- Worktree: `/tmp/ant-release-homepage-2026-10-17` on the fix branch. Tests temporarily used a `node_modules` symlink to `/tmp/ant-main-review-2026-10-14/node_modules` after confirming matching lockfiles; the symlink was removed afterward and the worktree is clean. Original dirty workspace work remains untouched apart from this checkpoint.
