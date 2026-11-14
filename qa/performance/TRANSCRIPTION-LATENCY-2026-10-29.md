# Transcription latency investigation — 2026-10-29

Removed the five-second readiness wait before CPU transcription. `get_model()`
already serializes model loading with its lock; a request can load immediately
when startup warmup did not run. Live microphone drafts now skip a busy Apple
GPU and pending completed utterances instead of joining the decoder queue.

## Local measurements

Apple Silicon, existing AINT_Venv and cached Whisper small models. Input was a
6.4-second synthetic Samantha recording: “Please send the project summary by
Friday. Maya will review the budget, and Daniel will schedule the next meeting.”
No microphone or private recording was used and no provider was called.

| Path | First transcription | Next two transcriptions |
| --- | --- | --- |
| CPU before (HEAD handler, no warmup) | 6.664 s | 1.093 s, 1.081 s |
| CPU after (no warmup) | 1.280 s | 1.025 s, 1.028 s |
| Apple GPU baseline | 4.483 s | 0.103 s, 0.102 s |

All runs returned the reference words. Times measure `transcribe()` after audio
decoding; they exclude recording, speech-boundary detection, upload, rendering,
and AI answer generation. The CPU fix does not remove GPU initialization time.
The GPU benchmark required execution outside the sandbox because Metal is
unavailable inside it. These single-clip results are not human-speech acceptance.

## Validation

45 tests passed across `test_live_speech_decode.py`, `test_apple_speech.py`,
`test_uploaded_audio.py`, `test_browser_transcriber_context.py`, and
`test_transcription_session_lifecycle.py`. New checks cover immediate CPU loading,
nonblocking previews, and releasing the GPU lock after an exception.

The desktop was reusing a separately started backend on port 8000, without
`--reload`. Changes require that backend to restart; reopening only the desktop
can reuse the old process again. No running session was interrupted during this
investigation. Live microphone latency remains to be verified after restart.
