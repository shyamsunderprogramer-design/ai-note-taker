# MINIMAX-M2 Task Assignment — Frontend, Testing & DevOps
**Date:** April 9, 2026 | **Model:** MINIMAX-M2 | **Tasks:** 6 | **Effort:** ~6-8 weeks

---

## START HERE — Quick Win (Do This First)

### T26: Remove Electron CORS Override (P0) — 1 hour
**File:** `electron/main.js:977`

**Current:**
```javascript
headers["Access-Control-Allow-Origin"] = ["*"]
headers["Access-Control-Allow-Methods"] = ["GET, POST, PUT, DELETE, OPTIONS"]
headers["Access-Control-Allow-Headers"] = ["Content-Type, Authorization"]
```

**Problem:** This overrides the backend's CORS whitelist (which GLM-5.1 is fixing to be strict). The Electron app adds `["*"]` on ALL responses, completely bypassing CORS security.

**Fix:**
1. **Remove** lines 977-979 entirely — let the backend handle CORS
2. If needed for file:// protocol, add ONLY localhost origins:
```javascript
// Only for file:// protocol (local renderer)
if (details.url.startsWith("file://")) {
    headers["Access-Control-Allow-Origin"] = ["http://localhost:3000", "http://localhost:8000"]
    headers["Access-Control-Allow-Methods"] = ["GET, POST, PUT, DELETE, OPTIONS"]
    headers["Access-Control-Allow-Headers"] = ["Content-Type, Authorization"]
}
```
3. Test that the Electron app still communicates with backend correctly

---

## P1 TASKS (Week 1-4)

### T13: Feature Health Dashboard (P1) — 2-3 days
**Files:** `backend/main.py` (add endpoint), `renderer/app.js` (add UI)

**Problem:** 12 feature modules silently degrade when dependencies are missing. Users don't know why features don't work.

**Backend endpoint — Add to `backend/main.py`:**
```python
@app.get("/health/modules")
async def get_module_health():
    """Show which feature modules are available and why."""
    modules = {
        "database": {
            "available": DATABASE_AVAILABLE,
            "type": "sqlite" if USE_SQLITE else "postgresql" if DATABASE_AVAILABLE else "json",
            "required_dependency": "sqlalchemy"
        },
        "neo4j": {
            "available": get_driver() is not None,
            "required_dependency": "neo4j package + running server",
            "config_hint": "Set NEO4J_PASSWORD env var"
        },
        "whisper": {
            "available": get_model() is not None,
            "type": "local" if get_model() else "unavailable",
            "required_dependency": "whisper model files"
        },
        "voice_clone": {
            "available": True,  # Edge TTS always available
            "rvc_available": os.path.exists("backend/rvc_engine.py"),
            "required_dependency": "RVC models for voice cloning"
        },
        "ai_router": {
            "available": True,
            "providers": list_providers(),  # function to check which providers have keys
            "required_dependency": "At least one AI provider key"
        },
        "collaboration": {
            "available": True,
            "required_dependency": "WebSocket support"
        },
        "document_rag": {
            "available": DOCUMENT_AVAILABLE,
            "required_dependency": "sentence-transformers + chromadb"
        },
        "analytics": {
            "available": True,
            "required_dependency": "None"
        },
        "mock_interview": {
            "available": True,
            "question_count": len(MockInterviewLibrary().all_questions),
            "required_dependency": "None"
        },
        "study_plan": {
            "available": True,
            "required_dependency": "None"
        },
        "cognitive_graph": {
            "available": get_driver() is not None,
            "required_dependency": "neo4j package + running server"
        },
        "encryption": {
            "available": os.getenv("ENCRYPTION_KEY") is not None,
            "required_dependency": "ENCRYPTION_KEY env var (KIMI-K2.5 implementing)"
        }
    }
    return {
        "modules": modules,
        "overall_health": sum(1 for m in modules.values() if m["available"]) / len(modules) * 100
    }
```

**Frontend UI — Add to `renderer/app.js`:**
1. Add a "System Health" section in settings/sidebar
2. Show each module as green (available) / yellow (partial) / red (missing)
3. Add "Configure" button next to unavailable modules
4. Show tooltip with dependency info on hover
5. Auto-refresh on startup

**Design mockup:**
```
┌─ System Health ─────────────────────────┐
│ ✅ Database (SQLite)                     │
│ ✅ AI Router (3 providers active)        │
│ ✅ Voice Clone (Edge TTS)                │
│ ⚠️ Voice Clone RVC (models missing)      │
│   → [Configure RVC Models]               │
│ ❌ Knowledge Graph (Neo4j not connected) │
│   → [Set NEO4J_PASSWORD]                 │
│ ✅ Document RAG                           │
│ ❌ Encryption (ENCRYPTION_KEY not set)    │
│   → [Set Encryption Key]                 │
│                                          │
│ Health: 75% (9/12 modules active)        │
└──────────────────────────────────────────┘
```

---

### T15: Integration Test Suite (P1) — 1-2 weeks
**Files:** `backend/tests/` (expand existing), `backend/tests/integration/` (new)

**Current state:** Only ~75 unit tests exist, no integration tests

**What to build:**

1. **Test infrastructure setup:**
   ```
   backend/tests/
   ├── conftest.py          # Shared fixtures (test client, test DB, auth tokens)
   ├── unit/                # Existing unit tests
   └── integration/
       ├── test_auth.py          # Auth flow: register → login → use token → refresh
       ├── test_conversations.py # Full conversation CRUD + AI interaction
       ├── test_job_tracker.py   # Job application pipeline
       ├── test_voice_clone.py   # Voice model management
       ├── test_documents.py    # Document upload + RAG
       ├── test_analytics.py    # Analytics endpoints
       ├── test_mock_interview.py # Mock interview flow
       ├── test_collaboration.py # Duo mode
       ├── test_cognitive_graph.py # Knowledge graph
       ├── test_settings.py      # User settings
       ├── test_byok.py         # BYOK provider management
       └── test_security.py     # Security middleware tests
   ```

2. **conftest.py fixtures:**
   ```python
   import pytest
   from fastapi.testclient import TestClient
   from main import app
   from database import init_database, close_database

   @pytest.fixture(scope="session")
   def test_db():
       """Set up test database (SQLite in-memory)"""
       os.environ["USE_SQLITE"] = "true"
       os.environ["AUTH_REQUIRED"] = "true"
       init_database()
       yield
       close_database()

   @pytest.fixture
   def client(test_db):
       return TestClient(app)

   @pytest.fixture
   def auth_token(client):
       """Register + login, return valid JWT token"""
       client.post("/auth/register", json={"username": "testuser", "password": "TestPass123!"})
       response = client.post("/auth/login", json={"username": "testuser", "password": "TestPass123!"})
       return response.json()["access_token"]

   @pytest.fixture
   def auth_headers(auth_token):
       return {"Authorization": f"Bearer {auth_token}"}
   ```

3. **Test coverage targets:**
   - Auth endpoints: 100%
   - CRUD endpoints: 80%+
   - AI interaction: 50%+ (harder to test without real AI keys)
   - WebSocket: 30%+ (basic connectivity + auth)
   - Security middleware: 90%+

4. **Add pytest configuration:**
   ```ini
   # backend/pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   addopts = -v --tb=short
   ```

5. **Add coverage reporting:**
   ```bash
   pip install pytest-cov
   pytest --cov=main --cov-report=html tests/
   ```

---

### T14-devops: CI/CD Pipeline (P1) — 3-4 days ✅

**Implemented as enterprise-grade DevOps pipeline:**

**CI Workflow (`.devsecops/.github/workflows/ci.yml`):**
- Pre-flight checks & secrets scanning (GitLeaks)
- Multi-stage linting (ESLint, Flake8, Black, MyPy, Checkov, Hadolint)
- Parallel test execution with coverage (Pytest, pytest-cov, pytest-xdist)
- SonarQube Cloud integration for SAST
- Multi-architecture container builds (Docker Buildx, linux/amd64, linux/arm64)
- Trivy container vulnerability scanning
- Snyk SCA for dependency analysis
- CycloneDX SBOM generation
- Artifact publishing to GitHub Container Registry

**CD Workflow (`.devsecops/.github/workflows/cd.yml`):**
- Terraform infrastructure provisioning (AWS EKS, Azure AKS, GCP GKE)
- Helm chart deployments with environment-specific values
- Canary/blue-green/rolling deployment strategies
- ArgoCD GitOps integration
- Post-deployment smoke tests
- Datadog synthetic monitoring
- Slack/Jira notifications

**Security Workflow (`.devsecops/.github/workflows/security.yml`):**
- Scheduled daily security scans
- Snyk, Trivy, GitLeaks, Checkov, Falco runtime security
- SonarQube security sweeps
- Dependency review and vulnerability aggregation

**Infrastructure as Code (`.devsecops/infrastructure/terraform/`):**
- **AWS**: EKS cluster, RDS PostgreSQL, ElastiCache, S3, ECR, IAM IRSA, Load Balancer Controller, Cluster Autoscaler
- **Azure**: AKS, Azure Database for PostgreSQL Flexible, Key Vault, Container Registry, Log Analytics
- **GCP**: GKE with Autopilot, Cloud SQL, Secret Manager, Artifact Registry, Cloud Armor WAF

**Kubernetes (`.devsecops/k8s/`):**
- Helm 3 chart with production-grade values
- PodDisruptionBudget, HPA, topology spread constraints
- ServiceMonitor for Prometheus scraping
- Staging and production environment values

**Container Images (`.devsecops/docker/`):**
- Multi-stage Dockerfile for backend (Python 3.11 slim)
- Multi-stage Dockerfile for Electron app
- docker-compose.yml for local development with PostgreSQL, Redis, Neo4j, Prometheus, Grafana, Jaeger

**Documentation:**
- `.devsecops/DEPLOYMENT.md` - Deployment guide with rollback procedures
- `.devsecops/SECURITY.md` - Security architecture and compliance checklist
- `.devsecops/README.md` - Pipeline overview and security gates

---

### T12: Chrome Extension Polish (P1) — 2-3 weeks
**Files:** `chrome-extension/` (all files)

**Current state:** MVP exists with basic manifest.json, popup, and background script

**What to improve:**

1. **Content script for meeting platforms:**
   - Detect Zoom/Meet/Teams meeting pages
   - Inject recording controls overlay
   - Capture audio from meeting tab
   - Auto-start when meeting detected

2. **Overlay UI improvements:**
   - Minimal, non-intrusive floating widget
   - Show recording status, duration
   - Quick-access to AI suggestions
   - Minimize/hide toggle

3. **Screen capture integration:**
   - Use `chrome.desktopCapture` API for screen sharing
   - Screenshot capture with `chrome.tabs.captureVisibleTab`
   - Send screenshots to backend for vision AI analysis

4. **Auto-join meeting detection:**
   - Detect meeting URLs (zoom.us, meet.google.com, teams.microsoft.com)
   - Show notification when meeting starts
   - Option to auto-connect to backend

5. **Manifest V3 compliance:**
   - Ensure manifest.json follows Manifest V3 spec
   - Use service worker (not background page)
   - Proper permissions (minimal, request at runtime)
   - Add `action` instead of `browser_action`

6. **Icons and branding:**
   - Add proper icon set (16, 32, 48, 128px)
   - Professional popup UI with the app branding
   - Connection status indicator

---

## P2 TASKS (Week 5+)

### T19: Mobile App / PWA Enhancement (P2) — 6-8 weeks
**This is a big task — consider PWA first, then native app**

**Phase 1: PWA Enhancement (2-3 weeks):**
1. Add `manifest.json` with proper icons, theme color, display mode
2. Add service worker for offline functionality
3. Responsive design for mobile screens
4. Push notification support
5. Add to homescreen prompt

**Phase 2: React Native App (4-6 weeks) — if needed:**
1. Core features: transcription, AI chat, interview practice
2. Push notifications for interview reminders
3. Audio recording from mobile microphone
4. Basic offline mode

**Recommendation:** Do PWA first (2-3 weeks vs 6-8 weeks for native). Most users don't need a native app for this type of tool. Only build native if user feedback demands it.

---

## TASK ORDER

```
Day 1:     T26 (Electron CORS override fix) — 1 hour ← START HERE
Week 1-2:  T13 (Feature health dashboard) — 2-3 days
Week 2-4:  T15 (Integration test suite) — 1-2 weeks
Week 3-4:  T14-devops (CI/CD pipeline) — 3-4 days
Week 4-6:  T12 (Chrome extension polish) — 2-3 weeks
Week 6+:   T19 (Mobile/PWA) — 2-8 weeks depending on scope
```

---

## COORDINATION NOTES

**With GLM-5.1:**
- GLM-5.1 is fixing CSP `connect-src` in electron/main.js (T25) — coordinate to avoid conflicts in main.js
- GLM-5.1 is adding auth enforcement — your integration tests should test with `AUTH_REQUIRED=true`

**With KIMI-K2.5:**
- KIMI-K2.5 is building database module — your integration tests should test against real DB
- KIMI-K2.5 is adding encryption — your health dashboard should show encryption status
- Don't start integration tests until T16 (database) is stable enough to test against

**File ownership — avoid editing same files simultaneously:**
- `electron/main.js` — MINIMAX-M2 owns this (T26), but GLM-5.1 needs to fix CSP (T25). Coordinate: GLM-5.1 does T25 first (quick fix), then MINIMAX-M2 does T26.
- `backend/main.py` — GLM-5.1 owns this. Don't modify it. Add new endpoints only if needed for tests/health.
- `renderer/app.js` — MINIMAX-M2 owns this for health dashboard UI.

---

## VERIFICATION CHECKLIST

After each task:
- [ ] Electron app starts without errors
- [ ] All existing features still work
- [ ] Chrome extension loads in Chrome
- [ ] Tests pass: `cd backend && python -m pytest tests/ -v`
- [ ] No new security vulnerabilities
- [ ] CI pipeline runs green (once set up)