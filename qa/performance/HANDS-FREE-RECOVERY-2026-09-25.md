# Hands-free recovery implementation

The main app now uses POST `/stream-recover` for typed questions, completed recordings, always-on transcript questions, and screenshot-assisted answers. Explicit model selection remains first. Auto uses an ordered provider list instead of the previous first-token race. Disabled provider/model preferences are respected; local fallback is limited to installed, enabled models. The legacy streaming routes remain compatible for other callers; they have not all been migrated to automatic recovery.

## Behavior

- At most two recovery attempts after the initial attempt; 60-second overall backend deadline, 15-second idle timeout per next packet, and at most 25 seconds of recovery after the first failure. The renderer has a 65-second watchdog, including discovery.
- Quota/auth/unavailable errors put that provider account into a temporary cooldown. Numeric or HTTP-date Retry-After is honored, bounded to 1–3600 seconds; otherwise the default is 60 seconds. Other models on the same account are skipped during cooldown.
- An output limit gets one same-model continuation before another provider. A context-window failure gets one retry with old conversation history removed; the full current question and its resume/JD/screen context remain.
- Partial text is preserved. The UI displays switching/continuation status and model provenance. Exact repeated openings/suffixes are removed using a short initial holdback; no fuzzy semantic rewriting is performed.
- The last recovery attempt prefers an available installed local model. All-failed responses remain visible as incomplete, release processing state, and leave the app ready for the next question.
- A new question aborts the previous request, preserves its partial answer, and prevents stale tokens from reaching the new answer. New-chat and loaded-chat actions also cancel outstanding work.
- Safety refusals are not retried across providers. Incomplete/recovered streams bypass the old successful-answer cache.

Provider adapters now distinguish normal completion from token limits, failed transport, empty output, and rate limits. This includes OpenAI-compatible adapters, Anthropic, Google, and their supported screenshot adapters. Completion handling follows [Anthropic stop-reason documentation](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) and [Gemini finish-reason documentation](https://ai.google.dev/api/generate-content).

The user's database shutdown warning was traced to a custom signal handler that created a new event loop during an already-running Uvicorn loop. That handler was removed. Uvicorn now invokes the existing async shutdown hook, which awaits database and HTTP-client cleanup on the correct loop.

## Verification

- 237 focused backend tests passed: recovery, deadlines, cancellation, cooldown, refusal handling, repetition removal, transport termination, transcription, resume handling, cache behavior, and shutdown cleanup.
- 70 desktop tests and 5 web service-worker tests passed. Production web build passed with existing classic-script bundling warnings.
- Five-page browser smoke passed. Saved-chat browser checks passed, including bulk deletion against synthetic fixtures.
- Isolated browser + production `/stream-recover` controller passed with injected provider failures: partial text preserved, backup attribution, resume/JD retained, complete-recording submission, provider cooldown across questions, newer spoken-question cancellation, local fallback, bounded exhaustion, and disabled-provider/model preferences. Cancellation closed the old server-side generator.
- Real Groq backup requests through the production controller completed after injected first failures:
  - Quota before text: 0.881 seconds. Correctly said no AWS certification was known from the provided resume evidence.
  - Mid-answer disconnect: 2.307 seconds. Preserved Cedar $1,400 over; added Maple $300 under and combined $1,100 over, without repeating Cedar.
  - Output limit: 2.204 seconds. Same-model continuation completed the calculation correctly, without repeating Cedar.

Live evidence: `results/2026-09-25-recovery-live.json` (synthetic questions, no user data or credentials).

## Limits

The live checks injected the first failure; they did not exhaust a provider's real quota. Browser voice checks used controlled transcription/synthetic audio, not a physical microphone. Local fallback and screenshot-provider termination were verified with controlled fixtures, not live local/vision generations in this run. Groq's three successful samples do not prove general grounding or cross-provider semantic consistency. Exact repetition removal cannot prevent paraphrased duplication or contradictions. A browser-to-backend disconnection is marked incomplete; server-side provider failures get the automatic recovery described above. A cancelled synchronous provider HTTP call may continue inside its worker until its transport returns, but its output cannot update the new question.

## Reproduction

```sh
AINT_Venv/bin/python -m pytest backend/tests/test_stream_recovery.py backend/tests/test_shutdown_cleanup.py backend/tests/test_provider_stream_errors.py -q
node --test electron/tests/*.test.js
npm --workspace ant-web test
npm run web:build
AINT_Venv/bin/python qa/performance/live/recovery-server.py
# Separate terminal; synthetic providers, no user database:
PLAYWRIGHT_BROWSERS_PATH=/tmp/ant-playwright-browsers node qa/performance/web/recovery.mjs
# Makes three real Groq requests with synthetic data:
AINT_Venv/bin/python qa/performance/ai/recovery-live.py
```

Restart the desktop/backend to load the new endpoint and shutdown handler. No user conversations were deleted during these checks.
