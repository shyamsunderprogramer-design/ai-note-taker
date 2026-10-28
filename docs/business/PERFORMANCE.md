# Performance and measurement

This guide brings the optimization plan, implementation notes, and outcome report together. Measure the current application before treating any historical improvement as a present guarantee.

## What to measure

| Metric | Measurement boundary |
| --- | --- |
| Startup | Process launch to visible window, then backend and model readiness separately |
| First answer | Submission to first useful streamed content |
| Complete answer | Submission to stream completion, including recovery |
| Transcription | Audio boundary to usable question text |
| Memory | Desktop, backend, and model processes, at idle and under load |
| UI responsiveness | Typing, scrolling, window resizing, and panel changes during an active answer |

Record OS, hardware, model, provider, input size, cold/warm state, commit, and sample count. Compare the same workloads and retain raw results.

## Implementation areas

- **Desktop:** startup order, backend reuse, splash feedback, Chromium settings, and native window resizing in [electron/main.js](../../electron/main.js).
- **Renderer:** streaming, input/scroll work, chat history, and compact conversation state in [app.js](../../apps/web/app.js).
- **Backend:** async provider streaming, model loading, resource cleanup, and database operations in [backend](../../backend/).
- **Models:** installed model size, memory limits, image input, network latency, and provider quota.

Use `core.main:app` for the normal backend entry point. The historical notes discuss `fast_startup.py` as an experiment; do not replace the application's backend entry point based on that old example alone.

## Run and review benchmarks

```bash
npm run benchmark:web
npm run benchmark:browser
```

Check the prerequisites and scope in the [performance workspace](../../qa/performance/README.md) before running live voice, desktop, or cloud benchmarks. They can require a running app, OS permissions, credentials, and provider usage.

## Optimization checklist

1. Reproduce a slow interaction with a defined workload.
2. Separate download/model warm-up from steady-state performance.
3. Profile the process or request segment responsible for the delay.
4. Change one meaningful bottleneck and rerun the same workload.
5. Check correctness, stream completion, memory, and cleanup along with speed.

The April reports include splash feedback, deferred initialization, lazy imports, debounce/throttle helpers, pooling, and caching. Their timing and memory figures lack a reproducible environment in those documents and remain historical observations.

## Historical references

The overlapping source documents are preserved in one [dated reference record](../archive/performance.md). Use that record for original technical examples and planning context, not current setup or status.
