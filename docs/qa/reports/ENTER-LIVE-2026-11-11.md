# Live Enter investigation

Status: DONE_WITH_CONCERNS. The blank numeric answer is fixed and was verified in
the user's normal desktop profile. Connected ChatGPT latency remains high.

## Observed symptoms and causes

- Initial live accessibility inspection showed Connected accounts selected, no
  enabled ChatGPT connection, and Providers open. Typed Enter reached submission,
  but screen capture/OCR ran before the connection error became visible.
- The account subsequently reported enabled. The actual Enter test, “What is
  2 + 2? Answer briefly.”, completed through GPT-6.1-Sol on the ChatGPT plan in
  22.9 seconds. Saved answer text was `4.`, but the bubble was blank. Running the
  production formatter on that text returned an empty ordered list. This is a
  confirmed rendering defect, not a missing model response.
- The existing diagnostic launcher passed a bare main.js to Electron. That chose
  Electron's default profile rather than the ai-note-taker package profile.
  Earlier greeting/microphone checks in that profile are not counted as proof of
  the user's normal-profile behavior. The launcher now passes the package
  directory and reports app name/profile. Final verification used a direct
  package launch and raw loopback CDP; the normal profile path was confirmed.

## Changes

- Ordered list markers now require whitespace and nonempty content. Numeric
  answers (`4.`), decimals (`3.14`) and bare letter answers remain visible;
  ordinary ordered lists still render as lists.
- Typed subscription questions check the locally known ChatGPT grant before
  capture. Missing connections produce an actionable error without marking the
  question as a failed screenshot. Ollama validation and quota fallback remain
  in their existing routes. There is no silent switch to API-key billing.
- Error bubbles are brought into view when automatic following is active, while
  a reader who scrolled up retains their position.

## Evidence and scope

- Numeric-answer regression failed before the fix with an empty `<ol>` and passed
  after it. Missing-account regression failed before the preflight fix and now
  verifies no capture/answer request, preserved question and cleared busy state.
- Repeated the identical question using real Enter in the normal profile with
  the connected ChatGPT account. The app displayed `4.` and completed in 26.8 s;
  no renderer errors occurred. The screenshot is
  `/tmp/ant-live-enter/direct.png`. This is a live provider test, not a mock.
- Desktop suite: **257 passed**. Renderer suite: **29 passed**. Asset check:
  **84 references resolved, 20 scripts syntax-checked**.
- The user's selected connected account was retained. No password was written
  to a script or used to bypass sign-in. Existing authentication restored itself.
- The scope included the renderer, regression tests and diagnostic launcher;
  no module freeze was acquired across those directories. No installer was built.

The safety fact for the formatter change is that a real list item still has
separated content; the executed tests cover that case and the live reproduction
proves the previously empty response now renders. The preflight only reads grant
status and does not connect accounts, change providers, or initiate capture.

Remaining concern: this investigation does not establish subsecond ChatGPT-plan
responses, microphone transcription latency, or every keyboard-focus scenario.
Enter inside a Providers control still has that control's normal behavior.

Durable learning: a received numeric answer can disappear when a permissive list
parser accepts a bare number and period. Compare raw saved text with rendered
content before blaming transport. Launch the Electron package directory when
testing a user's profile; launching its main file can select different settings.
