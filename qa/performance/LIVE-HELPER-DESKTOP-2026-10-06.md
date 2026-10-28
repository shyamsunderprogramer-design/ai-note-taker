# Live helper desktop check — 2026-10-06

Tested the real Electron desktop, signed-in test account, production backend and configured Groq provider. No mocked audio, transcription, OCR or model responses were used.

- Typed Enter during Live helper kept capture active. A three-sentence Kubernetes/Docker/CI/CD answer completed in 0.883 seconds measured from submission through completion.
- macOS speech playback of “What is a CI CD pipeline?” was captured as microphone speech and normalized to “What is a CI/CD pipeline?” for one answer. The generation badge showed 1.3 seconds; this excludes transcription and is not total speech-to-answer latency.
- Playback of “We agreed to send the report by Friday” entered retained session observations and the decision quotation card.
- Actual screenshot OCR populated current screen observations.
- Session observations remained after stopping. The desktop remained open. No renderer errors were recorded in the successful question test.

The initial test reused an older running backend and produced duplicate answers without retained completed speech. The backend was restarted and the test account signed in again before the successful checks. One repeat was interrupted by that login change and is not counted as successful validation.

Remote/system audio was requested but no remote-labeled completed speech was established. This is not a Zoom/Meet call test. Independent code/error guidance was tested in a browser fixture previously, not against a real visible code error in this desktop run. Provider recovery remains variable; the initial stale-backend run included a 15-second fallback answer.

Artifacts: `/tmp/ant-unified-live/report.json`, `/tmp/ant-unified-live/observations.json`, `/tmp/ant-unified-live/demo.png`. These local artifacts may contain captured screen text and are not committed with this report. Repeatable desktop driver: `qa/performance/live/unified-desktop.mjs` (requires a running signed-in desktop with debugging port 9223).
