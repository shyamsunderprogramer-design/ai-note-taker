# Desktop subscription login

This source build supports the official ChatGPT plan-usage flow for local/open-source apps. You do not paste an API key. OpenAI determines whether the selected account, workspace and model are eligible. This is a connection to your existing ChatGPT account, separate from the ANT account used for local history.

## Connect and use

1. Quit the old desktop process and run `npm run electron:start` from the repository root. After pulling these changes on another machine, run `npm ci` first. Existing downloaded releases need a new packaged release to include this feature.
2. Click **Providers** beside the Model picker, or open **Settings → Providers**.
3. Choose **Add an account** or a saved registration, then expand **ChatGPT subscription · no API key** under **OpenAI / ChatGPT** and choose **Continue with ChatGPT**. Complete the provider's consent screen in your browser and return to ANT.
4. Successful plan authorization selects **Connected accounts (no API key)** for answers. Choose an available model under that provider. **Use subscription for answers** restores this selection after using another provider.
5. Under **When you reach a limit**, optionally enable the other connected cloud account and choose a **Final local fallback**. Both are off by default. Start Ollama to list installed local models; ANT never downloads a local fallback automatically.

The model picker uses the account's current model catalog rather than guessing entitlements from a plan name. Saved registrations are separate even when they share an email address. Switching saved accounts is explicit. Disconnect clears local tokens and attempts to revoke the renewable provider session. A warning explains when remote revocation could not be confirmed.

## Ollama account without an API key

1. Install or update the Ollama desktop app and start it on this device.
2. Under **Ollama Cloud** in **Settings → Providers**, expand **Ollama account · no API key**, click **Connect Ollama account**. If needed, finish the Ollama sign-in page in your browser. ANT checks for completion for up to three minutes; **Check sign-in** refreshes manually.
3. Select a registered cloud model. If the list is empty, expand **Add a cloud model**, enter a cloud model name from Ollama (for example `gpt-oss:120b-cloud`), and click **Add cloud model**. This explicitly registers the cloud reference through the local Ollama service.
4. Click **Use Ollama account for answers**. ChatGPT is not required for this path. The chosen cloud model uses the allowance of the account signed into Ollama.

ANT uses Ollama's fixed local endpoint, `http://127.0.0.1:11434`, and its documented account flow. Ollama owns its credentials; ANT never reads its private keys or copies login tokens. An existing Ollama sign-in still requires an explicit **Connect** in ANT. ANT checks the account identity before cloud requests; changing or signing out of that account requires reconnection. **Disconnect from ANT** disables this connection without signing other apps out of Ollama.

## Usage limits and fallback

A 429 or subscription usage-limit event pauses the affected provider. A notice links to its usage settings. ANT tries the **First provider**, then the other connected cloud account only if you enabled **Use my other connected cloud account after a limit**, then the selected **Final local fallback**. Each candidate is attempted at most once. An unconnected or unconfigured alternative is skipped. No alternate cloud account is used by default.

An incomplete answer is visibly restarted when the fallback stream starts; text from two models is not silently concatenated. Screenshots require a vision-capable Ollama model. ANT verifies local fallback metadata before sending the question and history so a cloud alias cannot silently replace a local model.

ANT observes a provider-supplied `Retry-After` delay. Without one, it leaves the provider paused until you choose its **Retry** button. It does not invent a quota reset time or cycle models within an exhausted plan. Authentication failures, unsupported inputs and temporary infrastructure failures stop the request. API-key providers are not part of this recovery path.

Audio transcription and separate tools retain their existing settings; connected accounts handle chat and live answers. Background agent suggestions are suppressed while connected-account answers are selected so they cannot start independent provider calls.

## Other providers and actual connection requirements

| Provider | Connection in ANT | Consumer subscription login |
| --- | --- | --- |
| ChatGPT | Browser OAuth with eligible plan and model catalog | Implemented; eligibility depends on provider/account/workspace |
| Ollama Cloud | Account signed into the local Ollama app | Implemented; no manual API key |
| Local Ollama | Installed models on this device | No account or API key needed |
| Claude | Existing Anthropic API-key configuration | Not implemented: Anthropic prohibits third-party apps from offering Claude.ai login or routing through consumer credentials |
| Gemini | Existing Google AI Studio API-key configuration | Not implemented: Gemini CLI credentials cannot be reused as third-party app credentials |
| Grok | Existing xAI API-key configuration | No supported public subscription-login integration for ANT was found |
| Groq | Existing Groq API-key configuration | Official developer setup requires an API key |

Each provider has an **API key** button on the Providers page. ChatGPT and Ollama also show their supported account-login connection below the provider row. These connections use separate API billing; signing into ANT itself does not unlock another provider's subscription.

## Local API-key storage

In **Settings → Providers**, click **API key** beside the provider. Saving verifies the key directly with that provider, then keeps it in ANT’s existing encrypted local store. **Also save a local .env copy** is selected by default. Uncheck it to use only encrypted storage; saving with it unchecked removes that provider’s entry from ANT’s managed .env copy.

The optional file is `<ANT userData>/providers/.env`, outside the repository and installed application bundle. The success message shows its exact path. Writes are atomic, and new files use owner-only permissions (`0600`; folder `0700` on POSIX systems). Existing unrelated entries are preserved. The desktop passes this path to its local backend as `ANT_PROVIDER_ENV_FILE`; on restart, the backend loads only known provider-key variables without expanding environment references. Explicit process environment variables take precedence.

Keys are not written to a new project `.env` or synced to an ANT cloud account by this save flow. Existing manually configured project `.env` files remain supported and are not migrated or deleted. The `.env` copy is plaintext; local backups or file-sync software are outside ANT’s control. A cloud request necessarily sends the key to the selected provider for authentication. This is local storage, not a promise that credentials never travel over the network.

The local .env option is a desktop feature. Restart the desktop/local backend after changing keys loaded from the file. No real keys are needed for the automated tests.

## Implementation and security

- `electron/lib/subscription-auth.js`: loopback OAuth with state, nonce and PKCE; signed ID-token validation via `jose`; rotating refresh tokens; revocation; encrypted atomic owner-only storage using Electron safeStorage.
- `electron/lib/subscriptions.js`: ChatGPT model catalog, streamed Responses requests, quota pause and trusted IPC registration. Only the trusted main `index.html` frame can invoke subscription operations. The Electron instance lock prevents two app instances racing the same renewable session.
- `electron/lib/ollama-account.js`: local Ollama identity, validated browser sign-in URL, cloud references, model routing/capability checks and streaming.
- `electron/lib/connected-models.js`: explicit provider selection, cross-account opt-in, persisted quota pauses and ordered fallback.
- `electron/preload.js`: public account status and streamed answer events; no subscription credentials reach the renderer, browser storage or Python backend.
- `apps/web/js/subscriptions.js`: settings and existing chat-stream integration. The web-only client explains that desktop is required.

Only the documented text/image Responses route is used, with `store: false` and streaming. Remote calls still occur internally; “no API key” does not mean offline operation. Credential storage stays outside the repository under the app's private authentication directory.

## Verification

`node --test electron/tests/subscriptions.test.js electron/tests/connected-models.test.js electron/tests/auth-session.test.js` covers callback state/PKCE/client binding, ID-token cryptography, scopes, refresh rotation and races, encrypted storage, IPC trust, Ollama sign-in validation and consent, identity changes, model routing/capabilities, streamed limits, cancellation and cross-provider/local fallback.

`node qa/subscriptions/browser.cjs` checks the real HTML/controller/chat path with a synthetic native bridge. It requires Playwright and `@axe-core/playwright`; optional `ANT_AXE_MODULE` and `ANT_TEST_CHROMIUM` select an externally installed checker/browser. Screenshots and results are written to `/tmp/ant-subscription-qa/screenshots`.

These tests do not sign into a real subscriber account or consume plan usage. Live provider eligibility and completed real sign-in/inference sessions must be checked by the account owner. This is implemented and tested in source; it is not a claim that every consumer subscription is supported or live-verified.

References: [OpenAI registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in), [models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery).

Other provider references: [Ollama authentication](https://docs.ollama.com/api/authentication), [Ollama Cloud](https://docs.ollama.com/cloud), [official Ollama account client](https://github.com/ollama/ollama/blob/main/api/client.go), [Claude third-party authentication requirements](https://code.claude.com/docs/en/legal-and-compliance), [Gemini CLI credential restrictions](https://geminicli.com/docs/resources/faq/), [xAI setup](https://docs.x.ai/developers/quickstart), [Groq setup](https://console.groq.com/docs/quickstart).
