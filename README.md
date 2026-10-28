# ANT · AI Note Taker

A floating AI workspace for voice notes, screen-aware questions, and interview preparation. Type a question, speak into your microphone, or ask about what is on your screen. Use Ollama for local AI or connect your own cloud API keys.

**[Set up](#set-up-from-source) · [Start using ANT](#start-using-ant) · [Troubleshooting](#troubleshooting) · [Documentation](#documentation)**

## Choose how to run it

| Option | Best for | What you need |
| --- | --- | --- |
| Desktop installer | Using a packaged version | An installer for your OS from [GitHub Releases](https://github.com/shyamsunderprogramer-design/ai-note-taker/releases) |
| Desktop from source | Using the current source and floating window | Git, Python, Node.js, and the setup below |
| Browser from source | Using the web interface | The same setup, with the backend and web server running |

Packaged releases can lag behind the source. Available installers and versions are listed on the release page. Desktop features such as global shortcuts, native screen capture, and window controls depend on Electron; the browser interface does not provide every desktop feature.

## Set up from source

### 1. Install the prerequisites

- **Git** to clone the repository.
- **Python 3.11** as the repository's pinned Python series; use a 64-bit installation.
- **Node.js 20+ and npm 10+** for the JavaScript workspaces.
- **Ollama**, if you want local AI. Cloud AI does not require Ollama.

Run the commands below from the repository root unless a step says otherwise. Initial dependency installation and speech/model downloads require internet access. Model size and available memory determine how comfortably local AI runs.

### 2. Clone the repository

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

### 3. Install dependencies

**macOS / Linux**

```bash
python3 -m venv AINT_Venv
source AINT_Venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
npm install
```

**Windows PowerShell**

```powershell
py -3.11 -m venv AINT_Venv
.\AINT_Venv\Scripts\python.exe -m pip install --upgrade pip
.\AINT_Venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm install
```

Keep the virtual environment named `AINT_Venv`: the desktop app looks there for Python. React Native and other workspaces are installed by the root npm command; native mobile toolchains are only needed when building mobile apps.

If you have Make and a Bash-compatible shell, `make setup` creates the environment and installs Python, test, and JavaScript dependencies instead.

### 4. Configure the backend

Copy the environment template:

```bash
cp .env.example .env
```

On Windows PowerShell, use `Copy-Item .env.example .env`.

Generate the two keys using the virtual environment's Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

On Windows, replace `python` with `.\AINT_Venv\Scripts\python.exe` in these commands.

In `.env`, replace the blank `JWT_SECRET_KEY` and `ENCRYPTION_KEY` values with the respective outputs. Also set the development origins:

```dotenv
ENVIRONMENT=development
JWT_SECRET_KEY=your_generated_signing_secret
ENCRYPTION_KEY=your_generated_fernet_key
AUTH_REQUIRED=true
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
```

Use the generated values, not the placeholders above. Keep the keys stable across restarts and keep `.env` private. SQLite is the default local database when `DATABASE_URL` is empty; PostgreSQL, Redis, and Neo4j are optional for the basic workflow.

The backend also loads `backend/.env` if present. Check that file for conflicting settings when reusing an existing checkout.

### 5. Choose local or cloud AI

#### Local AI with Ollama

Install Ollama, start its service, and pull a model. The repository's default general-purpose model is:

```bash
ollama pull qwen3.5:9b
ollama list
```

If the service is not running, start `ollama serve` in a separate terminal. Leave it running while using local AI.

In ANT, select an installed local model. To use another model, pull its exact name and update `OLLAMA_MODEL` in `.env`. Individual modes have their own `OLLAMA_MODEL_*` settings; set those too if you want them to use the same model. You do not need to download every model listed in the template.

Screenshot questions need a model that supports images. Text-only models can still answer typed and transcribed questions.

#### Cloud AI with your own key

Launch ANT, open **Settings**, find the providers section, and enter your provider's API key. Save it, then choose that provider/model or **Auto**. Provider keys can also be supplied through the corresponding variables in `.env`.

Cloud responses need internet access and available provider quota. Screenshot questions need a vision-capable provider/model. Provider usage is billed according to your account with that service.

### 6. Launch ANT

**Desktop — from the repository root:**

```bash
npm run electron:start
```

Electron starts the Python backend automatically and reuses it if it is already running on port **8000**.

**Browser — start the backend in one terminal:**

```bash
source AINT_Venv/bin/activate
cd backend
python -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows PowerShell:

```powershell
cd backend
..\AINT_Venv\Scripts\python.exe -m uvicorn core.main:app --reload --host 127.0.0.1 --port 8000
```

**Then start the web app in another terminal, from the repository root:**

```bash
npm run web:dev
```

Open **http://localhost:5173**. Backend API documentation is available at **http://127.0.0.1:8000/docs** while the backend is running. Stop manually started servers with `Ctrl+C` in their terminals.

With Make, `make dev` starts the backend and desktop app; `make dev-web` starts the backend and browser development server.

## Start using ANT

### First launch

1. Create an account or sign in through the app's sign-in screen.
2. Complete onboarding and allow microphone access if you want voice input.
3. Choose your AI provider and model. Start with a typed question such as **“Explain this project in three bullet points.”**
4. Check that the answer arrives before enabling voice or screen capture.

### Ask a question

Type into the input field and press **Enter**. Follow-up questions use the current conversation, so you can ask **“Show an example”** or **“Explain that more simply”** without repeating the context.

The desktop starts with a compact window. The first message reveals the conversation; use the show/hide controls to collapse or expand it. Hiding the conversation preserves messages. Clearing it starts a fresh context.

### Use voice input

Allow microphone access, choose the appropriate input device, and use the microphone control to record. Enable **Always-on mic** in the background-services controls for continuous listening.

ANT transcribes speech locally with Whisper. The first transcription may need to download the speech model. For interviewer or meeting audio, use the available system-audio capture controls and grant the OS recording permission. Microphone input captures your voice; system audio captures sound played by your computer.

Typed questions can still be submitted while listening. Check the transcript when names, technical terms, or noisy audio are involved.

### Ask about your screen

On desktop, grant screen-recording access and attach a screenshot, or enable automatic screenshots in the background-services controls. Select a vision-capable model, then ask something specific:

- “Explain the error shown here.”
- “Complete this function and explain the change.”
- “Summarize the information in this window.”

Screen-aware interviewer questions request fresh screen context. Keep the relevant window visible and check that the capture contains what you want to discuss. Generated code is returned in the conversation; ANT does not automatically type it into your terminal.

### Personalize interview answers

Open the **Resume and job description** control, use **Resume +** to attach your resume, and save the job description. This context applies to future questions until you edit or remove it.

Choose **Interview** mode to set company and role context. The app menu also provides interview practice and preparation tools.

### Save, review, and export

Conversations are saved automatically. Open **History** from the app menu to search and reopen a saved chat. Use the summary control for structured notes, and the conversation export action to download **TXT**, **CSV**, or **JSON**.

### Desktop shortcuts

On macOS, use **Cmd** where the table says **Ctrl / Cmd**.

| Shortcut | Action |
| --- | --- |
| `Enter` | Submit typed text; voice behavior depends on input state |
| `Ctrl / Cmd + Enter` | Trigger AI globally |
| `Ctrl / Cmd + Shift + Enter` | Trigger AI with screen context |
| `Ctrl / Cmd + ,` | Open Settings |
| `Alt + Space` | Hide or show the desktop window |
| `Alt + D` | Toggle stealth mode |
| `Ctrl / Cmd + Arrow keys` | Move the desktop window |
| `Escape` | Close panels and dialogs |

Global shortcuts can conflict with shortcuts registered by your OS or another app.

## Permissions and data

| Capability | Permission or connection |
| --- | --- |
| Voice input | Microphone access |
| Screen questions | Screen-recording access and a vision-capable model |
| Interviewer / meeting sound | System-audio capture support and recording permission |
| Local AI | Running Ollama service and a downloaded model |
| Cloud AI | Internet access, valid API key, and provider quota |

For local source runs, Whisper transcription runs on your machine. When you select a cloud AI provider, the prompt and relevant conversation, resume, or screenshot context are sent to that provider. Local models may require initial downloads before offline use.

Desktop screen-capture protection depends on the operating system and capture application. Test it with your actual sharing setup before relying on it. Conversations and configuration persist locally; protect your `.env`, API keys, and saved data.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Backend offline | Confirm dependencies are installed in `AINT_Venv`. Start the backend manually with the command above to see its error output. |
| Port 8000 is already in use | Check whether an existing ANT backend is running. Avoid starting a second server on the same port. |
| Browser cannot connect | Keep both servers running, use the Vite URL, and include its origin in `CORS_ORIGINS`. Restart the backend after changing `.env`. |
| Local model does not answer | Check `ollama list`, confirm the Ollama service is running, and select an installed model. Check any mode-specific model overrides. |
| Cloud key fails to save or answer | Check the provider, key, selected model, account access, and quota. Try a short text question first. |
| Screenshot question fails | Grant screen-recording permission, verify the capture, and choose a vision-capable model. Restart the app after changing OS permissions if needed. |
| Microphone or system audio is silent | Check the selected device and OS recording permissions. On macOS, review Privacy & Security settings for microphone, screen, and system-audio recording. |
| First transcription is slow | Allow the Whisper model download to complete. `WHISPER_MODEL=base` is the template default. |
| Login stops working after restart | Set a stable `JWT_SECRET_KEY` in `.env`, restart the backend, and sign in again. |

For more help, see the [troubleshooting guide](docs/devops/development/TROUBLESHOOTING.md).

## Development commands

Run these from the repository root after setup:

| Command | Purpose |
| --- | --- |
| `npm run web:dev` | Start the browser development server |
| `npm run web:build` | Build the web app into `apps/web/dist/` |
| `npm run electron:start` | Launch the desktop app |
| `npm --workspace ai-note-taker test` | Run Electron unit tests |
| `make test` | Run the backend test target; requires test dependencies |
| `npm run e2e:install:browsers` | Install Playwright browsers |
| `npm run e2e:test` | Run browser end-to-end tests |
| `npm run electron:build:mac` | Build macOS desktop packages |
| `npm run electron:build:win` | Build Windows desktop packages |
| `npm run electron:build:linux` | Build Linux desktop packages |
| `make help` | List Make targets |

For backend tests, install `backend/requirements-test.txt` in the virtual environment first. Desktop packaging needs the platform-specific Python resources configured in [electron/package.json](electron/package.json); dependency installation alone does not prepare a distributable.

## Project layout

```text
apps/web/                    Browser UI shared with the desktop app
apps/ant-chrome-extension/   Browser extension workspace
backend/                     FastAPI, transcription, AI routing, and storage
electron/                    Desktop window, capture, shortcuts, and packaging
mobile/                      React Native app
e2e/                         Playwright tests
docs/                        Setup, API, deployment, and feature guides
```

## Documentation

- [Full documentation index](docs/README.md)
- [Detailed installation](docs/devops/development/INSTALL.md)
- [Feature and topic guides](docs/README.md)
- [Environment template](.env.example)
- [Mobile setup](mobile/README.md)
- [Browser extension](apps/ant-chrome-extension/README.md)
- [Cognitive Graph setup](docs/backend/setup/SETUP_COGNITIVE_GRAPH.md)
- [Docker setup](docker/README.md)
- [Contributing](CONTRIBUTING.md)

## License

See [LICENSE](LICENSE) for the project license.
