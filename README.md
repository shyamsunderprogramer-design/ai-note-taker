# AI Note Taker

A smart voice note-taking app with screen capture protection and AI-powered responses.

---

## Features

- **Voice Recording** - Press Start or Enter to record your voice
- **Text Input** - Type your question directly and press Enter to submit
- **AI Transcription** - Converts your voice to text using Whisper AI
- **Smart Responses** - Gets AI answers based on your questions
- **Response Styles** - Choose how AI responds: Concise, Detailed, or Bullet points
- **Multiple Modes** - Auto, Fast, Adaptive, Interview, Reasoning, Cloud, Code, Universal
- **Multiple Models** - Auto, Phi3, TinyLlama, Llama3, Mistral
- **Screen Capture Protection** - Stealth mode hides the app from screen capture
- **Always On Top** - Stays visible while you work
- **Compact Mode** - Minimize to a small bar
- **Font Size** - Change text size (Small, Medium, Large, XL)
- **Dark Theme** - Beautiful dark glass UI

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Toggle recording (when no text) / Submit text (when typing) / Start/Stop recording |
| `F` | Toggle maximize window |

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
  - `Universal` - General purpose

- **Model**: Click "Model" dropdown to choose AI model
  - `Auto` - Automatic selection
  - `Phi3` - Fast, small model
  - `TinyLlama` - Tiny, fast model
  - `Llama3` - Powerful model
  - `Mistral` - Balanced model

- **Response**: Click "Response" dropdown to choose output format
  - `Concise` - Short, brief answers
  - `Detailed` - Long, detailed explanations
  - `Bullet` - Bullet point format with asterisks

- **Font**: Click "Font" dropdown to change text size

### Stealth Mode

Click the **Detectable/Undetectable** button to toggle screen capture protection:
- **Detectable** (red dot) - App can be seen in screen capture
- **Undetectable** (green dot) - App is hidden from screen capture

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

---

## Project Structure

```
ai-note-taker/
├── electron/           # Desktop app (Electron)
│   ├── main.js        # Main window & process
│   ├── preload.js     # Security bridge
│   ├── stealth.js     # Screen capture protection
│   └── package.json   # NPM packages
├── backend/           # AI Backend (Python)
│   ├── main.py        # FastAPI server
│   ├── whisper_handler.py  # Speech to text
│   ├── ai_router.py   # AI routing
│   ├── cloud_providers.py  # Cloud AI integration
│   └── config.py      # Settings
├── renderer/          # App UI (HTML/CSS/JS)
│   ├── index.html    # App layout
│   ├── style.css     # Styling
│   └── app.js        # App logic
└── AINT_Venv/        # Python virtual environment
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
- **Whisper** - Speech recognition
- **Ollama** - Local AI model inference
- **CTranslate2** - Fast AI inference

---

## License

MIT License - Free to use, modify, and distribute.
