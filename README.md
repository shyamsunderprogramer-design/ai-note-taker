# ANT (AI Note Taker)

**A privacy-first AI notepad that runs entirely on your machine.**

Local speech-to-text, local and cloud AI models, floating overlay UI, screen capture protection, and real-time transcription — packaged as an Electron desktop app, a web SPA, a React Native mobile app, and a Chrome extension, all backed by a FastAPI Python backend.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Workspaces](#workspaces)
- [Configuration](#configuration)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Privacy](#privacy)
- [Tech Stack](#tech-stack)
- [Cognitive Graph](#cognitive-graph)
- [Building](#building)
- [Documentation](#documentation)
- [Project Status](#project-status)
- [License](#license)

---

## Features

### Voice & Transcription

| Feature | Description |
|---|---|
| **Real-time streaming transcription** | Speak and see text appear live (green italic) via WebSocket streaming to local Whisper |
| **Local Whisper STT** | `faster-whisper` runs on your machine — nothing leaves your device |
| **Blob fallback** | Automatic fallback to chunk recording if WebSocket fails |
| **Always-on microphone** | Continuous listening; detects silence, auto-sends buffered audio to AI |
| **Audio waveform** | Live mic visualization with green waveform animation |
| **Smart filtering** | Filters filler words (`uh`, `um`, `...`), noise, and small talk |
| **Question detection** | Recognizes questions vs. casual statements |

### AI Responses

| Feature | Description |
|---|---|
| **Real-time streaming** | AI responses stream character-by-character in the chat |
| **10 AI modes** | Instant, Auto, Fast, Turbo, Adaptive, Universal, Interview, Reasoning, Cloud, Code |
| **Smart Mode** | One-click coding-assistance toggle with amber glow |
| **Multi-provider routing** | Race all configured providers; fastest response wins |
| **Cloud providers** | OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Perplexity, Mistral, Cohere, HuggingFace, Ollama Cloud |
| **Local Ollama** | Free, offline AI — no API key needed |
| **Vision / screenshots** | Attach a screenshot, ask questions about what's on screen |
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
| **Session resume** | Restore mode, auto-screenshot, always-on mic state |
| **History panel** | Browse all past conversations with search |
| **Sort & filter** | By Recent, Oldest, A-Z, or message count |
| **Pin conversations** | Keep important sessions pinned to the top |
| **Time grouping** | Today / Yesterday / This Week / Earlier |
| **Export** | TXT, CSV, JSON with optional AES-256 encryption |
| **Copy conversation** | Copy full transcript as formatted text |

### Window & UI

| Feature | Description |
|---|---|
| **Floating overlay** | Always-on-top widget, stays visible over fullscreen apps |
| **Frameless window** | Custom traffic-light buttons, draggable and resizable |
| **Always on top** | Uses Windows `screen-saver` level to stay above fullscreen video |
| **Dark glass theme** | Modern translucent UI with CSS variables |
| **OS theme sync** | Adapts to dark/light system preference |
| **Onboarding** | First-launch wizard checks mic, Ollama, and vision model |

### Privacy & Stealth

| Feature | Description |
|---|---|
| **Screen capture protection** | Hides from Zoom, Teams, WebEx, Discord, OBS, Snipping Tool — free |
| **Stealth mode** | Toggle with `Alt+D` — app disappears from screen capture |
| **Screenshot toggle** | Independently enable/disable screen capture in Settings |
| **System tray** | Minimizes to tray when stealth is active |
| **Hide/show** | `Alt+Space` toggles window visibility without disabling stealth |
| **No cloud STT** | All transcription is local — nothing sent to external servers |

### Cognitive Graph

Personal knowledge graph powered by Neo4j to store and analyze your interview history.

| Feature | Description |
|---|---|
| **Semantic Search** | Search interview history by topic, company, or skill |
| **Entity Extraction** | Auto-extracts companies, skills, and topics from transcripts |
| **Company Insights** | See what questions companies typically ask |
| **Skill Progression** | Track your confidence across skills over time |
| **Auto-Ingest** | Conversations automatically added on save |
| **Q&A Extraction** | Parses transcripts into question-answer pairs |
| **Interview Predictions** | Predict likely questions for Google, Meta, Amazon, etc. |
| **Pre-Interview Prep** | Generated checklists based on company patterns |

**Access:** App menu (☰) → "Cognitive Graph" or "Pre-Interview Prep"

**Setup:** [docs/SETUP_COGNITIVE_GRAPH.md](docs/SETUP_COGNITIVE_GRAPH.md)

---

## Quick Start

### Prerequisites

- **macOS, Linux, or Windows 10/11**
- **Python 3.10+** — [python.org](https://python.org/downloads)
- **Node.js 20+** — [nodejs.org](https://nodejs.org) (LTS recommended)
- **Make** (optional but recommended) — macOS & most Linux ship with it; Windows users can use WSL or `choco install make`

### Step 1 — Clone

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

### Step 2 — One-command setup

```bash
make setup            # creates AINT_Venv/, installs Python + JS deps
# or:  make init       (alias for the above)
```

This is equivalent to:

```bash
python3 -m venv AINT_Venv
source AINT_Venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-test.txt
npm install           # installs all 4 workspaces
```

> Installing AI packages (`faster-whisper`, `spacy`, etc.) takes 5–10 minutes and ~4 GB disk.

### Step 3 — Ollama (recommended for free local AI)

```bash
brew install ollama   # or download from ollama.com
ollama serve &
ollama pull qwen2.5:1.5b
```

### Step 4 — Run the desktop app

```bash
make dev              # starts backend (:8000) + Electron window
# or:  make dev-web   # starts backend + Vite dev server (:5173), no Electron
```

The Electron app window appears. The Python backend starts automatically.

---

## Project Structure

ANT is a **monorepo with 4 npm workspaces** plus a Python backend. Each top-level directory is a deployable unit.

```
ai-note-taker/
├── apps/                          # Workspace 1: client apps
│   ├── web/                       # Vite SPA (multi-page, 14 HTML entries)
│   ├── landing/                   # Marketing landing page
│   └── ant-chrome-extension/      # Chrome extension (resume-copilot + meeting recorder)
│
├── electron/                      # Workspace 2: Electron desktop shell
│   ├── main.js                    # Main process: ~200 lines (slim entry point)
│   ├── preload.js                 # Secure context bridge
│   ├── stealth.js                 # Screen capture protection
│   ├── lib/                       # Shared helpers (logger, paths, crypto)
│   ├── windows/                   # BrowserWindow factories
│   ├── ipc/                       # IPC handler modules
│   ├── backend/                   # Python process management
│   └── features/                  # overlay-adapter, screen-recorder
│
├── mobile/                        # Workspace 3: React Native
│   ├── src/                       # 6+ screens (Login, Conversations, Interview,
│   │                              #   Career, Settings, VoiceRecording, ...)
│   ├── ios/                       # iOS native scaffold
│   ├── android/                   # Android native scaffold (Kotlin)
│   └── __tests__/                 # Jest smoke tests
│
├── backend/                       # FastAPI Python server
│   ├── core/                      # main.py, config.py, database.py, fast_startup.py
│   ├── modules/                   # 7 sub-packages: agents, ai, crm, interview,
│   │                              #   platform, video, voice
│   ├── routes/                    # 30+ FastAPI routers (one per concern)
│   ├── security/                  # auth, encryption, rate_limit, validation, audit
│   ├── lib/                       # http_client, sse_helpers
│   ├── migrations/                # Alembic versioned schema migrations
│   ├── tests/                     # 33 test files (~965 tests)
│   └── data/                      # SQLite DB, voice models, audit logs (gitignored)
│
├── docker/                        # 3 Dockerfiles (backend/cloud/electron)
│                                  #   + docker-compose.yml (with neo4j, postgres,
│                                  #   redis, prometheus, grafana profiles)
│
├── k8s/                           # Kubernetes Helm chart
│   ├── helm/backend/              # 11 templates (deployment, ingress, hpa, etc.)
│   └── applications/              # Argo CD / Flux app manifests
│
├── infrastructure/                # Terraform stacks for AWS / Azure / GCP
│   └── terraform/{aws,azure,gcp}/ # Each has main.tf + variables.tf + outputs.tf +
│                                  #   backend.tf + terraform.tfvars.example + README
│
├── e2e/                           # Workspace 4: Playwright e2e tests
│   └── tests/                     # 10 spec files
│
├── docs/                          # 50+ markdown docs (8 categories, see docs/README.md)
│                                  #   (getting-started, backend, devops, security,
│                                  #    product, performance, research, archive)
│
├── assets/                        # Design source files (icons, splash, etc.)
├── scripts/                       # Repo-helper scripts (PWA icons, dead-imports)
│
├── docker-compose.yml → docker/   # see docker/README.md
├── render.yaml                    # Render.com service definition
├── vercel.json                    # Vercel static-hosting config
│
├── Makefile                       # All dev commands (`make help` lists them)
├── package.json                   # Root workspace manifest (workspaces: [apps/*, electron, mobile, e2e])
├── MONOREPO.md                    # Monorepo layout + commands cheatsheet
├── .env.example                   # All env vars (copy to .env)
├── .github/                       # Dependabot, CODEOWNERS, PR/issue templates
│   └── workflows/ci.yml           # 4-job CI: backend-tests, web-build, e2e, security-scan
└── README.md                      # ← you are here
```

> The legacy `renderer/` directory mentioned in older docs has been moved to `apps/web/`. The Electron build's `extraResources` already points there.

---

## Workspaces

The root `package.json` declares 4 npm workspaces. Run any workspace's commands from the repo root:

| Command | What it does |
|---|---|
| `npm run web:dev` | Vite dev server for `apps/web` |
| `npm run web:build` | Production Vite build for `apps/web` |
| `npm run electron:start` | Run Electron desktop app |
| `npm run electron:build` | Build distributable for current platform |
| `npm run electron:build:win` | Windows .exe installer + portable |
| `npm run electron:build:mac` | macOS .dmg + .zip (x64 + arm64) |
| `npm run electron:build:linux` | Linux .AppImage + .deb |
| `npm run mobile:start` | React Native dev server |
| `npm run mobile:ios` | iOS simulator build |
| `npm run mobile:android` | Android emulator build |
| `npm run mobile:test` | Mobile Jest tests |
| `npm run e2e:test` | Playwright e2e suite |
| `npm run e2e:install:browsers` | Install Playwright browsers |
| `npm run extension:package` | Build Chrome extension |
| `npm run lint` | Lint all workspaces |
| `npm run test` | All non-backend tests |
| `npm run build` | Web + Electron production build |

See [MONOREPO.md](MONOREPO.md) for the full layout + migration story.

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))" >> .env
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env
```

The file lists every env var the backend reads, grouped into 14 sections (runtime, database, auth, CORS, rate limiting, cache, AI providers, embeddings, cognitive graph, webhooks, SSO, CRM, Whisper, dev overrides). See [.env.example](.env.example).

### Frontend env contract

The frontend (apps/web) does **not** read `.env.example`. It uses a `window.API_BASE` global (default `http://127.0.0.1:8000`). Override by injecting a `<script>` tag that sets `window.API_BASE = 'https://api.your-domain.com'` BEFORE `app.js` loads. There is no Vite `VITE_*` contract on the frontend.

### Ollama Model Management

In the app: **Settings → Ollama Models**
- **Pull** — enter a model name (e.g., `llama3:latest`, `deepseek-r1:8b`)
- **Delete** — remove a model to free disk space

---

## Keyboard Shortcuts

| Shortcut | Action | Scope |
|---|---|---|
| `Enter` | Toggle voice recording / Submit text | App window |
| `Ctrl+Enter` | Trigger AI from any app | **Global** (works when hidden) |
| `F` | Toggle maximize | App window |
| `Escape` | Close panels/modals | App window |
| `Alt+D` | Toggle stealth mode | **Global** |
| `Alt+Space` | Hide / show window | **Global** |
| `Ctrl+←/→/↑/↓` | Move window 50px | **Global** |

---

## Privacy

### Screen Capture Protection

ANT uses Electron's `setContentProtection()` API. When stealth mode is active, the window is hidden from Zoom, Meet, Teams, WebEx, Discord, Slack huddles, OBS, Snipping Tool, and any screen-capture app.

**How it works:** `electron/stealth.js` calls `window.setContentProtection(true)` which applies `WS_EX_FROMLEARN` on Windows — the same mechanism Netflix and Disney+ use. It does NOT use game-specific or anti-cheat APIs.

### No Cloud Transcription

All transcription runs locally via `faster-whisper` — audio never leaves your machine. AI responses are direct from the cloud provider to your device.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | Electron 41 |
| Frontend | Vanilla JavaScript, HTML5, CSS3 (Vite for builds) |
| Backend | FastAPI + uvicorn (Python 3.12) |
| Speech-to-text | faster-whisper (Whisper, local) |
| Local AI | Ollama |
| Cloud AI | OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Perplexity, Mistral, Cohere, HuggingFace, Ollama Cloud |
| Cognitive graph | Neo4j 5.x |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy + Alembic migrations |
| Audio capture | Browser MediaRecorder + Web Audio API |
| Mobile | React Native 0.73 (Kotlin Android / Obj-C iOS) |
| Persistent storage | electron-store + JSON files + SQLite |
| Logging | electron-log + Python logging (rotating JSON lines) |
| CI | GitHub Actions (4 jobs: backend-tests, web-build, e2e, security-scan) |
| Container | Docker + Docker Compose (with neo4j, postgres, redis profiles) |
| Orchestration | Kubernetes + Helm chart (with ingress, prometheus, sealed-secrets) |
| IaC | Terraform stacks for AWS, Azure, GCP |

---

## Building

### Web

```bash
cd apps/web
npm run build
# Output: apps/web/dist/
```

### Electron distributables

```bash
cd electron
npm run build:win      # Windows .exe (NSIS installer + portable)
npm run build:mac      # macOS .dmg + .zip (x64 + arm64)
npm run build:linux    # Linux .AppImage + .deb
# Output: electron/dist/
```

### Docker

```bash
docker build -f docker/Dockerfile.backend -t ant-backend .
# or
make docker-up                          # backend only
make docker-up-full                     # backend + neo4j + postgres + redis + monitoring
```

### Kubernetes

```bash
make helm-vendor        # one-time: vendor bitnami/common
helm lint k8s/helm/backend
helm template ant-backend k8s/helm/backend/ \
  --values k8s/helm/backend/values-production.yaml
```

---

## Documentation

> Pick the area you need. The full index is at [docs/README.md](docs/README.md).

### Start here

- [docs/COMPREHENSIVE_GUIDE.md](docs/COMPREHENSIVE_GUIDE.md) — 60KB deep-dive into every feature
- [docs/INSTALL.md](docs/INSTALL.md) — Step-by-step install for Windows / macOS / Linux
- [MONOREPO.md](MONOREPO.md) — Monorepo layout + workspace commands
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute
- [SECURITY.md](SECURITY.md) — Vulnerability disclosure policy
- [docs/README.md](docs/README.md) — Index of all 50+ docs

### Operations

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — Day-to-day dev commands
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — Production runbook
- [docs/MIGRATIONS.md](docs/MIGRATIONS.md) — Alembic migration guide
- [docs/MOBILE.md](docs/MOBILE.md) — React Native mobile setup
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Common errors + fixes

### API & data

- [docs/api/API_REFERENCE.md](docs/api/API_REFERENCE.md) — REST + WebSocket reference (280+ paths)
- [docs/database/SCHEMA.md](docs/database/SCHEMA.md) — 13 SQLAlchemy models
- [docs/architecture/TECHNICAL_SPECIFICATION.md](docs/architecture/TECHNICAL_SPECIFICATION.md) — Architecture spec
- [docs/COGNITIVE_GRAPH_API.md](docs/COGNITIVE_GRAPH_API.md) — Neo4j graph API
- [docs/SETUP_COGNITIVE_GRAPH.md](docs/SETUP_COGNITIVE_GRAPH.md) — Neo4j setup
- [docs/API_REFERENCE_PHASE2.md](docs/API_REFERENCE_PHASE2.md) — Phase 2 endpoint reference

### Security

- [docs/security/SECURITY_IMPLEMENTATION_SUMMARY.md](docs/security/SECURITY_IMPLEMENTATION_SUMMARY.md)
- [BROWSER_EXTENSION_SAFETY.md](BROWSER_EXTENSION_SAFETY.md)
- [SECURITY.md](SECURITY.md)

### Business & competitive

- [docs/BYOK_BUSINESS_MODEL.md](docs/BYOK_BUSINESS_MODEL.md) — Bring-Your-Own-Key model
- [docs/COMPETITIVE_GAP_ANALYSIS_UPDATED_APRIL_2026.md](docs/COMPETITIVE_GAP_ANALYSIS_UPDATED_APRIL_2026.md) — Competitor matrix

### Architecture

- [docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md)
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) — Production deployment
- [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) — Pre-launch checklist
- [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) — Release process

---

## Project Status

- **60 of 60 audit items closed** as of 2026-06-07. See [docs/shared/AUDIT_2026-06-05_Project_Audit.md](docs/shared/AUDIT_2026-06-05_Project_Audit.md) for the full breakdown.
- **965 backend tests** (905 pass, 3 pre-existing failures documented in [memory/pre-existing-test-failures.md](memory/pre-existing-test-failures.md), 57 skipped).
- **CI green** — every PR runs pytest, web build, e2e, and security scan via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
- **Shippable.** Backend boots, all major endpoint groups respond, auth gate fires on protected routes.

---

## License

MIT License — Free to use, modify, and distribute. See [LICENSE](LICENSE).
