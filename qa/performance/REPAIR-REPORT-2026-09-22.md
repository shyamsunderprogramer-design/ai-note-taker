# Recording and answer-quality repair, 2026-09-22

The recording, streaming, and cloud-provider repairs are implemented and verified. The cloud follow-up below supersedes the initial local-only result. Local-model accuracy failures remain documented; successful generation does not establish general factual accuracy.

## Cloud follow-up using the existing environment keys

The keys in `backend/.env` load correctly. The earlier local-only investigation missed working cloud access. Live requests confirmed Groq and Ollama Cloud work; OpenAI returns HTTP 401 and Google returns HTTP 403 with a current model. No credentials are printed or stored in these reports.

- Updated Groq choices to current catalog models, with GPT-OSS 120B first for Auto, and updated the default Ollama Cloud model from retired MiniMax M2 to MiniMax M3. Added the current Google Gemini 3.8 Flash choice; its configured credential is still rejected.
- Browser provider discovery now reads backend key-presence flags when the Electron bridge is unavailable. A configured key is described as configured, not verified connected.
- Auto races configured cloud providers first and uses local models only after cloud failure. Failed candidates cannot win on metadata alone; a failure after visible answer text remains an error instead of mixing model answers.
- OpenAI, Google, Groq, and Ollama Cloud adapters report safe provider failures. Incomplete, empty, and truncated streams cannot report success. Google keys travel in headers. Private reasoning is excluded from displayed answers.
- Groq uses grounded meeting/resume instructions and sufficient reasoning budget. Ollama Cloud now applies the shared prompt and conversation context.

### Follow-up verification

- 177 focused backend tests passed, followed by 23 provider-stream tests passing after adding four Ollama Cloud completion regressions.
- Production web build passed (existing classic-script warnings remain).
- Real browser → synthetic resume upload → production provider routing → Groq passed for explicit selection (1.39 seconds) and Auto (1.02 seconds). Provider discovery used the HTTP fallback. Evidence: `results/2026-09-22-cloud-browser.json`.
- All 14 Groq samples completed without API errors. Reviewed examples preserve unspecified resume facts, unassigned tasks, corrected deadlines, proposals versus actions, and the distinction between OOM events and liveness probes. Evidence: `results/2026-09-22-groq-release-quality.json`. These are finite samples, not a guarantee: technical answers still simplify edge cases (such as PostgreSQL updates that avoid index writes), so no universal factual-accuracy claim is made.
- Real Ollama Cloud generation passed through the repaired grounded adapter in 7.57 seconds and correctly left absent certification facts unknown. Evidence: `results/2026-09-22-ollama-cloud-grounded.json`.
- Catalog/status evidence: `results/2026-09-22-cloud-catalogs.json` and `results/2026-09-22-current-cloud-status.json`.

The browser test uses an isolated loopback server and synthetic resume, not the user database or a physical microphone. Existing explicitly selected local models remain selectable and retain the accuracy limitations below.

## Initial recording and local-model changes

- Browser speech previews wait at least three seconds and prefer a quiet phrase boundary, with an eight-second cap for continuous speech. Large audio packets are fully consumed; silence is not decoded.
- WebSocket transcription workers stop on disconnect, including ASGI cancellation. In-flight previews cannot call the client after stop. Starting a worker twice no longer creates duplicate workers.
- A graceful `{"type":"stop"}` control message drains queued phrases in order and includes the final short tail. The complete recording upload remains authoritative for normal desktop recording submission. A hard disconnect discards pending previews rather than decoding audio for a departed client.
- Whisper work runs off the event loop. Worker-to-WebSocket messages are scheduled on the owning event loop instead of writing directly to an asyncio queue from another thread.
- Meeting prompts distinguish explicit actions, proposals, decisions, and completed work. Summary mode no longer demands filler bullets or unsupported sections. Follow-up mode no longer asks the model to invent next steps. Concise answers have a 100-word instruction unless the user requests more.
- Local model streams report an error for a missing completion frame, an explicit generation error, or an output-budget cutoff. These incomplete streams no longer report successful completion or enter the successful-response cache.
- The model comparison accepts an explicit output path, preserves older evidence, covers six cases, and exits unsuccessfully on transport/generation errors. Semantic accuracy still requires review.
- The browser smoke test accepts both `first person` and `first-person` in the resume instruction. Its prior failure was an outdated wording assertion, not an upload failure.

## Verification

| Check | Result |
| --- | --- |
| Focused backend suite covering transcription, session lifecycle, auth, VAD, uploads, models, providers, caching, resume extraction, OCR, async streaming | 154 passed |
| Desktop unit tests | 52 passed |
| Web service-worker tests | 5 passed |
| Production web build | Passed; existing classic-script bundling warnings remain |
| Built browser smoke: sign-in, main app, job tracker, study plan, resume review | All five passed |
| Synthetic speech preview through real cached Whisper | 0.0 word error rate for one 6.21-second clean-English meeting fixture; 1.39 seconds accelerated decoding; worker stopped |
| Built renderer → real resume upload route → production AI stream route → local Qwen → visible answer | Passed in 3.86 seconds, with Acme/Python/PostgreSQL facts and processing cleared |
| Final six-case Qwen generation | Six complete responses, no generation errors; **three of six pass strict semantic review** |

The real browser check uses an isolated loopback QA server without authentication or a user database. Browser recording smoke uses a fake microphone and mocked backend responses. The real Whisper check uses accelerated packet delivery, not microphone capture. This run does not establish human-speech accuracy, real meeting-platform capture, or end-to-end physical-microphone latency.

## Remaining answer-quality failures

Final Qwen samples: `results/2026-09-22-model-quality-acceptance.json`. The filename denotes the acceptance run, not a passing result.

- `missing_fact`: pass. Unlisted certification remains unspecified.
- `meeting`: pass. Three actions retain their own owners and deadlines; missing values are unspecified.
- `meeting_owners`: pass. No deadline or owner is transferred between tasks.
- `meeting_status`: fail. The model invents an action for Omar to obtain test results from a statement that he needs them before agreeing.
- `technical`: fail under strict review. The model correctly identifies kernel cgroups but presents a subsequent restart as unconditional and uses a cgroup-v1-specific control name without qualification.
- `technical_restart`: fail. The model incorrectly says the kubelet kills the process for an OOM event; it also omits the conditional restart behavior despite identifying restart policy.

Reference for review: Kubernetes documents [kernel memory-limit enforcement](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) and [probe versus restart-policy behavior](https://kubernetes.io/docs/concepts/workloads/pods/probes/). These references were used to grade outputs, not inserted into model prompts to teach the benchmark answer.

Gemma and LFM were also tested locally (`results/2026-09-22-alternative-models.json`) before the last concise/system-prompt adjustment. Both had semantic failures. No selected model was silently changed. Cloud access was subsequently tested in the follow-up above. A code or prompt change cannot establish general factual accuracy for these models; the observed failures remain release blockers for a claim of fully grounded answers.

## Reproduction

```sh
AINT_Venv/bin/python -m pytest backend/tests/test_browser_transcriber_context.py backend/tests/test_transcription_session_lifecycle.py backend/tests/test_live_websocket_auth.py backend/tests/test_vad_segmenter.py backend/tests/test_uploaded_audio.py backend/tests/test_ollama_prompt.py backend/tests/test_ollama_memory_limits.py backend/tests/test_provider_transport_regression.py backend/tests/test_race_answer_selection.py backend/tests/test_live_selected_model.py backend/tests/test_live_suggestion_fallback.py backend/tests/test_async_stream_responsiveness.py backend/tests/test_resume_input.py backend/tests/test_ocr_service.py backend/tests/test_cache_manager.py -q
node --test electron/tests/*.test.js
npm --workspace ant-web test
npm run web:build
PLAYWRIGHT_BROWSERS_PATH=/tmp/ant-playwright-browsers node qa/performance/web/browser-smoke.mjs
AINT_Venv/bin/python qa/performance/voice/preview.py --output /tmp/ant-preview.json
AINT_Venv/bin/python qa/performance/ai/quality-comparison.py qwen3.5:9b --output /tmp/ant-model-quality.json
```

The preview fixture is created by the existing `qa/performance/voice/speech.py --generate` workflow on macOS. For the real browser check, start `qa/performance/live/selected-model-server.py`, then run `qa/performance/live/selected-model-browser.mjs --resume` with the Playwright browser path configured.

## Visible desktop follow-up

Launched the actual Electron app with its normal profile and production backend, restored its existing signed-in session, and submitted questions through the visible text input. Explicit Groq and Auto both returned answers. Visual inspection caught a real chat scrolling defect: incoming layout/scroll events disabled following and hid the newest response. Fixed following to pause on reader gestures and resume on a new user question, including the streaming message path.

Repeated both checks after the fix: explicit Groq finished in approximately 1.8 seconds and Auto in 1.4 seconds (2.10/1.73 seconds including the QA settling delay). Both left the viewport within two pixels of the bottom, with no captured JavaScript page errors. Two behavioral scroll regressions passed. Evidence: `results/2026-09-22-visible-desktop.json`; screenshots remain in `/tmp/ant-visible-desktop/`. The app was left open for the user. This live run validates typed cloud questions and their rendering, not physical microphone capture or every application feature.
