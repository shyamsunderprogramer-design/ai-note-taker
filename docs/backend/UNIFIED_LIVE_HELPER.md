# Unified Live helper

Start **Live helper** beside the recording button in the desktop app. One explicit session starts microphone capture, requests system/remote audio through the existing platform bridge, enables screen capture, and uses adaptive assistance. No interview/meeting/coding mode selection is required. Stop with **Stop live** or the recording stop control.

During a Live helper session, Enter with typed text submits that text without stopping capture. Empty Enter requests help: it cuts a pending spoken utterance for transcription, or asks about the latest completed speech/current context. It does not stop the session or cancel an already pending answer. Starting the session moves keyboard focus to the text input, avoiding accidental activation of the focused Stop live button.

The existing local transcription WebSockets deliver completed utterances from both sources. The desktop retains statements as well as questions, even while answer generation runs. Completed answerable questions use the normal recovery/provider route with relevant speech, current screen observations, chat history, and resume/JD context. Microphone and remote audio labels describe sources; they are not verified speaker identities. Existing platform permissions still control whether either capture succeeds.

The compact information icon opens session status, exact quotations mentioning commitments or decisions, current screen text, and a separately streamed code/error guidance card. The panel floats over the page and stays closed by default; click outside or press Escape to close it. Transcripts remain in background session context and are hidden from the main screen. Quotations are observations, not verified assignments: the app does not infer owners, deadlines, agreement or successful execution from those quotations. Existing meeting summarization uses actual participant speech when available, instead of treating AI answer drafts as meeting statements. The summary control becomes available with captured conversation.

## Concurrent vision and synthesis

A non-overlapping screen sampler runs every three seconds. It compares 64 × 36 grayscale thumbnails; fewer than 3% of samples changing by more than 20 brightness levels suppresses repeated OCR. An unchanged screen refreshes OCR after thirty seconds. This is a coarse pixel comparison, not a perceptual hash or guaranteed detection of every small code edit. On-demand explicit screen questions still take a fresh capture. OCR has a six-second deadline; capture waiting has a five-second deadline.

Recent cached captures can satisfy normal questions without serially repeating OCR. Disabling screen context pauses the sampler and removes cached screen context. Missing screen permission keeps listening available and reports degraded screen status.

Recognized screen errors trigger a separate, bounded streaming request using enabled provider candidates. This worker does not occupy the main answer ticket or stop microphone capture. A newer changed error cancels its predecessor; stopping the session cancels that worker. Guidance describes a possible explanation/next step; it does not claim to modify code. The automatic error detector is deliberately a small lexical detector, not a general autonomous visual reasoning model.

The normal spoken-answer scheduler preserves questions in order. It may still queue follow-ups behind an unfinished answer. No speech is generated automatically; reading an answer remains a user action. Browser echo cancellation is requested for microphone capture, but this is not proof that all system-loopback feedback is eliminated.

## Speech corrections and answer quality

Live spoken questions have a 650 ms correction window. A short correction from the same audio session can revise the pending question instead of producing a separate answer. Clear spellings of CI/CD are normalized; ambiguous DevOps acronyms request clarification or carry an explicit assumption. Raw observations remain unchanged in conversation memory. This does not repair the underlying speech recognizer.

General spoken technology questions omit unrelated screen observations and screenshots. Questions referring to the screen still receive visual context. Spoken prompts request short, natural explanations and prohibit invented acronym expansions or unsupported experience claims. Resume grounding additionally checks personal experience claims for a bounded set of common DevOps tools; this is not exhaustive fact verification.

When an enabled backup is available, cloud recovery has an absolute four-second first-content deadline (twelve seconds for detailed/code/reasoning requests). Metadata does not extend that deadline. Local models and requests without a backup retain the existing timeout. This bounds a stalled first cloud attempt, not total response latency.

## Session memory and persistence

Opening a saved conversation defaults to a participant-only Transcript view, with a separate AI answers button. Microphone and Remote audio labels identify capture sources, not verified people; speaker audio leaking into the microphone can be attributed to that source. Chat messages and AI drafts are never used to reconstruct missing participant speech. Older conversations without stored speech show an unavailable message.

New saved sessions retain a separate participant transcript, bounded to 20,000 utterances and 2,000,000 characters, outside the short AI working window. Older records can display their retained speech and archived excerpts; missing historical speech cannot be recovered. Partial utterances are excluded. The transcript remains inside the encrypted conversation record and is hidden from the live screen.

Recent working speech is bounded to 200 utterances / 32,000 characters. Relevant recent observations use a three-minute window and a 12,000-character prompt budget. Evicted speech is stored as bounded source quotations grouped into five-minute episodes, at most 30 episodes of 4,000 characters. Relevant older episodes are retrieved by lexical matching; these are excerpts, not AI-generated semantic summaries. Up to 60 commitment/decision quotations are retained.

Speech context, quotations and episodes are saved with the existing encrypted conversation record, including sessions with no chat answers yet. Loading a conversation restores them. New/cleared conversations reset memory. Partial transcripts, raw audio, screenshots, and current screen text are excluded from that persisted context. Memory is bounded, so this is not an unlimited verbatim recording archive.

Starting Live helper temporarily selects adaptive assistance and enables screen capture. Stopping restores the prior mode/screen setting. The legacy always-on microphone control is disabled during the session to prevent a second competing capture/transcription pipeline. The existing recording lifecycle and native system audio bridge are reused.

## Validation and architecture boundaries

Controller and context tests cover concurrency, source attribution, deduplication, bounded memory, retrieval/restoration, startup rollback, stale OCR exclusion and cleanup. Real WebSocket route tests verify complete statements are emitted without triggering unnecessary answers. A browser fixture verifies speech ingestion during pending OCR, independent streamed error guidance, narrow/desktop layout and stop behavior. Production-page browser smoke verifies both session scripts initialize with the full app.

Audio capture, OCR and AI responses in the focused browser fixture are simulated. This release has not established a live device speech-to-answer latency or a universal sub-300 ms target. Restart the application/backend to load the changed scripts and utterance protocol.

This implementation uses the app's existing transcription/provider adapters. It does not add a bidirectional provider Live API, ScreenCaptureKit video stream, non-blocking provider function tools, a new native overlay window, or automatic semantic topic summaries. The app's existing floating window remains available. Those are distinct architectural extensions, not interchangeable names for the implemented pipeline.

The supplied Gemini architecture describes a feasible optional provider path: Google's current documentation lists [`gemini-3.8-live`](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) and [Live API tools](https://ai.google.dev/gemini-api/docs/live-api/tools). This support is provider/model specific; it does not establish equivalent native Live interfaces or a complete-answer latency guarantee across all providers.
