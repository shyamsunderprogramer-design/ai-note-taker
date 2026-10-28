# Answer-quality follow-up — 2026-09-15

Updated the live suggestion prompt to treat earlier generated answers as unverified
drafts, not candidate evidence. Removed assumed role/skills when context is absent.
Missing experience, implementation details and measurement methods now explicitly
call for placeholders. Technical answers should explain concepts without inventing
personal experience.

Two local Qwen3.5:9b nonstreaming checks returned answers without invented employers
or measurement tools. The missing-resume case used placeholders (4.028 seconds).
The partial-resume case retained the supplied 20% improvement and used a measurement
placeholder (1.148 seconds). These are limited observations, not a grounding guarantee.

A streamed follow-up supplied an earlier AI draft with unsupported Google,
Prometheus and 50% claims. Both attempts timed out without content after about
12.25 seconds. Consequently resistance to history contamination on the streamed
path is **unverified**, and this run does not pass an overall live-quality gate.
No timeout was hidden or converted into a successful result.

Related regression tests: 57 passed. Whitespace diff check passed. The application
was not restarted or released; no real call or competitor account was used.

Evidence is saved under [results/2026-09-15](results/2026-09-15):

- [Nonstreaming cases](results/2026-09-15/ant-quality-followup.json)
- [Streaming attempt](results/2026-09-15/ant-quality-stream-followup.json)
- [Streaming retry](results/2026-09-15/ant-quality-stream-retry.json)
