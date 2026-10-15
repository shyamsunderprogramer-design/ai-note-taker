# TASK ASSIGNMENT SHEETS - AI Note Taker Production
**Date:** April 8, 2026 | **Models:** KIMI-K2.5 | MINIMAX-M2 | GLM-5.1

---

## QUICK START - Do These First

| Model | Task | Description | Time |
|-------|------|-------------|------|
| MINIMAX-M2 | T9 | Fix `webSecurity: false` in electron/main.js:168 | 1 hr |
| MINIMAX-M2 | T10 | Fix `allowRunningInsecureContent: true` in electron/main.js:169 | 1 hr |
| GLM-5.1 | T23 | Fix `HTTPS_REQUIRED = False` → `True` in backend/config.py | 1 hr |
| GLM-5.1 | T2 | Fix CORS `allow_origins=["*"]` → whitelist in backend/main.py:111 | 1 hr |
| GLM-5.1 | T4 | Fix Neo4j default password "password" in backend/cognitive_graph.py | 1 hr |

---

# ============================================
# KIMI-K2.5 - TASKS (7 Tasks)
# ============================================

## Task T16 - Database Migration (PRIORITY: P0)
**Time:** 2 weeks
**Files:** backend/database.py (NEW), backend/main.py
**Description:** Replace JSON files with PostgreSQL
- Design PostgreSQL schema (users, conversations, job_applications, voice_models, analytics)
- Create SQLAlchemy models with connection pooling
- Create migration scripts (JSON → PostgreSQL)
- Add automated backup endpoints
- Test data migration

**Steps:**
1. Create backend/database.py with connection pooling
2. Define SQLAlchemy models for all entities
3. Create migration script to convert existing JSON data
4. Add backup/restore endpoints
5. Update main.py to use new database

---

## Task T17 - Encryption at Rest (PRIORITY: P0)
**Time:** 3-4 days
**Files:** backend/main.py, backend/security/
**Description:** AES-256 encryption for conversations and API keys
- Implement AES-256 encryption layer
- Encrypt conversation content before storage
- Encrypt API keys (use existing Electron encrypted store as reference)
- Encrypt voice model data

**Steps:**
1. Add cryptography library (Fernet or AES-256)
2. Create encryption utility module
3. Integrate with conversation storage
4. Add key management

**Depends on:** T16 (database first)

---

## Task T18 - Redis Caching + Response Optimization (PRIORITY: P1)
**Time:** 2-3 weeks
**Files:** backend/main.py, backend/config.py
**Description:** Optimize response time from ~500ms to <200ms
- Add Redis caching layer
- Async database operations
- AI provider routing optimization
- Response compression (gzip/brotli)
- Connection pooling (PgBouncer)

**Target:** LockedIn AI response is 116ms, we need <200ms

**Steps:**
1. Install Redis/aioredis
2. Add caching for frequent queries
3. Make database operations async
4. Add compression middleware
5. Benchmark and tune

**Depends on:** T16 (database)

---

## Task T19 - Expand Mock Interview Library (PRIORITY: P1)
**Time:** 1-2 weeks
**Files:** backend/mock_interview_library.py
**Description:** Expand from 27 questions to 10,000+
- Generate question banks by category, company, role, difficulty
- Add company-specific interview patterns
- Include system design questions
- Add behavioral question bank (STAR method)
- Create question seeding script

**Competitor:** FinalRound has 2M+, we have 27

**Steps:**
1. Define question schema (category, difficulty, company, role, type)
2. Create generation templates for each type
3. Generate 10,000+ questions
4. Add search/filter API
5. Add user-submitted questions feature

---

## Task T20 - AI Voice Agent (PRIORITY: P2)
**Time:** 4-6 weeks
**Files:** backend/voice_agent.py (NEW)
**Description:** Real-time voice interaction during interviews
- Voice synthesis with interruption support
- Natural conversation flow
- Voice activity detection improvements
- Text-to-speech integration

**Why:** MeetGeek's biggest differentiator, customers expect this

**Steps:**
1. Research voice synthesis options (Edge TTS already exists in project)
2. Design voice agent architecture
3. Implement voice activity detection
4. Add interruption handling
5. Test with real interview scenarios

---

## Task T21 - MCP Server (PRIORITY: P2)
**Time:** 2-3 weeks
**Files:** backend/mcp_server.py (NEW)
**Description:** Model Context Protocol for Claude/Cursor integration
- Implement MCP server
- Expose transcript, summary, search via MCP
- Allow Claude/Cursor to query interview data
- Document MCP endpoints

**Why:** Otter, Fireflies, Grain all offer MCP servers

**Steps:**
1. Study MCP protocol specification
2. Create MCP server implementation
3. Expose relevant endpoints (transcripts, summaries, search)
4. Add authentication
5. Test with Claude/Cursor

---

## Task T22 - CRM Real Integration (PRIORITY: P2)
**Time:** 3-4 weeks
**Files:** backend/crm_integration.py
**Description:** HubSpot/Salesforce real sync (not just config)
- HubSpot contact sync (create/update contacts)
- Salesforce lead sync
- Activity logging
- Contact matching by email

**Why:** Competitors have this, enterprise customers need it

**Steps:**
1. Add HubSpot API integration
2. Add Salesforce API integration
3. Create sync scheduler
4. Add conflict resolution
5. Add activity logging

---

# ============================================
# MINIMAX-M2 - TASKS (7 Tasks)
# ============================================

## Task T9 - Fix webSecurity (PRIORITY: P0)
**Time:** 1-2 days
**Files:** electron/main.js:168
**Description:** Remove `webSecurity: false`
- Change to `webSecurity: true`
- Test all features still work
- Verify no CORS issues

**Code:** Line 168 - change `webSecurity: false` to `webSecurity: true`

---

## Task T10 - Fix allowRunningInsecureContent (PRIORITY: P0)
**Time:** 1 day
**Files:** electron/main.js:169
**Description:** Set to false
- Change `allowRunningInsecureContent: true` to `false`

**Code:** Line 169 - change `allowRunningInsecureContent: true` to `allowRunningInsecureContent: false`

---

## Task T11 - CSP Nonce-Based (PRIORITY: P0)
**Time:** 1 day
**Files:** electron/main.js
**Description:** Remove unsafe-inline from CSP
- Implement nonce-based CSP
- Remove `unsafe-inline` for scripts and styles
- Generate nonce per request

**Steps:**
1. Generate cryptographically secure nonce per request
2. Add nonce to script/style tags
3. Update CSP header to use 'nonce-{nonce}'
4. Remove unsafe-inline from policy

---

## Task T12 - Chrome Extension Polish (PRIORITY: P1)
**Time:** 2-3 weeks
**Files:** chrome-extension/
**Description:** Improve Chrome extension from MVP to production
- Content script improvements for meeting platforms
- Better overlay UI
- Screen capture integration
- Auto-join meeting detection
- Better icon/manifest

**Competitor:** MeetGeek has 7,000+ integrations

**Steps:**
1. Test on all major meeting platforms (Zoom, Teams, Meet)
2. Improve overlay UI/design
3. Add screen capture functionality
4. Add auto-detection of meeting URLs
5. Polish manifest and icons

---

## Task T13 - Feature Health Dashboard (PRIORITY: P1)
**Time:** 2-3 days
**Files:** renderer/app.js
**Description:** Show which features are available/enabled
- Add /health/modules endpoint (backend)
- Frontend shows module status (green/yellow/red)
- Clear messaging when modules require dependencies

**Why:** 12 feature modules silently degrade when dependencies missing

**Steps:**
1. Create /health/modules endpoint listing all modules
2. Add frontend UI showing module status
3. Add "Configure" buttons for missing dependencies
4. Test graceful degradation display

---

## Task T14 - CI/CD Pipeline (PRIORITY: P2)
**Time:** 3-4 days
**Files:** .github/workflows/
**Description:** GitHub Actions for lint, test, build, deploy
- Lint on push
- Run tests on PR
- Build Electron app for Windows/macOS/Linux
- Release automation with tags

**Steps:**
1. Create .github/workflows/ci.yml
2. Add lint step (ESLint, flake8)
3. Add test step (pytest, playwright)
4. Add build step (electron-builder)
5. Add release step on tag

---

## Task T15 - Integration Test Suite (PRIORITY: P2)
**Time:** 1-2 weeks
**Files:** backend/tests/
**Description:** Expand from 3 test files to full coverage
- Write integration tests for all 100+ endpoints
- Add frontend E2E tests (Playwright)
- Add test coverage reporting
- Target: 80%+ coverage

**Current:** Only 75 unit tests exist, no integration tests

**Steps:**
1. Map all 100+ endpoints
2. Write integration tests for each
3. Add Playwright E2E tests
4. Set up coverage reporting (coverage.py)
5. Run and fix failures

---

# ============================================
# GLM-5.1 - TASKS (10 Tasks)
# ============================================

## Task T1 - Auth Enforcement (PRIORITY: P0)
**Time:** 3-4 days
**Files:** backend/main.py
**Description:** Enforce JWT auth on all sensitive endpoints
- Add `require_authentication` to all sensitive endpoints
- Current state: JWT exists but only ~5 endpoints use it
- Add refresh token support
- Rate limiting on auth endpoints (register/login)

**100+ endpoints need review - focus on sensitive ones first**

**Steps:**
1. List all sensitive endpoints (user data, conversations, settings)
2. Add require_authentication dependency to each
3. Add refresh token endpoint
4. Rate limit auth endpoints (5 req/min)
5. Test all endpoints with auth token

---

## Task T2 - CORS Whitelist (PRIORITY: P0)
**Time:** 1 day
**Files:** backend/main.py:111
**Description:** Remove allow_origins=["*"]
- Change to specific allowed origins
- For dev: localhost:3000, localhost:8000
- For prod: your production domain

**Code:** Line 111 - change `allow_origins=["*"]` to `allow_origins=["http://localhost:3000", "http://localhost:8000"]`

---

## Task T3 - WebSocket Auth (PRIORITY: P0)
**Time:** 1 day
**Files:** backend/main.py (WebSocket handlers)
**Description:** Add token validation to WebSocket connect
- Validate JWT token on WebSocket connection
- Reject unauthenticated connections
- Pass user info to WebSocket handler

**Endpoints:** /ws, /ws/transcribe

**Steps:**
1. Create WebSocket auth middleware
2. Validate token on connection
3. Reject with 401 if invalid
4. Pass user info to handler

---

## Task T4 - Neo4j Password (PRIORITY: P0)
**Time:** 1 day
**Files:** backend/cognitive_graph.py
**Description:** Fix default password "password"
- Require strong password for Neo4j
- Enable authentication
- Add connection validation

**Current:** auth disabled, password = "password"

---

## Task T5 - Pagination (PRIORITY: P1)
**Time:** 2-3 days
**Files:** backend/main.py
**Description:** Add limit/offset to all list endpoints
- conversations, job_applications, voice_models, documents, analytics, mock_questions, study_plans
- Return total count with results

**Endpoints to update:** /conversations, /jobs, /voices, /documents, /analytics, /questions, /plans

**Steps:**
1. Add limit/offset query params to each list endpoint
2. Return {"data": [...], "total": N, "limit": X, "offset": Y}
3. Add max limit (1000)
4. Test all endpoints

---

## Task T6 - Structured Error Codes (PRIORITY: P1)
**Time:** 2-3 days
**Files:** backend/main.py
**Description:** Standardize error response format
- Current: {"error": "message string"}
- New: {"error": {"code": "ERROR_CODE", "message": "...", "status": 400}}

**Steps:**
1. Define error code constants
2. Create error response helper
3. Migrate all endpoints to new format
4. Document error codes

---

## Task T7 - Audit Logging (PRIORITY: P1)
**Time:** 2-3 days
**Files:** backend/main.py
**Description:** Log all security-relevant operations
- Log auth events (login, logout, failed attempts)
- Log data modifications (create, update, delete)
- Log configuration changes
- Store in database, not just console

**Why:** Required for enterprise/compliance

**Steps:**
1. Create audit_log table in database
2. Create audit logging middleware
3. Log all sensitive operations
4. Add admin audit dashboard endpoint

---

## Task T8 - BYOK Validation Fix (PRIORITY: P1)
**Time:** 1 day
**Files:** backend/main.py
**Description:** Actually test API keys, not just format
- /providers/byok/test/{provider} only validates format now
- Actually call provider API with the key
- Return specific error for invalid keys

**Steps:**
1. Make actual API call to provider
2. Return success/failure with details
3. Handle rate limiting from providers

---

## Task T23 - HTTPS Enforcement (PRIORITY: P0)
**Time:** 1 day
**Files:** backend/config.py
**Description:** Change HTTPS_REQUIRED to True
- Current: HTTPS_REQUIRED = False
- Change to: HTTPS_REQUIRED = True
- Add HSTS header

---

## Task T24 - Rate Limiting All Endpoints (PRIORITY: P1)
**Time:** 1 day
**Files:** backend/main.py
**Description:** Extend @rate_limit to all endpoints
- Currently only 3 endpoints have rate limits
- Add to all public endpoints
- Different limits for auth vs authenticated

**Steps:**
1. Add @rate_limit decorator to all endpoints
2. Set limits: 100/min authenticated, 20/min unauthenticated
3. Add rate limit headers to responses

---

# ============================================
# VERIFICATION CHECKLIST
# ============================================

After completing each task, verify:
- [ ] Code builds without errors
- [ ] Existing tests still pass
- [ ] No new security vulnerabilities
- [ ] Changes documented in code comments

---

# ============================================
# DEPENDENCY CHAIN
# ============================================

```
T16 (DB) → T17 (Encryption) → T18 (Redis)
                     ↓
              T20 (Voice Agent can use T18)

T1 (Auth) → T3 (WebSocket Auth)
   ↓
T5-T8, T24 (API hardening)

T9-T10-T11 (Electron security - can do in parallel)
T12 (Chrome extension - depends on T9-T11)
T13 (Feature health - can do anytime)
T14-T15 (CI/CD, Tests - do last)
```

---

*Generated: April 8, 2026*
*Models: KIMI-K2.5 | MINIMAX-M2 | GLM-5.1*