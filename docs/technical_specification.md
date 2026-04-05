# AI Note Taker - Technical Specification

## Document Information

| Attribute | Value |
|-----------|-------|
| **Version** | 1.0.0 |
| **Last Updated** | 2026-04-04 |
| **Branch** | phase1-predictive-interview |
| **Status** | Active Development |

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
+-------------------+      HTTP/WebSocket       +------------------------+
|                   | <-----------------------> |                        |
|  Electron App     |     (Port 8000)           |  FastAPI Backend         |
|  (Main + Renderer)|                            |  (Python)              |
|                   |                            |                        |
|  - main.js        |                            |  - REST API endpoints  |
|  - preload.js     |                            |  - WebSocket streams   |
|  - renderer/      |                            |  - AI routing          |
|                   |                            |  - Speech processing   |
+-------------------+                            +------------+-----------+
         ^                                                    |
         | IPC                                                | Bolt Protocol
         v                                                    v
+--------+-----------+                            +------------+-----------+
|  Secure Key Store  |                            |  Neo4j Community       |
|  (Encrypted)       |                            |  (Graph Database)      |
+--------------------+                            +------------------------+
                                                            |
         +--------------------------------------------------+
         |
         v
+--------------------+    +--------------------+    +--------------------+
|  Local AI Models   |    |  Cloud AI Providers |    |  Speech Recognition |
|  (Ollama)          |    |  - OpenAI           |    |  (Whisper)          |
|                    |    |  - Anthropic        |    |                     |
|  - Qwen 2.5        |    |  - Google (Gemini)  |    |  - faster-whisper   |
|  - DeepSeek R1     |    |  - xAI (Grok)       |    |  - Real-time stream |
|  - Llava (Vision)  |    |  - Groq             |    |  - VAD filtering    |
+--------------------+    |  - DeepSeek         |    +--------------------+
                          |  - Perplexity       |
                          +--------------------+
```

### 1.2 Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Frontend** | Electron | ^41.0.3 | Cross-platform desktop shell |
| **Frontend** | Vanilla JavaScript | ES2020+ | UI logic and state management |
| **Frontend** | HTML5/CSS3 | - | UI rendering and styling |
| **Backend** | Python | 3.11+ | AI/ML and business logic |
| **Backend** | FastAPI | 0.135.1 | REST API and WebSocket server |
| **Backend** | Uvicorn | 0.42.0 | ASGI server |
| **Database** | Neo4j Community | 5.x | Graph database for cognitive graph |
| **AI Local** | Ollama | Latest | Local LLM inference |
| **AI Local** | faster-whisper | 1.2.1 | Local speech-to-text |
| **NLP** | spaCy | 3.8.4 | Entity extraction |

### 1.3 Communication Protocols

| Protocol | Port | Usage |
|----------|------|-------|
| HTTP REST | 8000 | API endpoints (transcribe, ask, configure) |
| Server-Sent Events (SSE) | 8000 | Streaming AI responses |
| WebSocket | 8000 | Real-time transcription streams |
| Secure Key IPC | 18000 | Encrypted API key retrieval |

---

## 2. Component Details

### 2.1 Main Process (Electron: `electron/main.js`)

**Responsibilities:**
- Window lifecycle management (create, minimize, maximize, close)
- Backend Python process management (spawn, monitor, restart)
- Global shortcut registration (Ctrl+Enter, Alt+D, etc.)
- System tray integration for stealth mode
- Secure API key storage (encrypted with machine-specific key)
- Screenshot capture (desktopCapturer API)
- Auto-screenshot buffer management (ring buffer of 5 frames)

**Key Classes/Modules:**

| Module | Purpose |
|--------|---------|
| `stealth.js` | Screen capture protection, system tray management |
| `preload.js` | Secure IPC bridge between main and renderer |
| Secure Store | `electron-store` with AES encryption |

**Security Features:**
- Context isolation enabled (`contextIsolation: true`)
- Node integration disabled (`nodeIntegration: false`)
- Preload script is the only bridge to native APIs
- API keys encrypted using machine-specific derived key

### 2.2 Renderer Process (`renderer/`)

**File Structure:**

```
renderer/
├── index.html          # Main chat interface
├── app.js              # Core application logic (~180KB)
├── style.css           # Application styles (~104KB)
├── cognitive-graph.html    # Graph visualization UI
├── cognitive-graph.js      # Graph interaction logic
├── pre-interview.html      # Interview prep UI
├── pre-interview.js        # Interview prep logic
├── hljs.min.js            # Syntax highlighting
└── sw.js                  # Service worker (PWA)
```

**Key Features:**
- Real-time chat interface with message streaming
- Waveform audio visualization
- Always-on microphone mode with WebSocket connection
- Document upload and RAG (Retrieval-Augmented Generation)
- Settings panel with provider configuration
- Conversation history management
- Session timer with auto-stop

### 2.3 Backend Services (`backend/`)

#### 2.3.1 FastAPI Application (`main.py`)

**Core Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/stream` | GET | SSE streaming AI responses |
| `/stream-race` | GET | Race mode (fastest provider wins) |
| `/transcribe` | POST | Audio file transcription |
| `/transcribe-stream` | GET | Real-time transcription SSE |
| `/transcribe-cloud` | POST | Cloud-based transcription |
| `/ask-with-image` | POST | Multimodal AI with screenshot |
| `/ollama/models` | GET | List local Ollama models |
| `/ollama/pull` | POST | Download new model |
| `/providers` | GET | Check configured providers |
| `/set-mode` | POST | Change AI mode |

**Cognitive Graph Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cognitive-graph/status` | GET | Neo4j connection status |
| `/cognitive-graph/initialize` | POST | Create schema constraints |
| `/cognitive-graph/search` | GET | Semantic search |
| `/cognitive-graph/history/{user_id}` | GET | User interview history |
| `/cognitive-graph/ingest/{id}` | POST | Ingest conversation |
| `/extract-entities` | POST | NLP entity extraction |

#### 2.3.2 AI Router (`ai_router.py`)

**Mode Resolution Logic:**

```python
Modes: auto, fast, turbo, instant, adaptive, universal, interview,
       reasoning, code, cloud

Resolution:
- Code keywords + length >= 18  -> code mode
- Length >= 30 or reasoning words -> reasoning mode
- Technical keywords + interview hints -> interview mode
- Length <= 8 -> fast mode
- Default -> adaptive mode
```

**Provider Support:**

| Provider | Models | Streaming | Vision |
|----------|--------|-----------|--------|
| Ollama (Local) | All local models | Yes | Yes (llava, qwen-vl) |
| OpenAI | GPT-4o, GPT-4o-mini, o3-mini | Yes | No |
| Anthropic | Claude Sonnet, Opus, Haiku | Yes | No |
| Google | Gemini 2.0 Flash, 1.5 Pro | Yes | No |
| xAI | Grok 2, Grok 2 Mini | Yes | No |
| DeepSeek | DeepSeek Chat, Coder | Yes | No |
| Groq | Llama 3.3, Mixtral, Qwen | Yes | No |
| Perplexity | Sonar models | Yes | No |
| Ollama Cloud | Qwen 3.5, MiniMax, GLM | Yes | No |

#### 2.3.3 Speech Recognition (`whisper_handler.py`)

**Model Selection (Adaptive):**

| RAM | Model | Size | Speed | Accuracy |
|-----|-------|------|-------|----------|
| < 8GB | tiny | 39MB | Fastest | Basic |
| 8-16GB | base | 74MB | Fast | Good |
| >= 16GB | small | 244MB | Medium | Better |
| interview mode | small | 244MB | Medium | Better |

**Features:**
- Thread-safe lazy loading
- Warmup on startup (non-blocking)
- VAD (Voice Activity Detection) filtering
- Text cleaning and normalization
- Question detection (`is_question()`)
- Small talk filtering (`is_small_talk()`)
- Technical content detection (`is_technical()`)

#### 2.3.4 Cognitive Graph (`cognitive_graph.py`)

**Node Types:**

| Node | Properties | Purpose |
|------|------------|---------|
| `Interview` | id, title, timestamp, duration_ms, user_id | Session container |
| `Question` | id, text, category, difficulty, company_id | Interview questions |
| `Answer` | id, text, transcript, confidence | User responses |
| `Company` | id, name, industry, size | Organizations |
| `Role` | id, title, level, department | Job positions |
| `Topic` | id, name, category | Technical topics |
| `Skill` | id, name, proficiency | Demonstrated skills |

**Relationships:**
- `(Interview)-[:CONTAINS]->(Question)`
- `(Question)-[:ANSWERED_WITH]->(Answer)`
- `(Question)-[:ASKED_BY]->(Company)`
- `(Question)-[:RELATED_TO]->(Topic)`
- `(Answer)-[:DEMONSTRATES]->(Skill)`

#### 2.3.5 Predictive Interview (`predictive_interview.py`)

**Data Sources:**
1. User's cognitive graph history
2. Curated company question databases (Google, Meta, Amazon, etc.)
3. Question frequency and difficulty metrics

**Prediction Factors:**
- Company historical patterns
- Role/title matching
- User skill progression
- Common question categories

### 2.4 Database Layer (Neo4j)

**Connection Configuration:**

```python
URI = "bolt://localhost:7687"  # Configurable via NEO4J_URI
AUTH = ("neo4j", "password")   # Configurable via NEO4J_USER/PASSWORD
```

**Schema Constraints:**

```cypher
// Unique IDs
CREATE CONSTRAINT interview_id IF NOT EXISTS FOR (i:Interview) REQUIRE i.id IS UNIQUE
CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE
CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE

// Indexes for performance
CREATE INDEX interview_timestamp IF NOT EXISTS FOR (i:Interview) ON (i.timestamp)
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)
CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name)
```

---

## 3. Data Flow

### 3.1 Speech-to-Text Flow

```
[Microphone] -> [Audio Capture] -> [WhisperModel] -> [Text Processing] -> [UI Display]
                      |                                        |
                      v                                        v
              [sounddevice]                            [Clean Text]
              [faster-whisper]                         [is_meaningful]
                                                          [is_question]
```

**Process:**
1. Audio captured via `sounddevice` (16kHz, mono, float32)
2. Normalized and passed to Whisper model
3. Transcription with beam_size=3, greedy decoding for speed
4. Text cleaned (lowercase, punctuation normalized)
5. Meaningfulness check (filters coughs, noises)
6. Question detection (ends with ?, keywords)
7. Displayed in chat UI

### 3.2 AI Processing Flow

```
[User Input] -> [Mode Resolver] -> [Provider Router] -> [AI Model] -> [Stream Response]
       |                |                  |                |
       v                v                  v                v
[Context]      [fast/adaptive/    [Ollama/Cloud]    [SSE Events]
[History]       interview/code]    [Provider]        [UI Update]
```

**Modes and Their Use:**

| Mode | When Used | Model |
|------|-----------|-------|
| `instant` | Ultra-fast responses | Turbo model, 64 tokens |
| `turbo` | Quick answers | Turbo model, 150 tokens |
| `fast` | Short queries (<8 words) | Fast model |
| `adaptive` | Default | Context-dependent |
| `interview` | Technical questions | Interview-tuned model |
| `reasoning` | Complex questions | Reasoning model |
| `code` | Programming | Code-optimized model |
| `cloud` | High accuracy needed | Cloud provider |

### 3.3 Cognitive Graph Ingestion Flow

```
[Conversation] -> [Entity Extraction] -> [Node Creation] -> [Relationship Linking]
       |                    |                    |                   |
       v                    v                    v                   v
[Messages]      [Companies]  [Topics]     [Interview]         [CONTAINS]
[Transcript]    [Skills]   [Categories] [Question]         [ASKED_BY]
[QA Pairs]                                [Answer]           [RELATED_TO]
                                                               [DEMONSTRATES]
```

**Entity Extraction:**
- Rule-based matching (no ML model required)
- Known company names list (100+ companies)
- Technical topics dictionary (algorithms, system design, etc.)
- Skills catalog (languages, frameworks, tools)
- Question categorization (technical, behavioral, system-design)

### 3.4 Interview Prediction Flow

```
[Company Name] -> [Lookup Historical] -> [Filter by Role] -> [Sort by Frequency]
       |                |                      |                      |
       v                v                      v                      v
[User Input]    [Cognitive Graph]    [Role Matching]         [Top N Questions]
                       |
                       v
              [User Performance]
              [Skill Gaps]
```

---

## 4. Security Considerations

### 4.1 API Key Storage

**Threat Model:** API keys must not be stored in plain text or transmitted over insecure channels.

**Implementation:**

```javascript
// electron/main.js - Secure key storage
const apiKeyStore = new Store({
  name: "secure-api-keys",
  encryptionKey: crypto.scryptSync(
    app.getPath("userData"),
    "ai-note-taker-salt-v1",
    32
  ).slice(0, 16).toString("hex").slice(0, 16)
});
```

**Security Properties:**
- Keys encrypted at rest using AES-256-GCM
- Encryption key derived from machine-specific path + salt
- Keys never stored in `.env` files (P1 security fix)
- Keys retrieved via secure IPC, not HTTP
- HTTP configuration endpoint disabled

### 4.2 Local-Only Processing Options

**Offline Mode:**
- Ollama runs entirely locally (no network calls)
- Whisper transcription runs locally
- Neo4j can run locally
- No data leaves the machine

**Indicators:**
- Green indicator when using local models
- "Secure" badge in UI
- No cloud provider badges shown

### 4.3 Stealth Mode Implementation

**Screen Capture Protection:**

```javascript
// Windows: SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE
// macOS: setContentProtection (hides from screen recording)
// Linux: setContentProtection (best effort)

window.setContentProtection(true);  // Hide from Zoom, Teams, OBS
```

**Features:**
- Window hidden from screen capture APIs
- System tray icon (16x16 transparent blue dot)
- Alt+D global shortcut for toggle
- CSS `stealth-mode` class for UI dimming

### 4.4 Input Sanitization

**File Upload Security:**

```python
def get_secure_filename(original: str) -> str:
    # Generate UUID-based filename
    ext = safe_extension_only(original)
    return f"{uuid.uuid4()}.{ext}"

def sanitize_path(filename: str) -> str:
    # Reject directory traversal
    if ".." in filename or "/" in filename:
        raise ValueError("Invalid filename")
```

**API Key Sanitization:**
```python
# Remove API keys from uvicorn logs
class APIKeyFilter(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(r"api_key=[^&\s]*", "api_key=***", str(record.msg))
        return True
```

---

## 5. Deployment

### 5.1 Development Setup

**Prerequisites:**
- Node.js 18+ and npm
- Python 3.11+
- Neo4j Community Edition 5.x
- Ollama (for local AI)
- ffmpeg (for audio processing)

**Installation Steps:**

```bash
# 1. Clone repository
git clone <repo-url>
cd ai-note-taker

# 2. Setup Python backend
cd backend
python -m venv ../AINT_Venv
source ../AINT_Venv/bin/activate  # Windows: ..\AINT_Venv\Scripts\activate
pip install -r requirements.txt

# 3. Setup Neo4j
cd ../neo4j
unzip neo4j-community.zip
# Edit conf/neo4j.conf to set initial password
bin/neo4j console

# 4. Setup Electron
cd ../electron
npm install

# 5. Start development
cd ..
./start-app.bat  # Windows
./start-app.sh   # macOS/Linux
```

### 5.2 Production Build Process

**Electron Builder Configuration:**

```json
{
  "build": {
    "appId": "com.ainotetaker.app",
    "productName": "AI Note Taker",
    "directories": { "output": "dist" },
    "win": { "target": ["portable"], "arch": ["x64"] },
    "mac": { "target": ["dmg", "zip"], "arch": ["x64", "arm64"] },
    "linux": { "target": ["AppImage", "deb"], "arch": ["x64"] },
    "extraResources": [
      { "from": "../renderer", "to": "renderer" },
      { "from": "../backend", "to": "backend" },
      { "from": "../AINT_Venv", "to": "AINT_Venv" }
    ]
  }
}
```

**Build Commands:**

```bash
# Windows
cd electron
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux

# All platforms
npm run build
```

### 5.3 Neo4j Installation Requirements

**System Requirements:**

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| Disk | 1GB | 10GB+ |
| CPU | 2 cores | 4 cores+ |
| Java | JDK 17 | JDK 17+ |

**Configuration:**

```properties
# neo4j/conf/neo4j.conf
server.memory.heap.initial_size=512m
server.memory.heap.max_size=2G
server.memory.pagecache.size=1G
server.bolt.listen_address=0.0.0.0:7687
server.http.listen_address=0.0.0.0:7474
```

**Environment Variables:**

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
```

---

## 6. Performance

### 6.1 Caching Strategies

**Model Caching:**

```python
# whisper_handler.py
models = {}
_model_lock = threading.Lock()

def get_model(mode="adaptive"):
    selected = select_model(mode)
    if selected not in models:
        with _model_lock:
            if selected not in models:
                models[selected] = WhisperModel(selected, device=DEVICE)
    return models[selected]
```

**API Key Caching:**

```python
# cloud_providers.py
_key_cache = {}

def fetch_key_from_secure_server(provider):
    if provider in _key_cache:
        return _key_cache[provider]
    # ... fetch from secure server
    _key_cache[provider] = key
    return key
```

**Vision Model Caching:**

```python
# ai_router.py
_vision_model_cache = None

def _get_vision_model():
    global _vision_model_cache
    if _vision_model_cache is not None:
        return _vision_model_cache
    # ... scan available models
    _vision_model_cache = found_model
    return found_model
```

### 6.2 Query Optimization

**Neo4j Index Usage:**

```cypher
// Fast lookup by ID (indexed)
MATCH (i:Interview {id: $id}) RETURN i

// Timestamp range queries (indexed)
MATCH (i:Interview)
WHERE i.timestamp > datetime($from)
RETURN i ORDER BY i.timestamp DESC

// Company name lookup (indexed)
MATCH (c:Company {name: $name})<-[:ASKED_BY]-(q:Question)
RETURN q
```

**Full-Text Search Strategy:**

```cypher
// Multi-field search with scoring
CALL {
    MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WHERE q.text CONTAINS $keyword
    WITH q, a, 10 as score
    RETURN q, a, score
    UNION
    MATCH (q:Question)-[:ANSWERED_WITH]->(a:Answer)
    WHERE a.text CONTAINS $keyword
    WITH q, a, 8 as score
    RETURN q, a, score
}
WITH q, a, max(score) as relevance
ORDER BY relevance DESC
LIMIT $limit
```

### 6.3 Memory Management

**Whisper Model Memory:**

| Model | Memory Usage | Load Time |
|-------|-------------|-----------|
| tiny | ~150MB | 2-3s |
| base | ~300MB | 3-5s |
| small | ~1GB | 8-12s |

**Memory Optimization Strategies:**

```python
# Unload unused models
def unload_all_models():
    global models
    with _model_lock:
        for name, model in models.items():
            del model
        models.clear()

# Auto-screenshot buffer cleanup
SCREENSHOT_BUFFER_MAX = 5  # Ring buffer limit
screenshotBuffer = collections.deque(maxlen=SCREENSHOT_BUFFER_MAX)
```

**Electron Memory:**

| Component | Typical Usage | Peak Usage |
|-----------|--------------|------------|
| Main Process | 80-120MB | 150MB |
| Renderer | 100-200MB | 300MB |
| GPU Process | 50-100MB | 200MB |
| Total | 230-420MB | 650MB |

**Backend Memory:**

| Component | Typical Usage | Peak Usage |
|-----------|--------------|------------|
| Python Runtime | 100-150MB | 200MB |
| Whisper Model | 150-1000MB | 1000MB |
| Neo4j Driver | 20-50MB | 100MB |
| Total | 270-1200MB | 1300MB |

---

## 7. Appendix

### 7.1 File Structure

```
ai-note-taker/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # Main application, API endpoints
│   ├── ai_router.py           # AI provider routing
│   ├── cloud_providers.py     # Cloud AI provider integrations
│   ├── whisper_handler.py     # Speech recognition
│   ├── cognitive_graph.py     # Neo4j graph operations
│   ├── predictive_interview.py # Interview prediction
│   ├── entity_extraction.py   # NLP entity extraction
│   ├── document_store.py      # RAG document storage
│   ├── speaker_diarization.py # Multi-speaker detection
│   ├── analytics.py           # Usage analytics
│   ├── crm_integration.py     # CRM webhook integrations
│   ├── config.py              # Configuration management
│   ├── utils.py               # Utility functions
│   └── requirements.txt       # Python dependencies
├── electron/                   # Electron main process
│   ├── main.js                # Main process entry
│   ├── preload.js             # IPC bridge
│   ├── stealth.js             # Stealth mode module
│   └── package.json           # Electron dependencies
├── renderer/                   # Frontend UI
│   ├── index.html             # Main interface
│   ├── app.js                 # Application logic
│   ├── style.css              # Styles
│   ├── cognitive-graph.html   # Graph visualization
│   ├── cognitive-graph.js     # Graph logic
│   ├── pre-interview.html     # Interview prep UI
│   └── pre-interview.js       # Interview prep logic
├── docs/                       # Documentation
│   ├── technical_specification.md  # This document
│   ├── COGNITIVE_GRAPH_API.md    # Graph API docs
│   ├── ENTITY_EXTRACTION.md      # NLP docs
│   └── SETUP_COGNITIVE_GRAPH.md  # Setup guide
└── neo4j/                      # Neo4j installation
    └── neo4j-community.zip
```

### 7.2 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | bolt://localhost:7687 | Neo4j connection URI |
| `NEO4J_USER` | neo4j | Neo4j username |
| `NEO4J_PASSWORD` | password | Neo4j password |
| `OLLAMA_URL` | http://localhost:11434 | Ollama API URL |
| `OLLAMA_MODEL` | qwen2.5:1.5b | Default model |
| `AI_TEMPERATURE` | 0.1 | AI creativity (0-1) |
| `AI_TIMEOUT` | 30 | Request timeout (seconds) |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `GOOGLE_API_KEY` | - | Google API key |
| `XAI_API_KEY` | - | xAI API key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API key |
| `GROQ_API_KEY` | - | Groq API key |
| `PERPLEXITY_API_KEY` | - | Perplexity API key |

### 7.3 Related Documentation

- [COGNITIVE_GRAPH_API.md](./COGNITIVE_GRAPH_API.md) - Graph API reference
- [ENTITY_EXTRACTION.md](./ENTITY_EXTRACTION.md) - NLP documentation
- [SETUP_COGNITIVE_GRAPH.md](./SETUP_COGNITIVE_GRAPH.md) - Neo4j setup guide
- [README.md](../README.md) - Project overview

---

*Document generated for AI Note Taker Phase 1 - Predictive Interview*
