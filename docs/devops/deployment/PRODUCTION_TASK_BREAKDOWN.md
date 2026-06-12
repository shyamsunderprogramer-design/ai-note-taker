# Production Task Breakdown — AI Note Taker

**Date:** April 9, 2026
**Source:** Unified analysis from 3 competitive docs (GLM-5.1, MINIMAX-M2, original)
**Goal:** Get to production-ready state ASAP

---

## Priority Definitions

- **P0** = Blocking production launch. Must fix before anyone else uses the app.
- **P1** = Important for competitive parity. Fix within 2 weeks of launch.
- **P2** = Nice-to-have for differentiation. Fix within 1-2 months.

---

## P0 — SECURITY & STABILITY (Must Fix Before Production)

### Task 1: Database Migration (JSON → PostgreSQL/SQLite)
**All 3 analyses agree this is the #1 blocker**
- Replace flat JSON files with proper database for: users, conversations, job applications, voice models, analytics
- Use SQLAlchemy models with connection pooling
- Create migration scripts
- Add automated backup endpoints
- **Estimated effort:** 2 weeks
- **Assigned to:** ___________

### Task 2: Enforce Authentication on All Endpoints
**Current state:** JWT exists but only 2 endpoints use it. 100+ endpoints unprotected.**
- Add `require_authentication` middleware to all sensitive endpoints
- Add refresh token support
- Rate limiting on auth endpoints (register/login)
- **Estimated effort:** 3-4 days
- **Assigned to:** ___________

### Task 3: Fix Electron Security Issues
**Current state:** `webSecurity: false`, `allowRunningInsecureContent: true`**
- Remove `webSecurity: false` from `electron/main.js`
- Set `allowRunningInsecureContent: false`
- Implement nonce-based CSP (remove `unsafe-inline`)
- Fix CORS whitelist (remove `["*"]`, add specific origins)
- **Estimated effort:** 1-2 days
- **Assigned to:** ___________

### Task 4: Encryption at Rest
**Current state:** Conversations, API keys stored in plain files**
- AES-256 encryption for conversation content
- Encrypt API keys in storage (Electron already has encrypted store)
- Encrypt voice model data
- **Estimated effort:** 3-4 days
- **Assigned to:** ___________

### Task 5: WebSocket Authentication
**Current state:** `/ws` and `/ws/transcribe` have no auth — anyone can connect**
- Add token validation on WebSocket connect
- Reject unauthenticated connections
- **Estimated effort:** 1 day
- **Assigned to:** ___________

### Task 6: Neo4j Security
**Current state:** Default password "password", auth disabled**
- Require strong password
- Enable authentication
- Add connection validation
- **Estimated effort:** 1 day
- **Assigned to:** ___________

### Task 7: HTTPS Enforcement
**Current state:** `HTTPS_REQUIRED = False`**
- Enable HTTPS with self-signed cert for dev, Let's Encrypt for prod
- Redirect HTTP → HTTPS
- Add HSTS header
- **Estimated effort:** 1-2 days
- **Assigned to:** ___________

### Task 8: Rate Limiting on All Endpoints
**Current state:** Only `/providers` and `/ask-with-image` have rate limits**
- Extend `@rate_limit` decorator to all endpoints
- Per-user rate limiting (not just per-IP)
- Different limits for authenticated vs unauthenticated
- **Estimated effort:** 1 day
- **Assigned to:** ___________

---

## P1 — DATA & API HARDENING (Within 2 Weeks of Launch)

### Task 9: Pagination on All List Endpoints
**All 3 analyses flag missing pagination**
- Add `limit`/`offset` query params to: conversations, job applications, voice models, documents, analytics, mock questions, study plans
- Return total count with results
- **Estimated effort:** 2-3 days
- **Assigned to:** ___________

### Task 10: Structured Error Codes
**Current state:** All errors return `{"error": "message string"}`**
- Define standard error format: `{"error": {"code": "AUTH_REQUIRED", "message": "...", "status": 401}}`
- Migrate all endpoints to structured format
- **Estimated effort:** 2-3 days
- **Assigned to:** ___________

### Task 11: Audit Logging
**Required for enterprise/compliance**
- Log all auth events (login, logout, failed attempts)
- Log all data modifications (create, update, delete)
- Log all configuration changes
- Store logs in database, not just console
- **Estimated effort:** 2-3 days
- **Assigned to:** ___________

### Task 12: Fix BYOK Key Validation
**Current state:** `/providers/byok/test/{provider}` only validates format, doesn't test the key**
- Actually call the provider API with the key to verify it works
- Return specific error for invalid keys
- **Estimated effort:** 1 day
- **Assigned to:** ___________

### Task 13: Response Time Optimization (500ms → 200ms)
**MINIMAX-M2 flags this as competitive gap vs LockedIn's 116ms**
- Add Redis caching layer for frequent queries
- Async database operations
- Response compression (gzip/brotli)
- AI provider routing optimization
- Connection pooling
- **Estimated effort:** 2-3 weeks
- **Assigned to:** ___________

### Task 14: Expand Mock Interview Library (27 → 10K+)
**All analyses flag: FinalRound has 2M+, we have 27 questions**
- Generate question banks by category, company, role, difficulty
- Add question bank seeding script
- Add user-submitted questions
- Add question search/filter improvements
- **Estimated effort:** 1-2 weeks for 10K
- **Assigned to:** ___________

### Task 15: CI/CD Pipeline
**No CI/CD exists currently**
- GitHub Actions: lint, test, build on push
- Automated testing on PR
- Build Electron app for Windows/macOS/Linux
- Release automation
- **Estimated effort:** 3-4 days
- **Assigned to:** ___________

### Task 16: Integration Test Suite
**Only 3 test files exist**
- Write integration tests for all 100+ endpoints
- Write frontend E2E tests (Playwright)
- Add test coverage reporting
- Target: 80%+ coverage
- **Estimated effort:** 1-2 weeks
- **Assigned to:** ___________

---

## P2 — COMPETITIVE FEATURES (1-2 Months)

### Task 17: AI Voice Agent (MeetGeek's Differentiator)
**MINIMAX-M2 calls this "biggest competitive gap"**
- Real-time voice interaction during interviews
- Voice synthesis with interruption support
- Natural conversation flow
- Voice activity detection improvements
- **Estimated effort:** 4-6 weeks
- **Assigned to:** ___________

### Task 18: MCP Server for Claude/Cursor Integration
**GLM-5.1 analysis: Otter, Fireflies, Grain all offer MCP servers**
- Implement Model Context Protocol server
- Expose transcript, summary, and search via MCP
- Allow Claude/Cursor to query interview data
- **Estimated effort:** 2-3 weeks
- **Assigned to:** ___________

### Task 19: Chrome Extension Polish
**Current state: MVP exists**
- Content script improvements for all meeting platforms
- Better overlay UI
- Screen capture integration
- Auto-join meeting detection
- **Estimated effort:** 2-3 weeks
- **Assigned to:** ___________

### Task 20: CRM Real Integration
**Current state: Config only, no actual sync**
- HubSpot contact sync
- Salesforce lead sync
- Activity logging
- Contact matching
- **Estimated effort:** 3-4 weeks
- **Assigned to:** ___________

### Task 21: Mobile App (React Native)
**6/9 competitors have mobile apps**
- React Native app for iOS + Android
- Core features: transcription, AI chat, interview practice
- Push notifications for interview reminders
- **Estimated effort:** 6-8 weeks
- **Assigned to:** ___________

### Task 22: Multi-Language Transcription
**Fireflies supports 100+ languages, we support English only**
- Leverage existing Whisper model for multi-language
- Language auto-detection
- Speaker labels in multiple languages
- **Estimated effort:** 2-3 weeks
- **Assigned to:** ___________

### Task 23: Video Recording
**All note-taking competitors offer this**
- Screen recording alongside audio
- Camera overlay option
- Recording management (save, search, export)
- **Estimated effort:** 3-4 weeks
- **Assigned to:** ___________

### Task 24: Feature Health Dashboard
**12 feature modules silently degrade when dependencies missing**
- Add `/health/modules` endpoint showing module availability
- Frontend: show which features are available/enabled
- Clear messaging when modules require dependencies
- **Estimated effort:** 2-3 days
- **Assigned to:** ___________

---

## TASK ASSIGNMENT BY MODEL

| Task | Priority | Effort | Best Model Fit |
|------|----------|--------|---------------|
| **1. Database Migration** | P0 | 2 weeks | Full-stack (DB schema + API rewrite) |
| **2. Auth Enforcement** | P0 | 3-4 days | Backend (FastAPI middleware) |
| **3. Electron Security** | P0 | 1-2 days | Frontend (Electron) |
| **4. Encryption at Rest** | P0 | 3-4 days | Backend (crypto) |
| **5. WebSocket Auth** | P0 | 1 day | Backend (WebSocket) |
| **6. Neo4j Security** | P0 | 1 day | Backend (database) |
| **7. HTTPS Enforcement** | P0 | 1-2 days | Backend (SSL/TLS) |
| **8. Rate Limiting** | P0 | 1 day | Backend (FastAPI) |
| **9. Pagination** | P1 | 2-3 days | Backend (API) |
| **10. Error Codes** | P1 | 2-3 days | Backend (API) |
| **11. Audit Logging** | P1 | 2-3 days | Backend (database) |
| **12. BYOK Validation** | P1 | 1 day | Backend (API) |
| **13. Response Optimization** | P1 | 2-3 weeks | Full-stack (caching, async) |
| **14. Mock Library Expansion** | P1 | 1-2 weeks | Backend (data) |
| **15. CI/CD Pipeline** | P1 | 3-4 days | DevOps |
| **16. Integration Tests** | P1 | 1-2 weeks | Full-stack (testing) |
| **17. AI Voice Agent** | P2 | 4-6 weeks | Full-stack (ML + audio) |
| **18. MCP Server** | P2 | 2-3 weeks | Backend (protocol) |
| **19. Chrome Extension** | P2 | 2-3 weeks | Frontend (extension) |
| **20. CRM Integration** | P2 | 3-4 weeks | Backend (API) |
| **21. Mobile App** | P2 | 6-8 weeks | Frontend (React Native) |
| **22. Multi-Language** | P2 | 2-3 weeks | Backend (Whisper) |
| **23. Video Recording** | P2 | 3-4 weeks | Full-stack (media) |
| **24. Feature Health** | P2 | 2-3 days | Full-stack |

---

## RECOMMENDED PARALLEL TRACKS

Since you want to assign tasks across models, here's how to split work efficiently:

### Track A: Security Hardening (P0 — Week 1-2)
Tasks 2, 3, 5, 6, 7, 8 — Can all be done in parallel by different models
- **Model A:** Tasks 2 (Auth) + 5 (WebSocket Auth) + 8 (Rate Limiting)
- **Model B:** Task 3 (Electron Security)
- **Model C:** Tasks 6 (Neo4j) + 7 (HTTPS)

### Track B: Database Migration (P0 — Week 2-3)
Task 1 — This is the biggest single task, needs dedicated focus
- **Model A (dedicated):** Database migration + all related API changes

### Track C: Data Hardening (P1 — Week 3-4)
Tasks 4, 9, 10, 11, 12 — Can be done in parallel
- **Model A:** Tasks 9 (Pagination) + 10 (Error Codes)
- **Model B:** Tasks 4 (Encryption) + 11 (Audit Logging)
- **Model C:** Task 12 (BYOK) + 14 (Mock Library)

### Track D: Performance & Quality (P1 — Week 4-6)
Tasks 13, 15, 16 — Can be done in parallel
- **Model A:** Task 13 (Response Optimization)
- **Model B:** Task 15 (CI/CD)
- **Model C:** Task 16 (Integration Tests)

### Track E: Competitive Features (P2 — Week 6+)
Tasks 17-24 — Pick based on market priority
- **Highest ROI:** Task 17 (Voice Agent) — biggest competitive gap
- **Second priority:** Task 19 (Chrome Extension) — user acquisition
- **Third priority:** Task 18 (MCP Server) — ecosystem integration

---

## TOTAL EFFORT ESTIMATE

| Priority | Tasks | Total Effort |
|----------|-------|-------------|
| P0 (Security) | 8 tasks | ~3.5 weeks |
| P1 (Hardening) | 8 tasks | ~5.5 weeks |
| P2 (Features) | 8 tasks | ~22 weeks |
| **Total** | **24 tasks** | **~31 weeks (7-8 months)** |

**Minimum viable for production:** P0 tasks only = ~3.5 weeks
**Recommended for launch:** P0 + P1 = ~9 weeks
**Full competitive parity:** P0 + P1 + P2 = ~31 weeks