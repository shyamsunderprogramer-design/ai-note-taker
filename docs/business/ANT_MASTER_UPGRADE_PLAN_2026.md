# ANT (AI Note Taker) — Master Upgrade Plan 2026

**Date:** April 25, 2026
**Type:** Comprehensive competitive analysis + 24-week upgrade roadmap
**Team size:** 4-8 parallel agents/developers
**Strategy:** Balanced — enterprise readiness + feature parity + user growth

---

## EXECUTIVE SUMMARY

### Market Position (April 2026)

ANT is uniquely positioned as the **only free, open-source, privacy-first** application that combines **meeting intelligence + interview coaching + career tools** in one product. No competitor — paid or free — covers all three verticals.

### What Changed in the Market (since existing analysis)

| Event | Impact on ANT |
|-------|---------------|
| Granola raised $125M at $1.5B valuation | Meeting intelligence market is HOT — validates the space |
| Google blocked third-party bots on Google Meet (March 25, 2026) | ANT's bot-free Electron approach is now an ADVANTAGE |
| Fathom added bot-free mode (April 15, 2026) | Bot-free is now table stakes — everyone is moving to it |
| FinalRound AI dropped pricing from $148 to $90/mo | Price war in interview tools — ANT's free model wins |
| Natively (OSS) hit 1,009 stars in 3 months | Open-source competition is accelerating |
| MCP servers launched by Granola, Fathom, MeetGeek, tl;dv | MCP is now enterprise table stakes |
| Many new interview copilot entrants (Diwa, Interview Lift, Parakeet) | Market is getting crowded — need to move fast |

### ANT's Competitive Score: 88/100 → Target: 95/100

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| Feature Coverage | 85% | 95% | Caption overlay, video, agents |
| Production Readiness | 45% | 85% | SOC 2, encryption, testing |
| Integration Breadth | 2/5 | 4/5 | Slack, CRM, Zapier, calendar |
| Team Features | 1/5 | 4/5 | Workspaces, RBAC, sharing |
| Privacy/Open Source | 5/5 | 5/5 | Already best-in-class |
| Multi-Provider AI | 5/5 | 5/5 | Already best-in-class |
| Real-time Capabilities | 2/5 | 4/5 | Caption overlay, real agents |

---

## PART 1: COMPETITIVE LANDSCAPE (April 2026 Update)

### Meeting Note-Taking Competitors

| Competitor | Pricing | Key Differentiator | ANT Advantage |
|------------|---------|-------------------|---------------|
| **Otter.ai** | $8-30/mo | Best transcription, 3 AI agents, $100M ARR | Free, multi-provider, interview tools, open source |
| **Fireflies.ai** | $10-39/mo | 200+ AI Skills, 100+ languages | Free, no credits system, open source |
| **Fathom.video** | $16-25/mo | Bot-free mode (NEW Apr 15), best UX | Free, interview tools, knowledge graph |
| **MeetGeek** | $10-17/mo | **Voice agents that SPEAK** (unique) | Free, open source, interview tools |
| **Granola** | $14-35/mo | $1.5B valuation, privacy-first | Free, open source, interview + career tools |
| **tl;dv** | $18-59/mo | Bot-free audio (NEW), 2M+ users | Free unlimited, interview focus |
| **Grain** | $15-29/mo | Best video clips | Free, interview + career tools |
| **Avoma** | $19-39/mo | Revenue intelligence | Free, open source |

**Key insight:** Granola's $1.5B valuation confirms the market sees meeting intelligence as a massive opportunity. ANT's open-source + privacy approach is perfectly timed.

### Interview Preparation Competitors

| Competitor | Pricing | Key Differentiator | ANT Advantage |
|------------|---------|-------------------|---------------|
| **FinalRound AI** | $25-90/mo (was $148!) | 2M+ questions, auto-apply, 10M users | Free, multi-provider, knowledge graph |
| **LockedIn AI** | $42-55/mo | 116ms response, 6 models, IDE integration | Free, open source, meeting + career tools |
| **Interview Coder** | $89-799 | 5K FAANG problems, 99% stealth | Free, behavioral + technical |
| **OphyAI** | $9/mo | Budget option, whisper mode | Free, more features |
| **Yoodli** | $5-20/mo | Best speech analytics | Free, real-time copilot |
| **Natively (OSS)** | Free (BYOK) | 1,009 stars, Rust native audio | Same price + more features |
| **Diwa Copilot (NEW)** | Free beta → one-time purchase | 100% local, zero telemetry | Same model + more features |
| **Interview Lift (NEW)** | Not public | 100K users, claims 93% success | Free, open source |

**Key insight:** Price war is intensifying (FinalRound dropped from $148 to $90). The market is commoditizing. ANT's free + open-source + hybrid vertical is the long-term moat.

### Critical Trends ANT Must Address

1. **Bot-free is now table stakes** — Google blocked bots March 25. ANT is ahead here.
2. **Voice agents are the next frontier** — MeetGeek's voice agents that SPEAK in meetings. ANT has nothing comparable.
3. **MCP servers are enterprise table stakes** — Every competitor launched one. ANT's has mock data.
4. **AI agents are expected** — Otter (3), Fireflies (200+), tl;dv (10), MeetGeek (5 voice). ANT has Shadow Agent with template matching.
5. **Enterprise compliance is a hard gate** — SOC 2, GDPR, HIPAA. Without these, enterprise deals are impossible.
6. **Video clips are standard** — 7/11 competitors offer them. ANT is audio-only.
7. **Mobile is expected** — 6/11 competitors have native apps. ANT has PWA only.

---

## PART 2: ARCHITECTURE VISION (Target State)

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTS (4 platforms)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Electron │  │  Mobile  │  │  Chrome  │  │   Web App  │  │
│  │ Desktop  │  │ (RN)     │  │ Extension│  │ (Cloud)    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │             │             │              │          │
└───────┼─────────────┼─────────────┼──────────────┼──────────┘
        │             │             │              │
┌───────┴─────────────┴─────────────┴──────────────┴──────────┐
│                    API GATEWAY (FastAPI)                      │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌───────┐ │
│  │ Auth   │  │ REST   │  │  WS    │  │  SSE   │  │ MCP   │ │
│  │ Routes │  │ Routes │  │ /ws/*  │  │ /sse/* │  │Server │ │
│  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬───┘ │
└───────┼──────────┼──────────┼──────────┼──────────┼──────┘
        │          │          │          │          │
┌───────┴──────────┴──────────┴──────────┴──────────┴──────┐
│              MASTER AI AGENT (NEW)                         │
│  ┌──────────────────────────────────────────────────┐     │
│  │  Orchestrator: intent detection → tool routing    │     │
│  │  ├── Meeting Agent (transcribe, summarize, action) │     │
│  │  ├── Interview Coach (real-time copilot, scoring)  │     │
│  │  ├── Career Agent (resume, job search, auto-apply) │     │
│  │  ├── Study Agent (SM-2 plans, spaced repetition)   │     │
│  │  └── Knowledge Agent (graph queries, entity RAG)  │     │
│  └──────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
        │          │          │          │
┌───────┴──────────┴──────────┴──────────┴──────────────────┐
│                    SERVICES LAYER                           │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────────┐  │
│  │  AI    │  │ Voice  │  │ Integ- │  │ Platform       │  │
│  │ Router │  │ (WS)   │  │ rations│  │ (Cloud, Sync)  │  │
│  ├────────┤  ├────────┤  ├────────┤  ├────────────────┤  │
│  │8 prov. │  │Whisper │  │Calendar│  │Cloud sync      │  │
│  │Race    │  │Diariz. │  │Slack   │  │MCP server      │  │
│  │Ollama  │  │RVC     │  │CRM     │  │Document store  │  │
│  │Vision  │  │System  │  │Zapier  │  │Portable mode   │  │
│  │OCR     │  │Audio   │  │Notion  │  │On-prem config  │  │
│  └────────┘  └────────┘  └────────┘  └────────────────┘  │
└──────────────────────────────────────────────────────────┘
        │          │          │          │
┌───────┴──────────┴──────────┴──────────┴──────────────────┐
│                    DATA LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │PostgreSQL│  │  Redis   │  │  Neo4j   │  │   S3      │ │
│  │(primary) │  │(cache)   │  │(graph)   │  │(files)    │ │
│  └──────────┘  └──────────┘  └──────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend | Hybrid: keep vanilla JS existing, use React for NEW UIs | Preserve investment, modernize incrementally |
| Cloud | Hybrid: local-first + optional cloud sync/hosting | Users who want privacy stay local; cloud for paid tier |
| Monetization | Free BYOK + Paid cloud tier (SaaS hosting) | Revenue without compromising open-source values |
| Agent System | Single Master Agent with specialized sub-agents | Unified routing, clean architecture, extensible |
| Database | PostgreSQL primary (production), SQLite fallback (local) | Scale for cloud, portability for local |

---

## PART 3: PHASED UPGRADE PLAN (24 Weeks)

### Phase 0: Foundation & Security (Weeks 1-2)
**Goal:** Production-safe foundation. Fix everything blocking deployment.

| # | Task | Effort | Agent | Dependencies |
|---|------|--------|-------|-------------|
| F1 | Remove default admin/admin123 — first-launch wizard | 1d | Security | None |
| F2 | Enable HTTPS by default — auto-cert generation | 2d | Security | None |
| F3 | Wire EncryptionManager into ALL storage paths | 3d | Security | None |
| F4 | Wire Redis into main.py — response <200ms | 2d | Backend | None |
| F5 | Fix MCP server — replace mock data with real DB queries | 2d | Backend | Database |
| F6 | Shadow Agent → real LLM-powered suggestions | 3d | AI/ML | AI Router |
| F7 | Persist collaboration data from memory to DB | 2d | Backend | Database |
| F8 | Install CRM SDKs + implement basic HubSpot/SF sync | 3d | Integrations | None |
| F9 | Migrate PostgreSQL schema to production-ready | 2d | Backend | None |
| F10 | Write 100 real interview questions (start of DB) | 3d | Content | None |

**Total Phase 0: ~23 agent-days (2 weeks with 3-4 agents)**

### Phase 1: Core Product Parity (Weeks 3-6)
**Goal:** Close biggest feature gaps vs competitors.

| # | Task | Effort | Agent | Dependencies |
|---|------|--------|-------|-------------|
| P1 | Real-time caption overlay window (PIP/floating) | 2w | Frontend | WS Transcription |
| P2 | Build Master Agent orchestrator (intent → tool routing) | 3w | AI/ML | AI Router |
| P3 | Calendar integration — Google + Outlook auto-detect | 2w | Integrations | OAuth |
| P4 | Team workspaces + RBAC (orgs, roles, shared search) | 3w | Backend | Database |
| P5 | Slack integration — bot for transcripts/summaries | 1w | Integrations | None |
| P6 | Public share links (password/expiry protected) | 3d | Backend | None |
| P7 | Custom AI templates/skills (user-created prompts) | 1w | Backend+Frontend | AI Router |
| P8 | Write 400 more real interview questions (500 total) | 1w | Content | None |

**Total Phase 1: ~12 agent-weeks (4 weeks with 4-5 agents)**

### Phase 2: Cloud & Monetization (Weeks 7-10)
**Goal:** Launch cloud tier + monetization infrastructure.

| # | Task | Effort | Agent | Dependencies |
|---|------|--------|-------|-------------|
| C1 | Cloud sync service — end-to-end encrypted sync | 3w | Backend+Infra | Phase 0 security |
| C2 | Paid cloud tier — subscription management (Stripe) | 2w | Backend | C1 |
| C3 | SSO — Google + Microsoft OAuth2 + SAML 2.0 | 3w | Backend | Auth system |
| C4 | SOC 2 Type II controls — RBAC, audit, encryption verify | 4w | Security | Phase 0 fixes |
| C5 | GDPR compliance — data export, deletion, consent UI | 2w | Security | Database |
| C6 | EU AI Act compliance — "AI active" notification, bias audit | 2w | Security | Feature complete |
| C7 | Zapier integration — triggers (new transcript, action item) | 2w | Integrations | Public API |
| C8 | React-based cloud dashboard (paid tier UI) | 3w | Frontend | C1, C2 |

**Total Phase 2: ~21 agent-weeks (4 weeks with 5-6 agents)**

### Phase 3: Advanced Features (Weeks 11-16)
**Goal:** Competitive differentiation + new capabilities.

| # | Task | Effort | Agent | Dependencies |
|---|------|--------|-------|-------------|
| A1 | Video recording via Electron — screen + camera | 3w | Electron | None |
| A2 | Video clip creation — transcript-synced clips | 2w | Backend+Frontend | A1 |
| A3 | Highlight reels — AI-select key moments | 2w | AI/ML | A1 |
| A4 | Write 500 more interview questions (1,000 total) | 1w | Content | None |
| A5 | Cover letter generator + salary negotiation docs | 2w | AI/ML | Master Agent |
| A6 | Notion integration — push summaries/action items | 1w | Integrations | None |
| A7 | Jira integration — auto-create tickets from action items | 1w | Integrations | None |
| A8 | Phone call support — system audio capture | 2w | Electron+Voice | None |
| A9 | Zero-config cognitive graph — SQLite-based fallback | 2w | AI/ML | Database |
| A10 | Auto-apply for jobs — LinkedIn/Indeed via extension | 3w | Integrations | Chrome extension |

**Total Phase 3: ~19 agent-weeks (6 weeks with 4-5 agents)**

### Phase 4: Growth & Ecosystem (Weeks 17-24)
**Goal:** Scale users, community, and platform.

| # | Task | Effort | Agent | Dependencies |
|---|------|--------|-------|-------------|
| G1 | Mobile app MVP — React Native (transcription, AI chat, job tracker) | 8w | Mobile | API Gateway |
| G2 | Frontend migration — React for settings, dashboard, new pages | 6w | Frontend | None |
| G3 | Agent marketplace — community-shared prompt templates | 3w | Backend+Frontend | Master Agent |
| G4 | Open-source community program — CONTRIBUTING.md, issue labels, CI | 2w | DevOps | None |
| G5 | Performance optimization — response <150ms, cold start <1s | 3w | Backend | Redis wired |
| G6 | Test coverage to 60%+ — auth, WS, security, integration | 4w | QA | All modules |
| G7 | Global CDN + multi-region for cloud tier | 3w | Infra | Cloud tier |
| G8 | Documentation overhaul — API refs, user guides, deployment | 2w | Docs | All features |
| G9 | Accessibility audit — ARIA, screen reader, keyboard nav | 2w | Frontend | None |
| G10 | Security audit + penetration testing | 2w | Security | All fixes |

**Total Phase 4: ~35 agent-weeks (8 weeks with 5-6 agents)**

---

## PART 4: AGENT ALLOCATION (4-8 Agents)

### Recommended Agent Roles

```
┌─────────────────────────────────────────────────────────────┐
│                     AGENT TEAM STRUCTURE                     │
├─────────────┬────────────────────┬──────────────────────────┤
│ Agent Role  │ Primary Focus      │ Phase Assignments        │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-1     │ Security &         │ F1, F2, F3, C4, C5, C6, │
│             │ Compliance         │ G10                      │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-2     │ Backend / Platform │ F4, F5, F7, F9, P4, P6, │
│             │                    │ C1, C2, G5               │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-3     │ AI / ML            │ F6, P2, A3, A5, A9, G3  │
│             │ (Master Agent)     │                          │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-4     │ Frontend / UI      │ P1, P7, C8, A2, G2, G9  │
│             │ (Hybrid: Vanilla+  │                          │
│             │  React)            │                          │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-5     │ Integrations       │ F8, P3, P5, C7, A6, A7, │
│             │                    │ A10                      │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-6     │ Mobile (React      │ G1 (dedicated for 8 wks) │
│             │ Native)            │                          │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-7     │ QA / Testing       │ G6 (dedicated for 4 wks) │
│             │                    │                          │
├─────────────┼────────────────────┼──────────────────────────┤
│ AGENT-8     │ Content / Docs /   │ F10, P8, A4, G4, G8     │
│             │ Community          │                          │
└─────────────┴────────────────────┴──────────────────────────┘
```

### Parallel Execution Strategy

**Phase 0 (Weeks 1-2):** 4 agents in parallel
- Agent-1: Security fixes (F1, F2, F3)
- Agent-2: Backend fixes (F4, F5, F7, F9)
- Agent-3: AI fixes (F6)
- Agent-5: CRM + questions (F8, F10)

**Phase 1 (Weeks 3-6):** 5 agents in parallel
- Agent-1: Security monitoring
- Agent-2: RBAC + share links (P4, P6)
- Agent-3: Master Agent orchestrator (P2)
- Agent-4: Caption overlay (P1)
- Agent-5: Calendar + Slack + templates (P3, P5, P7)

**Phase 2 (Weeks 7-10):** 6 agents in parallel
- Agent-1: Compliance (C4, C5, C6)
- Agent-2: Cloud sync + subscriptions (C1, C2)
- Agent-3: SSO integration (C3)
- Agent-4: React dashboard (C8)
- Agent-5: Zapier integration (C7)
- Agent-8: Interview questions (P8)

**Phase 3 (Weeks 11-16):** 5 agents in parallel
- Agent-2: Auto-apply + Notion + Jira (A6, A7, A10)
- Agent-3: Knowledge graph + highlight reels (A3, A9)
- Agent-4: Video UI + clips UI (A2)
- Agent-5: Cover letter generator (A5)
- Agent-7: Electron video recording + phone call support (A1, A8)

**Phase 4 (Weeks 17-24):** 5-6 agents in parallel
- Agent-1: Security audit (G10)
- Agent-2: Performance optimization (G5)
- Agent-3: Agent marketplace (G3)
- Agent-4: Frontend migration (G2)
- Agent-6: Mobile app (G1 — dedicated)
- Agent-7: Test coverage (G6)

---

## PART 5: MONETIZATION MODEL

### Free Tier (BYOK — stays free forever)
| Feature | Limit |
|---------|-------|
| Voice transcription (local Whisper) | Unlimited |
| AI chat (any provider) | Unlimited |
| Interview copilot | Unlimited |
| Meeting notes | Unlimited |
| Job tracking | Up to 50 saved |
| Cloud sync | None (local only) |
| Team features | None (single user) |
| Community support | Yes |

### Cloud Tier ($9-19/mo)
| Feature | Limit |
|---------|-------|
| Everything in Free | Unlimited |
| Cloud sync (E2E encrypted) | Unlimited |
| Team workspaces | Up to 5 members |
| Public share links | Unlimited |
| Custom AI templates | Unlimited |
| Video recording + clips | 10 hrs/month |
| Priority support | Email |

### Enterprise Tier ($29-99/mo)
| Feature | Limit |
|---------|-------|
| Everything in Cloud | Unlimited |
| SSO (SAML 2.0, OIDC) | Yes |
| SOC 2 reports | Yes |
| GDPR compliance | Yes |
| Dedicated hosting | Optional |
| Audit logging | Extended |
| SLA | 99.9% |
| Priority support | 24/7 |

---

## PART 6: MASTER AGENT ARCHITECTURE (Deep Dive)

### Architecture

```
User Input (text/voice/screenshot)
        │
        ▼
┌─────────────────────────────┐
│   INTENT CLASSIFIER         │
│   (LLM-based, <200ms)       │
│                             │
│   "summarize my meeting" →  │
│    Meeting Agent            │
│   "help me answer this" →   │
│    Interview Coach          │
│   "what do I know about X"  │
│    → Knowledge Agent        │
│   "optimize my resume" →    │
│    Career Agent             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│   CONTEXT BUILDER           │
│   Gathers:                  │
│   ├─ Current transcript     │
│   ├─ Conversation history   │
│   ├─ Knowledge graph        │
│   ├─ User preferences       │
│   └─ Relevant documents     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│   TOOL ROUTER               │
│   Selects tools:            │
│   ├─ Search knowledge graph │
│   ├─ Query interview DB     │
│   ├─ Analyze transcript     │
│   ├─ Generate suggestions   │
│   ├─ Fetch documents        │
│   └─ Web search             │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│   RESPONSE GENERATOR        │
│   (Multi-provider AI)       │
│   ├─ Primary: User's choice │
│   ├─ Race mode (fastest)    │
│   └─ Fallback chain         │
└──────────┬──────────────────┘
           │
           ▼
      Response → User
```

### Key Design Decisions

1. **Single orchestrator, multiple sub-agents** — Clean routing without over-engineering
2. **LLM-based intent classification** — More accurate than keyword matching
3. **Tool-based architecture** — Each capability is a tool the agent can invoke
4. **Context window management** — Sliding window of recent conversation + relevant graph context
5. **Race mode for latency** — Query multiple providers, return fastest
6. **Fallback chain** — If all cloud providers fail, fall back to local Ollama

---

## PART 7: RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep — trying to do everything | HIGH | HIGH | Strict phase gates; no feature moves up without completing current phase |
| Mobile app delay (6-8 wks) | MEDIUM | HIGH | Start Phase 4 week 1; PWA works as interim |
| SOC 2 audit failure | MEDIUM | HIGH | Do Phase 0 security fixes FIRST; hire auditor in Phase 2 |
| Cloud sync complexity | MEDIUM | MEDIUM | Start with simple E2E encrypted sync; add features iteratively |
| Open-source competitor (Natively) catches up | HIGH | MEDIUM | Move fast on Master Agent + integrations — our moat is hybrid vertical |
| LLM API cost for cloud tier | MEDIUM | MEDIUM | BYOK model keeps costs low; cloud tier uses pooled keys |
| Frontend framework migration stalls | MEDIUM | LOW | Hybrid approach means no need to migrate everything |
| Team burnout with 8 agents | MEDIUM | HIGH | Phase overlaps with buffer weeks; realistic timelines |

---

## PART 8: SUCCESS METRICS

| Metric | Current | 3-Month Target | 6-Month Target |
|--------|---------|----------------|----------------|
| GitHub stars | ~100 (est.) | 500 | 2,000+ |
| Active users | Unknown | 1,000 DAU | 10,000 DAU |
| Interview questions | ~100 templates | 500 curated | 1,000+ curated |
| Response time | ~500ms | <200ms | <150ms |
| Test coverage | ~2K lines | 40% | 60%+ |
| Cloud tier subscribers | 0 | 100 | 1,000 |
| Monthly revenue | $0 | $900-1,900 | $9,000-19,000 |
| Integrations (native) | 3 (partial) | 8 | 15+ |
| Platforms | Desktop + PWA | + Chrome ext | + Mobile + Web |

---

## SUMMARY: What to Build, In What Order, With Whom

| Phase | Weeks | Agents | Key Deliverables | Business Impact |
|-------|-------|--------|------------------|-----------------|
| **0: Foundation** | 1-2 | 4 | Security fixes, Redis, MCP, CRM | Can deploy safely |
| **1: Parity** | 3-6 | 5 | Caption overlay, Master Agent, RBAC, Slack | Feature-complete vs competitors |
| **2: Cloud** | 7-10 | 6 | Cloud sync, Stripe, SSO, SOC 2, GDPR | Revenue + enterprise ready |
| **3: Advanced** | 11-16 | 5 | Video, clips, auto-apply, graph, Notion/Jira | Market differentiation |
| **4: Growth** | 17-24 | 6 | Mobile app, React migration, 60% tests, CDN | Scale + community |

**Total: 24 weeks with 4-8 agents working in parallel.**

---

*Generated: April 25, 2026*
*Based on: Full codebase audit + competitive analysis of 25+ competitors + fresh April 2026 market research*
