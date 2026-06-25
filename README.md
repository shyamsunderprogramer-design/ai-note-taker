# ANT (AI Note Taker)

**A privacy-first AI notepad that runs entirely on your machine.**

Local speech-to-text, local and cloud AI models, floating overlay UI, screen capture protection, and real-time transcription — packaged as an Electron desktop app, a web SPA, a React Native mobile app, and a Chrome extension, all backed by a FastAPI Python backend.

[![Release v2.1.0](https://img.shields.io/github/v/release/shyamsunderprogramer-design/ai-note-taker?include_prereleases&sort=semver)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS · Linux · Windows](https://img.shields.io/badge/Platform-macOS%20·%20Linux%20·%20Windows-lightgrey.svg)](#download)

---

## Download

> **Latest stable: [v2.1.0](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest)** — released 2026-06-23. Closes out the Fix #35 series (full-fidelity users.json → SQL migration, AI race stream hardening).

| Platform | Installer | Notes |
|---|---|---|
| **Windows 10/11 (x64)** | [`ANT (AI Note Taker)-Setup-2.1.0-win-x64.exe`](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest) | NSIS installer (recommended) + portable .exe. Unsigned — SmartScreen will warn; click "More info" → "Run anyway". |
| **macOS (Apple Silicon)** | [`ANT (AI Note Taker)-2.1.0-mac-arm64.dmg`](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest) | Drag-to-Applications. Unsigned — first launch needs right-click → Open, or `xattr -d com.apple.quarantine /Applications/ANT.app`. |
| **macOS (Intel)** | [`ANT (AI Note Taker)-2.1.0-mac-x64.dmg`](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest) | Same as above for older Macs. |
| **Linux (x64)** | [`ANT (AI Note Taker)-2.1.0-linux-x64.AppImage`](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest) | `chmod +x *.AppImage && ./ANT*.AppImage`. No install needed. |
| **Linux (Debian/Ubuntu)** | [`ANT (AI Note Taker)-2.1.0-linux-x64.deb`](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest) | `sudo dpkg -i ant*.deb && sudo apt -f install` to pull any missing deps. |

All installers are built by electron-builder per `electron/package.json` → `build`. On first launch the app auto-migrates any existing `data/users.json` into the SQLAlchemy users table (no operator action required).

**Verify your download:** each release on GitHub includes `SHA256SUMS.txt` next to the installers — `shasum -a 256 -c SHA256SUMS.txt` (macOS/Linux) or `certutil -hashfile ANT-Setup-2.1.0-win-x64.exe SHA256` (Windows).

### First-launch notes (unsigned builds)

ANT's CI builds are **unsigned** to keep the project free-to-distribute. Operating systems will warn on first install — here's what to do on each platform:

**Windows (SmartScreen)**
1. Double-click `ANT (AI Note Taker)-Setup-2.1.0-win-x64.exe`.
2. SmartScreen shows "Windows protected your PC" → click **More info**.
3. Click **Run anyway**. The warning is permanent until the project signs with a code-signing certificate.

**macOS (Gatekeeper)**
1. Open the `.dmg` and drag `ANT.app` to `/Applications`.
2. **Don't** double-click `ANT.app` from the DMG or Launchpad. Instead, **right-click (or Control-click) → Open** from Finder.
3. Click **Open** in the dialog that warns "Apple could not verify...". macOS remembers your decision for this app on this machine.
4. After the first open, double-click works normally.

   **Alternative (terminal):** strip the quarantine attribute:
   ```bash
   xattr -dr com.apple.quarantine "/Applications/ANT (AI Note Taker).app"
   ```

**Linux**
- **AppImage:** `chmod +x ANT*.AppImage && ./ANT*.AppImage` — no install needed.
- **Debian/Ubuntu:** `sudo dpkg -i ant*.deb && sudo apt -f install` if missing deps.

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

**Setup:** [docs/backend/setup/SETUP_COGNITIVE_GRAPH.md](docs/backend/setup/SETUP_COGNITIVE_GRAPH.md)

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
├── docs/                          # 50+ markdown docs, per-role layout (see docs/README.md)
│                                  #   roles: backend, uiux, devops, qa, devsecops
│                                  #   topics: shared, business, competitive, research, archive
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
> Docs are organized by role (the same 5 roles defined in
> [`OWNERS.*.md`](OWNERS.backend.md) and enforced by
> [`.github/CODEOWNERS`](.github/CODEOWNERS)).

### Start here

- [docs/shared/COMPREHENSIVE_GUIDE.md](docs/shared/COMPREHENSIVE_GUIDE.md) — 60KB deep-dive into every feature
- [docs/devops/development/INSTALL.md](docs/devops/development/INSTALL.md) — Step-by-step install for Windows / macOS / Linux
- [MONOREPO.md](MONOREPO.md) — Monorepo layout + workspace commands
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute
- [docs/devsecops/compliance/SECURITY.md](docs/devsecops/compliance/SECURITY.md) — Vulnerability disclosure policy
- [docs/README.md](docs/README.md) — Index of all 50+ docs

### Operations (devops)

- [docs/devops/development/DEVELOPMENT.md](docs/devops/development/DEVELOPMENT.md) — Day-to-day dev commands
- [docs/devops/operations/OPERATIONS.md](docs/devops/operations/OPERATIONS.md) — Production runbook
- [docs/devops/development/MIGRATIONS.md](docs/devops/development/MIGRATIONS.md) — Alembic migration guide
- [docs/devops/development/MOBILE.md](docs/devops/development/MOBILE.md) — React Native mobile setup
- [docs/devops/development/TROUBLESHOOTING.md](docs/devops/development/TROUBLESHOOTING.md) — Common errors + fixes
- [docs/devops/deployment/DEPLOYMENT_GUIDE.md](docs/devops/deployment/DEPLOYMENT_GUIDE.md) — Production deployment
- [docs/devops/deployment/PRODUCTION_CHECKLIST.md](docs/devops/deployment/PRODUCTION_CHECKLIST.md) — Pre-launch checklist
- [docs/devops/deployment/RELEASE_CHECKLIST.md](docs/devops/deployment/RELEASE_CHECKLIST.md) — Release process

### API & data (backend)

- [docs/backend/api/API_REFERENCE.md](docs/backend/api/API_REFERENCE.md) — REST + WebSocket reference (280+ paths)
- [docs/backend/api/API_REFERENCE_PHASE2.md](docs/backend/api/API_REFERENCE_PHASE2.md) — Phase 2 endpoint reference
- [docs/backend/database/SCHEMA.md](docs/backend/database/SCHEMA.md) — 13 SQLAlchemy models
- [docs/backend/architecture/TECHNICAL_SPECIFICATION.md](docs/backend/architecture/TECHNICAL_SPECIFICATION.md) — Architecture spec
- [docs/backend/architecture/PROJECT_STRUCTURE.md](docs/backend/architecture/PROJECT_STRUCTURE.md) — File layout
- [docs/backend/COGNITIVE_GRAPH_API.md](docs/backend/COGNITIVE_GRAPH_API.md) — Neo4j graph API
- [docs/backend/setup/SETUP_COGNITIVE_GRAPH.md](docs/backend/setup/SETUP_COGNITIVE_GRAPH.md) — Neo4j setup

### Security (devsecops)

- [docs/devsecops/security/SECURITY_IMPLEMENTATION_SUMMARY.md](docs/devsecops/security/SECURITY_IMPLEMENTATION_SUMMARY.md)
- [docs/devsecops/security/BROWSER_EXTENSION_SAFETY.md](docs/devsecops/security/BROWSER_EXTENSION_SAFETY.md)
- [docs/devsecops/security/threat-model.md](docs/devsecops/security/threat-model.md)
- [docs/devsecops/supply-chain/dependabot-policy.md](docs/devsecops/supply-chain/dependabot-policy.md)
- [docs/devsecops/compliance/audit-log-policy.md](docs/devsecops/compliance/audit-log-policy.md)

### UI/UX

- [docs/uiux/README.md](docs/uiux/README.md) — web SPA, mobile, Chrome extension, Electron UI
- [docs/uiux/design-system/README.md](docs/uiux/design-system/README.md) — tokens, typography, spacing
- [docs/uiux/components/README.md](docs/uiux/components/README.md) — per-component docs
- [docs/uiux/accessibility/README.md](docs/uiux/accessibility/README.md) — a11y patterns, keyboard shortcuts

### QA

- [docs/qa/test-strategy.md](docs/qa/test-strategy.md) — the layered test strategy
- [docs/qa/test-environment.md](docs/qa/test-environment.md) — versions in use + known gotchas
- [docs/qa/DIY_TEST_GUIDE.md](docs/qa/DIY_TEST_GUIDE.md) — how to manually test the desktop app

### Business & competitive

- [docs/business/BYOK_BUSINESS_MODEL.md](docs/business/BYOK_BUSINESS_MODEL.md) — Bring-Your-Own-Key model
- [docs/business/PHASE2_PLAN.md](docs/business/PHASE2_PLAN.md) — Phase 2 product plan
- [docs/business/resume-builder/](docs/business/resume-builder/) — resume builder deep-dive
- [docs/competitive/](docs/competitive/) — competitor matrix + Pluely

### Cross-cutting

- [docs/shared/AUDIT_2026-06-05_Project_Audit.md](docs/shared/AUDIT_2026-06-05_Project_Audit.md) — June-2026 project audit
- [docs/shared/PRODUCTION_DEEP_DIVE_2026.md](docs/shared/PRODUCTION_DEEP_DIVE_2026.md) — production-readiness deep dive
- [docs/shared/CRITICAL_GAPS_FIXED.md](docs/shared/CRITICAL_GAPS_FIXED.md) — historical record of critical bugs

### Per-role charters

The 5 roles that own this repo (each has a charter at the root
and a CODEOWNERS block in `.github/CODEOWNERS`):

- [`OWNERS.backend.md`](OWNERS.backend.md) — FastAPI, services, DB, AI integration
- [`OWNERS.uiux.md`](OWNERS.uiux.md) — web SPA, mobile, Chrome extension, design
- [`OWNERS.devops.md`](OWNERS.devops.md) — deploy, runtime shell, CI, infra
- [`OWNERS.qa.md`](OWNERS.qa.md) — tests, fixtures, e2e, performance
- [`OWNERS.devsecops.md`](OWNERS.devsecops.md) — security, supply chain, secrets, compliance

---

## Project Status

- **60 of 60 audit items closed** as of 2026-06-07. See [docs/shared/AUDIT_2026-06-05_Project_Audit.md](docs/shared/AUDIT_2026-06-05_Project_Audit.md) for the full breakdown.
- **965 backend tests** (905 pass, 3 pre-existing failures documented in [memory/pre-existing-test-failures.md](memory/pre-existing-test-failures.md), 57 skipped).
- **CI green** — every PR runs pytest, web build, e2e, and security scan via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
- **Shippable.** Backend boots, all major endpoint groups respond, auth gate fires on protected routes.

---

## License

MIT License — Free to use, modify, and distribute. See [LICENSE](LICENSE).
