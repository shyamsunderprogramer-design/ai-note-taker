# AI Note Taker

A smart voice note-taking app with screen capture protection and AI-powered responses.

---

## Features

### Voice & Transcription
- **Microphone recording** - Press Enter or click Start to record
- **Local Whisper transcription** - Audio converted to text on backend
- **Smart filtering** - Filters out small talk and non-questions

### AI Responses
- **Streaming responses** - Real-time AI answer display
- **Multiple AI providers**:
  - Ollama (local, default)
  - OpenAI (GPT-4o, GPT-4o Mini, o1 Mini, o3 Mini)
  - Anthropic (Claude 3.5 Haiku, Sonnet, Opus 4)
  - Google (Gemini 2.0 Flash, 1.5 Pro)
  - xAI (Grok 2 Mini, Grok Beta)
  - DeepSeek (Chat, Coder, Math)
  - Groq (Llama 3.3 70B, Mixtral, Qwen)
- **Response styles**: Concise, Detailed, Bullet points

### Modes
| Mode | Purpose |
|------|---------|
| Auto | Automatically selects best model |
| Fast | Quick local model response |
| Adaptive | Adapts to content type |
| Interview | Technical questions focus |
| Reasoning | Enhanced reasoning |
| Code | Code-optimized responses |
| Cloud | Forces cloud provider |

### Conversation Management
- **Auto-save** - Conversations saved locally
- **History** - Browse past conversations
- **Search** - Filter conversations by keyword
- **Sort** - By Recent, Oldest, A-Z, Message count
- **Pin** - Keep important conversations on top
- **Export** - Copy as formatted text
- **Resume** - Continue any past conversation

### Window & UI
- **Frameless window** with custom title bar
- **Always on top** floating overlay
- **Resizable** via drag handle at bottom
- **Font size** selection (Small/Medium/Large/XL)
- **Dark glass UI**

### Privacy & Stealth
- **Screen capture protection** - Hides from Zoom, Teams, WebEx, Discord, OBS, Snipping Tool
- **Stealth mode** - ON by default, hides app from screen capture
- **Hide/show window** - Quick toggle to conceal app
- **System tray** - Minimizes to tray when stealth enabled

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Toggle voice recording / Submit text |
| `F` | Toggle maximize window |
| `Alt+D` | Toggle stealth mode (capture protection + show/hide) |
| `Alt+Space` | Hide / show window |
| `Ctrl+←→↑↓` | Move window in any direction |

---

## Setup (Step by Step)

### Step 1: Install Python

1. Go to [python.org/downloads](https://python.org/downloads)
2. Download Python 3.10 or newer
3. **Important**: Check the box **"Add Python to PATH"**
4. Click "Install Now"

### Step 2: Install Node.js

1. Go to [nodejs.org](https://nodejs.org)
2. Download the **LTS** version (left side, green button)
3. Open the file, click Next, Done

### Step 3: Install Git (optional but recommended)

1. Go to [git-scm.com](https://git-scm.com)
2. Download for Windows
3. Run installer, click Next, Next, Done

### Step 4: Download the Project

**Option A - With Git:**
```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

**Option B - Without Git:**
1. Go to the GitHub page: https://github.com/shyamsunderprogramer-design/ai-note-taker
2. Click the green "Code" button
3. Click "Download ZIP"
4. Extract the ZIP file
5. Open the extracted folder

### Step 5: Create the Virtual Environment

Open **Command Prompt** (Windows key + R, type `cmd`, press Enter):

```bash
cd ai-note-taker
python -m venv AINT_Venv
```

### Step 6: Install Python Packages

```bash
AINT_Venv\Scripts\activate.bat
pip install -r backend/requirements.txt
```

**Note:** This installs AI packages. It may take 5-10 minutes and require 4GB+ disk space.

### Step 7: Install NPM Packages

```bash
cd electron
npm install
cd ..
```

### Step 8: Run the App

```bash
cd electron
npm start
```

The app window will appear!

---

## How to Use

### Voice Input
1. Click the **Start** button or press **Enter**
2. Speak your question or thought
3. Click **Stop** or press **Enter** again
4. The AI will respond with an answer

### Text Input
1. Type your question in the text input field
2. Press **Enter** to submit
3. The AI will respond with an answer

### Changing Settings

- **Mode**: Click "Mode" dropdown to change AI behavior
  - `Auto` - Automatic selection based on input
  - `Fast` - Quick responses for simple questions
  - `Adaptive` - Balanced responses
  - `Interview` - For technical interviews
  - `Reasoning` - For complex reasoning questions
  - `Cloud` - Uses cloud AI providers
  - `Code` - Optimized for coding questions

- **Model**: Click "Model" dropdown to choose AI model
  - `Auto` - Automatic selection
  - `Phi3` - Fast, small model
  - `TinyLlama` - Tiny, fast model
  - `Llama3` - Powerful model
  - `Mistral` - Balanced model

- **Response**: Click "Response" dropdown to choose output format
  - `Concise` - Short, brief answers
  - `Detailed` - Long, detailed explanations
  - `Bullet` - Bullet point format

- **Font**: Click "Font" dropdown to change text size

### Stealth Mode

**Stealth mode is ON by default** when the app starts.

- **Undetectable** (green dot) - App is hidden from screen capture (Zoom, Teams, WebEx, Discord, OBS, Snipping Tool)
- **Detectable** (red dot) - App can be seen in screen capture

Press **`Alt+D`** to toggle stealth mode, or click the button in the header.

When stealth is enabled, a system tray icon appears. Click it to restore the window.

### Conversation History

Click the **history button** (↻) in the header to:
- Browse all past conversations
- Search conversations by keyword
- Sort by Recent, Oldest, A-Z, or message count
- Pin important conversations
- Resume, rename, export, or delete conversations

### Cloud Providers

Configure API keys for cloud AI providers:
1. Click the **menu button** (☰)
2. Select **Settings**
3. Click **Configure** next to your provider
4. Enter your API key and click **Save**

Available providers: OpenAI, Anthropic, Google, xAI, DeepSeek, Groq

**API Key Storage**: Keys are stored locally in `backend/.env` and never committed to git.

---

## Troubleshooting

### "Python not found" error
- Make sure Python is installed and added to PATH
- Restart Command Prompt after installing Python

### "pip not found" error
```bash
python -m pip install -r backend/requirements.txt
```

### App doesn't start
1. Make sure port 8000 is not in use
2. Check that all npm packages are installed
3. Make sure the virtual environment is activated

### No sound / Microphone not working
1. Check your computer's microphone is working
2. Allow microphone permission when prompted
3. Make sure no other app is using the microphone

### Backend won't start
Make sure the virtual environment is activated:
```bash
AINT_Venv\Scripts\activate.bat
cd electron
npm start
```

### Keyboard shortcuts not working
Some shortcuts may conflict with other apps. Try:
- Closing other apps that might use similar shortcuts
- Using the on-screen button instead of keyboard shortcuts

---

## Project Structure

```
ai-note-taker/
├── electron/              # Desktop app (Electron)
│   ├── main.js          # Main window & process
│   ├── preload.js       # Security bridge (IPC)
│   ├── stealth.js       # Screen capture protection module
│   └── package.json     # NPM packages
├── backend/              # AI Backend (Python)
│   ├── main.py          # FastAPI server
│   ├── whisper_handler.py  # Speech to text (Whisper)
│   ├── ai_router.py     # AI routing & prompts
│   ├── cloud_providers.py  # Cloud AI integration
│   └── config.py        # Settings
├── renderer/             # App UI (HTML/CSS/JS)
│   ├── index.html       # App layout
│   ├── style.css        # Styling
│   └── app.js           # App logic
├── electron-data/        # App data (conversations, settings)
└── AINT_Venv/           # Python virtual environment
```

---

## Requirements

- **OS**: Windows 10/11 or macOS
- **Python**: 3.10+
- **Node.js**: 18+
- **RAM**: 8GB+ recommended (for AI models)
- **Disk**: 5GB+ free space

---

## Tech Stack

- **Electron** - Desktop app framework
- **FastAPI** - Python web server
- **Whisper** - Speech recognition (local)
- **Ollama** - Local AI model inference
- **Multiple AI Providers** - OpenAI, Anthropic, Google, xAI

---

## License

MIT License - Free to use, modify, and distribute.
