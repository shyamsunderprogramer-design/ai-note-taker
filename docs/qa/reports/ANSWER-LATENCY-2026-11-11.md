# Answer latency investigation

Status: fixes implemented and verified in Electron. Three text questions produced
visible answer text in 376–713 ms; two screen-context questions took 750–1,060 ms.
These are individual synthetic samples, not a subsecond guarantee for every model,
question or capture path. Source changes require an app restart.

## Observations

Saved settings showed Qwen 3.8 27B on Groq, Code mode, spoken responses, automatic
screen context and an attached resume. No settings or credentials were changed.
Groq's authenticated model listing confirmed that the selected model is available.

Two synthetic questions exercised the actual Groq adapter and resume gate with
a fictional resume, Code mode and spoken style. No user resume, screen contents
or conversation were sent. RAG was disabled to isolate inference and verification.

| Synthetic question | First provider text | First verified text | Complete |
| --- | ---: | ---: | ---: |
| Python function to sum even numbers; code only | 435 ms | 502 ms | 502 ms |
| What is a Kubernetes cluster? | 342 ms | 513 ms | 792 ms |

Native Apple Vision recognized a synthetic text image in 164 ms outside the
sandbox. The sandboxed helper was unavailable; that result was not treated as an
application defect. These probes exclude desktop screen capture, inventory
discovery, full user context, UI rendering and provider contention.

## Confirmed causes and fixes

1. `recoveryCandidates` waited for full inventory even for an explicitly selected
   cloud text model. With a cold cache or inventory older than five minutes, this
   put the five-second catalog timeout on the answer path. That request now runs
   in the background; cold cloud text routing uses the existing configured-provider
   fallback. Recent inventory remains reusable. Auto, local selections and image
   requests still await capability information. Provider/model opt-outs are still
   checked. No model is downloaded or silently substituted as the first choice.
2. `streamRecoveringAnswer` formatted and laid out the whole answer for every
   token event, even when hundreds arrived together in one network packet. It now
   renders once per received batch before awaiting another read. Completion/error
   events render the final accumulated text directly. There is no typing timer.
3. Resume verification held the rest of a draft after any digit, even a function
   result, HTTP status or software version. It now uses the existing measured-claim
   detector to decide which numeric sentences need whole-draft verification.
   Unsupported personal claims and measured claims still receive verification,
   including when later personal context qualifies an earlier measurement.
4. The paced follow scroll could keep an answer below the visible area after it
   had rendered. One observed code answer finished at about 400 ms but became
   visible at 788 ms. The first nonempty answer now scrolls into view immediately;
   subsequent text retains paced following. A reader who scrolls up while waiting
   keeps their position.
5. The displayed duration previously started after capture/OCR. It now starts at
   question dispatch so the status includes that work.

The safety facts were exercised by regression tests: capability-dependent paths
still wait, disabled providers stay excluded, split SSE frames retain Unicode and
all answer characters, and a reset/error cannot replay an obsolete draft. Production
screen capture and model reasoning settings were not changed.

## Actual desktop measurements

The durable probe uses the production Electron renderer and preload, real Groq
adapter, recovery route, prompt construction and resume verification. A separate
loopback backend and in-memory IPC settings isolate the test from the user's
profile. Authentication and subscription IPC are fixtures; full production main
process startup, login, microphone transcription and connected accounts are not
part of these timings. Settings mirror the selected Groq Qwen 3.8 27B, Code mode,
spoken style and temperature 1, with a short fictional resume.

Timing begins at Enter and counts the first answer text only when its text range
intersects the chat viewport and is unobscured at that location. Initial fixture
runs counted DOM content beneath onboarding; those measurements were discarded.
The fixture now completes onboarding and checks actual visibility. Completion is
observed after the renderer finishes; timings include frame/poll overhead.

| Question | Request sent | First visible text | Complete |
| --- | ---: | ---: | ---: |
| Kubernetes cluster | 24 ms | 713 ms | 999 ms |
| Python sum of even numbers, code only | 2 ms | 515 ms | 516 ms |
| Process versus thread | 3 ms | 376 ms | 711 ms |
| Solve synthetic screen task, code only | 556 ms | 1,060 ms | 1,069 ms |
| Expected result from synthetic screen | 353 ms | 750 ms | 1,027 ms |

Screen cases use the production native capture helper and Apple Vision OCR.
Native capture took 285/183 ms; the OCR request took 210/156 ms. A separate Chrome
window displays a synthetic question with a magenta border. Only its cropped
content is transferred, after verifying the border on all four sides. No user
resume, conversation or surrounding desktop pixels are sent. Test requests are
restricted to the selected model, so paid fallback recovery is not benchmarked.
No renderer errors occurred, and answer screenshots were saved.

Reproduce (uses the configured Groq credential and incurs provider requests):

```sh
node qa/performance/renderer/desktop-answer-latency.cjs
node qa/performance/renderer/desktop-answer-latency.cjs --screen
```

The companion server is `qa/performance/ai/desktop-answer-server.py`.
Final artifacts, including `results.json` and screenshots, are under the macOS
temporary directory:

- Text: `/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-desktop-answer-vhGmUz/`
- Screen: `/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-desktop-answer-eyDyJU/`

## Verification

- New routing tests failed before the fix with cold and expired stalled inventory;
  both now return without waiting for that request.
- New rendering tests failed before the fix on duplicate full-answer redraws;
  they now pass, including immediate visibility before the next packet read.
- Real Chrome DOM replay used production SSE parsing and Markdown formatting with
  a synthetic 2,814-character code answer delivered in one burst. Reconstructing
  the prior per-event rendering produced 705 redraws and 202 ms of processing;
  the new path produced two redraws and 1 ms. Both retained the final code. This
  is one synthetic browser sample, not a model/network latency benchmark.
- First-text viewport regressions failed before the fix and pass afterward;
  existing paced-follow and manual-scroll checks still pass.
- Three numeric technical-sentence streaming tests failed before the fix and pass
  afterward. Backend resume grounding, stream recovery and provider stream-error
  tests: **116 passed**.
- Desktop tests: **252 passed**. Renderer tests: **29 passed**.
- Renderer asset check: **84 references resolved; 20 scripts syntax-checked**.
- Five-page renderer smoke check in Chrome: **passed**, no JavaScript errors.
- Syntax and CRLF-aware whitespace checks: **passed**.

The live provider probe is `/tmp/ant-response-probe.py`; the browser replay is
`/tmp/ant-answer-render-benchmark.cjs`. Durable regressions are in
`electron/tests/recovery-candidates.test.js` and
`electron/tests/stream-render-batching.test.js`.

## Remaining limits

Restart ANT to use the updated renderer. No running conversation was interrupted
and no release installer was built. Full model discovery is still necessary for
Auto/local/image routing. Cold explicit-cloud routing can use configured cloud
backups; local capability-based backups become available once the inventory loads.
Provider-presence discovery still has its own bounded wait. Screen capture, OCR,
long prompts, reasoning and conservative resume verification can still add delay.
Connected-account transport was not separately benchmarked in this investigation.
This latency probe is not a capture-exclusion certification. The native dropdown
and tooltip screenshot checks are recorded separately in
`PROTECTED-CONTROLS-2026-11-10.md`; Electron protection still cannot guarantee
exclusion from every macOS capture method.

The durable learning is to keep optional local inventory off a selected cloud
answer's critical path and coalesce token events already in the same network
packet. Writing this learning to the external gstack state directory was blocked
by the filesystem sandbox; it is retained here instead.
