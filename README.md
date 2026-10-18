# ANT · AI Note Taker

A floating workspace for voice notes, screen-aware questions, and interview preparation. Use local Whisper transcription and Ollama models, or connect your own cloud AI keys.

[![Latest release](https://img.shields.io/github/v/release/shyamsunderprogramer-design/ai-note-taker)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest)
[![CI](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**[Download](#download) · [Features](#features) · [Architecture](#architecture) · [Source setup](#run-from-source) · [Troubleshooting](#troubleshooting) · [Documentation](#documentation)**

## Download

**[ANT v2.3.0-rc.1](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/latest)** is the current download, published October 17, 2026. It appears in GitHub's **Latest** box and remains a release candidate for testing. Read the [release notes and known limits](docs/releases/2.3.0-rc.1.md) before upgrading. [Previous releases](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases) remain available.

The desktop packages include Electron and a standalone Python runtime. You do **not** need to install Python or Node.js to use them. AI model downloads, Ollama for local AI, and cloud provider credentials are separate.

| Platform | Installer | Notes |
|---|---|---|
| **Windows 10/11 (x64)** | [Windows installer (.exe)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-Setup-2.3.0-rc.1-win-x64.exe) | Install ANT with the setup wizard. |
| **Windows 10/11 (x64), portable** | [Portable Windows app (.exe)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-2.3.0-rc.1-win-x64.exe) | Run without the setup wizard. |
| **macOS (Apple Silicon)** | [Apple Silicon Mac (.zip)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-2.3.0-rc.1-mac-arm64.zip) | macOS 14 or newer; extract and move the app to Applications. |
| **macOS (Intel)** | [Intel Mac (.zip)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-2.3.0-rc.1-mac-x64.zip) | macOS 14 or newer; extract and move the app to Applications. |
| **Linux (x64)** | [Linux AppImage](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-2.3.0-rc.1-linux-x86_64.AppImage) | Make the downloaded file executable, then run it. |
| **Linux (Debian/Ubuntu, x64)** | [Debian package (.deb)](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/ANT-2.3.0-rc.1-linux-amd64.deb) | Install with your package manager. |

**Verify the file:** compare `shasum -a 256 <downloaded-file>` on macOS/Linux, or `certutil -hashfile <downloaded-file> SHA256` on Windows, with the matching entry in [SHA256SUMS.txt](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases/download/v2.3.0-rc.1/SHA256SUMS.txt).

### First launch

Back up existing data: this candidate does not automatically migrate data out of an older installation's internal resources. Windows builds have no publisher certificate and may display a publisher warning. On Linux, make the AppImage executable or install the `.deb` with your package manager.

**macOS verification warning:** these builds are signed ad hoc, without an Apple Developer ID certificate or notarization. A message such as “Apple could not verify ANT” means macOS cannot verify the app through its normal trust checks; it is not a safety assessment of this release.

If you trust the official download and its checksum matches:

1. Extract the ZIP for your Mac's processor and move **ANT (AI Note Taker).app** to **Applications**.
2. Try opening it once, then dismiss the verification warning.
3. Open **System Settings → Privacy & Security**, scroll to **Security**, and select **Open Anyway** for ANT.
4. Confirm **Open** and authenticate if requested.

This creates an exception for ANT. See [Apple's instructions](https://support.apple.com/en-us/102445). If the alert instead says the app will damage your computer or is damaged, stop and investigate that different warning.

## Features

| Workflow | What ANT provides |
| --- | --- |
| Voice notes and live assistance | Local speech transcription, live transcript display, microphone input, and system-audio capture where supported. |
| AI conversations | Streamed answers, follow-up context, model selection, and local or cloud providers. Auto/race routing can contact multiple enabled providers. |
| Screen questions | Attach screenshots or enable automatic capture; image questions require a vision-capable model. |
| Meeting notes and history | Conversation history, summaries, search, and export controls. |
| Interview preparation | Resume and job-description context, practice interviews, and preparation pages. |
| Desktop controls | Floating window, global shortcuts, tray controls, and OS-dependent capture protection. |

The browser shares the web interface but does not provide Electron's native capture, window controls, or global shortcuts. Mobile apps and browser extensions are separate projects in this repository; the desktop release does not certify all of their workflows. Legacy CRM write integrations remain unavailable until real provider implementations are connected.

## Architecture

[![ANT architecture: the Electron desktop and browser connect to FastAPI; the backend uses local Whisper, Ollama and storage, with optional cloud AI calls.](docs/architecture/overview.png)](docs/architecture/overview.svg)

The diagram shows the default local setup. Electron starts the Python backend on `127.0.0.1:8000`; browser development uses Vite on port `5173` alongside that backend. The interfaces use HTTP, streamed responses and WebSocket audio. Desktop native features use Electron's preload IPC bridge.

Whisper turns audio into text. The AI router sends the selected conversation and image context to local Ollama or configured cloud providers. SQLite and local files store application data; Electron also saves its own conversation JSON and settings. A remotely hosted backend moves the corresponding processing and data to that server.

[Architecture guide and source map](docs/architecture/README.md) · [Editable SVG](docs/architecture/overview.svg)

## Run from source

Use this path for development or to run the source directly. Packaged-app users can skip to [Start using ANT](#start-using-ant).

### 1. Prerequisites

- Git.
- **Python 3.12**, with `3.12.15` pinned in [`.python-version`](.python-version).
- **Node.js 22.12.0 or newer** and **npm 10 or newer**, as declared in [`package.json`](package.json).
- macOS 14 or newer, Windows 10/11 x64, or Linux x64 for the desktop targets covered by the release workflow.
- [Ollama](https://ollama.com/download) if you want local AI. Cloud AI does not require a local Ollama server.

Initial package installation and model downloads require internet access. Model size and available memory affect local performance. PostgreSQL, Redis and Neo4j are optional for the basic local workflow.

### 2. Clone and install

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

**macOS / Linux**

```bash
python3.12 -m venv AINT_Venv
source AINT_Venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
npm ci
```

**Windows PowerShell**

```powershell
py -3.12 -m venv AINT_Venv
.\AINT_Venv\Scripts\python.exe -m pip install --upgrade pip
.\AINT_Venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm ci
```

Keep the virtual environment named `AINT_Venv`: the desktop launcher looks there before falling back to a system Python. Run `npm ci` at the repository root so it installs the locked workspace dependencies.

### 3. Configure the backend

Copy the template to a private `.env` file:

```bash
cp .env.example .env
```

In PowerShell, use `Copy-Item .env.example .env`. On an existing checkout, check for `backend/.env`: dotenv finds it before the repository-root `.env`.

Generate the values requested by the template:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

In PowerShell, replace `python` with `.\AINT_Venv\Scripts\python.exe`. Put the first output in `JWT_SECRET_KEY` and the second in `ENCRYPTION_KEY`. Keep these settings private and stable across restarts; do not commit `.env`.

For local development, keep authentication enabled and allow the browser development origins:

```dotenv
ENVIRONMENT=development
AUTH_REQUIRED=true
HTTPS_REQUIRED=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
```

The default local database is SQLite. Additional deployment settings are described in [`.env.example`](.env.example).

### 4. Choose local or cloud AI

**Local:** install Ollama and start its service. The repository's general-purpose default is [qwen3.5:9b](https://ollama.com/library/qwen3.5:9b):

```bash
ollama pull qwen3.5:9b
ollama list
```

If needed, run `ollama serve` in a separate terminal. Select an installed model in ANT. To use another model, update `OLLAMA_MODEL` and any relevant `OLLAMA_MODEL_*` overrides in `.env`; you do not need every model listed in the template.

**Cloud:** enter your provider key in ANT's Settings, or set its variable in `.env`, then select that provider/model. Cloud requests require internet access and provider quota. Usage is billed through your provider account.

Screenshot questions require a model that accepts images. Text-only models can answer typed or transcribed questions.

### 5. Launch

**Desktop**, from the repository root:

```bash
npm run electron:start
```

Electron starts the local backend automatically, or reuses a responding backend on port 8000.

**Browser**, start the backend in one terminal:

```bash
source AINT_Venv/bin/activate
cd backend
python -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000
```

In PowerShell, from the repository root:

```powershell
cd backend
..\AINT_Venv\Scripts\python.exe -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000
```

Start the web server in a second terminal, from the repository root:

```bash
npm run web:dev
```

Open **http://localhost:5173/signin.html**. The running backend exposes API documentation at **http://127.0.0.1:8000/docs** and a health endpoint at **http://127.0.0.1:8000/health**. Stop manually started servers with `Ctrl+C`.

## Start using ANT

1. Create an account or sign in, then complete onboarding.
2. Choose a provider and model. Send a typed question first to check the connection.
3. Allow microphone access for voice input. The first transcription may download a speech model.
4. For screen questions, grant the required recording permission and select a vision-capable model.
5. Use History to revisit conversations, or generate a meeting summary and export it.

Microphone input captures your voice. System-audio capture, where available, captures sound played by the computer and needs the appropriate OS permissions. Screen capture protection and screenshot capture are separate controls.

### Desktop shortcuts

Use **Cmd** on macOS and **Ctrl** on Windows/Linux for `Ctrl / Cmd` entries.

| Shortcut | Action |
| --- | --- |
| `Ctrl / Cmd + Enter` | Trigger an AI response globally. |
| `Ctrl / Cmd + Shift + Enter` | Trigger an answer with screen context. |
| `Ctrl / Cmd + ,` | Open Settings. |
| `Alt + Space` | Hide or show the window. |
| `Alt + D` | Toggle capture-protection mode. |
| `Ctrl / Cmd + Arrow keys` | Move the window. |

The OS or another application may already use a global shortcut. Check the desktop logs if registration fails.

## Privacy and data

- **Transcription:** with the backend running locally, Whisper processes audio on your machine. Model downloads still require a network connection initially.
- **Local AI:** a local Ollama model processes the selected prompt on your machine. Remote Ollama endpoints and cloud models send it to their configured server.
- **Cloud AI:** selected transcript, conversation, resume and image context can be sent to the configured provider. Auto/race routing can send a request to more than one enabled provider.
- **Storage:** desktop history and settings are local. Packaged backend data is written to a user-data directory; source installs use local development paths. Browser state can also live in browser storage. Back up data and protect credentials before moving or replacing an installation.
- **Screen protection:** availability depends on the OS and capture method. It does not guarantee invisibility. Electron documents that newer macOS apps using ScreenCaptureKit can still capture protected windows; see [Electron's content-protection documentation](https://www.electronjs.org/docs/latest/api/browser-window#winsetcontentprotectionenable).

If you connect the interface to a remote backend, the audio, uploads and application data handled by that backend are processed on the remote server.

## Development and testing

Run these from the repository root after installing dependencies:

| Command | Purpose |
| --- | --- |
| `npm run web:dev` | Start Vite on port 5173. |
| `npm run web:build` | Build the web interface into `apps/web/dist/`. |
| `npm run electron:start` | Launch the desktop app. |
| `npm --workspace ai-note-taker test` | Run Electron unit tests. |
| `npm --workspace ant-web test` | Run web unit tests. |
| `npm run mobile:test -- --runInBand` | Run mobile Jest tests. |
| `npm run test:security` | Run dependency/security regression tests. |
| `npm run e2e:install:browsers` | Install the Playwright browsers. |
| `npm run e2e:test` | Run the browser suite with isolated test servers. |
| `make help` | List the Make convenience targets. |

For backend tests, activate the virtual environment, then run:

```bash
python -m pip install -r backend/requirements-test.txt
cd backend
python -m pytest core/test_startup.py tests/ --tb=short
```

[CI](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/workflows/ci.yml) runs backend, desktop, web and mobile checks, browser tests, workflow validation and security checks. [CodeQL](https://github.com/shyamsunderprogramer-design/ai-note-taker/actions/workflows/codeql.yml) runs separately. Passing checks do not establish that every optional integration or target-device audio workflow has been tested; see the [release limits](docs/releases/2.3.0-rc.1.md).

### Build a desktop package

Build on the target OS and architecture. Prepare the standalone Python runtime before calling electron-builder:

```bash
npm ci
python scripts/build_desktop_runtime.py
npm run electron:build:mac
```

Use `electron:build:win` or `electron:build:linux` on the corresponding host. Output goes to `electron/dist/`. The runtime builder downloads the checksum-pinned Python defined in [`scripts/python-runtime.json`](scripts/python-runtime.json), installs the backend dependencies into `AINT_Python/`, and refuses to overwrite an existing runtime directory.

The [release workflow](.github/workflows/release.yml) is the reference for the four native build targets, bundled-runtime audits, packaged sign-in checks and checksums. macOS output is ZIP; Windows output is installer and portable EXE; Linux output is AppImage and DEB.

Future macOS release builds require [Developer ID signing and Apple notarization](docs/devops/deployment/MACOS_SIGNING.md). Local builds remain ad-hoc signed. This pipeline change does not notarize the existing `v2.3.0-rc.1` downloads.

## Project layout

```text
apps/web/                    Shared desktop/browser UI and Vite build
apps/ant-chrome-extension/   Browser extension workspace
backend/core/                FastAPI entry point, configuration and database
backend/routes/              API route modules
backend/modules/             AI, voice, interview and other services
electron/                    Desktop main process, preload, capture and packaging
mobile/                      React Native app
e2e/                         Playwright browser tests
scripts/                     Runtime preparation and release verification
docs/                        Setup, architecture, API and operations guides
```

Additional extension variants and deployment templates are included in the repository. Consult their own documentation before using them.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| macOS says Apple could not verify ANT | Follow the [first-launch steps](#first-launch) for the official download. This release has no Apple notarization. |
| Backend is offline | Confirm dependencies are in `AINT_Venv`; run the backend manually to see startup errors. Packaged builds require their bundled Python directory. |
| Port 8000 is occupied | Check whether ANT is already running before starting another backend. |
| Browser cannot connect | Keep both servers running; allow port 5173 origins in `CORS_ORIGINS`. Restart the backend after editing `.env`. |
| Local model is unavailable | Check `ollama list`, the running service, model selection and per-mode overrides. |
| Cloud request fails | Check the provider key, model access, enabled providers and available quota. |
| Audio or screenshots are missing | Check the selected device and OS recording permissions; system-audio support varies by platform. |
| First transcription is slow | Allow the speech model download and initial load to finish. |
| Sign-in fails after restart | Keep a stable `JWT_SECRET_KEY`, restart the backend, then sign in again. |

See the [troubleshooting guide](docs/devops/development/TROUBLESHOOTING.md) for more detail.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture diagram and source map](docs/architecture/README.md)
- [Current release notes](docs/releases/2.3.0-rc.1.md) and [changelog](CHANGELOG.md)
- [Detailed installation](docs/devops/development/INSTALL.md)
- [Environment template](.env.example)
- [Cognitive Graph setup](docs/backend/setup/SETUP_COGNITIVE_GRAPH.md)
- [Mobile](mobile/README.md), [browser extension](apps/ant-chrome-extension/README.md), and [Docker](docker/README.md)
- [Contributing](CONTRIBUTING.md) and [security policy](SECURITY.md)

## License

[MIT](LICENSE).
