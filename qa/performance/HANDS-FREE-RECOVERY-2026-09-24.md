# Hands-free recovery feasibility

Production currently has pre-answer Auto fallback, but no automatic continuation after a winning provider emits answer text and then fails. No production recovery code was installed in this investigation.

## Controlled production-path checks

38 backend tests passed, covering provider transport errors, incomplete streams, race selection, and local fallback. Three added cases injected SSE error events after partial text: quota/429, output limit, and disconnect. All preserved the partial answer and ended with an error, without consuming a backup answer. These are passing characterization tests of a missing capability, not successful recovery tests.

## Live continuation feasibility

The standalone QA script supplied synthetic questions and partial answers to real configured provider adapters. It did not exhaust a real quota, interrupt a live primary stream, record a microphone, or exercise the desktop recovery UI. There is no automatic failure detector or recovery controller in this script; each case directly requests the proposed continuation.

| Scenario | Live provider | First text / completion | Review |
| --- | --- | --- | --- |
| No answer, simulated quota scenario | Groq GPT-OSS 120B | 0.744 / 0.796 s | Correctly treats unlisted AWS certification as unknown. |
| Supplied incomplete budget answer | Groq GPT-OSS 120B | 1.675 / 1.714 s | Correct continuation: Maple $300 under; combined $1,100 over. Does not repeat Cedar. |
| Supplied resume answer opening | Ollama Cloud MiniMax M3 | 7.696 / 8.076 s | Transport completed, but seamless continuation failed review: repeated the opening sentence, attributed a performance improvement without supporting resume evidence, and used ambiguous wording about an unlisted certification. |

Evidence: `results/2026-09-24-hands-free-feasibility.json`.
Reproduction: `AINT_Venv/bin/python qa/performance/ai/hands-free-recovery.py` (three live requests with synthetic data).

## Conclusion

Automatic continuation is technically feasible, but the current application does not implement it. These three requests do not establish reliability or latency guarantees. Cross-provider continuation needs visible provider attribution, repetition handling, bounded retries/deadlines, cancellation for a new question, and continued grounding checks. Cooldown/Retry-After behavior, provider exhaustion, local recovery, and real hands-free UI operation remain untested. Do not describe this prototype as a shipped or validated hands-free failover feature.
