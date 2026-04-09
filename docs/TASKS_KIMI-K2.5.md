# KIMI-K2.5 Task Assignment — Database & Complex Features
**Date:** April 9, 2026 | **Model:** KIMI-K2.5 | **Tasks:** 7 | **Effort:** ~10-12 weeks

---

## CRITICAL — Start Immediately (Week 1-3)

### T16: Complete Database Migration (P0) — 1-2 weeks
**Primary File:** `backend/database.py` (already exists, ~52KB)
**Secondary Files:** `backend/main.py`, `backend/requirements.txt`

**Current State:**
- SQLAlchemy models defined for: User, Conversation, VoiceModel, JobApplication, Document, Analytics, AuditLog
- 7 repository classes exist (UserRepository, ConversationRepository, etc.)
- Default is SQLite (`USE_SQLITE=true`)
- JSON fallback exists if SQLAlchemy import fails
- `DataMigrator` class exists for JSON → SQL migration
- PostgreSQL URL configured but not default

**What Still Needs Doing:**

1. **Make PostgreSQL the production default:**
   - Change `USE_SQLITE` default to `"false"` for production
   - Add env var `DATABASE_URL` that overrides everything
   - Keep SQLite as dev fallback

2. **Harden the migration path:**
   - Test `DataMigrator` end-to-end with real JSON data
   - Add `--migrate` CLI command to main.py
   - Add migration status tracking (don't re-migrate already-migrated data)
   - Add rollback capability

3. **Integrate repositories into main.py endpoints:**
   - Currently many endpoints still write to JSON directly
   - Replace all `save_json()`, `load_json()` calls with repository methods
   - Focus on these endpoint groups first:
     - `/conversations/*` → `ConversationRepository`
     - `/job-tracker/*` → `JobApplicationRepository`
     - `/voice-clone/models` → `VoiceModelRepository`
     - `/documents/*` → `DocumentRepository`
     - `/analytics/*` → `AnalyticsRepository`
     - `/auth/*` → `UserRepository`

4. **Add backup/restore via BackupManager:**
   - `BackupManager` class exists but needs testing
   - Verify automated backup endpoint works
   - Add scheduled backup (daily at 3am)
   - Test restore from backup

5. **Remove JSON fallback:**
   - After integration, make database REQUIRED (not optional)
   - Remove the `try/except ImportError` around database import
   - Add clear error message if database module unavailable

6. **Add database connection health check:**
   - Enhance `/health` endpoint to show DB status
   - Add connection pool stats
   - Add migration version tracking

**Steps in order:**
1. Read current `database.py` thoroughly
2. Test existing migration with sample data
3. Start replacing JSON calls in main.py with repository calls (one endpoint group at a time)
4. Test each group after replacement
5. Make PostgreSQL default for production
6. Add --migrate CLI flag
7. Remove JSON fallback

---

### T17: Encryption at Rest (P0) — 3-4 days
**Files:** `backend/database.py`, `backend/security/` (new module), `backend/main.py`

**Current State:**
- Database columns named `*_encrypted` exist but store PLAINTEXT
- `user_api_keys.py` saves API keys as plain JSON
- Electron has AES-256-CBC for file export (lines 763-820) — use as reference

**What to Implement:**

1. **Create `backend/security/encryption.py`:**
   ```python
   from cryptography.fernet import Fernet
   import os
   import base64

   class EncryptionManager:
       def __init__(self):
           key = os.getenv("ENCRYPTION_KEY") or self._generate_key()
           self.fernet = Fernet(key)

       def encrypt(self, plaintext: str) -> str:
           return self.fernet.encrypt(plaintext.encode()).decode()

       def decrypt(self, ciphertext: str) -> str:
           return self.fernet.decrypt(ciphertext.encode()).decode()

       def _generate_key(self) -> str:
           key = Fernet.generate_key().decode()
           logger.warning(f"[Encryption] Generated new key. Set ENCRYPTION_KEY env var for persistence!")
           return key
   ```

2. **Encrypt API keys in database:**
   - When saving API keys via `UserRepository`, encrypt values before storing
   - When reading API keys, decrypt after fetching
   - Update `user_api_keys.py` to use EncryptionManager instead of plain JSON

3. **Encrypt conversation content:**
   - Add encryption to `ConversationRepository.save()`
   - Decrypt in `ConversationRepository.get()`
   - Search functionality must decrypt-then-search (or use encrypted search index)

4. **Key management:**
   - `ENCRYPTION_KEY` env var for production (MUST be set)
   - Auto-generate for development (with warning)
   - Add key rotation support (decrypt with old key, re-encrypt with new key)

5. **Add encryption status to `/health`:**
   - Show whether encryption is active
   - Show key age (warn if key hasn't been rotated in 90 days)

**Depends on:** T16 (database must be working first)

---

### T18: Redis Caching + Response Optimization (P1) — 2-3 weeks
**Files:** `backend/main.py`, `backend/config.py`, `backend/cache.py` (new)

**Target:** Response time from ~500ms to <200ms (LockedIn AI is 116ms)

**What to Implement:**

1. **Create `backend/cache.py`:**
   ```python
   import redis.asyncio as aioredis
   import json
   import os

   class CacheManager:
       def __init__(self):
           redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
           self.redis = aioredis.from_url(redis_url)
           self.default_ttl = int(os.getenv("CACHE_TTL", "300"))  # 5 min

       async def get(self, key: str) -> Optional[dict]:
           data = await self.redis.get(key)
           return json.loads(data) if data else None

       async def set(self, key: str, value: dict, ttl: int = None):
           await self.redis.setex(key, ttl or self.default_ttl, json.dumps(value))

       async def invalidate(self, pattern: str):
           keys = await self.redis.keys(pattern)
           if keys:
               await self.redis.delete(*keys)
   ```

2. **Cache these expensive operations:**
   - AI provider list (`/providers`) — cache 10 min
   - Conversation list (`/conversations`) — cache 2 min, invalidate on new message
   - Mock interview questions (`/mock-interview/questions`) — cache 30 min
   - Analytics aggregations — cache 5 min
   - User settings — cache 5 min, invalidate on update
   - Cognitive graph queries — cache 2 min

3. **Async database operations:**
   - All repository methods should use `async`/`await`
   - Add connection pooling (already in database.py, verify it's used)

4. **Response compression:**
   - Add GZip middleware to FastAPI:
   ```python
   from fastapi.middleware.gzip import GZipMiddleware
   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

5. **AI provider routing optimization:**
   - Pre-warm connections to AI providers on startup
   - Use HTTP/2 keep-alive for provider connections
   - Add circuit breaker for failing providers (fail fast, don't wait 30s)

6. **Benchmark:**
   - Before: Measure current response times for key endpoints
   - After: Verify <200ms for cached endpoints
   - Add `/health/performance` endpoint with timing stats

**Depends on:** T16 (database), T17 (encryption — cache must not store plaintext)

**Add to requirements.txt:**
```
redis>=5.0.0
aioredis>=2.0.0
```

---

## P1 — Feature Expansion (Week 3-5)

### T14: Expand Mock Interview Library (P1) — 1-2 weeks
**File:** `backend/mock_interview_library.py`

**Current:** 27 questions across 3 roles (Software Engineer, Frontend, Data Engineer) + 5 companies
**Target:** 10,000+ questions across 20+ roles, 50+ companies, all difficulties

**Categories to add:**
1. **Roles (20+):** SWE, Frontend, Backend, Full-stack, Data Engineer, Data Scientist, ML Engineer, DevOps, SRE, PM, TPM, Design, QA, Security, Cloud Architect, Mobile (iOS/Android), Embedded, Blockchain, Game Dev, Database Admin
2. **Companies (50+):** FAANG + Microsoft, Netflix, Uber, Airbnb, Stripe, Spotify, Twitter/X, Snapchat, Pinterest, Salesforce, Oracle, IBM, Intel, AMD, NVIDIA, Tesla, SpaceX, Palantir, Databricks, Snowflake, Coinbase, Binance, etc.
3. **Question types:** Behavioral (STAR), Technical, System Design, Coding, Case Study, Leadership, Culture Fit, Salary Negotiation
4. **Difficulties:** Entry, Junior, Mid, Senior, Staff, Principal

**Approach — Template-based generation:**
```python
# Don't hand-write 10K questions. Use templates:
BEHAVIORAL_TEMPLATES = [
    "Tell me about a time when you {action} at {company_context}",
    "Describe a situation where you had to {challenge} with {constraint}",
    ...
]

# Generate variants programmatically
for role in ROLES:
    for difficulty in DIFFICULTIES:
        for template in TEMPLATES:
            questions.append(generate_question(template, role, difficulty))
```

**Also add:**
- Company-specific question patterns (Amazon LP questions, Google sys design, etc.)
- Question search/filter with text matching
- User-submitted questions feature (with moderation)
- Practice set generator (random subset by role/difficulty)

---

## P2 — Competitive Features (Week 5+)

### T20: AI Voice Agent (P2) — 4-6 weeks
**File:** `backend/voice_agent.py` (NEW)

**This is the BIGGEST competitive gap** — MeetGeek has it, nobody else does

**Architecture:**
1. Voice Activity Detection (VAD) — detect when interviewer is speaking
2. Real-time speech-to-text — transcribe interviewer's question
3. AI response generation — generate answer using existing AI router
4. Text-to-speech — use existing Edge TTS to speak the answer
5. Interruption handling — stop speaking when interviewer talks again

**Implementation plan:**
1. Research WebRTC VAD for Python (already have audio processing)
2. Design voice agent state machine (listening → thinking → speaking → interrupted)
3. Integrate with existing `/ws/transcribe` WebSocket
4. Add TTS streaming (chunked audio for low latency)
5. Add configuration UI (voice selection, speed, volume)
6. Test with mock interview scenarios

**Why this matters:** This is the single feature that could differentiate us from ALL competitors. Even MeetGeek only has it in meeting context, not interview.

---

### T21: MCP Server for Claude/Cursor Integration (P2) — 2-3 weeks
**File:** `backend/mcp_server.py` (NEW)

**Why:** Otter, Fireflies, Grain all offer MCP servers — becoming table stakes

**What to implement:**
1. MCP protocol server (stdio transport)
2. Expose tools:
   - `search_transcripts` — search across all conversations
   - `get_summary` — get AI summary of a conversation
   - `list_action_items` — get action items from meetings
   - `get_interview_notes` — get interview prep notes for a company/role
   - `ask_about_conversation` — Q&A over a specific conversation
3. Expose resources:
   - Conversation transcripts
   - Meeting summaries
   - Interview notes
4. Add to Claude Code MCP config:
   ```json
   {
     "mcpServers": {
       "ai-note-taker": {
         "command": "python",
         "args": ["backend/mcp_server.py"],
         "env": { "API_URL": "http://localhost:8000" }
       }
     }
   }
   ```

---

### T22: CRM Real Integration (P2) — 3-4 weeks
**File:** `backend/crm_integration.py` (exists but is config-only)

**Current:** CRM config UI exists but no actual API sync
**Target:** Real HubSpot + Salesforce integration

**HubSpot integration:**
1. OAuth 2.0 flow for HubSpot connection
2. Contact sync: create/update contacts from meeting participants
3. Activity logging: log meeting notes as HubSpot engagements
4. Deal sync: link interviews to HubSpot deals

**Salesforce integration:**
1. OAuth 2.0 flow for Salesforce connection
2. Lead/contact sync
3. Activity logging as Salesforce tasks
4. Custom object for interview records

**Add to requirements.txt:**
```
hubspot-api-client>=8.0.0
simple-salesforce>=1.12.0
```

---

## DEPENDENCY CHAIN

```
T16 (DB Migration) ─── START THIS FIRST
    ├── T17 (Encryption) — depends on T16
    │   └── T18 (Redis Caching) — depends on T16 + T17
    └── T14 (Mock Library) — can start independently

T20 (Voice Agent) — independent, can start anytime
T21 (MCP Server) — independent, can start anytime
T22 (CRM Integration) — independent, can start anytime
```

---

## TASK ORDER

```
Week 1-2:  T16 (Database migration completion)
Week 2-3:  T17 (Encryption at rest)
Week 3-5:  T18 (Redis + response optimization)
Week 3-4:  T14 (Mock library expansion) — can parallel with T17/T18
Week 5+:   T20 (Voice Agent) → T21 (MCP Server) → T22 (CRM)
```

**Total: ~10-12 weeks** | **Critical path: T16 → T17 → T18**