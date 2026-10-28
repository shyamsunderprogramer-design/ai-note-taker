# ANT measured benchmark — 2026-09-14

Latest follow-up: [live WebSocket and visible-answer validation](LIVE-VALIDATION-2026-09-14.md).
Complete synthetic questions now reach live assistance across reconnects. Real-call
acceptance and hands-on competitor measurement remain pending; generated answers
still require factual review.

**Result: the declared local synthetic profile passes its measured gates.**
This is not a certification of commercial-product parity or production readiness.
The earlier review measured mostly tests and cache performance; this scorecard adds
real local speech inference, AI generation, note persistence, and their connected
processing flow.

Profile: macOS ARM64, Python 3.12, cached Whisper `small`, installed local
`qwen3.5:9b`, Instant mode, 64-token response budget, temperature zero, RAG disabled,
temporary SQLite. No paid providers or real user recordings were used.

## Connected flow

### Follow-up: actual macOS system-audio capture

The production capture helper collected 10.5 seconds in 105 chunks from an
isolated synthetic playback process, with a nonzero signal and no errors. The
captured WAV then passed transcription → local AI → database save/read in three
runs: 0% WER, required facts retained and exact persistence in all runs. Warm
processing took 1.965–2.207 s; first assistance took 0.991–1.216 s. The first run
took 5.837 s total and 4.858 s to first assistance. These intervals start after
capture; they are not live meeting latency. Microphone, Meet/Zoom, WebSocket and
visible live UI behavior remain untested by this fixture. Desktop tests: 51 pass.

Evidence: [capture](results/2026-09-14/system-audio-report.json),
[captured-audio processing](results/2026-09-14/system-audio-pipeline.json),
[competitor comparison](COMPETITOR-COMPARISON-2026-09-14.md).

**Correction to the earlier database-isolation claim:** the database module
overrode the harness environment URL with the application's default SQLite path.
Earlier pipeline/storage runs therefore were not isolated as reported and may
have left synthetic benchmark records there. No existing records were deleted.
Both harnesses now override the module URLs before engine initialization. The
captured-audio results above use the corrected temporary database. A fresh storage
run passed 30/30 notes after reopen, with p95 writes 2.20 ms and reads 0.91 ms;
see [isolated results](results/2026-09-14/notes-isolated.json). Earlier timing
results below are retained as historical measurements, not isolation evidence.

### Earlier file-input measurements

Input: a 6.21-second synthetic meeting recording. The measured interval begins
**after recording ends** and includes decoding, transcription, AI action items,
and exact database save/read. Three repetitions; first run reported separately.

| Check | Declared target | Measured result | Status |
|---|---|---|---|
| Warm full processing flow | ≤4 s | 2.048–2.070 s | Pass |
| Warm first AI assistance after recording | ≤3 s | 1.051–1.064 s | Pass |
| Transcript word error rate | ≤15% | 0% on this clip | Pass |
| Required action-item facts retained | All required facts | 3/3 runs | Pass |
| Save/read content integrity | Exact match | 3/3 runs | Pass |

The first run took 2.452 seconds total. Whisper was preloaded and Ollama could
already hold its model; this is **not** a cold device startup result.

## Component measurements

| Check | Target | Result | Status |
|---|---|---|---|
| Speech accuracy, three synthetic clean-English clips ×3 | Mean WER ≤15% | 1.59% | Pass |
| Speech speed | p95 real-time factor ≤0.5 | 0.160 (0.991 s p95) | Pass |
| Three seconds of digital silence | No transcript | Empty transcript | Pass |
| AI first content, three tasks ×3 | Warm ≤2 s | Worst warm 0.241 s | Pass |
| AI required fact coverage | All required facts | 9/9 responses | Pass |
| AI final-answer output | No thinking passages | 9/9 responses | Pass |
| Event-loop responsiveness during generation | Lag ≤100 ms | Worst 1.50 ms | Pass |
| Note saves, 30 sequential notes | p95 ≤50 ms | 2.52 ms | Pass |
| Note reads, 30 sequential notes | p95 ≤20 ms | 0.86 ms | Pass |
| Notes survive database reopen | Exact content match | 30/30 | Pass |

The AI tasks cover meeting actions, a fact-constrained interview answer, and a
decision/blocker summary. Fact checks are deliberately simple and inspect declared
terms; they do not substitute for a human hallucination or usefulness evaluation.
Percentiles from these small local samples are descriptive, not field reliability
estimates. Targets are project acceptance targets, not claimed industry standards.

## Failures found and addressed

- Original silence transcription produced `you`; silent/invalid audio now bypasses
  inference. Uploaded files now decode/resample to 16 kHz and return plain text.
- Synchronous provider iteration blocked the event loop for about 400 ms. Worker
  iteration now keeps it responsive and closes cancelled streams after pending reads.
- File transcription ran on the event loop. It now runs in a worker, which also
  owns temporary-file cleanup, including after request cancellation.
- The generic prompt forced all tasks into a Slack-message format. It now follows
  the requested task/format and asks for missing facts to remain unspecified.
- The installed `lfm2.5:latest` alias returned truncated thinking passages at the
  Instant token cap. It **failed answer-quality gates**, even after the prompt fix.
  Instant now defaults to `DEFAULT_MODEL` through a separate `MODEL_INSTANT` setting;
  `OLLAMA_MODEL_INSTANT` remains an explicit override. The verified profile is Qwen.
  Explicit LFM selections and other modes/models are not covered by the passing score.
- Mobile Upload was a placeholder. It now sends authenticated multipart audio to
  `/transcribe`, displays the transcript, and supports error/retry and recorder cleanup.

The initial single-task Qwen comparison recorded 3.369 seconds to first content
on its first run, versus about 0.05 seconds warm. Cold model loading is not hidden
inside the warm score.

## Evidence and reproduction

Raw measurements: [results/2026-09-14](results/2026-09-14/).
Relevant artifacts: [pipeline](results/2026-09-14/pipeline.json),
[speech after fixes](results/2026-09-14/after.json),
[expanded Qwen tasks](results/2026-09-14/ai-qwen-expanded.json),
[note persistence](results/2026-09-14/notes.json), and
[failed LFM comparison](results/2026-09-14/ai-after.json).

From the repository root, with the named models already installed and Ollama running:

```sh
AINT_Venv/bin/python qa/performance/voice/speech.py --generate --output /tmp/ant-speech.json
AINT_Venv/bin/python qa/performance/ai/local-stream.py --output /tmp/ant-ai.json
AINT_Venv/bin/python qa/performance/storage/notes.py --output /tmp/ant-notes.json
AINT_Venv/bin/python qa/performance/pipeline/local.py --output /tmp/ant-pipeline.json
```

Speech generation uses macOS Samantha at 170 words/minute. On another platform,
provide the same fixture files with `--fixtures` and omit `--generate`. The pipeline
accepts `--audio` for its meeting fixture. Each script exits nonzero when its gates
fail. The database benchmarks create and remove their own temporary databases.

## Not measured

Live microphone/system capture; noise, accents, overlapping speakers and diarization;
native-device builds; HTTP/auth/UI overhead in the connected pipeline; retrieval
relevance/RAG; cloud-provider cost and latency; concurrent-user load; competitor
comparisons. These require separate workloads before any broader readiness claim.
The existing mobile notification service is still a stub.

Changes are in the workspace. The already-running user backend was not restarted;
restart the app to load the updated code and default model routing.

Regression validation: 1,078 backend tests passed, 59 skipped; 34 mobile tests
passed. A final targeted upload/stream/route check passed 20 tests after import
ordering and redundant cleanup were tidied. Existing device/browser limitations
in the earlier review still apply.
