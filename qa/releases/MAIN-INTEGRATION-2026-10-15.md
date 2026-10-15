# Main integration checkpoint — 2026-10-15

The user authorized moving the tested application onto `main` and proceeding with the release. This integration joins the previously unrelated histories with a normal merge commit. No branch is force-pushed and the original workspace's uncommitted work is preserved.

## Source reconciliation

- Remote main parent: `2846154dced96f5fb73f85157639934a47001b42`.
- Tested release parent: `7a8552e9f5e9b7b34d3fced57d032c3363e392cb` on `release/v2.3.0-rc.1`.
- Application conflicts use the tested release source. 85 old paths have confirmed destinations in the reorganized source tree; they are retained as moves rather than duplicate obsolete copies.
- The 41 other main-only files remain, including artwork, documentation, cloud lockfiles, development tools and legacy browser/VS Code extensions. These legacy extensions are not included in the desktop installers or certified by this prerelease.
- The original `ux-sprint` workspace remains untouched. Review/build work happens in `/tmp/ant-main-review-2026-10-14`.

## Workflow repairs

- Added checksum-verified actionlint validation to CI, aligned Python with the tested 3.12 runtime, and corrected workspace installation paths. Backend, desktop, web, mobile, browser and dependency checks remain enabled.
- Python auditing now fails on vulnerabilities or scanner errors instead of swallowing the command's failure. High-severity/high-confidence Bandit findings also fail CI.
- Fixed invalid deployment expressions, shell input interpolation and deployment of untested source. Cloud deployment requires `ENABLE_CLOUD_DEPLOYMENTS=true` and successful CI, or an explicitly dispatched run. Deployment notifications require a separate opt-in. Neither opt-in is enabled by this integration.
- Retained the broader advisory security workflow, pinned previously floating scanner actions, corrected Checkov report paths, restored default secret detectors and removed blanket test-directory secret exemptions. Cloud/low-severity review remains incomplete; an advisory job's completion is not evidence of zero findings.
- Escaped the retained VS Code extension's loading message before HTML rendering.

## Verified before the merge commit

- 1,647 backend tests passed; 59 skipped.
- 179 desktop tests, 15 web tests and six dependency-security regression tests passed.
- Clean locked dependency installation: zero npm vulnerabilities. Web production build and all workflow syntax checks passed.
- Hosted release build `38662127188` passed all four native platforms, including the actual packaged backend's registration, login and data persistence. CI `38662153761` passed.
- Release parent `7a8552e` fixes the two packaging-script findings from CodeQL run `38662156043`. Its native rebuild is `38804653301`; final results must be checked before publication.

## Resume / publication gates

1. Push this integration branch, open a PR against main, and inspect CI plus all CodeQL alert results for the final commit.
2. Merge normally after checks pass. Confirm remote main and its dependency/CodeQL status; do not infer default-branch security status from branch checks alone.
3. Tag the verified main source as `v2.3.0-rc.1` only if the tag does not exist. The release workflow builds native installers and creates a draft after all platform checks pass.
4. Inspect the six native installers, audits and SHA256SUMS before publishing as a prerelease. No tag/public release exists at this checkpoint.

Outstanding limits: cloud templates, low-severity scanner findings, optional voice runtimes and live hardware/provider behavior still need review. macOS builds are ad-hoc signed, Windows installers are unsigned, and no guarantee of universal capture invisibility or millisecond provider responses is made.
