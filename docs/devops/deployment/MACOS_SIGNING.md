# macOS release signing and notarization

The public `v2.3.0-rc.1` Mac archives are ad-hoc signed and are not notarized. Updating the workflow does not change those already downloaded files. Removing the verification warning requires a new app signed with an Apple Developer ID Application certificate and accepted by Apple's notarization service.

## Apple credentials

The account holder needs an active Apple Developer Program membership and a **Developer ID Application** certificate, including its private key. An Apple Development or Mac App Store distribution certificate does not work for this release path. Follow [Apple's Developer ID guide](https://developer.apple.com/developer-id/) to create the certificate and export it from Keychain Access as a password-protected `.p12` file.

Add these repository secrets in [GitHub Actions secrets](https://github.com/shyamsunderprogramer-design/ai-note-taker/settings/secrets/actions):

| Secret | Value |
| --- | --- |
| `MAC_CSC_LINK` | Base64-encoded `.p12` containing the Developer ID Application certificate and private key. |
| `MAC_CSC_KEY_PASSWORD` | Password chosen when exporting that `.p12`. |
| `APPLE_ID` | Apple Account email authorized for the developer team. |
| `APPLE_APP_SPECIFIC_PASSWORD` | An [app-specific password](https://support.apple.com/en-us/102654) for notarization. |
| `APPLE_TEAM_ID` | The certificate's 10-character Developer team ID. |

For example, upload the certificate through the GitHub CLI without printing its contents:

```bash
base64 -i /absolute/path/DeveloperID.p12 | gh secret set MAC_CSC_LINK --repo shyamsunderprogramer-design/ai-note-taker
gh secret set MAC_CSC_KEY_PASSWORD --repo shyamsunderprogramer-design/ai-note-taker
gh secret set APPLE_ID --repo shyamsunderprogramer-design/ai-note-taker
gh secret set APPLE_APP_SPECIFIC_PASSWORD --repo shyamsunderprogramer-design/ai-note-taker
gh secret set APPLE_TEAM_ID --repo shyamsunderprogramer-design/ai-note-taker
```

The last four commands prompt for their values. Keep credentials in the secret store; do not put them in source files, shell command arguments, pull requests or chat. `.p12` and `.p8` files are ignored by Git as an additional precaution.

## Release pipeline

The Release workflow checks for these credentials before starting either Mac build. Missing credentials fail the job; the workflow cannot upload an ad-hoc Mac archive as a verified release.

1. `electron/electron-builder.mac-release.cjs` requires signing, Hardened Runtime and notarization. It selects a Developer ID distribution identity instead of the local ad-hoc identity.
2. `electron/scripts/sign-runtime.cjs` imports the same certificate/keychain used by electron-builder and signs every actual Mach-O binary in the bundled Python runtime and the audio helper with a secure timestamp. It checks that the certificate belongs to `APPLE_TEAM_ID`.
3. electron-builder signs the outer Electron bundle, submits it to Apple with `notarytool`, staples the accepted ticket and creates the ZIP. It manages its temporary signing keychain.
4. `scripts/verify_macos_release.py` extracts the actual downloadable ZIP into a temporary directory. It checks the signature, Developer ID team, timestamp, Hardened Runtime, stapled ticket and Gatekeeper assessment. It then runs the bundled-runtime/authentication smoke test and checks the signature again.
5. Only a successful verification allows that Mac archive to be uploaded. All four platform builds must pass before a tagged release draft is assembled.

Run the workflow manually against the signing branch after configuring credentials. Review both native Mac jobs and test their downloaded archives on a separate Mac. Then prepare a new version and release tag with matching lockfiles and release notes. Preserve the existing release's files and checksums; do not describe it as notarized retroactively.

Local `npm run electron:build:mac` builds continue to use the ad-hoc configuration for development. The public release workflow uses the separate signed configuration explicitly.

## Verification and failures

Tests that do not require Apple credentials:

```bash
node --test electron/tests/macos-signing.test.js
python3 -m unittest discover -s scripts/tests -v
```

These cover credential and identity rejection, runtime signing behavior, archive selection and failures in each verification stage. They do not substitute for Apple's acceptance of a real build.

- **Credentials missing:** configure all five repository secrets. Secret values are never printed by the preflight check.
- **No Developer ID identity:** confirm the exported `.p12` includes the private key and is a Developer ID Application certificate.
- **Team mismatch:** use the team ID belonging to the signing certificate and Apple Account.
- **Notarization rejected:** inspect Apple's submission log, fix the reported binary or entitlement issue, and rebuild. Do not bypass the failed job.
- **Staple or Gatekeeper failure:** do not publish the archive. Confirm notarization completed and the ticket is included in the ZIP's app.

References: [Apple distribution signing](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac), [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), and [electron-builder v26 notarization](https://www.electron.build/v26/docs/notarization/).
