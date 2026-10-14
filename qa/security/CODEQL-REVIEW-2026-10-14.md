# CodeQL false-positive review — 2026-10-14

Reviewed against `235248f` on `ux-sprint`. These nine reports concern observable Python behavior that must remain. They are candidates for explicit **false positive** triage, with this evidence recorded on each alert. No query, path, or security rule is disabled by this review.

| Alert | Finding | Why the reported statement is necessary |
| --- | --- | --- |
| #1682, #1683 | `await reader` in `backend/modules/voice/local_clone_engine.py` | Joins the stderr-draining task before reading its retained error tail and during subprocess cleanup. Awaiting a task suspends until completion and propagates errors/cancellation; removing these statements can leave a child task running. `test_local_clone_engine.py` exercises timeout/cancellation cleanup. |
| #1514 | `await transcribe_task` in `backend/routes/transcription.py` | Joins the outgoing transcript worker before obtaining the final transcript and stopping its transcriber. `test_transcription_session_lifecycle.py` exercises final-tail preservation and worker shutdown. |
| #848 | `await transcribe_task` in `backend/core/main.py` | The legacy WebSocket handler uses the same worker-join pattern. The statement is an `await` expression, not a discarded reference to a task. |
| #1512 | `await monitor` in `qa/performance/ai/local-stream.py` | Waits for the heartbeat coroutine to observe `finished` and complete before reading the latency samples it produces. Removing it changes sampling and can leave a pending task. |
| #1451 | `_failed = True` in `backend/modules/voice/apple_speech.py` | The next `transcribe_cached()` call reads this module state before entering the failed GPU runtime. `test_gpu_failure_falls_back_without_repeating_a_broken_runtime` verifies two calls invoke the broken runtime only once. |
| #836 | `_IMPORT_ATTEMPTED = True` in `backend/modules/voice/rvc_engine.py` | The next `_get_tts_rvc_class()` call reads the flag and returns the cached class or cached unavailability. `test_rvc_import_cache.py` verifies an unavailable optional import is attempted/logged once across two calls. |
| #835 | `_vision_getter = _gvm` in `backend/modules/ai/ocr_service.py` | Subsequent `_get_vision_model()` calls read and invoke this cached getter. `TestGetVisionModel.test_caches_vision_getter` verifies that the cached callable is used. |
| #1460 | `prepare` in `qa/performance/ai/quality-comparison.py` | `reasoning_payload()` calls this saved original function after replacing `ai_router.prepare_text_payload` with the wrapper. Removing the binding breaks the explicitly enabled reasoning experiment; calling the replacement recursively would also be incorrect. |

The scanner's [ineffectual-statement rule](https://codeql.github.com/codeql-query-help/python/py-ineffectual-statement/) concerns expressions without effects; joining asynchronous work has effects. Its [unused-global rule](https://codeql.github.com/codeql-query-help/python/py-unused-global-variable/) concerns assignments never read; the four cache/wrapper values above have explicit consumers.

Other findings were corrected in source. In particular, the graph-driver report (#834) prompted a resource-lifecycle repair: a failed candidate driver is closed before retry, and only a verified driver is cached. This report is not included in the false-positive list.

Triage records are reversible and remain visible in GitHub's alert history. They do not imply all repository branches, cloud templates, or optional downloaded runtimes have been audited successfully.
