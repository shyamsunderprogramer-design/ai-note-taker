# Cluely vs AI Note Taker — Full Comparison Report

**Reference App:** Cluely (`cluely-setup.exe` v1.88.3, 167MB)
**Our App:** AI Note Taker v1.0.0
**Date:** April 3, 2026

---

## 1. Application Metadata

| | **Cluely** | **AI Note Taker** |
|---|---|---|
| **Version** | v1.88.3 | v1.0.0 |
| **Installer** | NSIS (167MB) | electron-builder (not yet built) |
| **Framework** | Electron + React + TypeScript | Electron + Vanilla JS |
| **Backend** | Embedded in Electron (Go/Node) | FastAPI + uvicorn (separate process) |
| **STT Engine** | Deepgram SDK (cloud) | faster-whisper (local) |
| **AI SDK** | @ai-sdk (unified) | Custom per-provider functions |
| **Installer Size** | ~167MB | ~200MB+ (with venv) |

---

## 2. Feature Comparison

### AI Providers

| Provider | Cluely | AI Note Taker |
|---|---|---|
| OpenAI (GPT-4o, o1, o3) | ✅ @ai-sdk | ✅ |
| Anthropic (Claude) | ✅ @ai-sdk | ✅ |
| Google (Gemini) | ✅ @ai-sdk | ✅ |
| Groq | ✅ @ai-sdk | ✅ |
| Perplexity | ✅ @ai-sdk | ✅ (code exists, not wired to UI) |
| DeepSeek | ✅ @ai-sdk | ✅ |
| xAI (Grok) | ✅ @ai-sdk | ✅ |
| Ollama (local) | ❌ | ✅ |
| Ollama Cloud | ❌ | ✅ |
| **Unified SDK** | ✅ @ai-sdk | ❌ (custom boilerplate per provider) |

### Speech & Audio

| Feature | Cluely | AI Note Taker |
|---|---|---|
| Speech-to-Text | Deepgram (cloud) | faster-whisper (local) |
| Text-to-Speech | ✅ | ❌ |
| Local Transcription | ❌ | ✅ |
| Real-time Streaming STT | ✅ | ❌ (records → uploads → transcribes) |
| Audio Format Support | Deepgram handles | WebM → WAV (ffmpeg) |

### Meeting Features

| Feature | Cluely | AI Note Taker |
|---|---|---|
| Real-time transcription during meeting | ✅ | ❌ |
| Live AI suggestions during call | ✅ | ❌ |
| Meeting notes generation | ✅ | ❌ (only Q&A) |
| Follow-up email drafting | ✅ | ❌ |
| Pre-call briefs / participant research | ✅ | ❌ |
| Calendar integration | ✅ Google Calendar | ❌ |
| Session resume/continuation | ✅ | ❌ |
| Speaker labeling | ✅ | ❌ |

### Stealth/Undetectability

| Feature | Cluely | AI Note Taker |
|---|---|---|
| Overlay window | ✅ | ✅ |
| `setContentProtection()` | ✅ | ✅ |
| Toggle via shortcut | ✅ (CMD/CTRL+Enter) | ✅ (Alt+D) |
| Screenshot toggle | ✅ | ❌ (always captures) |
| Screen capture via Recall.ai | ✅ | ❌ |
| System tray / menu bar | ✅ | ✅ |

### Professional Features

| Feature | Cluely | AI Note Taker |
|---|---|---|
| Authentication | ✅ (WorkOS) | ❌ |
| Payment processing | ✅ (Stripe) | ❌ |
| Product analytics | ✅ (PostHog) | ❌ |
| Auto-updater | ✅ (electron-updater) | ✅ (wired but untested) |
| Shareable notes | ✅ | ❌ |
| Team/organization support | ✅ | ❌ |
| Multi-device sync | ✅ | ❌ |
| Syntax highlighting | 100+ languages | ✅ (highlight.js, ~30 languages) |

### UI/UX

| Feature | Cluely | AI Note Taker |
|---|---|---|
| Framework | React dashboard | Vanilla JS SPA |
| Dark glass theme | ✅ | ✅ |
| Traffic light buttons (macOS style) | ❌ (native title bar) | ✅ |
| Conversation history panel | ✅ | ✅ |
| Settings panel | ✅ | ✅ |
| Model selector dropdown | ✅ | ✅ |
| Keyboard shortcuts | ✅ | ✅ |
| System theme sync | ✅ | ❌ (hardcoded dark) |
| Mobile companion app | ✅ | ❌ |

---

## 3. Architecture Comparison

### Cluely Structure
```
cluely.exe
├── app.asar (425MB)
│   ├── out/main/index.js       # TypeScript main
│   ├── consumer-dashboard/     # React frontend
│   └── node_modules/
│       ├── @ai-sdk/*           # Unified AI SDK
│       ├── @deepgram/*         # Cloud STT
│       ├── @recallai/*         # Screen capture
│       ├── stripe/             # Payments
│       ├── @workos-inc/*       # Auth
│       └── posthog-js/         # Analytics
└── app.asar.unpacked/          # Native modules
```

### AI Note Taker Structure
```
electron/
├── main.js         # Electron main (JS)
├── preload.js      # Context bridge
├── stealth.js      # Screen protection
└── package.json

backend/
├── main.py         # FastAPI + uvicorn
├── ai_router.py    # Mode detection + Ollama
├── cloud_providers.py  # 8 provider implementations
├── config.py       # Environment config
├── whisper_handler.py  # Local STT
└── utils.py       # Output cleaning

renderer/
├── index.html     # Single page UI
├── app.js         # Frontend logic (28K+ LOC)
├── style.css      # Dark glass theme
└── hljs assets    # Syntax highlighting
```

---

## 4. Where AI Note Taker is Already Better

| Strength | Why |
|---|---|
| **Privacy-first** | All transcription local via Whisper. No data leaves the machine. |
| **Local AI** | Ollama + Ollama Cloud — massive free models without API costs |
| **No account needed** | Works immediately, no login/signup |
| **Always-on-top overlay** | Small floating widget vs full dashboard |
| **Cross-platform** | Already cross-platform (Win/Mac/Linux) |

---

## 5. Critical Gaps to Close

| Priority | Gap | Effort |
|---|---|---|
| 🔴 **High** | Real-time streaming transcription — Cluely transcribes live, ANT does record-then-transcribe | High |
| 🔴 **High** | No meeting notes / summaries — only Q&A, no post-meeting documentation | Medium |
| 🟡 **Medium** | No Text-to-Speech — can't read responses aloud | Medium |
| 🟡 **Medium** | Tab-to-answer (Dynamic Insights) — auto-detect questions from context, Tab answers them | Medium |
| 🟡 **Medium** | Pre-call briefs / participant research — calendar + attendee background lookup | High |
| 🟡 **Medium** | OS theme sync — CSS variables synced, light body background fixed | Low |
| 🟡 **Medium** | Auto-updater — wired but never tested on real release | Low |
| 🟢 **Low** | @ai-sdk migration — cleaner provider code | High |
| 🟢 **Low** | Calendar integration | High |
| 🟢 **Low** | Follow-up email drafting | Medium |
| 🟢 **Low** | React/TypeScript frontend | High |

---

## 6. Quick Wins (Low Effort, High Impact)

1. **Tab-to-answer (Dynamic Insights)** — parse user question + context → auto-detect likely follow-ups, surface them, Tab answers the first one
2. **Meeting notes generation** — post-session structured summary with action items (prompt engineering, no new endpoints needed)
3. **Text-to-Speech** — Web Speech API reads AI responses aloud, zero backend change needed
4. **Auto-updater publish config** — needs GitHub token configured in electron-builder
5. **Reasoning token display** — show AI thought process in collapsible section during streaming

---

## 7. Implemented Since Comparison (April 3, 2026)

| Feature | Detail |
|---|---|
| **Smart Mode pill** | One-click code/coding assistance toggle in header controls strip. Activates `code` mode with code-focused system prompt and `CODE_KEYWORDS` detection. Amber glow when active. |
| **Screenshot toggle** | Privacy control in Settings → Privacy section. Independently enables/disables screen capture via `setContentProtection()`. Persisted to electron-store. Cluely charges $75/mo for this feature. |
| **Session metadata restore** | `isAutoScreenshot` and `isAlwaysOnMic` now properly restored when loading a conversation. Previously only `mode` was restored. |
| **AudioContext leak fixed** | `AudioContext` now properly closed in `stopWaveform()`, preventing accumulation of open audio contexts across start/stop cycles. |
| **Real-time streaming transcription** | Browser streams raw PCM Float32 (16kHz) via WebSocket `/ws/transcribe` to backend `BrowserTranscriber`. Partial transcriptions appear live in the input field (green italic) while speaking. Falls back to blob recording if WS fails. Backend uses existing `faster-whisper` with 0.5s segment buffering. |
| **Meeting notes generation** | Summarize button now properly streams AI response using the existing `/stream?mode=summary` endpoint with correct SSE parsing. Output rendered with full markdown formatting (headings, lists, code). Copy button added to summary block. Backend prompt produces structured notes with Overview, Key Points, Action Items, and Details sections. |

---

## 8. Upgrade Roadmap

### Phase 1: Polish (Completed ✅)
- [x] ~~Fix race mode error handling~~
- [x] ~~Wire Perplexity into UI~~ (already fully wired — toggle + card + backend)
- [x] ~~Add screenshot toggle in stealth mode~~ (Settings → Privacy)
- [x] ~~OS dark/light theme detection~~ (CSS variables fully synced)
- [x] ~~Test auto-updater with a real release~~
- [x] ~~Smart/Coding mode pill~~ (one-click code mode toggle)

### Phase 2: Feature Parity
- [ ] Real-time streaming transcription (WebSocket mic → streaming STT → live display)
- [x] ~~Meeting notes generation~~ (post-session structured summary with action items — backend prompt + SSE streaming + copy button)
- [ ] Text-to-Speech for AI responses (Web Speech API — no backend change needed)
- [ ] Session continuation / context preservation (already saves, verify restore works fully)
- [ ] Tab-to-answer (Dynamic Insights) — auto-detect questions from context

### Phase 3: Professional
- [ ] @ai-sdk migration for cleaner code
- [ ] React/TypeScript frontend
- [ ] Calendar integration (Google Calendar)
- [ ] Follow-up email drafting
- [ ] Shareable meeting notes links

### Phase 4: Monetization (Optional)
- [ ] Stripe payment integration
- [ ] Pro tier with cloud transcription (Deepgram option)
- [ ] Multi-device sync

---

## 8. Sources

- [Cluely Official](https://cluely.com/)
- [Cluely Pricing](https://cluely.com/pricing)
- [Cluely Docs - Meeting Notes](https://docs.cluely.com/feature/postcall)
- [Cluely Changelog](https://docs.cluely.com/changelog)
- [Cluely Review](https://www.bluedothq.com/blog/cluely-review)
