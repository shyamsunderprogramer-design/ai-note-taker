# Release preparation checkpoint — 2026-10-14

Superseded by [the October 15 checkpoint](CHECKPOINT-2026-10-15.md): integration is authorized and pushed as PR #25; one historical Ollama credential still needs revocation confirmation before the merge/release.

Requested release: a testing candidate, `2.3.0-rc.1`, proposed while repository-wide main/cloud review remains incomplete. The user subsequently asked whether code was pushed and then asked to switch the branch to main.

## Source and push status

- The verified application source remains on `ux-sprint` at `4b4a5e0`.
- Release preparation is committed and pushed separately on `release/v2.3.0-rc.1`, latest commit `d9a0330265868d5c3d775ab86559c4943255e965`.
- Isolated release worktree: `/tmp/ant-release-2.3.0-rc.1`.
- No new release tag or public release has been created. Do not describe the candidate as published.
- The original workspace's extensive unrelated uncommitted changes remain untouched.

## Candidate changes and local validation

- Version/lockfile metadata and reviewed release notes: `docs/releases/2.3.0-rc.1.md`.
- Replaced nonportable bundled virtual environments with checksum-pinned standalone Python 3.12.15 (20261013) for four native targets.
- Restored native macOS builds, committed formerly missing signing entitlements, limited each Mac build to its native architecture, and set a safe Linux executable filename for the patched AppImage builder.
- Added writable packaged data locations and rejected missing bundled Python instead of silently using system Python.
- Local results: 1,647 backend tests passed, 59 skipped; 179 desktop tests, 15 web tests and 6 security regressions passed; web production build passed; npm install audit found zero vulnerabilities.
- Actual local macOS arm64 package imports, backend health, registration, login and user-data persistence passed. The local x64 artifact from the initial multi-architecture configuration contains the wrong runtime and MUST NOT be distributed. Use only artifacts from the corrected native hosted builds.
- Local logs: `/tmp/ant-release-{backend-tests,desktop-tests,web-tests,web-build,security-tests,runtime,mac-build,mac-smoke}.log`.

## Hosted checks

- Initial build 38661002357: Windows passed, including packaged sign-in. macOS failed because entitlements were absent from Git; Linux failed the new AppImage filename validation. Both source causes are fixed in `d9a0330`.
- Corrected release build: https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/38662127188
- Full CI: https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/38662153761
- CodeQL: https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/runs/38662156043
- These corrected hosted checks were still running at this checkpoint. Read their final results before publishing or claiming success.

## Pending main-branch clarification

- GitHub `main` is protected and currently points to `2846154dced96f5fb73f85157639934a47001b42`.
- A clean detached checkout of that exact remote commit is prepared at `/tmp/ant-main-review-2026-10-14` for review. This does not switch the original workspace or update the local `main` branch.
- Local `main` points to a different history at `5b4055c`; it cannot simply fast-forward to remote main. Remote main and ux-sprint also have unrelated histories.
- Asked the user to choose between putting the tested app code onto main and opening the existing main only. No answer received at checkpoint time. Do not infer permission to replace main's contents or rewrite history.
- Comparison summary: `/tmp/ant-main-integration-summary.json`. Remote main has 388 files, the release candidate 802; 126 files exist only on main. Integration must preserve/review those differences rather than blindly replacing the tree.

## Resume

1. Resolve the user's intended main-branch action while preserving all local work and histories.
2. Finish the three hosted checks above; inspect failures and branch CodeQL alerts, not just workflow conclusion.
3. Download only the corrected native installer artifacts, require the complete platform set, and generate checksums for the final filenames using `scripts/release_checksums.py`.
4. Publish a prerelease only from the verified candidate commit with the reviewed notes and actual verified assets; do not overwrite existing tags/releases. Stable release and main-wide security cleanup are not complete.
