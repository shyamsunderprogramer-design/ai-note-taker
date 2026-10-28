# Screen context and question integration

Implemented one screen-context path for typed questions, completed microphone recordings, and always-on transcribed questions. With screen context enabled, it captures a fresh screen at submission time. An explicit screenshot attachment takes priority. With screen context disabled and no attachment, it sends only the question.

Desktop capture serializes requests, hides all visible ANT windows while the compositor captures the display under the pointer, and restores window visibility and focus even on failure. This uses a brief hide/show, not an OS-level invisible-window exclusion guarantee across every platform. Manual and periodic AI-context captures share the helper.

Readable screen text is extracted through OCR and combined with the actual typed or transcribed question. Screen content is labeled reference data rather than instructions. This permits the selected text model, including Groq GPT-OSS 120B, to answer from screen text without requiring unsupported image input. If OCR finds no text, the existing vision path remains; charts and image-only interpretation are not validated by this run. Capture failure does not silently discard enabled context.

## Verification

- 60 desktop tests passed; production web build passed.
- Actual Electron capture with a separate visible reference page behind ANT: reference figures were readable and ANT was absent. Inspected the saved image visually. Evidence: `results/2026-09-23-screen-exclusion.json`; image `/tmp/ant-visible-desktop/excluded-app-screen.jpg`.
- Native OCR read Cedar budget $4,800/spent $6,200 and Maple budget $3,000/spent $2,700.
- Cached Whisper transcribed the synthetic question as “which project is above budget and by how much.”
- Actual Groq requests combining that captured/OCR screen with typed and transcribed questions both correctly returned **Cedar, $1,400 over budget**, with no generation errors, in approximately 0.76 and 0.71 seconds respectively. Evidence: `results/2026-09-23-screen-pipeline.json`.

The app restarted at sign-in. The full signed-in UI combined-input check is pending the user signing in directly; no authentication was bypassed. Speech testing used a synthetic audio file through the production transcription function, not a physical microphone. The earlier typed-question desktop checks on September 22 did not include screen context.

## Signed-in live test and observed failure

After the user signed in, exercised the actual Electron UI with a visible browser reference page behind ANT, without injecting audio or calling transcription directly:

- Typed the budget question through the app input. The app captured the external screen, extracted its text, called Groq, and displayed the correct Cedar/$1,400 answer. Total check time was 1.80 seconds (model badge 0.8 seconds).
- Clicked the actual recording button and waited for `MediaRecorder` to record from the selected microphone. The resulting user message was “Do you know about Kubernetes? How can you write a bad script for... you”. The app attached the same reference page, excluding ANT, and returned an unhelpful refusal. This was **not** a successful voice accuracy/answer acceptance check. The 90.34-second harness time includes the recording/user-interaction window; it is not model latency.
- Inspected the screenshot attached to that microphone message, independently confirming the reference page was present and ANT was excluded. Confirmed recording had stopped.
- Updated the combined prompt to use screen content only where relevant, permit general technical answers when the screen is unrelated, and request clarification for an incomplete/ambiguous question rather than guessing its purpose.
- Replayed the **exact captured transcript** through the visible UI after reloading the updated frontend. The answer now explained Kubernetes briefly and asked what the script should do. This validates the answer-handling fix, **not** another microphone recording or proof of transcription accuracy. The user has been asked to confirm what they actually said; “bash script” is only a possible mishearing, not an established correction.

Evidence: `results/2026-09-23-live-screen-microphone.json` preserves the first failure, and `results/2026-09-23-voice-question-replay.json` preserves the corrected replay. Actual rendered screenshots are in `/tmp/ant-visible-desktop/screen-typed.png`, `screen-live-microphone.png`, and `screen-replayed-microphone-question.png`. All 60 desktop tests and the web build passed after the final prompt change. The app is left open with the latest answer; the microphone is off.

## Blinking repair

The initial hide/capture/show approach caused visible blinking during periodic capture. On macOS it is now replaced with native ScreenCaptureKit application exclusion, using `SCContentFilter(display:excludingApplications:exceptingWindows:)` and `SCScreenshotManager`. The native helper excludes ANT's process while leaving its windows and focus untouched. A native failure is reported instead of silently falling back to hide/show. Other platforms retain the earlier capture fallback; this verification covers macOS only. The development build compiles the Swift helper into a private per-user cache and requires macOS 14+ and the Swift toolchain.

Restarted the actual app with the new implementation and re-enabled periodic capture at three-second intervals. Placed a distinct visible “ANT SELF CAPTURE 9274” marker inside ANT, then captured a separate reference page behind it. The reference page was readable and the ANT marker was excluded. Observed 12 seconds of repeated capture: ANT stayed visible, with no hidden visibility events. All 62 desktop tests passed. Evidence: `results/2026-09-23-no-blink.json`. The marker was removed after testing, and the app was left open.

API reference: [Apple ScreenCaptureKit content filters](https://developer.apple.com/documentation/screencapturekit/sccontentfilter).
