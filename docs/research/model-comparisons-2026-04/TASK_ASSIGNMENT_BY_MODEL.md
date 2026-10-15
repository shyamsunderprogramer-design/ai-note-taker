# AI Note Taker - Production Tasks by Model
**Date:** April 8, 2026
**Goal:** Divide 24 prioritized tasks across 3 AI models for parallel execution
**Models:** KIMI-K2.5 | MINIMAX-M2 | GLM-5.1

---

## CURRENT STATUS

### ✅ ALREADY COMPLETED
- Security P0: HTTPS/TLS, JWT auth, rate limiting (30-100 req/min), input validation, XSS protection
- Security headers middleware
- Basic monitoring setup

### 🔴 CRITICAL GAPS REMAINING (P0)

| # | Task | Status | Effort | Model |
|---|------|--------|--------|-------|
| 1 | Database JSON → PostgreSQL | ❌ NOT DONE | 2 weeks | KIMI-K2.5 |
| 2 | Auth not enforced on most endpoints | ❌ NOT DONE | 3-4 days | GLM-5.1 |
| 3 | CORS allow_origins=["*"] | ❌ NOT DONE | 1 day | GLM-5.1 |
| 4 | webSecurity: false in Electron | ❌ NOT DONE | 1-2 days | MINIMAX-M2 |
| 5 | allowRunningInsecureContent: true | ❌ NOT DONE | 1 day | MINIMAX-M2 |
| 6 | CSP allows unsafe-inline | ❌ NOT DONE | 1 day | MINIMAX-M2 |
| 7 | WebSocket endpoints no auth | ❌ NOT DONE | 1 day | GLM-5.1 |
| 8 | Neo4j default password | ❌ NOT DONE | 1 day | GLM-5.1 |
| 9 | No encryption at rest | ❌ NOT DONE | 3-4 days | KIMI-K2.5 |
| 10 | No pagination on list endpoints | ❌ NOT DONE | 2-3 days | GLM-5.1 |

---

## TASK ASSIGNMENT BY MODEL

### 📋 KIMI-K2.5 (Database / Full-Stack / Complex Features)
**Best for:** PostgreSQL migration, encryption, AI Voice Agent, MCP server

| Task | Priority | Description | Files to Modify |
|------|----------|-------------|-----------------|
| **T16** | P0 | Database migration JSON → PostgreSQL | backend/database.py (new) |
| **T17** | P0 | Encryption at rest (AES-256) | backend/main.py |
| **T18** | P1 | Redis caching + response optimization (500ms → 200ms) | backend/main.py, config.py |
| **T19** | P1 | Expand mock interview library (27 → 10K+) | backend/mock_interview_library.py |
| **T20** | P2 | AI Voice Agent (MeetGeek's differentiator) | backend/voice_agent.py (new) |
| **T21** | P2 | MCP server for Claude/Cursor integration | backend/mcp_server.py (new) |
| **T22** | P2 | CRM real integration (HubSpot/Salesforce sync) | backend/crm_integration.py |

**Start with:** T16 (database migration - biggest task, longest lead time)
**Then:** T17 (encryption) → T18 (Redis)

---

### 📋 MINIMAX-M2 (Frontend / Electron / UI / Testing)
**Best for:** Electron security fixes, Chrome extension, CI/CD, tests

| Task | Priority | Description | Files to Modify |
|------|----------|-------------|-----------------|
| **T9** | P0 | Fix webSecurity: false | electron/main.js:168 |
| **T10** | P0 | Fix allowRunningInsecureContent: true | electron/main.js:169 |
| **T11** | P0 | CSP nonce-based (remove unsafe-inline) | electron/main.js |
| **T12** | P1 | Chrome extension polish | chrome-extension/ |
| **T13** | P1 | Feature health dashboard UI | renderer/app.js |
| **T14** | P2 | CI/CD pipeline (GitHub Actions) | .github/workflows/ |
| **T15** | P2 | Integration test suite | backend/tests/ |

**Start with:** T9, T10, T11 (Electron security - quick wins)
**Then:** T12 (Chrome extension)

---

### 📋 GLM-5.1 (Backend / Security / API Hardening)
**Best for:** Authentication, rate limiting, API security, validation

| Task | Priority | Description | Files to Modify |
|------|----------|-------------|-----------------|
| **T1** | P0 | Auth enforcement on all endpoints | backend/main.py |
| **T2** | P0 | CORS whitelist (remove allow_origins=["*"]) | backend/main.py:111 |
| **T3** | P0 | WebSocket auth (token validation on connect) | backend/main.py (WebSocket handler) |
| **T4** | P0 | Neo4j password fix (default "password") | backend/cognitive_graph.py |
| **T5** | P1 | Pagination on all list endpoints | backend/main.py (100+ endpoints) |
| **T6** | P1 | Structured error codes (all return {"error": {...}}) | backend/main.py |
| **T7** | P1 | Audit logging (auth events, data modifications) | backend/main.py |
| **T8** | P1 | BYOK key validation fix (actually test API keys) | backend/main.py |
| **T23** | P0 | Fix HTTPS_REQUIRED = False → True | backend/config.py |
| **T24** | P1 | Rate limiting on ALL endpoints (not just 3) | backend/main.py (add @rate_limit to all) |

**Start with:** T23 (quick fix) → T2, T4 (quick wins)
**Then:** T1 (auth enforcement - most critical)
**Then:** T3, T5, T6, T7, T8, T24

---

## QUICK WIN TASKS (~1 day each)

| Task | Description | Model | Notes |
|------|-------------|-------|-------|
| T23 | HTTPS_REQUIRED = False → True | GLM-5.1 | Config change |
| T4 | Neo4j default password fix | GLM-5.1 | 1 line change |
| T2 | CORS whitelist fix | GLM-5.1 | Remove ["*"] |
| T9 | webSecurity: false | MINIMAX-M2 | 1 line change |
| T10 | allowRunningInsecureContent: true | MINIMAX-M2 | 1 line change |
| T11 | CSP unsafe-inline removal | MINIMAX-M2 | Needs nonce implementation |

---

## EXECUTION ORDER (Parallel Tracks)

### Track 1: Security Hardening (Week 1-2)
**Focus:** Fix critical security gaps in parallel

```
GLM-5.1:
  - T23 (quick) → T2 → T4 → T1 (auth) → T3 (WebSocket) → T5-T8 → T24

MINIMAX-M2:
  - T9 → T10 → T11 (Electron security) → T12 (Chrome extension)

KIMI-K2.5:
  - Start T16 (database design/schema) immediately
```

### Track 2: Database & Performance (Week 2-3)
**Focus:** KIMI-K2.5 on DB migration, GLM-5.1 on API hardening

```
KIMI-K2.5:
  - Continue T16 (migration scripts)
  - T17 (encryption)
  - T18 (Redis caching)

GLM-5.1:
  - Finish T5-T8
  - T24 (rate limiting everywhere)
```

### Track 3: Feature Development (Week 3-6)
**Focus:** Competitive features to close gaps

```
KIMI-K2.5:
  - T19 (mock library 27 → 10K+)
  - T20 (AI Voice Agent - biggest gap)
  - T21 (MCP server)
  - T22 (CRM integration)

MINIMAX-M2:
  - T13 (feature health UI)
  - T14 (CI/CD)
  - T15 (integration tests)
```

---

## TOTAL EFFORT BY MODEL

| Model | Tasks | Total Effort |
|-------|-------|-------------|
| **KIMI-K2.5** | T16-T22 (7 tasks) | ~10-12 weeks |
| **MINIMAX-M2** | T9-T15 (7 tasks) | ~6-8 weeks |
| **GLM-5.1** | T1-T8, T23-T24 (10 tasks) | ~4-5 weeks |

---

## MILESTONES

| Week | Milestone | Tasks Complete |
|------|-----------|----------------|
| **1** | Security P0 fixed | T1-T4, T9-T11, T23 = 10 tasks |
| **2** | API hardened | T5-T8, T24 = 5 tasks |
| **4** | Database migrated | T16-T18 = 3 tasks |
| **6** | Feature parity | T19-T22 = 4 tasks |
| **8** | Production ready | T12-T15, all testing = 4 tasks |

**Minimum Viable Production:** Week 4 (T1-T18 complete)
**Full Production:** Week 8 (all 24 tasks)

---

## FILE OWNERSHIP

| Directory | Primary Model | Notes |
|-----------|--------------|-------|
| backend/main.py | GLM-5.1 | Auth, rate limiting, error codes |
| backend/security/ | GLM-5.1 | Middleware, validation |
| backend/database.py | KIMI-K2.5 | New PostgreSQL integration |
| backend/mock_interview_library.py | KIMI-K2.5 | Question bank expansion |
| backend/voice_agent.py | KIMI-K2.5 | New AI Voice Agent |
| backend/crm_integration.py | KIMI-K2.5 | Real CRM sync |
| electron/main.js | MINIMAX-M2 | Security fixes |
| renderer/app.js | MINIMAX-M2 | UI improvements |
| chrome-extension/ | MINIMAX-M2 | Extension polish |
| .github/workflows/ | MINIMAX-M2 | CI/CD pipeline |
| backend/tests/ | MINIMAX-M2 | Integration tests |

---

## VERIFICATION CHECKLIST

After each task completed, verify:
- [ ] Code builds without errors
- [ ] Existing tests still pass
- [ ] No new security vulnerabilities
- [ ] Changes documented

---

## HOW TO USE THIS DOCUMENT

1. **Copy task list** to each model's workspace
2. **Model starts** with their first task (quick wins first)
3. **Weekly sync** - report progress, blockers
4. **Dependency check** - T16 (DB) blocks T17-T18, so start early
5. **Test after each phase** - run full suite before moving on

---

*Document created: April 8, 2026*
*Models assigned: KIMI-K2.5 | MINIMAX-M2 | GLM-5.1*