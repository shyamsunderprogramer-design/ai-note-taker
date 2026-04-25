# ANT vs. Competitors — Architecture & Feature Comparison (April 2026)

**Scope:** Pin-to-pin comparison of how we build vs. how they build, with upgrade plan

---

## 1. ARCHITECTURE COMPARISON: How We Build vs. How They Build

### 1.1 Tech Stack Comparison

| Layer | ANT (Us) | Otter | Fireflies | tl;dv | Fathom | Grain | MeetGeek | FinalRound | LockedIn | Cluely |
|-------|----------|-------|-----------|-------|--------|-------|----------|------------|-----------|--------|
| **Desktop** | Electron 41.x | — | Desktop app | Electron | Electron | Desktop app | Desktop app | Electron | Desktop | Electron |
| **Frontend** | Vanilla JS/HTML/CSS | React SPA | Next.js + React | React SPA | TypeScript/Stencil | React SPA | React | Next.js + React | Browser ext | Chromium overlay |
| **Backend** | Python FastAPI | Python/Django | Node.js + GraphQL | Node.js | Ruby on Rails + Go | Unknown | Go | Node.js + Python + Go | Multi-cloud APIs | Node.js |
| **Database** | SQLite/PostgreSQL | MySQL + Cassandra | MongoDB + MySQL | PostgreSQL + MongoDB | MySQL | Unknown (AWS) | PostgreSQL | PostgreSQL + Firebase + MongoDB | — | — |
| **Cache** | Redis (dormant) | Redis | Redis | Redis | Redis | — | — | Redis | — | — |
| **Search** | — | Elasticsearch | Elasticsearch + Turbopuffer | Elasticsearch | Elasticsearch | — | — | — | — | — |
| **AI/LLM** | 8+ providers (Ollama, OpenAI, Anthropic, Google, xAI, DeepSeek, Groq, Perplexity) | Proprietary ASR + Anthropic/OpenAI | Claude + OpenAI + Groq + Perplexity + AssemblyAI + ElevenLabs | Claude (Anthropic) | Claude + OpenAI + Voyage AI | Claude + OpenAI | — | GPT-4o + Claude + Gemini + DeepSeek + o3-mini | GPT-4o + Claude + Gemini + DeepSeek + Grok | GPT-4.1 + Claude 3.7 |
| **STT** | faster-whisper (local) | Proprietary Transformer | AssemblyAI + Soniox | Unknown | Unknown | AssemblyAI + Rev AI | — | Unknown | Unknown | OpenAI Whisper |
| **Real-time** | WebSocket + SSE | WebSocket + SSE | WebSocket (Socket.IO) | SSE | SSE + Pusher | Recall.ai bots | WebSocket + SSE | WebSocket + SSE | WebSocket | WebSocket |
| **Knowledge Graph** | Neo4j (optional) | Cross-meeting search | Turbopuffer RAG | Multi-meeting AI | Voyage AI embeddings | — | — | — | — | — |
| **Cloud** | Local-first | AWS + GCP | GCP + AWS | GCP + AWS + Hetzner | GCP + GKE | AWS | Multi-region (US/EU/global) | AWS + GCP + Azure | — | — |
| **Container** | Docker + K8s + Terraform | K8s | K8s + Terraform | K8s | K8s + ArgoCD | — | — | K8s (EKS/GKS) | — | — |
| **MCP** | Yes (partial) | Yes | Yes | No | No | Yes | Yes | No | No | No |

### 1.2 Key Architectural Differences

**How we build (ANT):**
- **Local-first**: Everything runs on the user's machine. No cloud dependency.
- **Monolithic**: Single FastAPI backend (~1500 lines in main.py), all features in one process.
- **Vanilla frontend**: No framework (no React, no Vue). Hand-rolled SPA with pub/sub state management.
- **Embedded database**: SQLite by default (PostgreSQL optional). No external DB server required.
- **Multi-provider AI routing**: 8+ LLM providers with race mode (fastest wins). Unique in market.
- **Privacy-first architecture**: Screen capture protection, stealth mode, local Whisper, encrypted key storage.
- **Electron desktop**: Always-on-top overlay, frameless window, global shortcuts.

**How they build (competitors):**
- **Cloud-first**: All processing on their servers. Users send audio to the cloud.
- **Microservices**: Otter (Django + Kafka), Fireflies (Node.js + GraphQL + microservices), tl;dv (Node.js + PostgreSQL + MongoDB), Fathom (Rails + Go + C++ microservices), MeetGeek (Go API).
- **Modern frontend**: React/Next.js/TypeScript with component libraries.
- **Managed databases**: MongoDB Atlas, RDS PostgreSQL, Cassandra clusters.
- **Single LLM provider**: Most use 1-2 LLM providers (Claude primary, OpenAI fallback).
- **Server infrastructure**: Kubernetes on GCP/AWS, auto-scaling, CDN, multi-region.
- **Bot-based**: Most competitors send a visible bot to join meetings. Only Granola and Fathom (partially) are bot-free.

### 1.3 What Their Architecture Enables That Ours Doesn't

| Capability | Why They Can | Why We Can't (Yet) | Priority |
|-----------|-------------|-------------------|----------|
| **Real-time collaborative editing** | Server-authoritative with OT/CRDT | Local-only, no sync protocol | P2 |
| **Cross-meeting search at scale** | Elasticsearch + vector DB + server compute | SQLite FTS + local embedding model | P1 |
| **Team workspaces** | Centralized auth + shared DB | JWT auth, no org/team model | P1 |
| **Auto-join calendar meetings** | Server-side bot infrastructure | Client-side only, no calendar integration | P1 |
| **Video recording + clips** | Server-side video processing pipeline | Electron can capture but no processing pipeline | P2 |
| **Compliance certifications** | Cloud infrastructure with audit controls | Local app, no compliance framework | P1 |
| **Mobile apps** | Shared API backend + React Native | API exists but no mobile client | P3 |
| **Integration ecosystem** | OAuth + webhooks + public API + Zapier | Limited API, no OAuth, no webhooks | P1 |

---

## 2. FEATURE COMPARISON: Pin-to-Pin

### 2.1 Meeting Note-Taking Features

| Feature | ANT | Otter | Fireflies | tl;dv | Fathom | Grain | MeetGeek |
|---------|-----|-------|-----------|-------|--------|-------|----------|
| **Real-time transcription** | Partial (WS works, no caption UI) | Best-in-class (1M+ words/min) | Live on Meet only | Post-meeting | Live summaries | Post-meeting | Chrome ext live |
| **Live visible captions** | MISSING | Full overlay captions | In-meeting notes | None | Live summary panel | Live notepad | Copilot overlay |
| **Meeting bot auto-join** | None (bot-free) | OtterPilot auto-join | Fred bot auto-join | Bot auto-join | 3 modes (bot/bot-free) | Recall.ai bot | Bot + Chrome ext |
| **Calendar auto-join** | MISSING | Google + Outlook | Google + Outlook | Google + Outlook | Google + Outlook | Google + Outlook | Google + Outlook |
| **Cross-meeting search** | Yes (semantic) | Ask Otter (agentic) | AskFred (cross-meeting) | Multi-meeting AI | Ask Fathom (account-wide) | Ask Grain | AI Chat |
| **AI summaries** | Yes (multi-provider) | Custom templates | 200+ AI Skills | Custom templates | 15+ templates | Custom prompts | Auto-detect type |
| **Action items** | Yes | 81% precision | Auto-assigned | Yes | 93% precision (best) | Auto-generated | Yes |
| **Speaker diarization** | Conditional (pyannote) | 94% for known voices | Labels + timestamps | Auto detection | Bot-free diarization | Recall.ai attribution | Auto recognition |
| **Slide capture** | MISSING | Auto-capture | None | Auto-capture | None | None | None |
| **Video recording** | MISSING | Enterprise only | Business+ | Yes | Yes | Yes (unlimited clips) | Yes |
| **Clips/highlights** | MISSING | Yes | Soundbites | Clips + Reels | Clips + playlists | Stories (unique) | Clips + Reels |
| **CRM sync** | Stub only | Salesforce + HubSpot | 5+ CRMs native | Salesforce + HubSpot | Salesforce + HubSpot | Salesforce + HubSpot | 4+ CRMs |
| **Slack** | MISSING | Yes | Yes | Yes | No | Yes | Yes (Slack Assistant) |
| **Zapier** | MISSING | Yes | Yes | 5000+ | No | Yes | 7000+ |
| **Notion** | MISSING | No | Yes | Yes | No | Productboard | No |
| **Public share links** | MISSING | Yes | Yes | Yes | Yes | Yes | Yes |
| **Mobile app** | PWA only | iOS + Android | iOS + Android | iOS + Android (Lite) | iOS (coming) | None | iOS + Android |
| **SOC 2 Type II** | No | Yes | Yes | Type I | Yes | Yes | Yes |
| **GDPR** | No | Yes | Yes | Yes + EU AI Act | Yes | Yes | Yes |
| **HIPAA** | No | Yes (add-on) | Enterprise | No | Yes | No | Ready |
| **MCP Server** | Partial (mock data) | Yes | Yes | No | No | Yes | Yes |
| **Voice Agents** | Partial (TTS only) | 3 AI agents | Voice agents (speaking) | 10 AI agents | No | No | 5 voice agents |
| **Price** | FREE | $8-30/mo | $10-39/mo | $18-98/mo | $0-34/mo | $15-39/mo | $6-17/mo |

### 2.2 Interview-Focused Features

| Feature | ANT | FinalRound | LockedIn | Cluely | OphyAI | Yoodli |
|---------|-----|------------|----------|--------|--------|--------|
| **Copilot latency** | ~500ms | ~350ms | 116ms (fastest) | 5-10s | ~1s | N/A |
| **Stealth mode** | Full (screen protection) | Full | 20+ features | OS-level overlay | Whisper (PiP) | N/A |
| **Multi-provider AI** | 8+ providers | 1 (GPT-4o) | 6+ models | 2 (GPT, Claude) | Unknown | 1 |
| **Mock interviews** | Yes (simulator) | Yes (7 types) | Yes | No | Yes (6 types) | Yes (roleplay) |
| **Question bank** | ~100 templates | 2M+ curated | Limited | None | Moderate | Moderate |
| **Speech analytics** | STAR + pace | Basic | None | None | Post-session | Best-in-class |
| **Voice cloning** | Yes (RVC) | No | No | No | No | No |
| **Knowledge graph** | Yes (Neo4j) | No | No | No | No | No |
| **Study plans** | Yes (SM-2) | No | No | No | No | No |
| **Resume tools** | Review only | Builder (ATS) | Optimization | No | Builder + 16 tools | No |
| **Job tracking** | Full pipeline | Auto-apply (1K+/wk) | Auto-apply | No | 8-stage pipeline | No |
| **Cover letters** | No | No | Yes | No | 16 document tools | No |
| **Coding interview** | MVP stub | Full (LeetCode etc) | VSCode/Cursor | No | No | No |
| **Price** | FREE | $99-600/mo | $42-55/mo | $0-75/mo | $9-39/mo | $5-20/mo |

### 2.3 Where We're AHEAD

| Advantage | Detail | No Competitor Has This |
|-----------|--------|----------------------|
| **Free + Open Source** | $0, fully auditable code | Yes — unique |
| **8+ AI providers** | Race mode, no vendor lock-in | Yes — others use 1-2 |
| **Knowledge graph (Neo4j)** | Persistent entity memory across sessions | Yes — unique |
| **Voice cloning (RVC)** | Practice with different interviewer voices | Yes — unique |
| **Study plans (SM-2)** | Spaced repetition for interview prep | Yes — unique |
| **Hybrid vertical** | Meeting + Interview + Career in one app | Yes — unique |
| **Privacy-first + local processing** | No cloud dependency, open-source | Only Granola competes on privacy |
| **Bot-free by default** | Electron desktop = no visible bot | Only Granola/Grain/MeetGeek similar |
| **Document RAG + OCR** | Upload docs + screenshot context | Almost unique (only Cluely has RAG) |

### 2.4 Where We're BEHIND (Critical Gaps)

| Gap | Competitor Baseline | Our Status | Severity |
|-----|---------------------|------------|----------|
| **Real-time visible captions** | Otter streams 1M+ words/min with live overlay | Transcription works, NO caption UI | CRITICAL |
| **AI Agents (agentic)** | Otter (3), Fireflies (200+), MeetGeek (5 voice), tl;dv (10) | Shadow Agent = template matching, NOT real AI | CRITICAL |
| **Team workspaces** | Every competitor has orgs, RBAC, shared search | In-memory duo mode, lost on restart | CRITICAL |
| **Compliance (SOC 2/GDPR)** | 7/11 meeting competitors have SOC 2 Type II | Zero certifications | CRITICAL |
| **Calendar auto-join** | 9/11 competitors auto-join from calendar | Manual connection only | HIGH |
| **CRM integration** | Native bidirectional sync | SDKs not installed, webhook only | HIGH |
| **Video recording + clips** | 7/11 competitors | Audio-only | HIGH |
| **Encryption not active** | AES-256 at rest standard everywhere | EncryptionManager coded but NOT called | CRITICAL |
| **HTTPS disabled** | All competitors enforce HTTPS | `HTTPS_REQUIRED=false` | CRITICAL |
| **Default admin/admin123** | No default credentials anywhere | Auto-created on startup | CRITICAL |
| **Public share links** | 9/11 competitors | None | MEDIUM |
| **Mobile app** | 6/11 competitors | PWA only | MEDIUM |
| **Integration ecosystem** | Zapier + Slack + Notion + Jira | None of these | MEDIUM |
| **Custom AI templates** | Fireflies (200+), tl;dv (playbooks) | Meeting templates only | MEDIUM |

---

## 3. BUILD COMPARISON: Architecture Quality

### 3.1 Backend Architecture Maturity

| Aspect | ANT | Otter | Fireflies | tl;dv | Fathom |
|--------|-----|-------|-----------|-------|--------|
| **Scalability** | Single-process FastAPI | K8s + Kafka event streaming | K8s + GraphQL + microservices | K8s on multi-cloud | GKE + Sidekiq + Kafka |
| **API design** | REST (flat) | REST | GraphQL (17+ queries, 15+ mutations) | REST (v1alpha1) | REST |
| **Database** | SQLite (default) / PostgreSQL (opt) | MySQL + Cassandra | MongoDB + MySQL | PostgreSQL + MongoDB | MySQL + Elasticsearch |
| **Caching** | Redis (dormant) | Redis | Redis | Redis | Redis |
| **Search** | None | Elasticsearch | Elasticsearch + Turbopuffer (vector) | Elasticsearch | Elasticsearch + Voyage AI |
| **Real-time** | WebSocket + SSE | WebSocket + SSE | WebSocket (Socket.IO) | SSE | SSE + Pusher |
| **Event streaming** | None | Kafka | RabbitMQ | None | Kafka |
| **CI/CD** | GitHub Actions | Unknown | K8s + Terraform | GitLab CI | ArgoCD + GitHub Actions + CircleCI |
| **Testing** | ~2K lines, no auth/WS/security tests | Unknown (35M users) | Unknown | Unknown | 8-person senior team |
| **Monitoring** | Prometheus config exists | Unknown | New Relic + Sentry | Unknown | Sentry + New Relic |

### 3.2 Frontend Architecture Maturity

| Aspect | ANT | Otter | Fireflies | tl;dv | Fathom |
|--------|-----|-------|-----------|-------|--------|
| **Framework** | Vanilla JS | React SPA | Next.js + React | React SPA | TypeScript + Stencil |
| **State management** | Pub/sub (custom) | Redux likely | React state + GraphQL cache | React state | Web Components state |
| **Component model** | DOM manipulation | React components | React components | React components | Web Components |
| **Type safety** | None (plain JS) | TypeScript (likely) | TypeScript | TypeScript | TypeScript |
| **Testing** | None | Unknown | Unknown | Unknown | Unknown |
| **Accessibility** | Basic | ARIA compliant | ARIA compliant | ARIA compliant | ARIA compliant |
| **Responsive design** | Desktop-first (overlay) | Desktop + mobile | Desktop + mobile | Desktop + mobile | Desktop + mobile |

### 3.3 Security Comparison

| Aspect | ANT | Otter | Fireflies | tl;dv | Fathom | MeetGeek |
|--------|-----|-------|-----------|-------|--------|----------|
| **Encryption at rest** | Code exists, NOT wired | AES-256 | AES-256 | Encrypted at rest | Encrypted | Unknown |
| **Encryption in transit** | HTTPS disabled | TLS 1.2+ | TLS 1.2+ | TLS 1.2+ | TLS 1.2+ | TLS 1.2+ |
| **Auth** | JWT (default admin/admin123) | SSO + SCIM + SAML | SSO + SCIM | SSO + SAML | SSO + SCIM | SSO + SCIM |
| **Audit logging** | Yes (JSONL + DB) | Yes | Yes | Yes | Yes | Yes |
| **Rate limiting** | Yes (3-tier) | Yes | Yes (50-100 req/min) | Yes | Yes | Yes |
| **Input validation** | Yes (SQL/XSS/path) | Yes | Yes (HMAC webhooks) | Yes | Yes | Yes |
| **SOC 2 Type II** | No | Yes | Yes | Type I | Yes | Yes |
| **HIPAA** | No | Yes (add-on) | Enterprise | No | Yes | Ready |
| **GDPR** | No | Yes | Yes | Yes + EU AI Act | Yes | Yes |
| **SSO** | No | Yes | Yes | Yes | Team+ | Yes |
| **Data residency** | Local only | US | US | EU + US | US | US + EU + Global |
| **Default credentials** | admin/admin123 | None | None | None | None | None |

---

## 4. UPGRADE PLAN: Priority-Ordered Task Breakdown

### Phase 1: CRITICAL SECURITY FIXES (Week 1) — 5 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| S1 | **Remove default admin/admin123** | First-launch setup wizard, no default credentials | `backend/core/main.py`, `backend/core/database.py` | 4h |
| S2 | **Enable HTTPS by default** | Auto-generate SSL certs, enforce HTTPS, fix Electron HSTS | `backend/core/generate_ssl.py`, `backend/core/main.py`, `electron/main.js` | 6h |
| S3 | **Wire encryption into storage** | Activate EncryptionManager for conversations, API keys, documents | `backend/core/database.py`, `backend/routes/conversations.py`, `backend/modules/platform/document_store.py` | 2d |
| S4 | **Secure API key storage** | Move from plain JSON to encrypted electron-store (already implemented, verify wiring) | `electron/main.js`, `backend/routes/ollama.py` | 4h |
| S5 | **Add GDPR data export/deletion endpoints** | Right to export all data, right to delete all data | New: `backend/routes/gdpr.py` | 1d |

### Phase 2: REAL AI AGENTS (Week 2-3) — 10 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| A1 | **Replace Shadow Agent templates with LLM calls** | Use AI router to generate contextual suggestions based on transcript context | `backend/modules/agents/shadow_agent.py`, `backend/modules/agents/orchestrator.py` | 2d |
| A2 | **Build Meeting Agent** | Autonomous agent that joins meetings, takes notes, extracts action items, generates summaries | New: `backend/modules/agents/meeting_agent.py` | 3d |
| A3 | **Build Sales Coach Agent** | Real-time objection detection, deal insights, CRM field suggestions | New: `backend/modules/agents/sales_coach.py` (upgrade existing stub) | 3d |
| A4 | **Fix MCP server to use real data** | Replace mock responses with actual database queries for all 5 tools | `backend/modules/platform/mcp_server.py` | 2d |

### Phase 3: REAL-TIME CAPTIONS + UI (Week 4-5) — 10 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| U1 | **Build caption overlay window** | Floating always-on-top caption overlay showing real-time transcription | New: `apps/web/caption-overlay.html`, `apps/web/js/components/CaptionOverlay.js` | 3d |
| U2 | **Wire caption overlay to WebSocket** | Connect caption overlay to `/ws/transcribe` for live updates | `apps/web/js/core/api.js`, `electron/main.js` | 1d |
| U3 | **Build meeting notes auto-format** | Auto-structure meeting notes: title, attendees, action items, decisions, follow-ups | New: `backend/modules/agents/meeting_notes.py` | 2d |
| U4 | **Add public share links** | Generate password-protected share links for conversations | `backend/routes/conversations.py`, `backend/core/database.py` | 1d |
| U5 | **Add custom AI templates** | Allow users to create and save prompt templates for recurring meeting types | `backend/routes/ai.py`, `backend/core/database.py` (new model), `apps/web/js/components/SettingsPanel.js` | 2d |

### Phase 4: INTEGRATIONS + TEAM FEATURES (Week 6-8) — 15 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| I1 | **Calendar auto-join (Google Calendar)** | OAuth flow, detect upcoming meetings, auto-inject content script | New: `backend/routes/calendar.py`, `backend/modules/integration/google_calendar.py`, Chrome extension update | 3d |
| I2 | **Slack integration** | Bot that posts transcripts, summaries, action items to channels | New: `backend/routes/slack.py`, `backend/modules/integration/slack.py` | 2d |
| I3 | **CRM sync (HubSpot + Salesforce)** | Install SDKs, implement bidirectional contact/activity sync | `backend/routes/crm.py`, `backend/modules/crm/` (upgrade existing) | 3d |
| I4 | **Team workspaces + RBAC** | Organization model, team members, roles, shared conversations, team search | `backend/core/database.py` (new models), `backend/routes/auth.py`, `backend/routes/teams.py` | 4d |
| I5 | **Persist collaboration data** | Move from in-memory to database with message persistence | `backend/modules/agents/collaboration_mode.py`, `backend/core/database.py` | 1d |
| I6 | **Zapier integration** | Expose triggers (new transcript, action item) and actions (search, summarize) as webhook endpoints | New: `backend/routes/webhooks.py`, Zapier developer app | 2d |

### Phase 5: VIDEO + CONTENT (Week 9-11) — 15 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| V1 | **Screen recording via Electron** | Capture screen using desktopCapturer, save as video file with transcript sync | `electron/main.js`, New: `electron/features/screen-recorder.js` | 3d |
| V2 | **Video clip creation** | Select transcript section → auto-generate video clip with timestamps | New: `backend/routes/video.py`, `apps/web/js/components/VideoClipper.js` | 3d |
| V3 | **Highlight reels** | AI-select key moments, generate 60-90s highlight compilation | New: `backend/modules/ai/highlight_reel.py` | 2d |
| V4 | **Slide capture** | Auto-screenshot shared screens at intervals, embed in transcript | `electron/main.js`, `apps/web/js/components/SlideCapture.js` | 2d |
| V5 | **Write 500+ real interview questions** | Curated, verified questions by category/role/difficulty (not templates) | `backend/modules/interview/question_database_v2.py` (upgrade) | 3d |
| V6 | **Cover letter generator** | AI-generated cover letters, salary negotiation docs, follow-up emails | New: `backend/routes/career.py`, `backend/modules/interview/cover_letters.py` | 2d |

### Phase 6: COMPLIANCE + ENTERPRISE (Week 12-14) — 15 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| C1 | **SOC 2 Type II controls** | RBAC enforcement, access policies, encryption verification, audit trail | `backend/security/`, `backend/core/database.py` | 5d |
| C2 | **SSO (Google + Microsoft)** | OAuth2 login, SAML 2.0 for enterprise | `backend/routes/auth.py`, New: `backend/modules/integration/sso.py` | 3d |
| C3 | **EU AI Act compliance** | "AI Assistance Active" notification, human oversight, bias audit logging, model documentation | `apps/web/index.html`, `backend/routes/interview.py`, New: `backend/routes/compliance.py` | 2d |
| C4 | **Data residency options** | Configurable data storage location (local/EU/US cloud) | `backend/core/config.py`, `backend/core/database.py` | 2d |
| C5 | **Test coverage to 60%** | Unit tests for auth, WebSocket, database, encryption, security, API routes | `backend/tests/` (new test files) | 3d |

### Phase 7: DIFFERENTIATION (Week 15-18) — 20 days

| # | Task | What to Build | Files to Change | Effort |
|---|------|---------------|-----------------|--------|
| D1 | **Mobile app MVP (React Native)** | Core features: transcription, AI chat, interview practice, job tracker | New: `mobile/` directory | 10d |
| D2 | **Auto-apply for jobs** | LinkedIn/Indeed auto-apply via Chrome extension | Chrome extension update, New: `backend/modules/integration/auto_apply.py` | 3d |
| D3 | **Zero-config cognitive graph** | Embed graph DB or use SQLite-based graph; auto-initialize on first run | `backend/modules/ai/cognitive_graph.py` (upgrade) | 3d |
| D4 | **Notion integration** | Push summaries, action items, notes to Notion pages/databases | New: `backend/modules/integration/notion.py` | 1d |
| D5 | **Jira integration** | Auto-create tickets from action items | New: `backend/modules/integration/jira.py` | 1d |
| D6 | **Phone call support** | System audio capture for phone calls via Electron | `electron/main.js`, `electron/features/system_audio_capture.js` | 2d |

---

## 5. EFFORT SUMMARY

| Phase | Duration | Tasks | Key Outcome |
|-------|----------|-------|-------------|
| **Phase 1: Security** | Week 1 (5 days) | S1-S5 | Production-safe: no default creds, encryption active, HTTPS enforced |
| **Phase 2: AI Agents** | Week 2-3 (10 days) | A1-A4 | Real AI agents replace template matching; MCP uses real data |
| **Phase 3: UI + Captions** | Week 4-5 (10 days) | U1-U5 | Live caption overlay, meeting notes, share links, custom templates |
| **Phase 4: Integrations** | Week 6-8 (15 days) | I1-I6 | Calendar auto-join, Slack, CRM, teams, Zapier |
| **Phase 5: Video + Content** | Week 9-11 (15 days) | V1-V6 | Video recording, clips, highlights, real question bank, cover letters |
| **Phase 6: Compliance** | Week 12-14 (15 days) | C1-C5 | SOC 2 controls, SSO, EU AI Act, data residency, 60% test coverage |
| **Phase 7: Differentiation** | Week 15-18 (20 days) | D1-D6 | Mobile app, auto-apply, zero-config graph, Notion, Jira, phone calls |
| **TOTAL** | ~18 weeks | 32 tasks | Production-competitive application |

---

## 6. QUICK WINS (This Week)

These can be done immediately with no dependencies:

1. **Remove admin/admin123** (S1) — 4 hours
2. **Enable HTTPS by default** (S2) — 6 hours
3. **Wire encryption into storage** (S3) — 2 days
4. **Wire Redis into main.py** (G7) — 2 days
5. **Fix MCP server mock data** (A4) — 2 days
6. **Add public share links** (U4) — 1 day

**Total quick wins: ~7 days of work**

---

## 7. COMPETITIVE SCORECARD (After All Upgrades)

| Category | Current Score | After Upgrades | Market Leader |
|----------|--------------|----------------|---------------|
| **Transcription** | 3/5 | 4/5 (caption overlay) | Otter 5/5 |
| **AI Depth** | 3/5 | 5/5 (real agents) | Fireflies 5/5 |
| **Integration Breadth** | 2/5 | 4/5 (Slack, CRM, Zapier, Notion, Jira) | Fireflies 5/5 |
| **Security/Compliance** | 2/5 | 4/5 (SOC 2, GDPR, HIPAA-ready, encryption) | Otter/Fathom 5/5 |
| **Team Features** | 1/5 | 4/5 (workspaces, RBAC, shared search) | Otter 5/5 |
| **Interview Prep** | 4/5 | 5/5 (real questions, cover letters, auto-apply) | FinalRound 5/5 |
| **Career Tools** | 4/5 | 5/5 (cover letters, auto-apply) | FinalRound 4/5 |
| **Privacy** | 5/5 | 5/5 | Granola 4/5 |
| **Open Source** | 5/5 | 5/5 | — |
| **Multi-Provider AI** | 5/5 | 5/5 | — |
| **Knowledge Persistence** | 4/5 | 5/5 (zero-config graph) | — |
| **Real-time** | 2/5 | 4/5 (caption overlay, real agents) | Otter 5/5 |
| **Video** | 0/5 | 4/5 (recording, clips, highlights) | Grain 5/5 |
| **TOTAL** | **40/65** | **59/65** | — |

**After upgrades: ANT becomes the most feature-complete free+open-source AI meeting+interview tool in the market, with unique advantages (multi-provider AI, knowledge graph, voice cloning, study plans) that no competitor matches at any price.**