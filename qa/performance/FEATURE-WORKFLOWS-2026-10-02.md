# Feature workflow coverage — October 2, 2026

ANT-017 remains in progress. This matrix records available evidence and concrete gaps; page-load success is not complete feature certification. Evidence from the current continuation is under [resume-2026-10-02](results/2026-09-27-remediation/resume-2026-10-02/checkpoint.json).

| Family | Verified evidence | Remaining / disposition |
|---|---|---|
| Account | Disposable registration/login and BYOK auth success/denial; live API suite | Full logout, recovery, expired-session and SSO workflows incomplete |
| Window | Desktop unit coverage | Native minimize/maximize, startup, opacity, capture-protection and shortcut walkthrough pending |
| Text/voice | Typed and synthetic recorded-audio recovery submission, cancellation | Current native microphone/system audio, silence/noise and permission-denial checks pending |
| Resume/JD | Built-web smoke, synthetic recovery context, backend numeric-grounding regressions | Held-out factual quality, all upload formats and persistence workflows incomplete |
| Screen/PDF | Current desktop/web regressions; previous controlled OCR/Qwen evidence | Native capture, display selection and full PDF workflow not verified this revision |
| Answers | Recovery partial preservation, attribution, bounded failure and cancellation | Complete copy/read/scroll and malformed-network workflow matrix pending |
| History | Synthetic full-text search, pagination, sort, keyboard, deletion cancel/partial failure/retry, active-chat reset | Real import/export round trip and complete pin/rename workflow pending |
| AI options | Runtime inventory, disabled providers/models, image capability and requested budgets covered by regression suites | Live cloud model availability/quotas remain external; all picker combinations not manually reviewed |
| Settings | Existing unit/smoke coverage | All settings save/restart and error-state workflows incomplete |
| Knowledge | Existing API/unit coverage | Actual indexing/retrieval and optional-service failure workflows incomplete |
| Interview tools | Live bounded question catalogue, distinct pagination/search and exact five-question practice set | Full answer/evaluate/skip/session persistence and study completion workflows pending |
| Job tracker / resume review | Page smoke and API regression checks | **Confirmed gap:** job-card click only logs details in `apps/web/job-tracker.js`; no usable detail view. Creation form notes also appear unsubmitted. Repair and test creation/status/persistence/deletion before sign-off |
| Graph / analytics | Unavailable analytics state verified in both browsers | Graph service is absent in isolated runs; actual extraction/analytics workflows unverified |
| Overlays | Existing overlay lifecycle unit tests and prior file-page connection evidence | Current native IPC/click-through/pause/close lifecycle walkthrough pending |
| Voice clone | Existing unit/API coverage only | Consented fixture, model availability and create/train/test/cancel/delete workflow pending |
| External integrations | No live destinations contacted | Local stub contract/workflow coverage and separately authorized live checks pending |
| Mobile / extensions | Mobile: 34 Jest tests passed | Emulator/disposable extension installation, backend reachability and denied-permission/recording lifecycle checks pending |

Next implementation focus: replace the job-card detail stub, preserve notes and prove the application lifecycle on isolated data. Remaining accessibility work includes labeled controls, keyboard-only workflows and responsive layouts beyond the tested history panel. The final native desktop review and release gates remain open.
