# Real desktop audit, 2026-09-19

## Verdict

**The application is not release-ready. Repair the existing application before considering a full rewrite.** Its login, native microphone recording, explicit local-model answering, resume context persistence, and basic job tracking work. Several integration defects and misleading success states make the product feel unreliable even where the underlying services work.

This conclusion follows an actual signed-in Electron session, not unit-test counts or mocked browser responses. No production fixes were applied during this audit.

## Method and limits

- Launched the actual `electron/main.js`, with its real preload and real FastAPI backend, using the supplied test account and an isolated desktop profile.
- Exercised actual controls with Playwright attached to Electron. No mocked AI, authentication, transcription, or feature API responses.
- Used a synthetic resume and synthetic questions. Played a known speech recording through the computer and recorded it through a real live microphone track twice.
- Local inference used the installed Qwen model. Default Auto used its configured provider race and displayed a Groq model label.
- Test credentials are not included in the report or artifacts. The temporary credential input file was removed immediately after reading it.
- A debugger connection issue caused a duplicate job/study setup attempt. Two sample job records may remain in the test account. The connection issue was separated from product failures. Blank overlay windows were later reproduced as a product defect with an explicit exception.
- Timing below is wall-clock time observed by the audit driver unless explicitly labeled as the app's displayed timing. Preliminary `firstVisibleSeconds` in `core.json` includes model-label detection, so it is **not valid first-token latency** and must not be presented as such.

## Observed behavior

| Feature | Result | Actual observation |
| --- | --- | --- |
| Sign-in | Pass for test account | Real desktop login reached the main interface. |
| Default Auto answer | **Fail, repeated twice** | Model label and about 0.2 s completion badge appeared, but the answer bubble was empty. No actionable error was displayed. |
| Explicit model selection | Pass for Qwen | Selected `qwen3.5:9b` through the toolbar; responses displayed that model. Other installed models were not exhaustively exercised. |
| Resume upload | Pass for Markdown | Uploaded sample resume; filename and Remove appeared. Other formats were not exercised through Electron in this audit. |
| Resume persistence | Pass | Attachment survived actual page reload and remained available to prompting. |
| Resume removal | Pass | Removed attachment, reloaded, confirmed context was absent and status hidden. |
| Resume-grounded answer | Partial pass | Answer used the supplied Python/Kubernetes project and 900 ms to 120 ms metric; completed in 6.7 s. |
| Missing personal facts | **Fail in answer quality** | Resume only said no AWS certification was listed. Answer asserted the person holds none and added an unsupported career explanation. Absence of evidence became a personal claim. |
| Long technical answer | Functional, quality incomplete | A multi-part Kubernetes question in Code/Detailed completed in 8.7 s. It covered requested checks, but produced a dense paragraph and repetitive sentence openings. This is not proof of general answer quality or latency. |
| Enter start/stop | Pass, two native cycles | Both presses started/stopped the actual MediaRecorder. A live enabled microphone track was present. |
| Final speech transcription | Pass on clean playback fixture | Both cycles correctly transcribed the full meeting sentence, including Maya, Daniel, and Friday. Not tested across accents, noisy rooms, or real calls. |
| Live preview transcription | **Poor quality** | Preview omitted words and produced fragments such as “Please. the project summary ...”. Final transcript was more accurate. |
| Recording-to-answer latency | Measured, not universally fast | Entire cycles took 16.0 s and 11.3 s, **including playback/recording time**. App displayed AI times of 5.2 s and 2.2 s. These are not 16/11 s post-stop measurements. |
| Meeting-answer grounding | **Fail in answer quality** | Answer said “I have made sure everyone knows” although the app had not notified anyone. Added filler about everyone knowing their roles. |
| Protection toggle | Partial pass | Button label and native enabled state changed both ways. Capture exclusion in Meet/Zoom/Teams was not verified. |
| Screenshot attachment | Partial pass | Attachment eventually appeared. Initial 2 s check was insufficient and is superseded by the longer check. OCR preview started with “We need to extract all visible text ...”, exposing reasoning instead of clean extracted text. |
| Caption overlay | **Fail** | IPC raised `ReferenceError: isProd is not defined`. |
| Interview overlay | **Fail** | Same `isProd` exception. |
| Job tracker | Pass for create/read | Sample application saved, appeared in the Saved column, and survived reload. Editing, deleting, and every pipeline transition remain unverified. |
| Study-plan generation | Pass for generation | Produced a 30-day plan with 44 tasks and 33 study hours. |
| Study-plan continuation | Incomplete | Returning to the page showed setup, not restored tasks. Completion persistence could not be exercised from that state. |
| Interview simulator | **Fail** | Create request returned HTTP 405; UI still showed a question and an “Interview Complete” section with zero questions. |
| Pre-interview prediction | Limited | Sample company returned zero predictions and a generic checklist, with a low-confidence label. No evidence-based company prediction was established. |
| Original resume review | Pass for returning a result | Text analysis returned score 35, section scores, matched keywords, and improvement suggestions. Score validity was not assessed. |
| Resume Review V2 | **Fail, reproduced** | HTTP 401 while signed in; UI remained on “Analyzing” with no completed score. |
| Cognitive graph | **Fail to initialize** | Stayed on Connecting/Loading, including an additional 12 s wait. No populated graph appeared. |
| Analytics dashboard | **Partial/fail** | Dashboard loaded, but company comparison returned HTTP 405. Displayed “+12% this month” and “+3 new” with zero interviews; those strings are hard-coded in HTML. |
| Conversation history | Partial pass | Four test conversations were listed; opening one restored its question and the previously empty Auto response. |
| Export | **Unverified** | Export control was exercised, but no browser download appeared. Code uses a native save dialog, so absence of a browser download is not proof of export failure. File-save completion was not verified. |
| Settings tabs | UI pass only | General, Providers, Models, Voice, Clone, Data, and Integrations opened. This does not validate each service behind those tabs. |

## Representative real responses

Resume-based project answer:

> My most relevant project was building a Python inventory API for Acme that we deployed on Kubernetes. We added Redis caching to the system, which reduced the p95 latency from 900 ms down to 120 ms.

Unsupported conclusion from a missing resume fact:

> I do not currently hold any AWS certifications based on the resume provided.

Unsupported action claim after transcription:

> I have made sure everyone knows to send the project summary by Friday.

These examples show why transport success and a correctly displayed model name are insufficient acceptance criteria.

## Source findings explaining failures

- `backend/routes/ai.py` picks the Auto race winner upon `event: meta`, before proving that the provider supplied answer text. This is a concrete defect consistent with the repeated empty-answer result. Provider-specific error handling still needs tracing before claiming it is the only cause.
- `apps/web/interview-simulator.js` requests `/interview-simulator/create` using GET; `backend/routes/interview.py` declares POST. Error JSON is allowed to flow into a misleading session UI.
- `apps/web/analytics-dashboard.js` sends GET for company comparison; `backend/routes/analytics.py` declares POST.
- `electron/main.js` references undefined `isProd` when loading both overlay pages, after constructing their windows.
- `apps/web/js/cognitive-graph.js` contains an empty DOM-ready callback saying another component initializes the graph, but the page does not load that component. Fix initialization before attributing the loading screen solely to graph-database availability.
- V2 resume analysis has an additional request-contract discrepancy: its pasted-text branch sends JSON while the server endpoint accepts form fields. The observed 401 must be fixed first, then the payload contract verified. Do not stop after adding authentication.
- Analytics improvement labels are literal HTML strings. Remove or replace unsupported metrics with actual data.

## Recommended repair order

1. **Reliable answer path:** Auto must select a provider only after usable content; empty streams and provider failures must produce an actionable result. Add a real-account regression case for the exact blank answer.
2. **Grounded, useful answers:** preserve uncertainty about missing resume facts; never claim notifications or actions were completed; use readable paragraphs. Agree on several accepted real questions and evaluate content, not just timing.
3. **One authenticated API contract:** align methods, payloads, and errors for interview practice, analytics, and both resume-review versions. Failed requests must not leave success-looking screens or permanent spinners.
4. **Desktop functionality:** repair overlay initialization; keep screenshot capture separate from clean OCR and vision answering. Validate protection with the intended screen-sharing method.
5. **Secondary-feature completeness:** restore study plans, initialize the graph, complete export/save testing, and replace static analytics claims.
6. **Release gate:** rerun the real desktop flows, including long resume context, cold model load, warm model load, two microphone cycles, reload persistence, failures, and cancellation. Measure post-stop transcription, first answer text, and final completion separately.

Do not begin a whole-app rewrite on this evidence. The working core supports targeted repairs. After these integration and answer-quality defects are resolved, simplify duplicated streaming and authentication paths incrementally.

## Explicitly unverified

Voice cloning and TTS quality; paid-provider quality across every listed model; CRM, calendar, phone, team, and SSO integrations; real meeting-platform system audio; actual capture protection against third-party recording; mobile apps; browser extensions; packaged installers and updates; production deployment; exhaustive file-format compatibility; every mode/provider combination; long-term persistence and multi-account isolation; adversarial security testing.

No claim that “all features work” is warranted.

## Evidence

Artifacts are under `results/2026-09-19-account-audit/`:

- `login.json`, `core.json`, `desktop.json`, `verify.json`, `extras.json`.
- `default-answer.png`, `long-detailed-answer.png`, `verify-resume-review-v2.png`, `page-interview-simulator.png`, `page-cognitive-graph.png`.

Reproduction tooling: `qa/performance/live/account-audit-launch.mjs` and `account-audit.mjs`. These tools require a running local Ollama/backend and test credentials supplied separately. They do not embed credentials in source.
