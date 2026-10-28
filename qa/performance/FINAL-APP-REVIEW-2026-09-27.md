# ANT final test and live feature review — 2026-09-27

Full review completed with failures. This report does not certify every workflow as working. No product code or credentials were changed. Existing unrelated working-tree changes were left alone.

## Live walkthrough

The real desktop app was opened and you signed in. Main controls, all seven settings tabs and each expandable settings card were shown, followed by History and eleven feature/overlay pages. The app was returned to its main screen. The independent review guide provides 49 screen captures and 617 control definitions (static and runtime, with intentional duplicates and hidden controls).

Review guide: http://127.0.0.1:8047/

## Test results

| Suite | Result |
|---|---|
| Desktop (Electron unit tests) | 70 passed |
| Web unit tests | 5 passed |
| Mobile unit tests | 34 passed / 5 suites |
| Full backend + startup | 1,173 passed; 49 failed; 61 skipped |
| Focused backend recheck (overlaps full suite) | 68 passed; 1 failed; 2 skipped — confirms streaming tests depend on import order |
| Live API integration (isolated backend) | 37 passed; 20 failed; 2 setup errors — replaces the 59 API skips with an actual run |
| Existing Chromium + Firefox E2E suite | 16 passed; 28 failed; extensionless URL/404 problems in test server |
| Built-web five-page smoke check | Passed; no captured page errors |
| Saved conversations browser acceptance | Passed; synthetic search/sort/pagination/delete-confirmation scenarios |
| Hands-free recovery browser acceptance | Passed; partial preservation, provider attribution, cooldown, cancellation, local fallback and exhaustion |
| Production web build | Passed; existing classic-script bundling warnings remain |
| Browser extension JavaScript syntax | Passed; no actual extension installation/capture test |

Counts overlap: focused rechecks rerun existing tests, and the 59 API integration tests initially skipped were later run separately. Do not sum rows as unique tests.

## Findings and limits

- The full test run is NOT all green. No product fixes were made during this review.
- Desktop overlay error: file:// makes location.hostname empty; caption/interview overlays construct ws://:8000/ws/transcribe. One such error was observed during the tour; both pages share the URL construction.
- Full backend tests mutate streaming functions when importing the app. Forty-eight full-suite stream tests fail after startup converts generators to async generators; the affected tests pass in the focused recheck.
- A clean isolated backend lacks the expected data/recordings directory. The directory-existence test fails; two related checks skip. Existing personal recordings were intentionally excluded.
- API integration: BYOK status returned 500; conversation list/create returned 404; multiple tests received 422 due to payload/contract mismatch; document list expects a list but receives a pagination object; mock interview requests/setup timed out. Individual failures are in the report.
- The legacy E2E server serves plain files without extensionless routing. Many /feature paths return 404. Some shallow page tests even pass on error pages, so their pass count is not feature certification.
- Isolated API logs also contain AuditLogRepository: NoneType object is not callable. This error was also seen earlier in the desktop logs; it needs investigation.
- No real microphone/system-audio recording, paid-provider quota exhaustion, SSO, voice cloning, external integrations, outbound messages, or destructive operations on personal data were performed. Those workflows remain unverified in this final review.
- Previous 30-minute interview run (separate evidence): 60/60 responses and 20/20 recoveries completed, but two numerical hallucinations and recurring cache/cash transcription errors affected quality.
- Runtime model listings differ from the static HTML definitions. A listed model and a token-budget option do not guarantee provider availability or supported context size.

## API integration failure detail

| Test | Failure |
|---|---|
| test_byok_status | assert 500 in [200, 401]  +  where 500 = <Response [500 Internal Server Error]>.status_code |
| test_list_conversations | assert 404 == 200  +  where 404 = <Response [404 Not Found]>.status_code |
| test_create_conversation | assert 404 in [200, 201]  +  where 404 = <Response [404 Not Found]>.status_code |
| test_import_conversation | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_list_documents | AssertionError: assert False  +  where False = isinstance({'documents': [], 'limit': 50, 'offset': 0, 'total': 0}, list) |
| test_retrieve_documents | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_realtime_process | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_predict_questions | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_predict_checklist | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_performance_analyze | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_study_plan_generate | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_job_tracker_search | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_mock_interview_questions | httpx.ReadTimeout |
| test_mock_interview_random_question | failed on setup with "httpx.ReadTimeout" |
| test_mock_interview_practice_set | failed on setup with "httpx.ReadTimeout" |
| test_mock_interview_search | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_collab_status | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_collab_messages | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_search_web | assert 422 in [200, 400, 503]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_resume_analyze | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_resume_compare | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |
| test_analysis_complexity | assert 422 in [200, 400]  +  where 422 = <Response [422 Unprocessable Entity]>.status_code |

## Feature guide

### Main workspace

Ask typed questions or record voice; read streamed answers. Camera adds screenshot/OCR context. Summarize creates structured notes. Welcome suggestions submit example prompts. Scroll-to-bottom returns to the latest answer.

UI opened; text/audio submission and screenshot-context logic covered by automated tests. Real microphone and system audio were not exercised in this final run.

### Window controls

Minimize, maximize, close; opacity slider; protection toggle; window movement and hide/show shortcuts. Protection requests capture exclusion but is not a guarantee across every sharing method.

Window shown live. Closing, autostart, stealth and opacity preferences were not changed during this tour.

### Answer context

Resume + imports resume context. Job description + opens a separate editor with Save, Cancel and Remove. Remove resume clears resume context. Context personalizes answers; it cannot guarantee that the model never invents facts.

Upload/JD behavior covered in browser and unit checks; your existing resume was left intact.

### AI controls

Mode: Instant, Auto, Fast, Turbo, Adaptive, Universal, Interview, Reasoning, Cloud, Code. Model chooses Auto or an enabled model. Smart mode targets code assistance. Modes are preferences passed into the pipeline, not separate models.

Shown live. Cloud model availability varies with configuration and provider lifecycle; catalog entries are not proof a model works.

### AI options

Style: Concise, Detailed, Bullet. Temperature: Precise 0, Focused 0.1, Balanced 0.3, Creative 0.5, Imaginative 0.7, Max 1. Context: Off, 1, 3, 5 or 10 messages. Token display limits: 8K through 1024K.

Dropdown options inventoried. UI token limits do not enlarge a provider’s actual context/output limits.

### Display and behavior

Display provides font sizes and company/role context plus the interview overlay. Behavior exposes automatic screenshots and always-on microphone. Speakers identifies speakers; Sales enables objection-related assistance.

Panels shown; no new recording, screen sharing, or external message was started.

### Hands-free recovery

Automatically reacts to provider quota/outage, output limits and some context failures. Preserves partial text, records provider changes and cancels superseded questions. Attempts and waiting are bounded so the interface becomes ready again.

Production recovery endpoint + real UI passed fault-injection tests. Prior 30-minute local speech test is separate evidence, not rerun in this review.

### Saved conversations

Open History from the menu. Search titles/messages; sort Recent, Oldest, A–Z or Messages. Open chats, start new chats, select, export, import, clear current chat, or delete all with confirmation.

Search, pagination, sorting, keyboard access, delete cancellation, partial failure/retry, and active-chat reset passed using synthetic data.

### General settings

Quick Actions: Analytics and Export Data. Startup: launch on login and start hidden. Privacy: screenshot preferences. CRM: provider, credentials, matching/logging options and format. Module Health summarizes subsystem checks.

Cards expanded. CRM save/test and autostart were not invoked. Live health card showed 81.8%, not all modules available.

### Providers and models

Providers toggle availability and expose key configuration, save and restart controls. Models includes default-cloud selection, model groups, enable/disable actions and local/custom entries.

Panels expanded; credentials were not revealed, edited, or retested. Runtime inventory below is authoritative for what appeared in this session.

### Voice and Clone

Voice covers transcription/language/output controls. Clone provides local voice-model creation, samples, training/gallery and test controls where available.

Controls inspected only. No voice sample was recorded or cloned; end-to-end cloning is not certified by this review.

### Data and integrations

Knowledge Base imports PDF/DOCX/TXT/MD. Interview Data Import offers a dry run/import workflow. Integration cards include Slack, Notion, calendar, phone and other configured connections.

All cards expanded; import, deletion, Connect, Test and outbound messaging were not run on personal accounts.

### Feature pages

Cognitive Graph: overview/search/company/skill/entity extraction. Pre-Interview: company/role predictions. Analytics: performance metrics. Study Plan: role/company/JD/skills/time. Interview Simulator: start/record/skip/submit/next. Job Tracker: add/edit application status, priority, salary, URL, notes. Resume Review: resume upload/text and optional JD analysis.

Pages opened live. Successful rendering is distinct from successful generation, storage, or external service operations.

### Overlays

Caption overlay has clear and pause/resume. Interview overlay has click-through, window controls, microphone and answer controls. Generic overlay has mic/voice/screenshot/file/opacity/settings.

A live file:// page emitted invalid WebSocket URL ws://:8000/ws/transcribe. Both caption and interview source use location.hostname, which is empty for file://.

### Account and navigation

Sign In supports username/password, remember me, SSO buttons, registration, and password recovery. Menu offers new chat/history/export, feature pages, settings, shortcuts, logs, about, sign out and quit.

Existing session used after you signed in. SSO/recovery/sign-out and account deletion were not exercised on your account.

## Test isolation and evidence

Backend was copied to /tmp/ant-final-review/backend without .env, personal databases, uploads, recordings or runtime data. Full suite ran there with offline model download settings. API tests used that backend on port 8046; only the temporary test copy’s hard-coded port changed. E2E used the original tests on both installed browsers and the same plain-file frontend server design; the real already-running desktop backend supplied auth/health. Tests did not change user settings.

Evidence directory: /tmp/ant-final-review-ui. Main logs: /tmp/ant-final-backend.log, /tmp/ant-final-backend-recheck.log, /tmp/ant-final-integration.log, /tmp/ant-final-e2e.log, /tmp/ant-final-desktop.log, /tmp/ant-final-mobile.log, /tmp/ant-final-web.log, /tmp/ant-final-build.log.

The guide and desktop are left open for review. Temporary API/recovery test servers are stopped after testing. Browser extension syntax is checked, not end-to-end behavior. Mobile tests run in Jest, not a phone simulator.
