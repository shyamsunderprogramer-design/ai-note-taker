# Remember me verification — 2026-10-18

Result: the checkbox remembers a username but does not implement reliable,
optional persistent sign-in. No application source, user account, or published
release was changed during this audit.

## Version and scope

- Release: `v2.3.0-rc.1`, commit `b16e551331a6387286ff754de0accc7ef7d9d7f4`.
- The tested sign-in HTML, configuration script, and authentication helper were
  byte-compared with that tag before execution.
- Chromium ran the actual sign-in page in disposable persistent browser profiles.
  Profiles were closed and reopened between checks. Authentication responses and
  the post-login destination page were fixtures; this was not an installed-app
  end-to-end test.
- Independent Python processes loaded the release's real authentication module
  to check token signatures across process restarts. No personal database or
  credentials were used.

## Findings

| Severity | Finding | Source at release tag |
| --- | --- | --- |
| Major | The checkbox only stores/removes the username. Both checked and unchecked logins persist the access token, and both automatically return to the app after browser restart while the token is valid. | `apps/web/signin.html:598`, `apps/web/js/core/auth-helper.js:19` |
| Major | Login issues a 24-hour access token and a refresh token, but the frontend only saves the access token. On a simulated expired-token rejection it clears the login without attempting renewal, even with Remember me checked. | `backend/routes/auth.py:157`, `apps/web/js/core/auth-helper.js:81`, `apps/web/js/core/auth-helper.js:608` |
| Major | Without an explicitly configured persistent `JWT_SECRET_KEY`, each backend process generates a new signing key. A token issued by one process fails signature verification in the next. The packaged launcher does not provision a persistent JWT signing key. | `backend/security/auth.py:37`, `electron/main.js:757` |
| Minor | A failed login with the checkbox checked still overwrites the remembered username, because the preference is saved before authentication succeeds. | `apps/web/signin.html:598` |

## Verified behavior

- Checked: username restored; password not saved or prefilled.
- Unchecked: no username restored, but the access token is still persisted.
- Unchecking a previously remembered account removes the saved username only.
- The checkbox works using keyboard Space; the password field submits using Enter.
- After expiry rejection, the remembered username remains but a fresh login is required.
- Backend restart control: the same token signature remains valid when both
  processes receive the same explicitly configured signing secret.

## Reproduction artifacts

- `/tmp/ant-remember-me-2026-10-18/audit.cjs`
- `/tmp/ant-remember-me-2026-10-18/results.json`
- `/tmp/ant-remember-me-2026-10-18/backend-restart.json`
- `/tmp/ant-remember-me-2026-10-18/remembered-after-expiry.png`

## Required follow-up

Make the option govern session persistence, retain a protected per-installation
signing secret for the desktop backend, implement session renewal with correct
expiry/revocation behavior, and test checked/unchecked login through a full app
restart. Authentication readers in the renderer and Electron preload must use
the same session policy. Existing download assets have not been updated.
