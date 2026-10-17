# Security remediation checkpoint — 2026-10-08

Work is ongoing. This checkpoint does not mean that all repository findings are resolved.

## Tested application fixes

- Public HTTP connections validate all DNS answers and connect to a validated numeric address, retaining TLS hostname verification. Proxies and redirects are disabled; explicit internal-service access remains separate.
- Jira requires a public HTTPS origin. Integration logs no longer include conversation text, phone numbers, usernames, or upstream error bodies.
- Authentication uses PyJWT rather than the affected python-jose implementation. The auth/session regression tests pass.
- Python and Electron dependency upgrades address the resolved advisory sets. XML parsing is hardened and Salesforce queries use the library's parameter formatter.
- Mobile tooling retains its current APIs using documented private patches for brace nesting and IP classification, plus an adapter around the patched image-size parser. These are local packages, not upstream patched releases. Their original licenses are retained.
- Model downloads are pinned to an immutable Hugging Face revision.
- CI runs the dependency attack regression tests.

## Verification

The isolated staged checkout passed 1,317 backend tests (59 skipped), 169 desktop tests, 26 mobile tests, 5 web tests, 3 dependency attack/compatibility tests, and the production web build. The final root npm graph and standalone Electron graph reported zero known vulnerabilities; the resolved production Python audit also reported zero. These results concern the audited graphs, not every possible vulnerability or the existing development virtual environment.

The historical secret scan passes with six exact, reviewed false-positive fingerprints: documentation/environment placeholders and an old OS-encrypted Electron state value. No blanket file exclusions were added.

## Remaining work

- GitHub's baseline contains 482 open code-scanning findings, including quality findings. Main-branch alerts require merged changes and a fresh analysis; this checkpoint does not close them.
- Infrastructure scanning currently reports 62 failed checks (down from 72), with no parsing errors. Cloud configurations validate with downloaded providers, but AWS/Azure have deprecation warnings. Cloud hardening is still under review and is not part of this application checkpoint.
- Bandit has no high-severity findings; lower-severity findings and scanner false positives still require individual review.
- Native desktop packaging, mobile device builds, and cloud deployment have not been verified in this checkpoint.

Unrelated existing workspace edits are preserved. No cloud resources were deployed.
