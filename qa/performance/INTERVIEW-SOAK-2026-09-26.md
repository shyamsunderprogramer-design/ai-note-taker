# 30-minute synthetic interview test — 2026-09-26

The full run lasted 1,800 seconds, from 10:26:57 to 10:56:57 America/Chicago. Sixty turns were scheduled 30 seconds apart. Delivery was stable; answer quality had material failures.

## Setup and scope

macOS Samantha generated ten clean English questions, repeated six times. Each turn used the production Whisper file-transcription function (cached small model), the production HTTP `/stream-recover` endpoint, and real local Qwen 3.5 9B generation. A synthetic resume and job description were included on every turn, along with the last eight conversation messages. An isolated server injected ten quota failures and ten mid-answer disconnections before real local-model recovery. No cloud API calls, real microphone, user resume, saved chats, or meeting platform were used.

This is not a live Zoom/Teams/audio-capture test. It does not exercise continuous audio, VAD, browser/Electron rendering, barge-in, or a real provider outage. Timings start after the synthetic audio file is available, excluding the duration of the spoken question. Whisper was warmed before the timed run; the first AI turn was retained. Failed-provider partial text in disconnect cases was scripted. No product code was changed during this test.

## Measured performance

| Measurement | Result |
|---|---:|
| Completed responses | 60/60 |
| Quota recoveries | 10/10 |
| Mid-answer disconnect recoveries | 10/10 |
| Health checks | 180/180 successful |
| Median transcription time | 5.83 s |
| Median first local-model content after AI request | 0.82 s |
| 95th-percentile first local-model content | 1.91 s |
| Median complete AI answer | 2.48 s |
| Median transcription + complete answer | 8.39 s |
| 95th-percentile transcription + complete answer | 9.22 s |
| Slowest turn, including first AI warm-up | 11.17 s |
| Mean per-clip word error rate | 2.02% |
| Median health response | 3.33 ms |
| 95th-percentile health response | 6.24 ms |

The first ten turns had median total time 8.21 s; the last ten had 8.71 s. There was no sustained stall or restart. Server RSS peaked at about 1,940 MiB, with no monotonic growth observed. RSS is server-only, excludes Ollama/Electron, and on macOS does not establish total memory pressure. CPU/GPU utilization and power consumption were not comprehensively measured.

## Quality findings

- Turns **10 and 40** changed the supplied latency improvement from **900 → 120 ms** to **900 → 12 ms**.
- Turns **6, 16, 26, 36, 46, 56** transcribed “cache invalidation” as “cash invalidation.” Answers then introduced cash balances, ledgers, transactions, or double-spending. Low average transcription error did not prevent meaningful failures.
- Some answers invented personal implementation details. Turn 12 added logs-and-metrics validation; turn 56 claimed testing the exact invalidation logic under high-velocity updates. Those facts were absent from the resume.
- All six direct AWS-certification questions avoided claiming an unlisted certification.
- These are targeted review findings, not an exhaustive quality score. **60/60 completed is not 60/60 correct.**

## Assessment and next work

Automatic recovery handled every injected failure in this run. The largest latency component was transcription. Improve technical-term recognition/context handling, preserve numerical resume facts, and prevent conversation history from reinforcing invented experience. Validate those changes on held-out audio, then test real continuous meeting audio and interruption behavior before treating this as live-interview validation.

The live dashboard remains at http://127.0.0.1:8045 and now shows completed results. Raw measurements: `results/2026-09-26-interview-soak.json`. Temporary runner: `/tmp/ant-interview-soak.py`. Test server shut down after completion; the test did not stop or restart the user's separate desktop app. Its port 8000 was not monitored during this isolated run.
