# Desktop session and capture regression checks — 2026-10-18

Candidate: `2.3.0-rc.2`, based on main `adc9a0124179fc88ea78ee6fa66ad9e76fe41773`.
All local authentication checks used disposable profiles, accounts and databases.

## Reproduced problems and fixes

- The old Remember me checkbox saved only a username. Desktop sessions now use
  encrypted OS storage when checked and process memory when unchecked. Packaged
  backend signing keys persist across restarts; explicit environment keys win.
  Development launches retain their existing `.env` configuration behavior.
- Access tokens renew while the refresh session remains valid. Desktop windows
  and preload API calls share renewal, and sign-out removes the saved session.
  Revoked sessions cannot refresh; refresh tokens cannot serve as access tokens.
- Browser authentication preflight was rejected without a bearer token. It now
  reaches the existing CORS allowlist; actual API calls still require auth.
- Global recorder chunks and late stop events could interfere with another
  recording. Each recorder now owns its stream, chunks and discard state.
- The Mac screen helper previously compiled on the user's computer. Packaging
  now builds and signs it for each Mac architecture. Optional capture failures
  allow ordinary text questions to continue with a visible notice. Explicit
  screen questions still require real image/text evidence.

## Local results

| Check | Result |
| --- | --- |
| Backend `tests/` | 1,648 passed, 59 skipped |
| Electron, web and dependency/security unit tests | 232 passed |
| Full Chromium and Firefox suite | 62 passed |
| New Remember me browser flow, repeated three times per browser | 18 passed |
| Vite production build | Passed |
| Real Electron process restarts and macOS `safeStorage` | Unchecked login not restored; checked login restored; saved bytes encrypted; sign-out persisted |
| Real browser recording with generated audio | 14,683-byte Opus/WebM recording; no recording errors |
| Sign-in axe WCAG 2 A/AA, 2.1 A/AA and 2.2 AA | No automated violations reported |
| Sign-in visuals and checkbox keyboard interaction | Desktop and mobile screenshots reviewed; keyboard check passed |
| ARM64 screen helper | Compiled, ad hoc signed, strict signature check and `--self-test` passed |

Reproduce the committed regressions with:

```sh
node --test electron/tests/*.test.js apps/web/tests/*.test.mjs qa/security/*.test.cjs
python qa/performance/backend/isolated.py test tests core/test_startup.py -q
npm run web:build
npm run e2e:test -- --workers 1
```

The QA charter's repeated-run check was also applied to the new session tests.
The browser server injects its disposable API URL; it does not use personal keys.

## Limits

The generated-audio check verifies recorder delivery, not the user's physical
microphone or macOS permission grants. The native helper self-test does not take
a screenshot. Actual capture, system audio and device-specific behavior still
depend on OS permissions and hardware. Apple notarization is not part of this
candidate. Signing improvements remain in separate draft PR #55.

Native Windows, Linux, Intel Mac and Apple Silicon installer verification is
performed by the Release workflow before assets are published. These local
results alone do not certify all native installers or every optional provider.
