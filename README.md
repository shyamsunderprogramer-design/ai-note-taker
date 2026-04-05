# ANT (AI Note Taker)

**A privacy-first AI notepad that runs entirely on your machine.**

Local speech-to-text, local and cloud AI models, floating overlay UI, screen capture protection, and real-time transcription — all in one free, open-source app.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Privacy](#privacy)
- [Tech Stack](#tech-stack)
- [Cognitive Graph](#cognitive-graph-new-in-phase-1)
- [Building](#building)

---

## Features

### Voice & Transcription

| Feature | Description |
|---|---|
| **Real-time streaming transcription** | Speak and see text appear live in the input field (green italic) as you talk, powered by WebSocket streaming to local Whisper |
| **Local Whisper STT** | All transcription runs on your machine via `faster-whisper` — nothing leaves your device |
| **Blob fallback** | If WebSocket streaming fails, automatically falls back to standard chunk recording |
| **Always-on microphone** | Continuous listening mode — detects silence, auto-sends buffered transcription to AI |
| **Audio waveform** | Live microphone visualization with green waveform animation |
| **Smart filtering** | Filters filler words (`uh`, `um`, `...`), noise, and small talk |
| **Question detection** | Automatically recognizes questions vs. casual statements |

### AI Responses

| Feature | Description |
|---|---|
| **Real-time streaming** | AI responses stream character-by-character in the chat |
| **10 AI modes** | Instant, Auto, Fast, Turbo, Adaptive, Universal, Interview, Reasoning, Cloud, Code |
| **Smart Mode** | One-click coding assistance toggle — amber glow when active |
| **Multi-provider routing** | Race all configured providers simultaneously, fastest response wins |
| **8 cloud providers** | OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Ollama Cloud, Perplexity |
| **Local Ollama models** | Free, offline AI — no API key needed |
| **Vision / screenshots** | Attach a screenshot and ask questions about what's on screen |
| **3 response styles** | Concise, Detailed, Bullet points |
| **Token counter** | Live estimate of tokens used vs. context limit |

### Meeting Notes

| Feature | Description |
|---|---|
| **Meeting notes generation** | One-click structured summary — Overview, Key Points, Action Items, Details |
| **Streaming render** | Notes stream in with full markdown formatting in real-time |
| **Copy to clipboard** | One-click copy of the full meeting summary |

### Conversation Management

| Feature | Description |
|---|---|
| **Auto-save** | Conversations saved automatically as JSON files |
| **Session resume** | Restore full session state — mode, auto-screenshot, always-on mic |
| **History panel** | Browse all past conversations with search |
| **Sort & filter** | By Recent, Oldest, A-Z, or message count |
| **Pin conversations** | Keep important sessions pinned to the top |
| **Time grouping** | Organised by Today, Yesterday, This Week, Earlier |
| **Export** | Save as TXT, CSV, JSON — with optional AES-256 encryption |
| **Copy conversation** | Copy full transcript as formatted text |

### Window & UI

| Feature | Description |
|---|---|
| **Floating overlay** | Always-on-top widget, stays visible over fullscreen apps |
| **Frameless window** | Custom traffic light buttons, draggable and resizable |
| **Always on top** | Uses Windows `screen-saver` level to stay above fullscreen video |
| **Dark glass theme** | Modern translucent UI with CSS variables |
| **OS theme sync** | Automatically adapts to dark/light system preference |
| **Onboarding** | First-launch setup wizard checks mic, Ollama, and vision model |

### Privacy & Stealth

| Feature | Description |
|---|---|
| **Screen capture protection** | Hides from Zoom, Teams, WebEx, Discord, OBS, Snipping Tool — free |
| **Stealth mode** | Toggle with `Alt+D` — app disappears from screen capture |
| **Screenshot toggle** | Independently enable/disable screen capture in Settings |
| **System tray** | Minimizes to tray when stealth is active |
| **Hide/show** | `Alt+Space` toggles window visibility without disabling stealth |
| **No cloud STT** | All transcription is local — nothing sent to external servers |

### Cognitive Graph (New in Phase 1)

Personal knowledge graph powered by Neo4j to store and analyze your interview history.

| Feature | Description |
|---|---|
| **Semantic Search** | Search your interview history by topic, company, or skill |
| **Entity Extraction** | Automatically extracts companies, skills, and topics from transcripts |
| **Company Insights** | See what questions companies typically ask |
| **Skill Progression** | Track your confidence across different skills over time |
| **Auto-Ingest** | Conversations automatically added to graph on save |
| **Q&A Extraction** | Parses transcripts into question-answer pairs |
| **Interview Predictions** | Predict likely questions for companies like Google, Meta, Amazon |
| **Pre-Interview Prep** | Generated preparation checklists based on company patterns |

**Access:** Open app menu (☰) → "Cognitive Graph" or "Pre-Interview Prep"

**Setup:** See [docs/SETUP_COGNITIVE_GRAPH.md](docs/SETUP_COGNITIVE_GRAPH.md)

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Enter` | Toggle voice recording or submit text |
| `Ctrl+Enter` | **Trigger AI from any app** (works globally, even when ANT is hidden) |
| `F` | Toggle maximize |
| `Escape` | Close panels and modals |
| `Alt+D` | Toggle stealth mode |
| `Alt+Space` | Hide / show window |
| `Ctrl+Arrow` | Move window in any direction |

---

## Quick Start

### Prerequisites

- **Windows 10/11** or **macOS**
- **Python 3.10+** — [Download](https://python.org/downloads)
- **Node.js 18+** — [Download](https://nodejs.org) (LTS recommended)

### Step 1 — Clone

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

### Step 2 — Python environment

```bash
python -m venv AINT_Venv
AINT_Venv\Scripts\activate       # Windows
# source AINT_Venv/bin/activate   # macOS/Linux
pip install -r backend/requirements.txt
```

> Installing AI packages (`faster-whisper`, etc.) may take 5–10 minutes and require 4 GB+ disk space.

### Step 3 — Ollama (recommended for free local AI)

Download from [ollama.com](https://ollama.com) and install. Then pull a model:

```bash
ollama pull qwen2.5:1.5b
```

### Step 4 — Install Electron packages

```bash
cd electron
npm install
cd ..
```

### Step 5 — Run

```bash
cd electron
npm start
```

The app window appears. The Python backend starts automatically.

---

## How It Works

### Voice Recording Flow

```
You press Enter / click Start
         │
         ▼
Browser: MediaStream → ScriptProcessor → downsample to 16kHz Float32
         │
         ▼
WebSocket /ws/transcribe  ──────────────►  Backend: BrowserTranscriber
                                              (buffers 500ms, faster-whisper inference)
         ◄──────────────────────────────────  {"type": "partial", "text": "..."}
         │
         ▼
Text appears live in input field (green italic)
         │
   You press Enter to stop
         │
         ▼
Full transcript sent to AI → streaming response in chat
```

### AI Routing Flow

```
Your text (or transcribed voice)
         │
         ▼
Backend AI Router — resolves mode via keyword + word count heuristics
         │
         ├── "code" keywords + ≥18 words  →  code mode
         ├── technical keywords            →  interview / universal
         ├── long input (≥30 words)       →  reasoning
         ├── short input (≤8 words)       →  fast
         └── default                       →  adaptive
         │
         ▼
Provider decision:
  • Auto + no model selected  →  race all configured providers (parallel)
  • Specific model chosen      →  route to that provider directly
         │
         ▼
Streaming SSE response  →  Frontend renders character-by-character
```

### Data Privacy

```
Local recording:  MediaStream → WebSocket PCM → BrowserTranscriber → faster-whisper
Cloud AI:         Backend → OpenAI/Anthropic/etc. API
                 ─────────────────────────────────────
                 Transcription NEVER leaves your machine
                 AI responses go directly to your device
```

---

## Project Structure

```
ai-note-taker/
├── electron/                      # Electron desktop shell
│   ├── main.js                   # Main process: window, shortcuts, IPC, backend spawn
│   ├── preload.js                 # Secure context bridge
│   ├── stealth.js                 # Screen capture protection (setContentProtection)
│   └── package.json
│
├── backend/                       # FastAPI Python server (port 8000)
│   ├── main.py                   # Endpoints: /stream, /transcribe, /ws/transcribe, etc.
│   ├── ai_router.py              # Mode detection, prompt building, Ollama routing
│   ├── cloud_providers.py         # Streaming wrappers for all cloud AIs
│   ├── whisper_handler.py         # faster-whisper STT, filters, BrowserTranscriber
│   ├── config.py                 # Environment config, per-mode model selection
│   ├── utils.py                  # AI output cleaning (strips markdown artifacts)
│   └── requirements.txt
│
├── renderer/                      # Web UI loaded by Electron
│   ├── index.html                # Full UI layout
│   ├── app.js                    # Frontend logic, SSE, voice, streaming
│   └── style.css                # Dark glass theme with CSS variables
│
└── AINT_Venv/                   # Python virtual environment
```

---

## Configuration

### Environment Variables

Create `backend/.env` to configure API keys and model preferences:

```env
# ─── Local Ollama ───────────────────────────────────────────
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_ADAPTIVE=qwen2.5:1.5b
OLLAMA_MODEL_FAST=qwen2.5:1.5b
OLLAMA_MODEL_TURBO=qwen2.5:1.5b
OLLAMA_MODEL_INSTANT=qwen2.5:1.5b
OLLAMA_MODEL_UNIVERSAL=mistral:latest
OLLAMA_MODEL_INTERVIEW=llama3:latest
OLLAMA_MODEL_REASONING=qwen2.5:1.5b
OLLAMA_MODEL_CODE=qwen2.5:1.5b
OLLAMA_MODEL_SUMMARY=mistral:latest

# ─── Ollama Cloud ───────────────────────────────────────────
OLLAMA_CLOUD_API_KEY=sk-...

# ─── Cloud AI Providers ──────────────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
XAI_API_KEY=xai-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
PERPLEXITY_API_KEY=...

# ─── Behavior ───────────────────────────────────────────────
AI_TEMPERATURE=0.1
AI_TIMEOUT=30
TURBO_MAX_TOKENS=150
INSTANT_MAX_TOKENS=64
```

### Provider API Keys

API keys are stored in `backend/.env` and are never committed to git. Configure via the Settings UI (menu → Settings → Configure next to any provider).

### Ollama Model Management

In the app: **Settings → Ollama Models**
- Lists all installed models
- **Pull**: Enter a model name (e.g., `llama3:latest`, `deepseek-r1:8b`)
- **Delete**: Remove a model to free disk space

---

## Keyboard Shortcuts

| Shortcut | Action | Scope |
|---|---|---|
| `Enter` | Toggle voice recording / Submit text | App window |
| `Ctrl+Enter` | Trigger AI from any app | **Global** (works when ANT is hidden) |
| `F` | Toggle maximize | App window |
| `Escape` | Close panels/modals | App window |
| `Alt+D` | Toggle stealth mode | **Global** |
| `Alt+Space` | Hide / show window | **Global** |
| `Ctrl+←/→/↑/↓` | Move window 50px | **Global** |

---

## Privacy

### Screen Capture Protection

ANT uses Electron's `setContentProtection()` API — the standard Windows mechanism for content protection. When stealth mode is active, the window is hidden from:

- Zoom, Google Meet, Microsoft Teams, WebEx
- Discord, Slack huddles
- OBS, Snipping Tool, Screen Recorder
- Any screen capture application

### How It Works

`electron/stealth.js` calls `window.setContentProtection(true)` which applies `WS_EX_FROMLEARN` (Windows) — the same underlying mechanism used by Netflix, Disney+, and other DRM-protected apps. It does not use any game-specific or anti-cheat APIs.

### Screenshot Toggle

A separate privacy control in **Settings → Privacy → Screen Capture** lets you disable screen capture independently of stealth mode. When off, the app is visible on screen but not captured by screen sharing tools.

### No Cloud Transcription

All transcription runs locally via `faster-whisper` — audio never leaves your machine.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| Backend | FastAPI + uvicorn |
| Speech-to-text | faster-whisper (Whisper, local) |
| Local AI | Ollama |
| Cloud AI | OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Ollama Cloud, Perplexity |
| Audio capture | Browser MediaRecorder API + Web Audio API |
| Persistent storage | electron-store + JSON files |
| Logging | electron-log + Python logging |

---

## Building

Build a distributable executable:

```bash
cd electron
npm run build:win    # Windows .exe
npm run build:mac    # macOS .dmg
npm run build:linux  # Linux .AppImage
```

Output goes to `electron/dist/`.

---

## License

MIT License — Free to use, modify, and distribute.
