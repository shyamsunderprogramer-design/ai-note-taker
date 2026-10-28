# Model selection follow-up

Found and fixed model-selection loss in multiple paths:

- Audio WebSockets now carry the selected model and accept selection updates during a session.
- Explicit local models reach the live generator; explicit cloud choices use the normal provider router.
- Explicit selections disable default-model previews. Responses from an earlier selection are discarded if selection changes during generation.
- Screenshot requests preserve the selected model instead of falling into the default vision race. Unsupported choices produce errors.
- Disabled selections no longer silently trigger Auto. A provider's race-participation setting no longer resets the saved selection.
- Missing Ollama Cloud credentials and provider failures no longer silently switch to local Ollama.

Validation: 1,086 backend tests passed, 59 skipped; production browser smoke passed five pages. Added routing tests cover selected provider forwarding, errors, and explicit local/cloud screenshot models. No paid provider inference was performed in these tests.

Live visual verification remains pending: captured screens showed VS Code, not the affected ANT page. These changes have not been applied to the running app by restarting it yet. Actual dropdown interaction and live response latency must still be verified on the user's intended page. No speed improvement is asserted from these routing tests.
