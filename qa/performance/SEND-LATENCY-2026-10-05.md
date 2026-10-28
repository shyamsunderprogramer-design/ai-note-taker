# Send latency, 2026-10-05

The answer path previously forced high reasoning effort for every Groq request and buffered the entire response whenever a resume was attached. Provider settings were read serially, after screen capture and OCR.

Changes:

- Start candidate preparation alongside typed-question screen capture, and overlap it with resume/JD readiness. Read each provider's settings once, in parallel.
- Display the assistant preparation state before waiting for discovery.
- Keep the selected model. Use low reasoning effort for spoken/instant answers, medium for ordinary adaptive answers, and high for code/reasoning mode or Detailed style. Low effort can trade reasoning depth for speed; it does not establish equal accuracy on complex tasks.
- Release checked, complete resume-answer sentences as they arrive. Any sentence containing digits holds the remaining draft for whole-answer verification, because later personal context can change whether an earlier measurement is a personal claim. Unsupported leadership claims remain withheld. Repairs continue after the already visible opening.
- When runtime catalog discovery is unavailable, usable cloud candidates do not wait for optional local discovery. The normal catalog path retains installed local fallback candidates.

Four sequential live requests used Groq `openai/gpt-oss-120b`, spoken style, instant mode, temperature 0.2, and a short synthetic resume. The before variant emulates the prior high effort and complete-answer buffering with the same current prompt. No retries, model races, or smaller model were used.

| Question | Before first visible | After first visible | After complete |
|---|---:|---:|---:|
| Kubernetes cluster | 2,134 ms | 701 ms | 1,039 ms |
| On-call rotations | 3,508 ms | 466 ms | 838 ms |

This small sample measures prompt construction, network, inference and resume verification, excluding desktop capture/OCR and provider discovery. It is not an end-to-end desktop benchmark, a latency guarantee, or proof of equivalent accuracy. Both variants completed both requests without provider errors. Answers were readable, relevant, and hypothetical; the cluster explanation still simplifies differences between managed and self-managed setup.

Evidence: [raw results](results/2026-10-05-send-latency.json), [benchmark script](ai/send-latency.py).

Validation: 102 backend tests covering grounding, recovery and provider streams; 27 Electron tests covering selection, discovery, screen context and submission persistence; web production build passed with existing non-module-script warnings. Backend/frontend changes require restarting the running application.

Groq supports low, medium and high reasoning effort for GPT-OSS: [official API reference](https://console.groq.com/docs/api-reference).
