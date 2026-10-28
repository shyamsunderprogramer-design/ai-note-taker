# Live assistance validation — 2026-09-14

ANT's real WebSocket handler now passes the controlled synthetic interview
delivery check. This does not establish parity with Final Round, Cluely or
Parakeet, and does not replace a real meeting-platform acceptance test.

## Fixes made during validation

- Await asynchronous token validation in both WebSocket endpoints. Invalid
  query-string and first-message tokens are rejected before audio starts.
- Register the system-audio channel only after authentication/setup succeeds,
  avoiding channel-count leaks from rejected connections.
- Bound the adaptive voice detector's noise threshold. Speech starting immediately
  at connection time previously raised its own noise floor and cut a question
  after 1.3 seconds. The entire synthetic question now reaches the answer generator.
  The configurable 0.06 RMS ceiling passes existing noise tests through 0.05 RMS;
  it is not a guarantee for arbitrary microphone levels or noisy rooms.
- Include a unique session ID with committed answers. The renderer uses session
  and answer IDs together, so reconnecting cannot overwrite an earlier call's
  answer numbered 1.
- Remove invented default resume experience and instruct the live model to use
  supplied facts. Fix fallback retrieval to use Suggestion.content.

## Evidence

The [live report](results/2026-09-14/live-websocket.json) contains three repetitions
of a synthetic interview question, sent as 100 ms PCM chunks through the actual
ASGI WebSocket route, VAD, Whisper small and local Qwen3.5:9b. Each repetition
reconnects. All three delivered a completed answer whose question retained
“problem”, “change”, “measure” and “result”. Completed-answer latency reported by
the route was 3.789, 3.411 and 3.155 seconds from its utterance boundary.

This gate checks complete-question delivery and nonempty answers, not semantic
accuracy. Manual review found unsupported elaboration, including a monitoring
dashboard absent from the supplied resume. The revised prompt reduces invented
defaults but does not guarantee grounded answers. Interim slice transcripts also
contain repeated or clipped words; the final question supplied to the AI is better.

The Chromium production smoke test verifies that a partial answer becomes one
complete visible chat bubble, that saved in-memory history contains the complete
text, and that a reconnect creates a separate bubble. Those UI inputs are synthetic;
this is not a single integrated browser-to-model network test.

Validation: backend suite 1,082 passed / 59 skipped; the subsequently added provider
fallback regression passed separately. Desktop 51 passed. Production build 0.710 s,
71 asset references present, 16 scripts syntax-checked. Five browser pages passed,
including the live-answer update/reconnect assertions.

## Remaining acceptance work

A consenting Meet/Zoom call is still required to exercise microphone plus remote
audio, actual network transport, permissions in the packaged app, visible live
responses, pause/resume and reconnection together. No meeting link or consenting
participant was available during this run. Competitor account access and matched
recordings are needed for hands-on latency/quality comparisons; the
[official-document comparison](COMPETITOR-COMPARISON-2026-09-14.md) is complete.

Do not market the current results as full competitor parity, a production release
certification, or reliable factual interview answers. Changes are in the workspace;
the user's running backend was not restarted and no release was published.

## Reproduce

With the existing synthetic fixtures and cached local models:

```sh
AINT_Venv/bin/python qa/performance/live/websocket.py --output /tmp/ant-product-benchmark/live-websocket.json
AINT_Venv/bin/python -m pytest backend/tests/test_live_websocket_auth.py backend/tests/test_vad_segmenter.py backend/tests/test_live_suggestion_fallback.py -q
npm run benchmark:web
PLAYWRIGHT_BROWSERS_PATH=/tmp/ant-playwright-browsers npm run benchmark:browser
```

The harness disables authentication only in its isolated process; the separate
authentication tests exercise rejection with authentication enabled. No real user
recordings or competitor services are contacted by the harness.
