# GLM-5.1 Task Assignment — Backend Security & API Hardening
**Date:** April 9, 2026 | **Model:** GLM-5.1 | **Tasks:** 10 | **Effort:** ~4-5 weeks

---

## START HERE — Quick Wins (Do These First, ~2 hours total)

### T2: CORS Whitelist (P0) — 1 hour
**File:** `backend/main.py:140`
**Current:** `CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "true").lower() == "true"`
**Change to:** `CORS_ALLOW_ALL = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"`
**Why:** Default should be secure (whitelist), devs can opt-in to `["*"]` via env var

### T23: HTTPS Enforcement (P0) — 1 hour
**File:** `backend/main.py:58`
**Current:** `HTTPS_REQUIRED = os.getenv("HTTPS_REQUIRED", "false").lower() == "true"`
**Change to:** `HTTPS_REQUIRED = os.getenv("HTTPS_REQUIRED", "true").lower() == "true"`
**Also verify:** The HTTPS middleware at line 248-268 works correctly when enabled
**Why:** Production must enforce HTTPS by default

---

## MEDIUM PRIORITY — Auth & Security (Week 1)

### T1: Auth Enforcement on All Endpoints (P0) — 2-3 days
**File:** `backend/main.py:297`
**Current:** `AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"`
**Change to:** `AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"`

**Then audit all 157 endpoints:**
1. Search for all `@app.get`, `@app.post`, `@app.put`, `@app.delete`, `@app.patch` in main.py
2. Add `Depends(require_auth)` to any endpoint that touches user data:
   - All `/conversations/*` endpoints
   - All `/job-tracker/*` endpoints
   - All `/voice-clone/*` endpoints
   - All `/documents/*` endpoints
   - All `/analytics/*` endpoints
   - All `/cognitive-graph/*` endpoints
   - All `/study-plan/*` endpoints
   - All `/mock-interview/*` endpoints (except question listing)
   - All `/settings/*` endpoints
   - All `/user-api-keys/*` endpoints
3. Keep these public (no auth required):
   - `/`, `/health`, `/auth/login`, `/auth/register`, `/docs`, `/openapi.json`, `/redoc`
   - `/providers` (listing available providers)
   - `/voice-clone/audio/{filename}` (audio playback)

**Steps:**
1. Flip default to `true`
2. Test app still works with valid JWT token
3. Add `Depends(require_auth)` to ~50 sensitive endpoints
4. Verify public endpoints still work without token
5. Test that protected endpoints return 401 without token

---

### T3: WebSocket Auth — Remove Gate (P0) — 2-3 hours
**Files:** `backend/main.py` (WebSocket handlers for `/ws` and `/ws/transcribe`)

**Current behavior:** Token validation code exists at lines ~1901-1914 and ~2255-2268, but it's gated by:
```python
if AUTH_REQUIRED:
    # validate token...
```

**Change:** Remove the `if AUTH_REQUIRED:` gate. WebSocket auth should ALWAYS be enforced, regardless of `AUTH_REQUIRED` setting. An unauthenticated WebSocket is a security hole.

**Steps:**
1. Find `if AUTH_REQUIRED:` in both WebSocket handlers
2. Remove the condition — always validate tokens on WebSocket connect
3. Keep the same rejection logic (close with code 4001 if invalid)
4. Test WebSocket connection with and without valid token

---

### T25: Fix Electron CSP `connect-src` (P1) — 2-3 hours
**File:** `electron/main.js:973,977`

**Current issues:**
1. Line 973: CSP has `connect-src *` — allows connections to ANY origin
2. Line 977: `headers["Access-Control-Allow-Origin"] = ["*"]` — overrides backend CORS

**Fix CSP:**
```
connect-src 'self' ws://localhost:* http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:*
```

**Fix CORS override (line 977):**
```javascript
// Remove this line entirely — let the backend handle CORS
// headers["Access-Control-Allow-Origin"] = ["*"]
```

**Also fix** `img-src` and `media-src` to remove `http:` (should be `https:` only):
```
img-src 'self' data: blob: https:;
media-src 'self' mediastream: blob: https:;
```

---

## P1 TASKS — API Hardening (Week 2-3)

### T5: Add Pagination to Remaining List Endpoints (P1) — 2-3 days
**File:** `backend/main.py`

**Already have pagination (5 endpoints):**
- `/documents` (line ~1730)
- `/job-tracker/applications` (line ~3436)
- `/mock-interview/questions` (line ~4257)
- `/voice-clone/models` (line ~4448)
- `/meeting-templates` (line ~4899)

**Need pagination (~10 endpoints):**
- `/conversations` — conversation listing
- `/conversations/{id}/messages` — message listing
- `/analytics/*` — analytics data endpoints
- `/cognitive-graph/entities` — entity listing
- `/cognitive-graph/relationships` — relationship listing
- `/study-plan/{plan_id}/sessions` — study sessions
- `/mock-interview/practice-sets` — practice set listing
- `/job-tracker/search` — job search results
- `/collaboration/sessions` — collaboration sessions
- `/user-api-keys/status` — if it returns a list

**Pattern to follow:**
```python
@app.get("/endpoint")
async def list_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ...
):
    # Return {"data": [...], "total": N, "limit": limit, "offset": offset}
```

---

### T6: Adopt Structured Error Codes (P1) — 2-3 days
**File:** `backend/main.py` + `backend/security/errors.py`

**Current state:** `security/errors.py` defines `ErrorCode` enum and `APIError` class, but most endpoints still return `{"error": "message string"}`

**Steps:**
1. Search for all `JSONResponse(status_code=4xx, content={"error": ...})` in main.py
2. Replace with `raise APIError(ErrorCode.ERROR_CODE, "message", status_code=4xx)`
3. Common error codes to use:
   - `AUTH_REQUIRED` (401)
   - `FORBIDDEN` (403)
   - `NOT_FOUND` (404)
   - `VALIDATION_ERROR` (422)
   - `RATE_LIMIT_EXCEEDED` (429)
   - `PROVIDER_ERROR` (502)
   - `CONFLICT` (409)
4. Add a global exception handler for `APIError`:
```python
@app.exception_handler(APIError)
async def api_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
```

---

### T7: Migrate Audit Logging to Database (P1) — 1-2 days
**File:** `backend/main.py` + `backend/security/audit.py`

**Current:** Audit events stored in JSONL file (`audit.log.jsonl`)
**Target:** Store audit events in database (use existing `AuditLogRepository` from `database.py`)

**Steps:**
1. Check `database.py` for `AuditLogRepository` — it should already exist
2. Update `security/audit.py` to write to database instead of/in addition to JSONL
3. Add database fallback: if DB unavailable, write to JSONL file
4. Keep the existing `get_audit_log()` and `get_audit_stats()` endpoints working

---

### T24: Add Per-Endpoint Rate Limit Decorators (P1) — 1 day
**File:** `backend/main.py`

**Current:** Global rate limiting middleware covers all HTTP endpoints with 3 tiers
**Add:** Per-endpoint `@rate_limit()` decorators for finer control

**Steps:**
1. Add `@rate_limit("30/minute")` to expensive endpoints:
   - `/ask-with-image`
   - `/voice-clone/create`
   - `/voice-clone/create-rvc`
2. Add `@rate_limit("60/minute")` to moderate endpoints:
   - `/conversations` (POST)
   - `/documents` (POST/upload)
   - `/transcribe-cloud`
3. Add `@rate_limit("5/minute")` to auth endpoints:
   - `/auth/login`
   - `/auth/register`
4. Keep global middleware as safety net

---

### T8: BYOK Key Validation Fix (P1) — 1 day
**File:** `backend/main.py` — look for `/providers/byok/test/{provider}` endpoint

**Current:** Only validates format, doesn't actually test the key
**Fix:** Make a real API call to the provider with the user's key

**Steps:**
1. For each provider (openai, anthropic, google, etc.), add a test call:
   - OpenAI: `GET https://api.openai.com/v1/models` with Authorization header
   - Anthropic: `POST https://api.anthropic.com/v1/messages` with minimal request
   - Google: Use discovery API to verify key
2. Return `{"valid": true, "provider": "openai", "models_available": N}` on success
3. Return `{"valid": false, "error": "Invalid API key", "provider": "openai"}` on failure
4. Add timeout (5 seconds) and error handling

---

## VERIFICATION CHECKLIST

After each task:
- [ ] Run `python -m pytest backend/tests/` (existing tests)
- [ ] Run `python backend/main.py` and verify app starts
- [ ] Check `/health` endpoint still works
- [ ] Verify no import errors

---

## TASK ORDER

```
1. T2 (CORS) + T23 (HTTPS) — 2 hours ← START HERE
2. T3 (WebSocket auth gate removal) — 2-3 hours
3. T25 (Electron CSP fix) — 2-3 hours
4. T1 (Auth enforcement + flip default) — 2-3 days
5. T5 (Pagination remaining endpoints) — 2-3 days
6. T6 (Structured error codes) — 2-3 days
7. T24 (Per-endpoint rate limits) — 1 day
8. T7 (Audit logging to DB) — 1-2 days
9. T8 (BYOK validation) — 1 day
```

**Total: ~4-5 weeks** | **Critical path: T1 (auth) blocks most other work**