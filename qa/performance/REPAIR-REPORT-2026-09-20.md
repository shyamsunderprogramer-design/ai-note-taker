# Desktop repair and benchmark, 2026-09-20

The known integration failures are repaired and the desktop runs. **The full quality benchmark is not yet passed.** Local Qwen still makes some factual errors and adds unsupported details to voice-generated meeting answers. Configured cloud alternatives returned rate/quota errors, so their quality could not be assessed.

## Repairs verified

- Auto selects a provider after nonempty answer text, rather than metadata. Empty responses and mid-stream failures surface errors. Provider failure does not cancel other candidates before an answer exists.
- Explicit model selection is preserved. Auto respects the selected answer mode. Streaming timeouts remain active through response consumption.
- Regular streaming now parses complete SSE frames for its response cache; empty and failed responses are not cached as successful answers.
- Resume answers use relevant facts, missing credentials remain unspecified in the final case, and detailed technical answers use paragraphs. The installed Qwen model has a raw-only prompt template; a request-level repair supplies its official text chat framing without modifying the installed model.
- Instant mode has room for a complete short answer, and Detailed mode takes precedence over its old 64-token cap.
- Enter started and stopped the real microphone twice; both final transcripts matched the synthetic speech fixture. Final answers completed 4.35 and 5.25 seconds after Stop in the last recording run. This is a small fixture test, not a universal latency claim.
- Live preview now waits for three-second phrases. The final run produced one accurate partial phrase and one empty preview before Stop. This reduced the observed garbling but does not establish consistent live-preview quality.
- Resume upload, reload persistence, and removal passed in the desktop.
- Caption and interview overlays opened without the previous undefined-variable exception. The macOS quit flag is set before window closing, allowing clean restarts.
- Protection UI and native state changed in both directions. Third-party screen-share exclusion remains unverified. The legacy audit row names `protection-on`/`protection-off` describe click order; inspect actual labels and native state for the resulting values.
- Interview creation now uses POST and rejects failed HTTP responses. The real page displayed Question 1 of 5 without the prior HTTP 405. Answer evaluation was not exercised by the text-only page driver because that page uses recorded answers.
- V2 resume analysis submits authenticated form data, handles unsuccessful responses, and actually hides its loading state. Real analysis produced results without the prior 401.
- Cognitive graph initializes its component and displays its connected state and data. Analytics sends repeated company parameters with POST; unsupported fixed improvement numbers were removed.
- A generated study plan survives reload. Completing one task changed progress from 0 to 1 and reopening preserved 1. New persisted plans and completion keys are scoped to the signed-in user's token subject; this is not a complete multi-user security audit.
- On macOS, screenshot OCR now uses native Apple Vision text recognition before the existing fallbacks. The authenticated app route returned the exact two-line fixture in 0.274 seconds with `method: apple-vision`; the screenshot button also attached recognized text. OCR runs in a worker thread so it does not block other backend requests.

## Final answer timings

First visible text is observed at a 200 ms polling interval and excludes model labels/loading indicators. Completion includes UI interaction time. Model/context loading state varied between cases.

| Case | First visible answer text | Completion |
| --- | --- | --- |
| default-answer | 3.25 s | 4.47 s |
| resume-answer | 3.45 s | 5.27 s |
| unsupported-experience | 0.82 s | 1.02 s |
| long-detailed-answer | 0.82 s | 8.31 s |
| meeting-actions | 3.05 s | 6.09 s |

## Remaining failures and limits

1. **Model accuracy:** the final Kubernetes answer wrongly attributes an OOM kill to the scheduler. Voice-generated meeting answers still invent agreement, sequencing, or rationale absent from the speech. These responses must not be presented as fully grounded.
2. **Cloud availability:** glm-5.3-flash:cloud, nemotron-3-ultra:cloud, and minimax-m3:cloud returned rate/quota errors before any answer text. No cloud quality or latency comparison is claimed.
3. **Live preview:** still inconsistent before Stop. The complete recording remains the source of the final transcript.
4. **OCR portability:** the native helper is compiled once into a private user cache using installed macOS command-line tools. Compilation is excluded from warm OCR timings. Packaging must prebuild it or provide a supported fallback; other platforms retain existing OCR fallbacks.
5. **Unverified:** real meeting-platform capture exclusion, every installed model and file format, export through the native save dialog, voice cloning/TTS quality, mobile/extensions/installers, and the other external integrations listed in the original audit.

## Validation

54 focused backend tests passed; 16 focused desktop tests passed; production web build passed. Real Electron checks used the supplied test account, actual backend, actual Ollama, and real microphone input. The speech fixture contains no personal information. Synthetic OCR text was checked exactly, not merely for a nonempty response. Test credentials are excluded from artifacts and removed from the temporary launcher input file.

Tooling: `qa/performance/live/account-audit-launch.mjs --verify` runs the answer and desktop checks sequentially; `--ocr-only` checks the authenticated native OCR path. The initial test-account audit remains in `DESKTOP-AUDIT-2026-09-19.md`. Evidence for this repair is in `results/2026-09-20-repair-check/`.

Implementation references: [Qwen's published chat template](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/chat_template.jinja), [Ollama generate API and raw prompts](https://github.com/ollama/ollama/blob/main/docs/api.md), and [Apple text recognition request](https://developer.apple.com/documentation/vision/vnrecognizetextrequest).
