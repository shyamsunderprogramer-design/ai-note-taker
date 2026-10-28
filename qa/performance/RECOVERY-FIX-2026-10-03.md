# Recovery repair — October 3, 2026

Implemented in source:
- Runtime-catalog automatic local fallback sorts eligible local models by installed size, rather than taking Ollama listing order. Explicit user selection, enabled settings, and vision/text capability filters remain in effect.
- Exhaustion reports no-answer versus partial-answer status plus sanitized per-model failure categories and next checks; raw provider errors are not exposed.

Validation:
- 22 backend recovery tests pass.
- 98 desktop/web tests pass.
- Web build passes.
- Live production recovery-code test with synthetic PNG asking “What is 2 + 3?”: OpenAI and Google returned unavailable in this test process; local minicpm-v4.6:1b completed with the correct answer in 2.91 seconds, after two recoveries. See results/2026-10-03-recovery/synthetic-screen.json.

Limits:
- This does not establish why the previously running desktop's cloud requests failed; its credentials may differ from the test process.
- The normal backend on port 8000 was offline at the diagnostic check.
- Source changes and web build are complete; an already installed packaged ANT application has not been rebuilt or replaced. It must run the updated source/build to receive the fix.
- Full GUI screen capture, OCR, and desktop launch were not part of this live recovery-code test. The screenshot was synthetic and supplied directly to the production provider adapter.
- The typed Enter issue remains separate and unresolved.
