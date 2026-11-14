# Subscription feature verification — 2026-10-30

Scope: desktop ChatGPT plan connection, Ollama account connection, chat/live-answer transport, explicit cross-account fallback and local Ollama fallback. No real account authorization or paid/subscription inference was performed.

## Results

- `node --test electron/tests/subscriptions.test.js`: 14/14 passed. Includes a real temporary localhost callback server and locally signed JWT fixtures, with simulated provider responses.
- `node --test electron/tests/auth-session.test.js`: existing 10/10 passed.
- `node --test electron/tests/connected-models.test.js`: 12/12 passed. Covers official Ollama sign-in URLs, explicit ANT consent, cancellation, account changes, model registration/routing, both fallback directions, opt-out, persisted pauses, Retry-After, partial output, screenshot capabilities and non-limit failures. Combined subscription/auth result: 36/36 passed.
- `node --test electron/tests/provider-env.test.js electron/tests/provider-key-validation.test.js`: 13/13 passed. Combined native result: 49/49 passed.
- `AINT_Venv/bin/python -m pytest -q backend/tests/test_provider_env.py`: 2/2 passed.
- `npm run web:build`: passed. Existing classic-script Vite warnings remain; emitted assets include the subscription controller and stylesheet.
- `git diff --check`: passed.
- `qa/subscriptions/browser.cjs`: six combinations passed (1440×900, 390×844, 320×844; dark/light OS preferences; reduced motion). Real source HTML/app/controller, synthetic Electron bridge, all external requests intercepted. Zero uncaught page errors. Zero axe WCAG A/AA violations within Providers, API-key configuration and the welcome dialog; this is not an app-wide accessibility certification.

## Requirement inventory

| Requirement | Functional evidence | Visual evidence in `/tmp/ant-subscription-qa/screenshots` |
| --- | --- | --- |
| Discoverable sign-in | Keyboard activation of toolbar shortcut opens the unified Providers page | `*-disconnected.png` |
| Account login and consent | OAuth state, PKCE, issued client, verified identity and scopes covered by native tests | `*-welcome.png` |
| Available models | Native catalog filtering, real select and use action | `*-connected.png` |
| Explicit fallback choice | Installed local option saved; off-by-default native fixture | `*-connected.png` |
| 429 notification and switching | Plan pauses, retry delay observed, subsequent requests stay local, partial text reset in actual chat renderer | Browser assertions on visible notice and replacement answer |
| Cancel and disconnect | Callback cancellation UI, token revocation/refresh race tests, no token resurrection | Browser assertions on cancelled status |
| Keyboard/reflow | Enter opens shortcut; Escape closes welcome/settings and returns focus; no settings content overflow | All six screenshot sizes/themes |
| Settings scrolling | Wheel down/up changes the settings body's scroll position; panel and body explicitly use Electron `no-drag` regions | All six sizes/themes; native drag-region CSS assertions |
| Ollama account and models | Connect explicitly, choose the second model, add a cloud reference, select Ollama for answers, disconnect ANT only | `*-ollama.png` |
| Cross-account fallback | Off by default, explicit checkbox persists; native tests cover both directions and local final fallback | Browser controls plus native transport assertions |
| Unified provider setup | No separate Subscriptions tab; account details under ChatGPT/Ollama; API buttons open their provider configuration | Browser assertions for Anthropic, Google, xAI and Groq |
| Local key storage | Synthetic key saves select local .env or encrypted-only; input clears after saving; Escape returns focus to the provider | `*-api-key.png`; native permissions/replacement/removal/symlink tests and backend literal-key loading tests |

Manual visual inspection: desktop, 390px and 320px connected/account screenshots. The app currently retains its dark palette under a light OS preference; the feature follows that existing behavior. Settings use existing typography/radius/control styling, with an opaque content surface for readable text. No decorative imagery added. The additional tab uses natural width to avoid overlapping labels.

Issues found and fixed: the existing document outside-click handler closed the new shortcut immediately; it now recognizes the subscription entry point and welcome dialog. Successful authorization selects subscription mode immediately, preventing a new user from unknowingly retaining Auto/API-key mode.

Additional fixes: preserve the newly selected Ollama model while busy controls rerender; skip unconfigured alternate accounts; report cancellation as cancellation before any fallback starts; give the settings body sole scroll ownership and remove redundant backdrop filtering from its opaque subscription panel. Capturing immediately after scrolling upward produced a temporarily blank card in headless Chromium; waiting two animation frames for the compositor before taking the screenshot showed the content correctly.

User-reported desktop scrolling: the settings panel had no `-webkit-app-region: no-drag` override inside the draggable shell. Added explicit overrides on the panel and body, retained the bounded scroll viewport, and added wheel down/up checks plus computed native-region assertions. All six browser combinations passed. The previously running Electron renderer requires a reload or restart to load the changed stylesheet; physical trackpad testing was not performed.

Limitations: real provider eligibility, browser consent, model catalog and inference have not been exercised against a subscriber account. Packaged installers were not rebuilt. Native screen-reader testing was not performed. The underlying web page still has existing UI unrelated to this change; the checks are scoped to the subscription feature.

Providers consolidation: API-key buttons now have text labels; API toggles have a distinct visible label from account status. Fixed delayed config status loading that could erase a newly typed key, and corrected API-save/status contrast. Keyboard checks include Escape from API configuration and restored focus. Local `.env` tests use temporary directories and synthetic keys only. No existing real key files were read, migrated or modified.
