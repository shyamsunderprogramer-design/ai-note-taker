# Spoken introduction repair

- Introduction requests now specify a natural three-paragraph career story, about 140–180 words (shorter when evidence is limited), at most three technologies, and at most one measured achievement.
- Instructions prohibit unsupported leadership, compliance claims, project reassignment, and an unrelated tool inventory.
- The existing resume verifier now catches explicit first-person leadership claims when no leadership evidence is present, permits one correction, and refuses an answer that still fails. This is targeted verification, not a full factual guarantee.
- After a cloud availability/quota failure with no partial answer, recovery prefers an eligible local candidate immediately. Explicit initial model selection remains respected.

Validation: 107 desktop/web tests, 32 recovery/grounding backend tests, web build pass. Real Qwen inference with synthetic resume and injected cloud-unavailable event returned 124 words in 8.48 seconds including a successful leadership-claim correction. This is not a measurement of the user's actual cloud/account latency or resume. Evidence: results/2026-10-04-two-tasks/introduction.json.

Source/build updated; a running backend requires restart to load Python changes. No packaged installer was rebuilt.
