# AI Note Taker - Production Project Structure

## Overview
Clean, modular architecture following production best practices.

## Directory Structure

```
ai-note-taker/
├── apps/                          # Frontend applications
│   ├── desktop/                   # Desktop app (Electron)
│   ├── mobile/                    # Mobile app
│   └── web/                       # Web application
│       ├── css/                   # Stylesheets
│       ├── js/                    # JavaScript modules
│       ├── *.html                 # HTML pages
│       └── manifest.json          # PWA manifest
│
├── backend/                       # Python backend
│   ├── api/                       # API endpoints
│   ├── core/                      # Core modules
│   │   ├── database.py            # Database layer (T16)
│   │   ├── config.py            # Configuration
│   │   └── utils.py             # Utilities
│   ├── lib/                       # Libraries
│   ├── modules/                   # Feature modules
│   │   ├── ai/                    # AI/ML modules
│   │   │   ├── cache_manager.py       # T18 - Redis caching
│   │   │   ├── cognitive_graph.py
│   │   │   └── ...
│   │   ├── crm/                   # CRM modules
│   │   │   ├── crm_integration.py
│   │   │   └── crm_real_integration.py  # T22
│   │   ├── interview/             # Interview modules
│   │   │   ├── interview_simulator.py
│   │   │   └── mock_interview_library.py  # T19
│   │   ├── platform/              # Platform modules
│   │   │   └── mcp_server.py      # T21
│   │   └── voice/                 # Voice modules
│   │       ├── voice_agent.py       # T20
│   │       └── ...
│   ├── security/                  # Security modules
│   │   └── encryption.py          # T17 - Encryption
│   └── tests/                     # Backend tests
│
├── browser-extension/             # Browser extension
├── chrome-extension/              # Chrome extension
├── config/                        # Configuration
│   └── secrets/                   # Secrets (gitignored)
├── data/                          # User data (gitignored)
├── deploy/                        # Deployment configs
├── docker/                        # Docker files
├── docs/                          # Documentation
│   ├── API/                       # API documentation
│   ├── ARCHITECTURE/              # Architecture docs
│   ├── DEPLOYMENT/                # Deployment guides
│   ├── DEVELOPMENT/               # Dev guides
│   ├── SECURITY/                  # Security docs
│   └── USER_GUIDES/               # User documentation
├── electron/                      # Electron main process
├── infrastructure/                # Infrastructure as Code
│   └── terraform/
├── k8s/                           # Kubernetes manifests
│   ├── applications/
│   └── helm/
├── libs/                          # Shared libraries
│   ├── ai/
│   ├── cv/
│   ├── shared/
│   └── voice/
├── neo4j/                         # Neo4j database
├── scripts/                       # Scripts
│   ├── development/               # Dev scripts
│   ├── production/                # Production scripts
│   └── utils/                     # Utility scripts
├── tests/                         # Tests
│   ├── e2e/                       # End-to-end tests
│   └── integration/               # Integration tests
├── tools/                         # Development tools
└── vscode-extension/              # VS Code extension
```

## Key Features (T16-T22)

| Task | Feature | Location |
|------|---------|----------|
| T16 | Database Migration | `backend/core/database.py` |
| T17 | Encryption at Rest | `backend/security/encryption.py` |
| T18 | Redis Caching | `backend/modules/ai/cache_manager.py` |
| T19 | Mock Interview Library | `backend/modules/interview/mock_interview_library.py` |
| T20 | AI Voice Agent | `backend/modules/voice/voice_agent.py` |
| T21 | MCP Server | `backend/modules/platform/mcp_server.py` |
| T22 | CRM Integration | `backend/modules/crm/crm_real_integration.py` |

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///data/ainotetaker.db  # Dev
# DATABASE_URL=postgresql+asyncpg://...  # Production

# Security
ENCRYPTION_KEY=your-secret-key

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Neo4j
NEO4J_PASSWORD=your-neo4j-password
```

## Development

### Start Development Server
```bash
cd scripts/development
./start-app.bat
```

### Run Tests
```bash
pytest tests/
```

## Production Deployment

See `docs/DEPLOYMENT/` for detailed deployment guides.

## Git Ignore

All sensitive data, build artifacts, and temporary files are excluded via `.gitignore`:
- Virtual environments (`venv/`, `AINT_Venv/`)
- Node modules (`node_modules/`)
- Python cache (`__pycache__/`, `*.pyc`)
- User data (`data/`)
- Secrets (`.env`, `*.pem`)
- Logs (`*.log`)
- Temp files (`temp_audio/`)
