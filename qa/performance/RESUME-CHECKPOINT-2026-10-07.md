# Resume checkpoint — 2026-10-07

Branch: `ux-sprint`. Task: reduce unified live assistant latency, retain continuous listening, and handle a panel follow-up while the candidate is speaking. Implementation and this checkpoint are committed together; use `git log -1` for the checkpoint commit.

## Implemented

- Optional cached Apple Silicon MLX Whisper-small recognition, serialized across sources, prewarmed on live start; CPU fallback on unsupported hardware or accelerator failure. Runtime never downloads a model implicitly.
- Faster live utterance settling, bounded cross-source question deduplication, short relevant prompts, reduced Groq live completion reservation, and a race between at most two configured cloud providers for Auto live responses. Explicit model choices remain explicit. Existing recovery and resume grounding remain enabled.
- Interrupting follow-ups carry the original question and recent provisional candidate speech. Pending old answers are cancelled; stale queued answers cannot overwrite the follow-up. Provisional speech stays out of saved history and decisions.
- Unified microphone, remote audio and screen following; Enter keeps listening active. Ordinary spoken questions avoid unrelated OCR. Compact header status, participant-only history transcript, encrypted conversation migration, and local clone integration are included as dependent work already requested in this session.
- Native audio ownership cleanup and single IPC subscribers prevent repeated starts/reloads from duplicating capture.

## Verified on this Mac

Real Electron app and native remote audio capture, real ASR and configured AI providers; synthetic spoken interview questions, no mocked answers.

| Replay | First visible answer after question audio ends |
|---|---:|
| Kubernetes incident | 1.548 seconds |
| CI/CD pipeline | 0.614 seconds |
| Terraform state locking | 1.072 seconds |

Three questions produced three completed answers without duplicate cards. Both source channels were observed. The Terraform answer avoided the earlier incorrect dependency-lock-file deletion advice.

Panel follow-up test: the original question and ongoing provisional candidate speech reached the request; the follow-up answer completed 540 ms after follow-up speech ended, while live listening stayed active. Candidate PCM was injected into the existing microphone WebSocket; remote speech used actual native capture. This was a simulated panel, not an actual Zoom/Meet call or a verified multi-person diarization test. Tests measure behavior, timing, relevance and completion, not expert technical correctness. The panel answer suggested traffic/read-only-replica changes which require scenario-specific review; generated operational advice is not a deployment plan.

182 targeted Python tests and 107 Node tests passed against an isolated snapshot of the exact staged source (with installed Node dependencies linked); production web build passed in that snapshot with existing classic-script bundling warnings. Video decoded without errors.

## Artifacts

- Desktop: `~/Desktop/ANT Technical Interview.mp4` (updated faster replay, 50.315 seconds).
- Full local replay: `artifacts/live-fast-panel-final-2026-10-07/`.
- Panel results/screenshot: `artifacts/panel-followup-2026-10-07/`.
- Sanitized timing summaries: `qa/performance/results/2026-10-07-live-summary.json`.
- Earlier `artifacts/live-fast-panel-2026-10-07/` is a FAILED quota/fallback regression (third answer technically wrong); do not present it as a passing replay.

The app was left open; live recording stopped at the end of the tests. Credentials, model weights, raw recordings and personal history are not committed.

## Reproduce

Install optional acceleration with `AINT_Venv/bin/python -m pip install -r backend/requirements-apple-speech.txt` on Apple Silicon. Explicitly download `mlx-community/whisper-small-mlx` to the normal Hugging Face cache before enabling GPU recognition. This Mac already has the dependencies and cached model. `ANT_SPEECH_ACCELERATOR=cpu` disables it. Other platforms retain CPU recognition; these GPU timing results do not apply there.

Start the desktop with remote debugging on port 9223 using `node qa/performance/live/visible-desktop.mjs`. Sign in normally, or supply `ANT_QA_USERNAME` and `ANT_QA_PASSWORD` to the recording harness only if needed. No password is embedded in the scripts.

- `node qa/performance/live/record-interview.mjs artifacts/new-interview-run`
- `node qa/performance/live/panel-followup.mjs artifacts/new-panel-run`
- `npm run web:build`
- Python regression files: apple_speech, live_speech_decode, transcription_session_lifecycle, vad_segmenter, stream_recovery, provider_stream_errors, resume_grounding, local_clone_engine, local_clone_routes.
- Node regression files: unified-session-controller, unified-session-context, interview-screen-queue, system-audio, system-audio-ipc-contract, live-helper-enter, conversation-storage.

## Resume next

Sub-second responses are observed, not guaranteed: network, provider quotas, cold model startup and question complexity still vary. Finish a real multi-participant call validation, test interruptions during a still-generating answer in addition to the existing cancellation unit test, and review technical answer quality on held-out scenarios. Named speaker recognition from calendar invitations is not implemented; microphone/remote labels do not establish a person's identity.

There was substantial unrelated work already uncommitted before this task. Only the live assistant and its required source/test dependencies are staged; unrelated documentation removals, security/mobile/job changes and local artifacts remain in the working tree. Preserve them when resuming; do not reset the repository.
