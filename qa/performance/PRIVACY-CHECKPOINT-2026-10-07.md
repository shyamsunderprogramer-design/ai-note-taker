# Cross-platform privacy checkpoint — 2026-10-07

Implemented shared Windows, macOS and Linux privacy controls:

- Normal launches disable remote debugging and developer tools. Development QA requires `ANT_ENABLE_LOCAL_QA=1`; packaged builds ignore this opt-in.
- Diagnostic file logging requires `ANT_DIAGNOSTICS=1`. Credential redaction applies before Electron transports and to formatted Uvicorn access records. Voice pipeline diagnostics no longer print transcript or answer snippets.
- Private conversation starts a fresh chat and prevents history persistence and graph ingestion. Leaving private conversation starts another fresh chat. Existing saved history is preserved; cloud requests still leave the device.
- Screenshot capture defaults off for new profiles; opening history cannot silently enable capture. Existing explicit capture preferences are retained.
- Capture exclusion is applied to registered auxiliary windows as well as the main window. State reads actual Electron flags and reports incomplete protection.

Platform limits: Windows requests the OS capture-exclusion flag; macOS requests content protection but ScreenCaptureKit can still capture protected windows; Linux capture exclusion is unsupported. None of these flags establishes external verification. Installation files, OS records, security audit records, network connections and provider records are not erased or concealed.

Validation: 13 Node privacy tests passed, including Windows/macOS/Linux capability branches, auxiliary windows, private-session asynchronous persistence and credential redaction. 18 Python redaction/transcription lifecycle tests passed. Web production build passed with existing classic-script bundling warnings. These are automated tests, not external-recorder tests or validation on physical Windows/Linux machines. Restart the app to load Electron changes.

Related checkpoint: RESUME-CHECKPOINT-2026-10-07.md. Existing interview videos and histories were preserved.
