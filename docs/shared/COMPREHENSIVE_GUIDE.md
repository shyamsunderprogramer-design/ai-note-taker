# ANT (AI Note Taker) - Comprehensive Documentation

**Version:** 2.0 | **Last Updated:** April 9, 2026

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Features & Capabilities](#features--capabilities)
4. [Installation & Setup](#installation--setup)
5. [API Documentation](#api-documentation)
6. [Development Guidelines](#development-guidelines)
7. [Deployment Instructions](#deployment-instructions)
8. [Business Model (BYOK)](#business-model-byok)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

ANT (AI Note Taker) is a privacy-first, AI-powered interview preparation and meeting transcription application. It combines local speech-to-text, multi-provider AI support, and a sophisticated cognitive graph to provide personalized interview coaching and productivity enhancement.

### Key Differentiators

- **100% Free Option:** Use Ollama local models with zero cost
- **BYOK (Bring Your Own Key):** Use your own API keys for premium AI - pay providers directly, no markup
- **Privacy-First:** All transcription runs locally; screen capture protection; encrypted storage
- **Open Source:** Full transparency and community-driven development
- **Multi-Provider:** Support for 8+ AI providers with intelligent routing

### Target Users

- Job seekers preparing for technical interviews
- Professionals who want meeting transcription and notes
- Teams conducting remote interviews
- Anyone needing privacy-focused AI assistance

### Project Stats

- **113+ Backend Endpoints** across 20+ feature groups
- **10 AI Modes** for different use cases
- **8 Cloud Providers** supported
- **10,000+ Mock Interview Questions**
- **Phase 2 Complete:** Real-time suggestions, entity extraction, analytics dashboard, performance insights, study plans

---

## Architecture

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ELECTRON DESKTOP APP                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Renderer   │  │  Main Process │  │   Preload    │  │ System Tray  │  │
│  │  (UI/UX)     │  │  (IPC/Window) │  │   (Bridge)   │  │  (Stealth)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                    │                                        │
│                              WebSocket/HTTP                                 │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND (Port 8000)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CORE MODULES                                 │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ AI Router  │ │ Transcriber│ │ Analytics  │ │   Security │       │   │
│  │  │(Multi-Prov)│ │  (Whisper) │ │  Engine    │ │   Layer    │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FEATURE MODULES                                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │   Cognitive  │ │   Interview  │ │     Job      │ │   Resume   │ │   │
│  │  │    Graph     │ │  Simulator   │ │   Tracker    │ │   Review   │ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │   │
│  │  │    Study     │ │     Voice    │ │   Entity     │ │   Realtime │ │   │
│  │  │    Plans     │ │    Cloning   │ │ Extraction   │ │ Suggestions│ │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
           ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   PostgreSQL    │    │   Neo4j (Graph)     │    │   Local Storage       │
│   (Primary DB)  │    │   (Cognitive Graph) │    │   (Conversations)     │
└─────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                         │                         │
           │                         ▼                         │
           │              ┌─────────────────────┐              │
           │              │   AI Providers      │              │
           │              │  ┌────┐┌────┐┌────┐ │              │
           │              │  │ Oll││Open││Anth│ │              │
           │              │  │ama ││ AI ││ropic│              │
           │              │  └────┘└────┘└────┘ │              │
           │              │  ┌────┐┌────┐┌────┐ │              │
           │              │  │Goog││ xAI││Deep│ │              │
           │              │  │ le ││    ││Seek│ │              │
           │              │  └────┘└────┘└────┘ │              │
           │              └─────────────────────┘              │
           │                                                   │
           └───────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Desktop Shell** | Electron 41.x | Cross-platform desktop app |
| **Frontend** | Vanilla JS, HTML5, CSS3 | UI without heavy frameworks |
| **Backend** | FastAPI + Uvicorn | High-performance Python API |
| **Database** | PostgreSQL/SQLite + SQLAlchemy | Primary data storage |
| **Graph DB** | Neo4j | Cognitive graph & relationships |
| **Speech-to-Text** | Faster-Whisper | Local transcription |
| **Local AI** | Ollama | Free, offline AI models |
| **Cloud AI** | OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Perplexity | Premium AI providers |
| **Audio** | Web Audio API + WebSocket | Real-time audio streaming |
| **Cache** | Redis (optional) | Response caching |

### Module Structure

```
backend/
├── core/                      # Core application
│   ├── main.py               # FastAPI app & 113+ endpoints
│   ├── database.py           # SQLAlchemy models (T16)
│   ├── config.py             # Configuration management
│   ├── ai_router.py          # AI routing logic
│   └── security/             # Security layer
│       ├── auth.py           # JWT authentication
│       ├── rate_limit.py     # Rate limiting
│       └── encryption.py     # Data encryption
│
├── modules/                   # Feature modules
│   ├── ai/                   # AI & analytics
│   │   ├── ai_router.py      # Multi-provider routing
│   │   ├── analytics.py      # Usage analytics
│   │   ├── analytics_engine.py
│   │   ├── cognitive_graph.py    # Neo4j graph
│   │   ├── entity_extraction.py  # ML + rule-based NER
│   │   ├── performance_analyzer.py
│   │   ├── predictive_interview.py
│   │   ├── realtime_suggestions.py
│   │   ├── study_plan_generator.py
│   │   └── voice_cloning.py
│   │
│   ├── interview/            # Interview features
│   │   ├── interview_simulator.py
│   │   ├── mock_interview_library.py (10K+ questions)
│   │   └── resume_review.py
│   │
│   ├── crm/                    # CRM integrations
│   ├── platform/               # Platform features
│   └── voice/                  # Voice processing
│
├── api/                        # API definitions
├── data/                       # Data storage
└── tests/                      # Test suites
```

---

## Features & Capabilities

### 1. Voice & Transcription

| Feature | Description | Status |
|---------|-------------|--------|
| **Real-time Streaming** | WebSocket-based transcription appears live as you speak | ✅ |
| **Local Whisper STT** | Faster-Whisper runs entirely on-device | ✅ |
| **Always-on Microphone** | Continuous listening with silence detection | ✅ |
| **Audio Waveform** | Live microphone visualization | ✅ |
| **Smart Filtering** | Removes filler words ("um", "uh") and small talk | ✅ |
| **Question Detection** | Automatically identifies questions vs statements | ✅ |
| **Multi-language** | Supports 99 languages via Whisper | ✅ |

**Technical Details:**
- Model: `faster-whisper` (base/large-v3)
- Sampling: 16kHz Float32
- Buffer: 500ms chunks
- WebSocket: `/ws/transcribe`

### 2. AI Modes & Routing

| Mode | Description | Use Case | Default Model |
|------|-------------|----------|---------------|
| **Instant** | Sub-100ms responses | Quick facts | Ollama turbo |
| **Fast** | Optimized for speed | Brief explanations | Ollama fast |
| **Adaptive** | Context-aware routing | General purpose | Ollama adaptive |
| **Universal** | Balanced quality/speed | Most conversations | Mistral |
| **Interview** | Technical focus | Interview prep | Llama3 |
| **Reasoning** | Deep analysis | Complex problems | Qwen2.5 |
| **Code** | Programming-optimized | Coding questions | Code-specialized |
| **Cloud** | Premium provider | Best quality | GPT-4o/Claude |
| **Turbo** | Token-limited speed | Quick answers | Ollama turbo |
| **Summary** | Meeting notes | Post-interview | Mistral |

**Routing Logic:**
```python
def resolve_mode(user_input, requested_mode="auto"):
    prompt = user_input.lower()
    word_count = len(prompt.split())
    
    if any(keyword in prompt for keyword in CODE_KEYWORDS) and word_count >= 18:
        return "code"
    elif word_count >= 30:
        return "reasoning"
    elif word_count <= 8:
        return "fast"
    # ... more rules
```

### 3. Cognitive Graph (Neo4j)

Personal knowledge graph for interview history analysis:

| Feature | Description | Endpoint |
|---------|-------------|----------|
| **Semantic Search** | Query by topic, company, skill | `/cognitive-graph/search` |
| **Entity Extraction** | Auto-extract companies, skills, technologies | On ingest |
| **Company Insights** | See what questions companies typically ask | `/cognitive-graph/company/{name}` |
| **Skill Progression** | Track confidence over time | `/analytics/skills` |
| **Interview Predictions** | ML-based question prediction | `/cognitive-graph/predict` |
| **Q&A Parsing** | Automatic transcript analysis | On ingest |

**Graph Schema:**
```
(:Interview)-[:HAS_QUESTION]->(:Question)
(:Question)-[:HAS_ANSWER]->(:Answer)
(:Interview)-[:ABOUT]->(:Company)
(:Interview)-[:COVERS]->(:Topic)
(:Interview)-[:TESTS]->(:Skill)
(:Skill)-[:RELATED_TO]->(:Skill)
```

### 4. Interview Preparation Suite

| Feature | Description | Endpoints |
|---------|-------------|-----------|
| **Interview Simulator** | Mock interviews with AI-generated questions | `/interview/create`, `/interview/{id}/question` |
| **Mock Question Bank** | 10,000+ questions by company/role/difficulty | `/interview/questions` |
| **Performance Analysis** | STAR method detection, code quality scoring | `/interview/analysis/{id}` |
| **Study Plan Generator** | Spaced repetition with weak area focus | `/study-plan/generate` |
| **Pre-Interview Prep** | Company-specific preparation checklists | `/pre-interview/checklist/{company}` |
| **Job Tracker** | Application pipeline management | `/jobs` |
| **Resume Review** | AI-powered resume analysis | `/resume-review/analyze` |

### 5. Real-Time Intelligence (Phase 2)

| Feature | Description | Accuracy |
|---------|-------------|----------|
| **Realtime Suggestions** | Contextual hints during live interviews | Context-dependent |
| **Entity Extraction** | Hybrid ML + rule-based extraction | >90% |
| **Conversation Analysis** | Auto-categorization and quality metrics | 85%+ |
| **Analytics Dashboard** | Visual insights with Chart.js/D3.js | N/A |
| **Performance Insights** | Speaking pace, filler words, answer structure | 80%+ |

**Study Plan Features:**
- Spaced repetition (SM-2 algorithm)
- Weak area identification
- Resource library integration (LeetCode, System Design Primer)
- Export to JSON/iCal/Markdown
- Adaptive difficulty adjustment

### 6. Privacy & Security

| Feature | Description | Implementation |
|---------|-------------|----------------|
| **Screen Capture Protection** | Hide from Zoom, Teams, OBS | Electron `setContentProtection()` |
| **Stealth Mode** | `Alt+D` toggle - invisible to screen capture | `WS_EX_FROMLEARN` (Windows) |
| **Encrypted Storage** | AES-256 for conversations and API keys | `crypto.scryptSync()` |
| **Local-First** | All transcription on-device | Whisper local inference |
| **No Cloud STT** | Audio never leaves your machine | WebSocket to localhost only |
| **BYOK** | You control your API keys | User-provided keys |

---

## Installation & Setup

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Windows 10, macOS 11, Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| **Python** | 3.10 | 3.11+ |
| **Node.js** | 18.x LTS | 20.x LTS |
| **RAM** | 8GB | 16GB+ |
| **Disk** | 10GB free | 20GB+ (for multiple models) |
| **GPU** | Optional | NVIDIA with CUDA (faster Whisper) |

### Step 1: Clone Repository

```bash
git clone https://github.com/shyamsunderprogramer-design/ai-note-taker.git
cd ai-note-taker
```

### Step 2: Python Environment Setup

```bash
# Create virtual environment
python -m venv AINT_Venv

# Activate (Windows)
AINT_Venv\Scripts\activate

# Activate (macOS/Linux)
source AINT_Venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

**Note:** Installing AI packages (`faster-whisper`, etc.) may take 5-10 minutes and requires 4GB+ disk space.

### Step 3: Install Ollama (Free AI Option)

1. Download from [ollama.com](https://ollama.com)
2. Install and start Ollama
3. Pull recommended models:

```bash
# Default - fast and capable
ollama pull qwen2.5:1.5b

# Better reasoning
ollama pull mistral:latest

# Advanced reasoning
ollama pull deepseek-r1:8b

# Code-focused
ollama pull codellama:7b

# Vision-capable
ollama pull llava:latest
```

### Step 4: Electron Setup

```bash
cd electron
npm install
cd ..
```

### Step 5: Database Setup

**Option A: SQLite (Default, easiest)**
```bash
# SQLite is used by default - no setup needed
mkdir -p data
```

**Option B: PostgreSQL (Production)**
```bash
# Install PostgreSQL
# Create database
createdb ainotetaker

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/ainotetaker"
export USE_SQLITE=false
```

### Step 6: Neo4j Setup (Optional - for Cognitive Graph)

```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-secure-password \
  neo4j:5.15.0

# Or download from neo4j.com
```

Configure in `backend/.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password
```

### Step 7: Environment Configuration

Create `backend/.env`:

```env
# === Local Ollama (FREE) ===
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_ADAPTIVE=qwen2.5:1.5b
OLLAMA_MODEL_FAST=qwen2.5:1.5b
OLLAMA_MODEL_TURBO=qwen2.5:1.5b
OLLAMA_MODEL_UNIVERSAL=mistral:latest
OLLAMA_MODEL_INTERVIEW=llama3:latest
OLLAMA_MODEL_REASONING=qwen2.5:1.5b
OLLAMA_MODEL_CODE=qwen2.5:1.5b
OLLAMA_MODEL_SUMMARY=mistral:latest

# === Cloud AI Providers (BYOK) ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
XAI_API_KEY=xai-...
DEEPSEEK_API_KEY=sk-...
GROQ_API_KEY=gsk_...
PERPLEXITY_API_KEY=...

# === Database ===
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///data/ainotetaker.db

# PostgreSQL (production)
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ainotetaker

# === Neo4j ===
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# === Security ===
AUTH_REQUIRED=true
HTTPS_REQUIRED=false  # Set true for production
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# === Rate Limiting ===
RATE_LIMIT_PUBLIC=60
RATE_LIMIT_AUTHED=200
RATE_LIMIT_SENSITIVE=20

# === Behavior ===
AI_TEMPERATURE=0.1
AI_TIMEOUT=30
TURBO_MAX_TOKENS=150
INSTANT_MAX_TOKENS=64

# === Logging ===
LOG_LEVEL=info
DEBUG=false
```

### Step 8: Run the Application

```bash
cd electron
npm start
```

The app will:
1. Start the Python backend (port 8000)
2. Launch the Electron window
3. Open the onboarding wizard (first run)

### Verification

```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "1.0.0", "modules": {...}}

# Check database
curl http://localhost:8000/health/database

# Check Neo4j (if configured)
curl http://localhost:8000/cognitive-graph/status
```

---

## API Documentation

### Base URL

```
http://localhost:8000
```

### Authentication

Most endpoints require JWT authentication:

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -d "username=myuser" \
  -d "email=user@example.com" \
  -d "password=securepassword"

# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=myuser" \
  -d "password=securepassword"

# Response: {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600}

# Use in subsequent requests
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/protected-endpoint
```

### Endpoint Categories (113+ Total)

#### Health & Status

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Backend health check |
| `/health/database` | GET | No | Database connectivity |
| `/health/modules` | GET | No | Module availability |
| `/health/neo4j` | GET | No | Neo4j connectivity |

**Response Example:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-04-09T10:30:00Z",
  "uptime_seconds": 3600,
  "modules": {
    "cognitive_graph": true,
    "interview_simulator": true,
    "job_tracker": true,
    "resume_review": true
  }
}
```

#### Authentication (8 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/register` | POST | No | Create account |
| `/auth/login` | POST | No | Login, get token |
| `/auth/logout` | POST | Yes | Invalidate token |
| `/auth/me` | GET | Yes | Current user info |
| `/auth/refresh` | POST | Yes | Refresh token |
| `/auth/change-password` | POST | Yes | Change password |
| `/auth/reset-password` | POST | No | Request reset |
| `/auth/verify-email` | GET | No | Verify email |

#### Conversations (7 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/conversations` | GET | Yes | List conversations |
| `/conversations` | POST | Yes | Create conversation |
| `/conversations/{id}` | GET | Yes | Get specific conversation |
| `/conversations/{id}` | PUT | Yes | Update conversation |
| `/conversations/{id}` | DELETE | Yes | Delete conversation |
| `/conversations/{id}/export` | GET | Yes | Export conversation |
| `/conversations/{id}/share` | POST | Yes | Create share link |

**Pagination:**
```bash
curl "http://localhost:8000/conversations?limit=20&offset=40" \
  -H "Authorization: Bearer TOKEN"
```

#### AI Chat (6 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/chat` | POST | Yes | Send message, get response |
| `/stream` | POST | Yes | Streaming chat (SSE) |
| `/stream-race` | POST | Yes | Multi-provider race |
| `/ask-with-image` | POST | Yes | Vision-capable query |
| `/mode` | GET | Yes/No | List available modes |
| `/mode` | POST | Yes | Switch AI mode |

**Chat Request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain JavaScript closures",
    "mode": "code",
    "style": "detailed",
    "conversation_id": "conv-123",
    "include_rag": true
  }'
```

**Response:**
```json
{
  "response": "A closure is a function that remembers its outer scope...",
  "mode": "code",
  "provider": "ollama",
  "model": "qwen2.5:1.5b",
  "tokens_used": 245,
  "prompt_tokens": 45,
  "completion_tokens": 200,
  "duration_ms": 850,
  "timestamp": "2026-04-09T10:30:00Z"
}
```

**Streaming Chat:**
```javascript
const response = await fetch('/stream', {
  method: 'POST',
  headers: { 
    'Authorization': 'Bearer TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ 
    message: 'Hello', 
    mode: 'adaptive',
    stream: true
  })
});

const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = new TextDecoder().decode(value);
  // Handle SSE chunk: "data: {...}\n\n"
}
```

#### Speech-to-Text (6 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/transcribe` | POST | Yes | File transcription |
| `/transcribe-cloud` | POST | Yes | Cloud STT (optional) |
| `/transcribe-with-speakers` | POST | Yes | Speaker diarization |
| `/transcribe-stream` | WS | Yes | WebSocket streaming |
| `/ws/transcribe` | WS | Yes | Browser transcription |
| `/whisper/models` | GET | Yes | Available models |

#### Cognitive Graph (12 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/cognitive-graph/status` | GET | Yes | Graph DB status |
| `/cognitive-graph/initialize` | POST | Yes | Initialize schema |
| `/cognitive-graph/ingest/{id}` | POST | Yes | Ingest conversation |
| `/cognitive-graph/history/{user_id}` | GET | Yes | User history |
| `/cognitive-graph/search` | POST | Yes | Semantic search |
| `/cognitive-graph/predict` | GET | Yes | Interview predictions |
| `/cognitive-graph/company/{name}` | GET | Yes | Company insights |
| `/cognitive-graph/topic/{name}` | GET | Yes | Topic analysis |
| `/cognitive-graph/skill/{name}` | GET | Yes | Skill progression |
| `/cognitive-graph/relationships` | GET | Yes | Entity relationships |
| `/cognitive-graph/analytics` | GET | Yes | Graph analytics |
| `/cognitive-graph/export` | POST | Yes | Export graph data |

**Ingest Conversation:**
```bash
curl -X POST http://localhost:8000/cognitive-graph/ingest/conv-123 \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Interview - Google",
    "user_id": "user-123",
    "duration_ms": 3600000,
    "messages": [
      {"role": "interviewer", "content": "What is a closure?", "timestamp": 1712345679000},
      {"role": "user", "content": "A closure is a function...", "timestamp": 1712345680000}
    ]
  }'
```

**Semantic Search:**
```bash
curl -X POST http://localhost:8000/cognitive-graph/search \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "React performance optimization",
    "limit": 10,
    "filters": {
      "companies": ["Meta", "Google"],
      "date_range": {"from": "2026-01-01", "to": "2026-04-09"}
    }
  }'
```

#### Interview Simulator (8 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/interview/create` | POST | Yes | Create mock interview |
| `/interview/{id}` | GET | Yes | Get interview state |
| `/interview/{id}/question` | GET | Yes | Get next question |
| `/interview/{id}/submit` | POST | Yes | Submit answer |
| `/interview/{id}/finish` | POST | Yes | Complete interview |
| `/interview/analysis/{id}` | GET | Yes | Get analysis |
| `/interview/questions` | GET | Yes | Question bank |
| `/interview/feedback` | POST | Yes | Request feedback |

#### Job Tracker (8 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/jobs` | GET | Yes | List applications |
| `/jobs` | POST | Yes | Add application |
| `/jobs/{id}` | GET | Yes | Get application |
| `/jobs/{id}` | PUT | Yes | Update application |
| `/jobs/{id}` | DELETE | Yes | Delete application |
| `/jobs/{id}/status` | PUT | Yes | Update status |
| `/jobs/{id}/notes` | POST | Yes | Add notes |
| `/jobs/analytics` | GET | Yes | Application analytics |

#### Analytics (6 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/analytics/summary` | GET | Yes | Usage summary |
| `/analytics/trends` | GET | Yes | Performance trends |
| `/analytics/skills` | GET | Yes | Skill breakdown |
| `/analytics/companies` | GET | Yes | Company insights |
| `/analytics/performance` | GET | Yes | Performance metrics |
| `/analytics/export` | GET | Yes | Export analytics |

#### Study Plans (5 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/study-plan/generate` | POST | Yes | Generate study plan |
| `/study-plan/{id}` | GET | Yes | Get study plan |
| `/study-plan/{id}` | PUT | Yes | Update plan |
| `/study-plan/{id}/progress` | POST | Yes | Update progress |
| `/study-plan/{id}/export` | GET | Yes | Export plan |

#### Resume Review (4 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/resume-review/analyze` | POST | Yes | Analyze resume |
| `/resume-review/{id}` | GET | Yes | Get analysis |
| `/resume-review/{id}/feedback` | GET | Yes | Get feedback |
| `/resume-review/compare` | POST | Yes | Compare versions |

#### Voice Cloning (6 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/voice-clone/models` | GET | Yes | List models |
| `/voice-clone/create` | POST | Yes | Create voice model |
| `/voice-clone/{id}/train` | POST | Yes | Train model |
| `/voice-clone/{id}/generate` | POST | Yes | Generate speech |
| `/voice-clone/{id}` | DELETE | Yes | Delete model |
| `/voice-clone/audio/{filename}` | GET | No | Play audio |

#### BYOK Provider Management (8 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/providers` | GET | No | List available providers |
| `/providers/byok/status` | GET | Yes | Your configured keys |
| `/providers/byok/configure` | POST | Yes | Add/update key |
| `/providers/byok/{provider}` | GET | Yes | Provider details |
| `/providers/byok/{provider}` | DELETE | Yes | Remove key |
| `/providers/byok/costs` | GET | No | Cost comparison |
| `/providers/byok/test/{provider}` | POST | Yes | Test key validity |
| `/providers/byok/usage` | GET | Yes | Usage stats |

**Configure Provider Key:**
```bash
curl -X POST http://localhost:8000/providers/byok/configure \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "provider=openai" \
  -d "api_key=sk-..."
```

**Response:**
```json
{
  "status": "success",
  "message": "OpenAI API key configured successfully",
  "provider": "openai",
  "validated": true
}
```

#### Real-time Suggestions (4 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/suggestions/stream` | WS | Yes | Real-time suggestion stream |
| `/suggestions/trigger` | POST | Yes | Manual trigger |
| `/suggestions/history` | GET | Yes | Suggestion history |
| `/suggestions/config` | PUT | Yes | Update config |

#### Entity Extraction (3 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/entities/extract` | POST | Yes | Extract from text |
| `/entities/batch` | POST | Yes | Batch extraction |
| `/entities/types` | GET | Yes | Available entity types |

#### Pre-Interview Prep (4 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/pre-interview/checklist/{company}` | GET | Yes | Get checklist |
| `/pre-interview/company-research` | GET | Yes | Company research |
| `/pre-interview/questions` | GET | Yes | Likely questions |
| `/pre-interview/materials` | GET | Yes | Study materials |

#### Performance Analysis (4 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/performance/analyze` | POST | Yes | Analyze transcript |
| `/performance/{id}` | GET | Yes | Get analysis |
| `/performance/trends` | GET | Yes | Performance trends |
| `/performance/compare` | POST | Yes | Compare sessions |

#### Admin (6 endpoints)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/admin/users` | GET | Yes | List users (admin) |
| `/admin/users/{id}` | DELETE | Yes | Delete user (admin) |
| `/admin/analytics` | GET | Yes | System analytics (admin) |
| `/admin/audit-log` | GET | Yes | Audit log (admin) |
| `/admin/backup` | POST | Yes | Trigger backup (admin) |
| `/admin/maintenance` | POST | Yes | Maintenance mode (admin) |

### Error Response Format

All errors follow a structured format:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required for this endpoint",
    "status": 401,
    "details": {},
    "timestamp": "2026-04-09T10:30:00Z",
    "request_id": "req-123-456"
  }
}
```

**Common Error Codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## Development Guidelines

### Project Structure

```
ai-note-taker/
├── apps/
│   ├── desktop/              # Desktop-specific assets
│   ├── mobile/               # React Native (planned)
│   └── web/                  # Web applications
│       ├── index.html        # Main app
│       ├── app.js            # Core logic (242KB)
│       ├── style.css         # Styling (147KB)
│       ├── analytics-dashboard.html
│       ├── analytics-dashboard.js
│       ├── cognitive-graph.html
│       ├── interview-simulator.html
│       ├── interview-simulator.js
│       ├── job-tracker.html
│       ├── job-tracker.js
│       ├── pre-interview.html
│       ├── pre-interview.js
│       ├── resume-review.html
│       ├── resume-review.js
│       ├── study-plan.html
│       ├── study-plan.js
│       └── js/
│           ├── core/         # API, auth, utils
│           │   ├── api.js
│           │   └── auth-helper.js
│           ├── components/     # Reusable UI
│           └── features/       # Feature modules
│
├── backend/
│   ├── core/
│   │   ├── main.py           # FastAPI app & 113+ endpoints
│   │   ├── database.py       # SQLAlchemy models (T16)
│   │   ├── config.py         # Configuration
│   │   ├── ai_router.py      # AI routing logic
│   │   ├── whisper_handler.py # STT handling
│   │   └── security/         # Security layer
│   │       ├── __init__.py
│   │       ├── auth.py       # JWT authentication
│   │       ├── rate_limit.py # Rate limiting
│   │       └── input_validator.py
│   ├── modules/
│   │   ├── ai/               # AI & analytics
│   │   ├── interview/        # Interview features
│   │   ├── crm/              # CRM integrations
│   │   ├── platform/           # Platform features
│   │   └── voice/              # Voice processing
│   ├── api/                    # API definitions
│   ├── data/                   # Data storage
│   └── tests/                  # Test suites
│
├── electron/
│   ├── main.js                 # Electron main process (37KB)
│   ├── preload.js              # Secure preload script (10KB)
│   ├── stealth.js              # Screen protection (8KB)
│   └── package.json
│
├── browser-extension/          # Chrome/Firefox extension
├── chrome-extension/           # Chrome-specific
├── vscode-extension/           # VS Code extension
│
├── docs/                       # Documentation
│   ├── API/                    # API docs
│   ├── ARCHITECTURE/           # Architecture docs
│   ├── DEPLOYMENT/             # Deployment guides
│   ├── DEVELOPMENT/            # Dev guides
│   ├── GUIDES/                 # User guides
│   ├── SECURITY/               # Security docs
│   └── REFERENCE/              # Reference material
│
├── config/                     # Configuration files
├── docker/                     # Docker configs
├── k8s/                        # Kubernetes manifests
├── deploy/                     # Deployment scripts
├── scripts/                    # Utility scripts
├── tests/                      # Integration tests
└── data/                       # Local data storage
```

### Code Style Guidelines

#### Python (Backend)

```python
"""
Module docstring explaining purpose.
"""

from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Use type hints for all functions
def process_message(
    message: str, 
    user_id: str,
    mode: Optional[str] = None
) -> Dict[str, any]:
    """
    Process a user message and return AI response.
    
    Args:
        message: The user's input message
        user_id: Unique user identifier
        mode: Optional AI mode override
        
    Returns:
        Dictionary containing:
        - response: AI generated text
        - tokens_used: Token count
        - duration_ms: Processing time
        
    Raises:
        APIError: If processing fails
    """
    try:
        # Implementation
        result = _internal_process(message, mode)
        return {
            "response": result.text,
            "tokens_used": result.tokens,
            "duration_ms": result.duration
        }
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise APIError(ErrorCode.PROCESSING_FAILED, str(e))


# Constants in UPPER_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30


# Private functions with underscore prefix
def _internal_process(message: str, mode: str) -> Result:
    """Internal processing implementation."""
    pass
```

**Python Standards:**
- Follow PEP 8 style guide
- Maximum line length: 100 characters
- Use `black` for formatting: `black backend/`
- Use `isort` for imports: `isort backend/`
- Use `pylint` for linting: `pylint backend/`
- Document all public functions with docstrings
- Use type hints for function signatures

#### JavaScript (Frontend)

```javascript
/**
 * @fileoverview AI Chat module - handles communication with backend
 * @module features/ai-chat
 */

/**
 * Send message to backend and get AI response
 * @param {Object} params - Message parameters
 * @param {string} params.message - User message text
 * @param {string} [params.mode='adaptive'] - AI mode
 * @param {string} [params.style='concise'] - Response style
 * @param {string} [params.conversationId] - Conversation ID
 * @returns {Promise<ChatResponse>} Server response with AI reply
 * @throws {APIError} When request fails
 * @example
 * const response = await sendMessage({
 *   message: 'Hello',
 *   mode: 'interview'
 * });
 */
async function sendMessage(params) {
  const defaults = {
    mode: 'adaptive',
    style: 'concise'
  };
  
  const config = { ...defaults, ...params };
  
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify(config)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.code, error.message);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to send message:', error);
    throw error;
  }
}


// Constants
const API_BASE = 'http://127.0.0.1:8000';
const MODES = {
  INSTANT: 'instant',
  FAST: 'fast',
  ADAPTIVE: 'adaptive',
  UNIVERSAL: 'universal',
  INTERVIEW: 'interview',
  REASONING: 'reasoning',
  CODE: 'code',
  CLOUD: 'cloud'
};


// Event listener pattern
document.addEventListener('DOMContentLoaded', () => {
  initializeApp();
});
```

**JavaScript Standards:**
- Use ES6+ features (async/await, arrow functions, destructuring)
- JSDoc for all public functions
- `const` for immutable, `let` for mutable (avoid `var`)
- Strict equality checks: `===` and `!==`
- Semicolons required
- Single quotes for strings
- 2 spaces for indentation

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html --cov-report=term

# Run specific module
pytest backend/tests/test_ai_router.py -v

# Run specific test
pytest backend/tests/test_ai_router.py::TestRouter::test_resolve_mode -v

# Run integration tests
pytest tests/integration/ -v

# Frontend tests (when implemented)
npm test
```

**Test Coverage Targets:**
- Unit tests: 80%+ coverage
- Integration tests: All 113+ endpoints
- E2E tests: Critical user journeys

### Git Workflow

```bash
# Feature branch workflow
git checkout -b feature/new-feature-name

# Make changes
git add .
git commit -m "feat: Add new feature"

# Push to remote
git push origin feature/new-feature-name

# Create PR via GitHub
```

**Commit Message Format:**
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Build process, dependencies

**Examples:**
```
feat: Add real-time suggestion engine

- Implement WebSocket-based streaming
- Add cooldown mechanism
- Include confidence scoring

Refs: #28
```

```
fix: Resolve database connection leak

- Close connections in finally block
- Add connection pool limits

Fixes: #123
```

### Security Best Practices

```python
# 1. Always sanitize user inputs
from security import sanitize_input
clean_input = sanitize_input(user_input)

# 2. Use parameterized queries (SQLAlchemy handles this)
result = await session.execute(
    select(User).where(User.username == username)
)

# 3. Validate file uploads
from security import validate_file_upload
is_valid, error = validate_file_upload(file)

# 4. Rate limiting
@rate_limit(requests_per_minute=60)
async def sensitive_endpoint():
    pass

# 5. Audit logging
from security import log_audit_event
log_audit_event(
    action="user_login",
    user_id=user.id,
    details={"ip": request.client.host}
)

# 6. Never log sensitive data
# Bad: logger.info(f"User password: {password}")
# Good: logger.info("User login attempt", extra={"user_id": user_id})
```

---

## Deployment Instructions

### Docker Deployment

#### Development

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f backend

# Rebuild after changes
docker-compose up -d --build
```

#### Production

```bash
# Production Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Scale backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# View scaled logs
docker-compose -f docker-compose.prod.yml logs -f
```

**Production docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: docker/Dockerfile.prod
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/ainotetaker
      - AUTH_REQUIRED=true
      - HTTPS_REQUIRED=true
    depends_on:
      - postgres
      - neo4j
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: ainotetaker
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d ainotetaker"]
      interval: 10s

  neo4j:
    image: neo4j:5.15.0
    environment:
      NEO4J_AUTH: neo4j/secure-password
    volumes:
      - neo4j_data:/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend

volumes:
  postgres_data:
  neo4j_data:
  redis_data:
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMaps and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy database
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml

# Deploy Neo4j
kubectl apply -f k8s/neo4j-deployment.yaml
kubectl apply -f k8s/neo4j-service.yaml

# Deploy backend
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n ainotetaker
kubectl get svc -n ainotetaker
kubectl get ingress -n ainotetaker

# View logs
kubectl logs -f deployment/backend -n ainotetaker

# Scale backend
kubectl scale deployment backend --replicas=5 -n ainotetaker
```

**Kubernetes HPA (Horizontal Pod Autoscaler):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: ainotetaker
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Electron App Distribution

```bash
cd electron

# Install dependencies
npm install

# Build for Windows
npm run build:win

# Build for macOS
npm run build:mac

# Build for Linux
npm run build:linux

# Build all platforms
npm run build
```

**Output Locations:**
- Windows: `electron/dist/ANT Setup-X.X.X-win-x64.exe`, `ANT-X.X.X-win-x64.portable.exe`
- macOS: `electron/dist/ANT-X.X.X-mac-x64.dmg`, `ANT-X.X.X-mac-x64.zip`
- Linux: `electron/dist/ANT-X.X.X-linux-x64.AppImage`, `ANT-X.X.X-linux-x64.deb`

### Environment-Specific Configuration

#### Development

```env
# .env.development
DEBUG=true
AUTH_REQUIRED=false
HTTPS_REQUIRED=false
CORS_ALLOW_ALL=true
LOG_LEVEL=debug
USE_SQLITE=true
DATABASE_URL=sqlite+aiosqlite:///data/ainotetaker-dev.db
```

#### Staging

```env
# .env.staging
DEBUG=false
AUTH_REQUIRED=true
HTTPS_REQUIRED=true
CORS_ALLOW_ALL=false
CORS_ORIGINS=https://staging.ainotetaker.com
LOG_LEVEL=info
USE_SQLITE=false
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/ainotetaker
RATE_LIMIT_PUBLIC=100
RATE_LIMIT_AUTHED=300
```

#### Production

```env
# .env.production
DEBUG=false
AUTH_REQUIRED=true
HTTPS_REQUIRED=true
HSTS_MAX_AGE=31536000
CORS_ALLOW_ALL=false
CORS_ORIGINS=https://app.ainotetaker.com
LOG_LEVEL=warning
LOG_FORMAT=json
USE_SQLITE=false
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/ainotetaker
NEO4J_URI=bolt://prod-neo4j:7687
RATE_LIMIT_PUBLIC=60
RATE_LIMIT_AUTHED=200
RATE_LIMIT_SENSITIVE=20
SSL_CERT_PATH=/etc/ssl/certs/ainotetaker.crt
SSL_KEY_PATH=/etc/ssl/private/ainotetaker.key
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-test.txt
      
      - name: Run tests
        run: pytest --cov=backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Electron App
        run: |
          cd electron
          npm install
          npm run build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: electron-app-${{ matrix.os }}
          path: electron/dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Deployment script
          echo "Deploying to production..."
```

---

## Business Model (BYOK)

### Overview

**Bring Your Own Key (BYOK)** - Users provide their own API keys for premium AI providers.

```
┌─────────────────────────────────────────────────────────────┐
│                      USER REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI ROUTER (ai_router.py)                    │
│  1. Check if user has premium key for requested provider     │
│  2. If yes → Use user's key                                   │
│  3. If no → Fallback to Ollama (free)                        │
└─────────────────────────────────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌──────────┐      ┌──────────┐
│  Ollama  │      │  Cloud   │
│  (FREE)  │      │ Providers│
│  $0      │      │(BYOK)    │
│          │      │User pays │
└──────────┘      │provider  │
                  └──────────┘
```

### Cost Comparison

| Provider | Input/1K Tokens | Output/1K Tokens | Typical Interview Cost |
|----------|-------------------|------------------|------------------------|
| **Ollama** | **$0** | **$0** | **FREE** |
| DeepSeek | $0.00014 | $0.00028 | ~$0.0005 |
| Google Gemini | $0.0005 | $0.0015 | ~$0.002 |
| Groq | $0.00059 | $0.00079 | ~$0.002 |
| OpenAI GPT-4o | $0.0015 | $0.002 | ~$0.005 |
| Anthropic Claude | $0.003 | $0.015 | ~$0.01 |

**Cost Examples:**
- 100 interviews with GPT-4o: ~$0.50 total
- 100 interviews with Claude: ~$1.00 total
- 100 interviews with Ollama: $0

**vs Competitors:**
| Competitor | Monthly Cost | Our Equivalent |
|------------|--------------|----------------|
| Final Round AI | $148/mo | FREE or ~$0.50/mo |
| Interview Coder | $299/mo | FREE or ~$0.50/mo |
| LockedIn AI | $69/mo | FREE or ~$0.50/mo |

### Value Propositions

1. **"Free forever"** - Ollama option costs nothing
2. **"Premium when you want it"** - BYOK for better quality
3. **"Your keys, your choice"** - No vendor lock-in
4. **"99% cheaper"** - Same features, fraction of the cost
5. **"Transparent costs"** - Pay providers directly

### User Journeys

**Free User:**
1. Download app
2. Install Ollama
3. Use completely free
4. No signup required
5. Unlimited usage

**Premium User:**
1. Try app with Ollama (free)
2. Want better quality → Sign up
3. Add OpenAI key in Settings
4. Get GPT-4o quality
5. Pay ~$0.50/month (not $148!)

**Power User:**
1. Sign up
2. Add multiple provider keys
3. Switch between providers
4. Optimize for cost/quality
5. Total cost: $5-10/month

---

## Security Considerations

### Authentication & Authorization

- **JWT-based authentication** with refresh tokens
- **Role-based access control** (RBAC)
- **Token expiration** and rotation
- **Secure password hashing** (bcrypt)
- **Session management** with revocation

### Data Protection

- **Encryption at Rest:** AES-256 for sensitive data
- **Encryption in Transit:** TLS 1.3 for all connections
- **API Keys:** Encrypted storage, never logged
- **Conversations:** Optional encryption with user passphrase
- **Backup Encryption:** Automated encrypted backups

### Network Security

- **CORS whitelist** (no `*` in production)
- **Rate limiting** per endpoint and user
- **Request size limits** (10MB max)
- **HSTS headers** enforced
- **HTTPS enforcement** in production

### Audit & Compliance

- **Comprehensive audit logging**
- **GDPR-compliant** data export/deletion
- **Data retention policies**
- **Access logging** and monitoring

### Security Checklist

```bash
# Run security scans
bandit -r backend/
safety check -r backend/requirements.txt
npm audit

# Check for secrets
git-secrets --scan

talisman --scan
```

---

## Troubleshooting

### Common Issues

#### Backend Won't Start

```bash
# Check if port 8000 is in use
lsof -i :8000
# or
netstat -ano | findstr :8000

# Kill process or change port
export PORT=8001

# Check Python dependencies
pip check

# Verify virtual environment is activated
which python  # Should show AINT_Venv path
```

#### Whisper Model Not Found

```bash
# Download model manually
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu')"

# Check model cache location
ls ~/.cache/whisper/  # Linux/macOS
ls %USERPROFILE%\.cache\whisper\  # Windows

# Clear cache and re-download
rm -rf ~/.cache/whisper/
```

#### Ollama Connection Failed

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama service status
# Windows: Check system tray icon
# macOS: brew services list | grep ollama
# Linux: systemctl status ollama

# Restart Ollama
# macOS: brew services restart ollama
# Linux: sudo systemctl restart ollama
```

#### Electron Blank Screen

```bash
# Clear Electron cache
rm -rf ~/AppData/Roaming/ai-note-taker/Cache  # Windows
rm -rf ~/Library/Application\ Support/ai-note-taker/Cache  # macOS
rm -rf ~/.config/ai-note-taker/Cache  # Linux

# Check backend is running
curl http://localhost:8000/health

# View developer tools
# Ctrl+Shift+I (Windows/Linux)
# Cmd+Option+I (macOS)

# Check console for errors
```

#### Neo4j Connection Issues

```bash
# Verify Neo4j is running
docker ps | grep neo4j

# Check credentials
curl -u neo4j:password http://localhost:7474/db/data/

# Reset Neo4j
docker stop neo4j && docker rm neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/newpassword neo4j:5.15.0

# Check logs
docker logs neo4j
```

#### Database Migration Issues

```bash
# Reset database (WARNING: Deletes all data!)
rm data/ainotetaker.db

# For PostgreSQL
dropdb ainotetaker && createdb ainotetaker

# Re-run migrations
python -c "from backend.core.database import init_database; asyncio.run(init_database())"
```

### Performance Issues

```bash
# Check memory usage
ps aux | grep python

# Profile backend
python -m cProfile -o profile.stats backend/core/main.py

# Check for memory leaks
# Use memory_profiler package

# Optimize Whisper
# Use smaller model: base instead of large-v3
# Use GPU if available
```

### Getting Help

1. **Check Logs:**
   - Electron: `%APPDATA%/ai-note-taker/logs/main.log`
   - Backend: Console output or `backend/logs/`

2. **Enable Debug Mode:**
   ```bash
   export DEBUG=true
   export LOG_LEVEL=debug
   ```

3. **Community Support:**
   - GitHub Issues: [Report bugs](https://github.com/shyamsunderprogramer-design/ai-note-taker/issues)
   - Discussions: [Ask questions](https://github.com/shyamsunderprogramer-design/ai-note-taker/discussions)

4. **Documentation:**
   - API Reference: `/docs/API_REFERENCE_PHASE2.md`
   - Setup Guide: `/docs/SETUP_COGNITIVE_GRAPH.md`
   - Security: `/docs/SECURITY/`
   - Architecture: `/docs/ARCHITECTURE/`

---

## License

MIT License - See [LICENSE](../../LICENSE) file

**Copyright (c) 2026 ANT (AI Note Taker) Contributors**

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

---

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - Optimized inference
- [Ollama](https://ollama.com) - Local AI models
- [Neo4j](https://neo4j.com) - Graph database
- [FastAPI](https://fastapi.tiangolo.com) - Web framework
- [Electron](https://www.electronjs.org) - Desktop framework
- [spaCy](https://spacy.io) - NLP library
- [SQLAlchemy](https://www.sqlalchemy.org) - Database ORM

---

**Made with love by the ANT Team**

*Privacy-first AI for everyone.*
