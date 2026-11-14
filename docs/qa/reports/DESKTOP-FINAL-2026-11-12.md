# Desktop latency and capture verification — 2026-11-12

The Enter/blank numeric-answer repair remains in place. This follow-up removes
unnecessary screen preparation from standalone typed questions and bounds the
renderer OCR wait. These are source changes used by `npm run electron:start`;
no installer was built.

## Measured delay

In the normal desktop profile, the same arithmetic question spent 22,201 ms in
screen preparation, including 21,968 ms in OCR, before the provider request.
A screen-specific repeat took 28,508 ms, including 28,317 ms of OCR, and reported
the Ollama extractor. Native OCR separately took 14.7 seconds on one real screen;
the helper's 15-second deadline can therefore cause the slower fallback. Native
recognition also completed in 412 ms on a later screen. Timing is content/load
dependent, not uniformly slow.

The isolated real ChatGPT request first produced text in 2,602 ms and finished in
2,767 ms. Its model already defaults to low reasoning effort. A comparison request
returned HTTP 429; the existing account pause was retained. No provider selection
or paid fallback was changed. Further live AI calls were stopped.

## Changes and verification

- Typed questions use the existing screen-reference classifier outside live mode
  as well as inside it. Explicit capture, supplied context and attachments retain
  their context. Without the classifier, the previous capture behavior remains.
- `runOcr` aborts its fetch after 2.5 seconds and clears its timer afterward.
  An unavailable/slow OCR result retains the original image for the existing
  vision routing. This requires a configured compatible vision model. Aborting
  the client wait does not kill an already-running backend OCR worker.
- New regressions failed before the changes and passed afterward: standalone
  text bypasses a failing capture; screen references/attachments/provided context
  survive both session modes; a timed-out OCR fetch is aborted and the image
  reaches the vision route.
- Live arithmetic preparation after the fix: **78 ms**, with no capture or OCR.
- Live screen-question preparation after the fix: **679 ms**, with native OCR
  taking **412 ms**. No renderer exceptions occurred.
- Final validation: **260 desktop tests and 29 renderer tests passed**;
  **84 asset references resolved and 20 scripts passed syntax checks**.

The preparation probes used actual Enter, the actual desktop profile and local
OCR, but deliberately replaced the provider response with a clearly labelled QA
response. These figures are preparation latency, not end-to-end AI latency.
Synthetic probe replies were not autosaved. Temporary screenshot input used for
native OCR diagnostics was deleted. A fast-mode experiment was not shipped:
its accurate comparison timed out and did not establish equivalent quality.

## Capture protection

Executed `node qa/performance/renderer/protected-controls.cjs --capture
--screen-capture-kit` against an isolated synthetic window, including an
unprotected control. The normal desktop app's window settings were not changed.

- macOS region screenshot: unprotected picker visible; protected picker and
  tooltip excluded.
- ScreenCaptureKit single-window screenshot: unprotected fixture pixel fraction
  0.964565; protected fraction 0. The protected image was visually checked and
  was black. This is an observed result for this machine and capture path.
- Keyboard selection, dynamic controls, scrolling, reload, in-document popups
  and window protection flags passed.
- Artifacts: `/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-controls-XHeiU1`.

This does not establish universal invisibility. Electron documents that other
ScreenCaptureKit capture paths may capture protected windows:
https://github.com/electron/electron/blob/main/docs/api/browser-window.md

## Limits

Fraction-of-a-second answers from every provider are not established. The tested
ChatGPT account is paused after a usage limit; provider/account availability must
recover before that route can answer. Screen-specific inference latency still
depends on the selected vision model. Full microphone transcription latency and
every third-party screen-sharing application were not retested in this pass.

Durable finding: measure capture/OCR separately from provider time before blaming
the selected model. A dense-screen OCR timeout can add an entire second OCR
pipeline before the answer request begins.
