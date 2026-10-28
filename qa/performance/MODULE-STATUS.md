# Module verification status

Latest recording/streaming repair: [2026-09-22 report](REPAIR-REPORT-2026-09-22.md). Session cleanup, phrase previews, ordered final transcription, and incomplete-answer errors verified. Cloud follow-up: existing Groq and Ollama keys verified; explicit Groq and Auto passed real browser checks, and 14 Groq samples completed with reviewed grounding improvements. OpenAI returns 401, Google 403. Local Qwen still passes only three of six strict semantic cases. See the report for scope and accuracy limitations.

Previous desktop repair: [2026-09-20 report](REPAIR-REPORT-2026-09-20.md). Integration fixes and native OCR verified; full release remains blocked by observed answer-quality failures and unavailable cloud comparisons. The older checks below are historical.

Updated 2026-09-16. "Verified" below applies only to the stated test, not the whole product.

Latest checks: 1,089 backend tests passed (59 skipped), 50 desktop tests passed, and five browser pages passed smoke checks. Desktop relaunched with these fixes; backend health returned `ok` with authentication enabled. Actual microphone and native dropdown acceptance remain pending.

| Module | Status | Evidence and next acceptance check |
| --- | --- | --- |
| Recording and transcription | Synthetic microphone cycles verified; native check pending | Fixed Stop/Enter submitting live partial text instead of stopping. Two real browser MediaRecorder cycles with fake microphone produce one upload each; Enter and Stop both tested with nonempty partial text. Pending microphone permission cancellation and stale socket events guarded. Verify actual microphone cycles in the desktop app. |
| Selected model and streaming | Local browser integration verified | Production renderer → production HTTP streaming route → local qwen3.5:9b → visible answer, correct model badge, processing cleared: 4.70 s for a short Docker question. Isolated server, concise mode, no microphone/auth/database. Paid cloud providers not exercised. |
| Cloud transport | Regression checks pass | HTTPX streaming arguments, string SSE lines, response closure, and unknown model lookup covered. Live credentials/quotas and model availability remain provider-dependent. |
| Interface controls | Automated checks pass; native selection pending | Desktop suite: 50 passed. Browser smoke covers recording toggle and answer replacement. Real Electron dropdown interaction still requires verification. |
| Capture protection | Toggle checks pass; capture compatibility pending | State and failure handling tested. Screen-capture exclusion depends on macOS and the capturing application; no universal undetectability claim. |

## Integration sequence

Resume input added: Resume + accepts PDF, DOC/DOCX, UTF-8 TXT/Markdown/JSON (5 MB; longer resumes retained in full, with up to 12,000 characters of question-relevant excerpts supplied per answer). Context is held in the current page and removable; the upload endpoint does not save the file. Legacy DOC uses macOS textutil; scanned PDFs require searchable text. The selected answer provider receives the extracted resume as context. Twelve extraction/endpoint tests passed, plus browser upload/removal and deduplication checks. Actual browser → upload endpoint → local Qwen → first-person answer passed in 4.447 seconds with a synthetic Markdown resume; response used Acme/Python/PostgreSQL facts. Raw result: `/tmp/ant-resume-browser.json`. This is not a guarantee against model hallucination.

1. Recording acceptance: Enter starts; Enter stops; repeat; complete transcript matches speech.
2. Model acceptance: select a model; request keeps that model; answer or actionable error appears; no silent fallback.
3. UI acceptance: partial and final output form one answer; processing state clears on success, failure, and timeout.
4. Desktop acceptance: protection toggle reports actual state; test the intended screen-sharing application.
5. Complete flow: repeat recording → transcript → selected model → visible answer and record latency/errors.

The isolated browser check is reproducible with `qa/performance/live/selected-model-server.py` and `selected-model-browser.mjs` after building `apps/web`. It uses only local Qwen and does not open the user database. Raw result: `/tmp/ant-selected-model-browser.json`.

Git review: fetched origin. Relevant historical dropdown and streaming commits 18c9855 and 2c1ae31 are already ancestors of the current branch; no duplicate cherry-pick was performed. Existing working changes were preserved.

## Long-question latency follow-up

The speaker transcription endpoint now runs in FastAPI's worker pool, disables unused word-level timestamps, and uses a single deterministic decoding temperature instead of repeated temperature-fallback attempts. A roughly 25-second repeated synthetic speech recording completed transcription in 1.883 seconds with checked names/deadline present. The prior fallback benchmark was interrupted while stuck in model generation; no valid before/after ratio is asserted. This is not a human-speech accuracy benchmark. The endpoint now logs transcription and speaker-processing durations separately. Detailed Qwen responses still allow 2,000 tokens; user preference for shorter answers is pending.

## Model loading investigation, 2026-09-18

The latest app request selected Qwen 9B, Code, Detailed, temperature 1, and timed out after 30 seconds. Ollama logs also show eviction with 1.9 GiB free and a cancelled model load. An oversized 262,144-token context appears in the scheduler log; this alone does not identify its originating caller. The app's live warmup and nonstream helper omitted context limits. Both now set explicit bounds (warmup 2,048; nonstream 2,048 or 8,192 for resume context). Two regression tests pass. No model is silently changed or explicitly unloaded.

Measured short synthetic Qwen prompts through the app streaming adapter: first answer 8.63 seconds (first text 7.80); subsequent answers 1.50 and 0.90 seconds (first text about 0.27). All checked facts present. These do not measure the user's long question or complete recording workflow. Raw results: `/tmp/ant-delay-qwen.json`.
