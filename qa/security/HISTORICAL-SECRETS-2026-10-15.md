# Historical credential review — 2026-10-15

The main integration's old Gitleaks action constructed an invalid range beginning at the parent of a root commit. It scanned zero bytes and failed. The replacement uses checksum-pinned Gitleaks 8.30.1 to scan all commits reachable from HEAD, including merge resolutions, with default detectors plus the existing project rules. Scanner failures remain fatal.

The first complete scan covered 323 commits and approximately 29 MB. It found five already-reviewed documentation placeholders under additional historical commit/path fingerprints and three real credential-shaped values in the old `backend/.env` commit `d854fcbe98d3358b74f80ee9b0247737f8906580`.

| Finding | Evidence / treatment |
| --- | --- |
| Google API key, line 12 | GitHub [secret alert #1](https://github.com/shyamsunderprogramer-design/ai-note-taker/security/secret-scanning/1) is resolved with reason `revoked`; its location matches this exact commit and line. GitHub validity is `unknown`, not a fresh live validation. |
| GitHub PAT, line 15 | GitHub [secret alert #2](https://github.com/shyamsunderprogramer-design/ai-note-taker/security/secret-scanning/2) is resolved with reason `revoked`; its location matches this exact commit and line. GitHub validity is `unknown`, not a fresh live validation. |
| Ollama Cloud key, line 10 | No provider revocation evidence available. User confirmation/rotation is pending. This finding remains unignored and blocks a clean secret scan. |

The two recorded revocations are exact historical exceptions in `.gitleaksignore`, explicitly distinguished from false positives. The five other exact exceptions contain `YOUR_TOKEN` documentation placeholders or the literal instruction `replace-with-32-char-encryption-key`, identical to previously reviewed historical copies. Current examples now use environment variables or an empty value rather than credential-shaped literals.

No credential value was printed, used to authenticate, or sent to a third party during this review. No new secret directory/file exemptions were added and no Git history was rewritten. Do not publish a clean-security claim while the Ollama finding is unresolved.
