# Historical model comparisons and task assignments — historical source records

These are dated source records preserved during documentation consolidation. Their prices, legal statements, feature completion claims, paths, and benchmark numbers have not been revalidated. They are not current setup instructions or release acceptance results.

Current guide: [Historical model comparisons and task assignments](../research/model-comparisons-2026-04/README.md).

## Source index
- [COMPETITIVE_ANALYSIS_2026-04-08_MINIMAX_M2.md](#source-competitive-analysis-2026-04-08-minimax-m2)
- [COMPETITIVE_ANALYSIS_2026_glm-5.1_cloud.md](#source-competitive-analysis-2026-glm-5-1-cloud)
- [TASKS_GLM-5.1.md](#source-tasks-glm-5-1)
- [TASKS_KIMI-K2.5.md](#source-tasks-kimi-k2-5)
- [TASKS_MINIMAX-M2.md](#source-tasks-minimax-m2)
- [TASK_ASSIGNMENT_BY_MODEL.md](#source-task-assignment-by-model)
- [TASK_ASSIGNMENT_SHEETS.md](#source-task-assignment-sheets)

<a id="source-competitive-analysis-2026-04-08-minimax-m2"></a>

## Source: COMPETITIVE_ANALYSIS_2026-04-08_MINIMAX_M2.md

<details>
<summary>Read the original source record</summary>

# AI Note Taker - Competitive Analysis & Production Upgrade Roadmap
**Date:** April 8, 2026
**Model:** minimax-m2:cloud
**Analysis Type:** Comprehensive Competitive Intelligence Report

---

## 1. OUR APPLICATION GOALS

### Primary Mission
**"Democratize AI interview assistance - Premium features, zero cost"**

### Core Value Propositions
| Pillar | Description | Status |
|--------|-------------|--------|
| **Free Forever** | No subscription, no credit cards, no limits | ✅ Unique |
| **Open Source** | Auditable, customizable, community-driven | ✅ Unique |
| **Multi-Provider AI** | Not locked to one AI vendor (8+ providers) | ✅ Unique |
| **Privacy First** | Local processing, no data mining | ✅ Unique |
| **Comprehensive** | Interview + Meeting + Career tools | ✅ Unique |

### Target Users
1. **Job Seekers** - Interview preparation and real-time assistance
2. **Students** - Mock interviews, study plans
3. **Career Switchers** - Resume review, skill assessment
4. **Professionals** - Meeting notes, CRM integration
5. **Remote Workers** - Collaboration, productivity

---

## 2. UPDATED COMPETITIVE LANDSCAPE (2026)

### 2.1 Premium Competitors ($29-800/month)

#### FinalRound AI ($149/mo)
**Strengths:**
- 2M+ mock interview question database
- Strong brand recognition (10M+ users)
- AI Resume Builder + Cover Letter Generator
- Auto-apply feature
- Behavioral + technical + salary negotiation

**Weaknesses:**
- Most expensive in market ($1,788/year)
- Single AI provider (locked in)
- No document RAG
- No vision capabilities
- 350ms+ response time
- Closed source

**Our Advantage:**
- ✅ Free vs $149/mo (saves $1,788/year)
- ✅ 8+ AI providers vs 1
- ✅ Document intelligence they lack
- ✅ Screenshot analysis they lack
- ✅ Editable summaries they lack

**Gap to Close:**
- ⚠️ Expand mock library (we have 27, they have 2M+)
- ⚠️ Auto-apply feature (risky from ethics standpoint)

---

#### LockedIn AI ($55/mo)
**Strengths:**
- 116ms response time (fastest in market)
- Duo mode (collaboration during interviews)
- VSCode/Cursor integration
- WebSearch built-in
- Career Launchpad tools
- Stealth Mode (20+ invisibility features)
- 90%+ accuracy claims

**Weaknesses:**
- Credit-based pricing (unpredictable)
- Limited document features
- No vision AI
- No analytics depth
- Premium stealth features cost extra

**Our Advantage:**
- ✅ Document RAG they lack
- ✅ Vision/screenshots they lack
- ✅ Advanced analytics they lack
- ✅ Editable summaries they lack
- ✅ Free vs $55/mo (saves $660/year)

**Gap to Close:**
- ⚠️ Response time optimization (we're ~500ms vs their 116ms)
- ⚠️ Duo feature (we have alternative ✅)
- ⚠️ Career tools (we have Job Tracker ✅)

---

#### Interview Coder ($29-799/mo)
**Strengths:**
- 5,000+ real FAANG interview problems
- Sub-2-second AI explanations
- 30,000+ weekly active community
- Screenshot capture for LeetCode/HackerRank
- 99% invisibility claims
- 12+ languages (Python, Java, C++, Go, Rust, TypeScript)
- Free tier with 100+ problems

**Weaknesses:**
- Coding-only (no behavioral/system design)
- No document features
- No meeting tools
- Ethically questionable (stealth cheating)
- Extremely expensive for full suite

**Our Advantage:**
- ✅ Free vs $29-799
- ✅ Behavioral + technical interviews
- ✅ Document RAG
- ✅ Meeting features
- ✅ Legal/ethical approach

**Gap to Close:**
- ⚠️ IDE extension polish (we have basic version)
- ⚠️ Add complexity badges (already implemented ✅)

---

### 2.2 Mid-Tier Competitors ($10-59/month)

#### MeetGeek ($15-59/mo)
**Strengths:**
- AI Voice Agents (unique innovation)
- 95%+ transcription accuracy
- Chrome extension (bot-free recording)
- 7,000+ integrations
- 60+ language support
- Meeting templates

**Weaknesses:**
- No interview focus
- No document RAG
- No vision capabilities
- Expensive for what you get

**Our Advantage:**
- ✅ Interview focus
- ✅ Document RAG
- ✅ Vision AI
- ✅ Free vs $15-59/mo

**Gap to Close:**
- ⚠️ AI Voice Agent (biggest gap - they have it, we don't)
- ⚠️ Chrome extension polish (we have MVP)
- ⚠️ Integration count (7,000+ vs our MVP)

---

#### Fireflies AI ($10-20/mo)
**Strengths:**
- 100+ language support
- AskFred AI search assistant
- Topic Tracker for governance
- 95%+ transcription accuracy
- Built-in meeting intelligence

**Weaknesses:**
- No interview-specific features
- No document RAG
- No vision AI

**Our Advantage:**
- ✅ Interview focus we have
- ✅ Document RAG
- ✅ Vision AI
- ✅ Free vs $10-20/mo

---

#### Fathom (Free-$19/mo)
**Strengths:**
- Unlimited free recording tier
- 30-second summary generation
- Native HubSpot/Salesforce integration
- Real-time coaching features

**Weaknesses:**
- Limited to meetings (no interview focus)
- No document features
- No vision AI

**Our Advantage:**
- ✅ Interview-specific features
- ✅ Document RAG
- ✅ Vision AI

---

### 2.3 Open Source Competitors (2026 - NEW THREAT)

#### Natively (GitHub: evinjohnn/natively-cluely-ai-assistant)
**Stats:** 876 stars, AGPL-3.0 License

**Strengths:**
- Real-time AI interview copilot
- Undetectable stealth mode
- Dual audio channels
- Local RAG memory
- BYOK (Bring Your Own Key)
- Supports GPT, Claude, Gemini, Ollama (offline mode)
- Screenshot OCR for LeetCode/HackerRank

**Weaknesses:**
- Newer project (less mature)
- No meeting tools
- No job tracker
- No Chrome extension

**Our Advantage:**
- ✅ Meeting tools they lack
- ✅ Job tracker
- ✅ Chrome extension MVP
- ✅ More comprehensive suite

---

#### Interview Coder Without Paywall (GitHub: greeneu/interview-coder-withoupaywall-opensource)
**Stats:** 1,815 stars

**Strengths:**
- Screenshot capture + GPT-4o analysis
- 99% invisibility
- LeetCode/HackerRank focused
- Free, uses your own OpenAI API key

**Weaknesses:**
- Coding-only
- No behavioral/system design
- No document features

**Our Advantage:**
- ✅ Full interview suite
- ✅ Document RAG
- ✅ Meeting tools

---

#### Friday (GitHub: mostofashakib/Friday)
**License:** MIT

**Strengths:**
- AI mock interview coach
- Adaptive difficulty (5 levels: Entry → Staff/Principal)
- Multi-agent loop (Interviewer, Grader, Follow-up, Coach)
- RAG-powered gap detection
- Voice-first interface with ElevenLabs TTS
- Built with LangGraph, Claude, FastAPI, Next.js 15

**Weaknesses:**
- Practice only (no real-time assistance)
- New project
- No live interview features

**Our Advantage:**
- ✅ Real-time live interview assistance
- ✅ Stealth mode during actual interviews

---

#### Carific.ai
**License:** MIT

**Strengths:**
- Open-source AI career agents
- Resume Editor, Interview Coach, Career Path Generator
- 100+ resumes processed
- Weekly public builds

**Weaknesses:**
- Less feature-rich than ours
- No real-time assistance
- No meeting tools

**Our Advantage:**
- ✅ Real-time assistance
- ✅ Meeting tools
- ✅ Chrome extension

---

## 3. DEEP FEATURE COMPARISON MATRIX

| Feature | FinalRound | LockedIn | MeetGeek | Fireflies | Natively (OSS) | **Our App** |
|---------|------------|----------|----------|-----------|----------------|-------------|
| **Price** | $149/mo | $55/mo | $15-59/mo | $10-20/mo | Free | **FREE** ✅ |
| **Real-time AI** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Multi-Provider AI** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Document RAG** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Vision/Screenshot OCR** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Mock Library** | **2M+** | Limited | ❌ | ❌ | ❌ | ⚠️ 27 |
| **IDE Integration** | ❌ | ✅ | ❌ | ❌ | ✅ | ⚠️ MVP |
| **AI Voice Agent** | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Stealth Mode** | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| **Duo/Collaboration** | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Chrome Extension** | ❌ | ⚠️ | ✅ | ❌ | ❌ | ⚠️ MVP |
| **Analytics Dashboard** | ⚠️ Basic | ⚠️ Basic | ✅ | ✅ | ❌ | ✅ Advanced |
| **Open Source** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Local Processing** | ❌ | ⚠️ | ❌ | ❌ | ✅ | ✅ |
| **Meeting Tools** | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Job Tracker** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Resume Builder** | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **CRM Integration** | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| **SSO/Enterprise** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 4. COMPETITIVE POSITION SCORE

### Scoring Breakdown

| Category | Score | Notes |
|----------|-------|-------|
| **Feature Coverage** | 85% | Competitors average 55-60% |
| **Price Competitiveness** | 100% | Free beats all paid tools |
| **Uniqueness** | 92% | Multi-provider, vision, open source |
| **Production Readiness** | 45% | Security/scaling gaps remain |

**Overall Score: 80.5%** - Strong feature set, needs production hardening

### Where We Win
1. **Document Intelligence** - Only app with document RAG + vision + meeting tools
2. **Multi-Provider Choice** - Users control their AI destiny
3. **Comprehensive Suite** - Interview + Meeting + Career in one
4. **Open Source + Free** - Enterprise-grade without enterprise pricing
5. **Vision for Coding** - Screenshot OCR works on LeetCode/HackerRank

### Where We Lose
1. **AI Voice Agent** - MeetGeek's unique differentiator
2. **Response Time** - 116ms (LockedIn) vs ~500ms (ours)
3. **Mock Library** - 27 vs 2M+ (FinalRound) or 5,000+ (Interview Coder)
4. **Brand Recognition** - 10M+ users (FinalRound) vs our early stage

---

## 5. PRODUCTION READINESS GAP ANALYSIS

### 5.1 Critical Production Gaps (P0 - Must Fix)

#### 1. Security & Compliance
| Item | Current | Required | Priority |
|------|---------|----------|----------|
| **HTTPS/TLS** | ❌ HTTP only | ✅ SSL certificate | P0 |
| **API Authentication** | ⚠️ Basic JWT | ✅ JWT/API Keys + refresh tokens | P0 |
| **Rate Limiting** | ⚠️ Basic | ✅ 100 req/min per user | P0 |
| **Input Validation** | ⚠️ Basic | ✅ Strict validation + sanitization | P0 |
| **XSS Protection** | ⚠️ Basic | ✅ CSP headers + sanitization | P0 |
| **Penetration Testing** | ❌ None | ✅ Full security audit | P0 |

#### 2. Database & Storage
| Item | Current | Required | Priority |
|------|---------|----------|----------|
| **Database** | JSON files | ✅ PostgreSQL | P0 |
| **Backup** | ❌ None | ✅ Automated daily | P0 |
| **Encryption at Rest** | ❌ None | ✅ AES-256 | P0 |
| **File Storage** | Local FS | ✅ S3/Cloud option | P1 |
| **Conversation History** | ⚠️ Local only | ✅ Cloud sync | P1 |

#### 3. Monitoring & Observability
| Item | Current | Required | Priority |
|------|---------|----------|----------|
| **Logging** | ⚠️ Console | ✅ Structured (ELK stack) | P0 |
| **Error Tracking** | ❌ None | ✅ Sentry | P0 |
| **Metrics** | ❌ None | ✅ Prometheus/Grafana | P0 |
| **Health Checks** | ✅ Basic | ✅ Comprehensive | OK |
| **APM** | ❌ None | ✅ New Relic/Datadog | P1 |

#### 4. Testing & QA
| Item | Current | Required | Priority |
|------|---------|----------|----------|
| **Unit Tests** | ⚠️ 75 tests | ✅ 80%+ coverage | P0 |
| **Integration Tests** | ❌ None | ✅ Full suite | P0 |
| **E2E Tests** | ❌ None | ✅ Playwright | P1 |
| **Load Tests** | ❌ None | ✅ k6/locust | P0 |
| **Security Tests** | ❌ None | ✅ Penetration testing | P0 |

---

### 5.2 Scalability Gaps (P1)

#### Infrastructure Requirements
```
Current: Single server, local files
Required:
  - Docker containers
  - Kubernetes orchestration
  - Auto-scaling (HPA)
  - CDN for static assets
  - Redis caching
  - Load balancer
  - Multi-region deployment
```

#### Performance Targets
| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Response Time | ~500ms | <200ms | 2.5x slower |
| Concurrent Users | ~10 | 10,000+ | 1000x |
| Uptime | N/A | 99.9% | N/A |
| Throughput | Unknown | 1000 req/s | Unknown |

---

### 5.3 Feature Gaps for Production

#### Must-Have (Before Production)
| Feature | Competitor Status | Our Status | Priority |
|---------|-------------------|------------|----------|
| **AI Voice Agent** | MeetGeek has | ❌ Missing | P0 |
| **Chrome Extension** | MeetGeek/Convo | ✅ MVP ready | P1 (polish needed) |
| **Cloud Sync** | All have | ❌ Local only | P0 |
| **SSO/SAML** | Enterprise need | ❌ Missing | P1 |
| **Audit Logs** | Compliance | ❌ Missing | P0 |
| **Mock Library Expansion** | FinalRound: 2M+ | ⚠️ 27 | P0 |

#### Nice-to-Have (Post-Production)
| Feature | Competitor | Priority |
|---------|-----------|----------|
| AI-generated cover letters | FinalRound | P2 |
| Auto-apply | FinalRound | P2 (ethics concern) |
| LinkedIn integration | N/A | P2 |
| Interview scheduling | N/A | P2 |
| Salary negotiation assistant | FinalRound | P3 |
| AR/VR interview practice | N/A | P3 |

---

## 6. PRODUCTION UPGRADE ROADMAP

### Phase 1: Security & Compliance (Month 1)
- [ ] SSL/TLS certificates (Let's Encrypt)
- [ ] JWT authentication with refresh tokens
- [ ] Rate limiting (100 req/min per user)
- [ ] Input sanitization & validation
- [ ] CSP headers & XSS protection
- [ ] Security audit & penetration testing
- [ ] SOC 2 compliance start

**Cost:** ~$500 (certs, security tools)
**Effort:** 1-2 weeks

---

### Phase 2: Database & Infrastructure (Month 1-2)
- [ ] Migrate JSON → PostgreSQL
- [ ] Redis caching layer
- [ ] File storage (S3/MinIO)
- [ ] Automated backup system
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] Monitoring stack (Prometheus/Grafana)
- [ ] Error tracking (Sentry)

**Cost:** ~$500-1000/month (cloud infrastructure)
**Effort:** 3-4 weeks

---

### Phase 3: Critical Features (Month 2-3)
- [ ] AI Voice Agent (biggest gap)
- [ ] Cloud sync (cross-device)
- [ ] Chrome extension polish
- [ ] Mock library expansion (27 → 50,000+)
- [ ] Mobile app (React Native)

**Cost:** ~$3000-6000 (development time)
**Effort:** 6-10 weeks

---

### Phase 4: Scale & Optimize (Month 3-4)
- [ ] Load testing & performance tuning
- [ ] CDN setup
- [ ] Auto-scaling configuration
- [ ] Multi-region deployment
- [ ] SSO/Enterprise features

**Cost:** ~$2000-3000/month (scaled infrastructure)
**Effort:** 4-6 weeks

---

## 7. COST ANALYSIS

### Current Cost: $0/month
- Running locally
- No infrastructure
- Manual maintenance

### Production Cost Estimate

| Tier | Users | Cost/Month | Components |
|------|-------|------------|------------|
| **Starter** | 100 | $50-100 | VPS, PostgreSQL, basic monitoring |
| **Growth** | 1,000 | $200-500 | Kubernetes, CDN, Redis |
| **Scale** | 10,000 | $1000-2000 | Multi-region, auto-scale |
| **Enterprise** | 100,000 | $5000+ | Dedicated infra, SLA |

### Revenue Options (Since Free)
1. **Freemium Model** - Keep core free, charge for AI Voice Agent, Cloud Sync
2. **Enterprise Support** - Paid support contracts
3. **Cloud-Hosted Version** - Subscription for managed version
4. **Donations** - GitHub Sponsors, Open Collective

---

## 8. STRATEGIC RECOMMENDATIONS

### Short-term (0-3 months) - Critical
1. **Fix security gaps** - Can't launch without HTTPS/auth
2. **Database migration** - JSON files won't scale
3. **Add AI Voice Agent** - Biggest competitive gap (MeetGeek's advantage)
4. **Polish Chrome extension** - Critical for user acquisition
5. **Expand mock library** - 27 → 50,000+ problems

### Medium-term (3-6 months)
1. **Kubernetes deployment** - Auto-scaling, reliability
2. **Cloud sync** - Cross-device experience
3. **Mobile native app** - iOS/Android
4. **Enterprise features** - SSO, audit logs

### Long-term (6-12 months)
1. **AI Career Agent** - Autonomous job search
2. **Integration marketplace** - LinkedIn, Indeed, etc.
3. **Community features** - User-generated questions
4. **Enterprise sales** - B2B offering

---

## 9. OPEN SOURCE COMPETITION THREAT

**NEW IN 2026:** Open source alternatives are emerging that directly compete with our value proposition.

### Threat Assessment
| Competitor | Threat Level | Why |
|------------|--------------|-----|
| Natively | Medium | Similar features, newer project, 876 stars |
| Interview Coder OSS | Medium | Focused on coding, 1,815 stars |
| Friday | Low-Medium | Voice-first, MIT license, practice only |

### Mitigation Strategy
1. **Move faster** - Ship features before OSS can catch up
2. **Community building** - Build contributor base
3. **Documentation** - Make OSS alternatives look incomplete
4. **Integration** - Better UX, easier onboarding

---

## 10. CONCLUSION

### Current State: **BETA-READY, NOT PRODUCTION-READY**

**Strengths:**
- Feature-rich (85% coverage vs competitors' 55%)
- Unique value prop (free + open source + multi-provider)
- Technical foundation solid
- Fast development velocity

**Blockers for Production:**
- Security (no HTTPS, basic auth)
- Database (JSON files)
- Monitoring (blind deployment)
- Mock library (27 vs 2M+)

**Time to Production:** 2-3 months with focused effort

**Biggest Differentiator:** Free + Open Source + Multi-provider AI + Vision
**Biggest Gap:** AI Voice Agent (MeetGeek's competitive advantage)
**Biggest Threat:** Open source alternatives (Natively, Interview Coder OSS)

---

**Recommendation:**
- ✅ **Launch as open-source beta** immediately
- 🔧 **Production deployment** after security hardening
- 🚀 **Compete on features + price** (already winning)
- ⚠️ **Watch OSS competition** - move faster than they can copy

---

## 11. SOURCES

- [Final Round AI vs LockedIn AI Review](https://www.lockedinai.com/blog/finalroundai-vs-lockedinai-comprehensive-review)
- [LockedIn AI vs Final Round AI Comparison](https://www.lockedinai.com/compare/lockedinai-vs-final-round-ai)
- [Interview Coder vs Final Round AI](https://www.interviewcoder.co/blog/interviewcoder-vs-final-round-ai)
- [Best AI Meeting Minutes Tools 2026](https://www.hugo.team/blog/best-ai-meeting-minutes-tools)
- [MeetGeek Review 2026](https://max-productive.ai/ai-tools/meetgeek/)
- [Fathom AI Review 2026](https://max-productive.ai/ai-tools/fathom/)
- [Natively - Open Source Interview Copilot](https://github.com/evinjohnn/natively-cluely-ai-assistant)
- [Interview Coder Without Paywall (Open Source)](https://github.com/greeneu/interview-coder-withoupaywall-opensource)
- [Friday - AI Mock Interview Coach](https://github.com/mostofashakib/Friday)
- [Best Cluely Alternatives After Data Breach](https://geekbye.com/blog/best-cluely-alternatives)
- [Free AI Interview Copilot Tools 2026](https://ophyai.com/blog/career-advice/free-ai-interview-copilot-tools-comparison/)
- [Best AI Interview Software 2026](https://interviewsidekick.com/blog/best-ai-interview-software)
- [AI Vision Models 2026 Practical Guide](https://www.aimagicx.com/blog/ai-vision-models-image-understanding-guide-2026)

---

*Analysis completed on April 8, 2026*
*Model: minimax-m2:cloud*
*Next review: After Phase 1 security implementation*

</details>

<a id="source-competitive-analysis-2026-glm-5-1-cloud"></a>

## Source: COMPETITIVE_ANALYSIS_2026_glm-5.1_cloud.md

<details>
<summary>Read the original source record</summary>

# ANT (AI Note Taker) - Competitive Analysis & Production Readiness Assessment

**Date**: April 2026  
**Scope**: Feature comparison with market competitors, deep-dive gap analysis, and production upgrade roadmap

---

## Market Overview

- **AI Note-Taking Market**: ~$450-535M (2024), projected $1.8-2.5B by 2032 (CAGR 18.9%)
- **150+ active competitors** globally
- Top 5 players hold ~58-62% of enterprise deployments
- ~62% of digital-native knowledge workers now use AI notetaking tools
- North America holds ~34-38% market share

---

## Competitor Feature Matrix: AI Note-Taking

| Feature | Otter.ai | Fireflies.ai | tl;dv | Fathom | Grain | **ANT** |
|---|---|---|---|---|---|---|
| **Transcription** | Real-time, 4 langs | Post-meeting, 100+ langs | Post-meeting, 30+ langs | Post-meeting, 25 langs | Post-meeting, 130+ langs | Whisper (local/cloud) |
| **Accuracy** | ~90% | ~95% | Good | ~95% | Good | TBD |
| **AI Summary** | ✅ | ✅ | ✅ | ✅ (instant) | ✅ | ✅ |
| **Action Items** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Cross-Meeting Search** | ✅ | ✅ (AskFred) | ✅ (Ask tl;dv) | ✅ (Ask Fathom) | ✅ (Ask Grain) | ✅ (via RAG) |
| **CRM Integration** | Salesforce, HubSpot | 5+ CRMs | Salesforce, HubSpot, Pipedrive | Salesforce, HubSpot | HubSpot, Salesforce | ❌ CRM config only |
| **API Access** | Enterprise | Public API | Zapier | Business plan | Yes | ✅ Full REST API |
| **SOC 2 Type II** | ✅ | ✅ | ❌ (Type I) | ✅ | ✅ | ❌ |
| **HIPAA** | ✅ (add-on) | ✅ (with BAA) | ❌ | ✅ | ❌ | ❌ |
| **GDPR** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **SSO/SCIM** | ✅ Enterprise | ✅ Enterprise | ✅ Enterprise | ✅ Team+ | ✅ Enterprise | ❌ |
| **Encryption** | AES-256 + TLS | AES-256 + TLS 1.2+ | AES-256 + SSL/TLS | E2E | AES-256 + SSL | Basic (no at-rest) |
| **Mobile App** | iOS + Android | iOS + Android | iOS + Android (Lite) | Coming soon | ❌ | ❌ |
| **Desktop App** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Electron |
| **Bot-Free Option** | ✅ Desktop | ❌ | ❌ | Coming soon | ✅ | ✅ Native |
| **MCP Server** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| **Voice Cloning** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ RVC + Edge TTS |
| **Interview Practice** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Full suite |
| **Job Tracking** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Full pipeline |
| **Knowledge Graph** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Neo4j |
| **Collaboration** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Duo mode |
| **Free Tier** | 300 min/mo | 800 min total | Unlimited rec/transcripts | Unlimited rec/trans | Unlimited (45-min cap) | N/A (self-hosted) |
| **Paid From** | $8.33/mo | $10/mo | $18/mo | $15/mo | $15/mo | Self-hosted |
| **Unique** | AI Meeting Agents, Live transcription | 200+ AI Skills, FERPA | EU-hosted, best free tier | Highest rated (G2 5.0), best accuracy | No-bot, clips/playlists | Interview prep + notes + voice clone |

---

## Competitor Feature Matrix: AI Interview Prep

| Feature | Yoodli | BigInterview | Pramp/Exponent | Interviewing.io | **ANT** |
|---|---|---|---|---|---|
| **Mock Interviews** | AI roleplay | AI + video | Peer + AI | Human (FAANG) + AI | AI + real-time |
| **Real-Time Coaching** | ✅ (live nudges) | ❌ | ❌ | ❌ | ✅ Shadow agent |
| **Speech Analytics** | ✅ (pacing, fillers) | Limited | ❌ | ❌ | ✅ (STAR, pace, fillers) |
| **Voice Cloning** | ❌ | ❌ | ❌ | ❌ | ✅ RVC + TTS |
| **Company-Specific** | ✅ | ✅ (from JD) | ✅ (filter) | ✅ (FAANG) | ✅ (knowledge graph) |
| **Knowledge Graph** | ❌ | ❌ | ❌ | ❌ | ✅ Neo4j |
| **Curriculum** | ❌ | 170 video lessons | Courses ($79/mo) | Replay library | Study plans |
| **Answer Builder** | ❌ | ✅ (STAR) | ❌ | ❌ | ❌ |
| **SOC 2** | ✅ Type 2 | ❌ | ❌ | ❌ | ❌ |
| **GDPR** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Pricing** | Free-$20/mo | $39-$299 | Free-$79/mo | Free-$225/session | Self-hosted |

---

## ANT's Unique Differentiators (What NO Competitor Has)

1. **Hybrid Note-Taking + Interview Prep**: No other tool combines both. Otter/Fireflies/tl;dv are note-only. Yoodli/BigInterview are interview-only.
2. **Voice Cloning for Interview Practice**: RVC + Edge TTS allows users to practice with different interviewer voices. Unique in the market.
3. **Knowledge Graph (Neo4j)**: Persistent entity-relationship graph connecting companies, skills, topics, questions, and user history. No competitor offers this.
4. **Shadow Interview Agent**: Real-time coaching during actual interviews with live suggestions. Only Yoodli offers something similar.
5. **Job Application Tracker**: Full pipeline from application → interview → offer → onboarding. No note-taking tool has this.
6. **Self-Hosted + BYOK**: Users own their data, bring their own API keys. Privacy-first. Most competitors are cloud-only SaaS.
7. **Desktop-First (Electron)**: Native desktop experience with stealth mode, auto-screenshots, global hotkeys. Most competitors are web-only.
8. **Multi-Provider AI Router**: Race mode across 8+ providers simultaneously. No competitor offers this flexibility.
9. **Performance Analytics**: STAR method detection, filler word tracking, speaking pace, code quality scoring. Only Yoodli offers comparable analytics.

---

## Production Readiness Gap Analysis

### CRITICAL (Must Fix Before Production)

| # | Gap | Risk | Fix Effort |
|---|---|---|---|
| 1 | **No database** (flat JSON files for users, conversations, job apps) | Data loss, corruption, no concurrent access | Medium (add PostgreSQL/SQLite) |
| 2 | **CORS open to all origins** (`allow_origins=["*"]`) | XSS, CSRF, data theft | Low (whitelist origins) |
| 3 | **Auth not enforced** (JWT exists but most endpoints unprotected) | Anyone can access all data | Medium (add auth middleware) |
| 4 | **No encryption at rest** (conversations, API keys stored in plain files) | Data breach if filesystem compromised | Medium (add encryption layer) |
| 5 | **`webSecurity: false`** in Electron | Disables same-origin policy | Low (remove flag) |
| 6 | **`allowRunningInsecureContent: true`** in Electron | Allows mixed content | Low (set to false) |
| 7 | **CSP allows `unsafe-inline`** for scripts/styles | Weakens XSS protection significantly | Medium (use nonce-based CSP) |
| 8 | **No HTTPS enforcement** (`HTTPS_REQUIRED = False`) | Data in transit can be intercepted | Low (enable HTTPS) |
| 9 | **Neo4j default password "password"** | Database compromise | Low (require strong password) |
| 10 | **WebSocket endpoints have no auth** (`/ws`, `/ws/transcribe`) | Anyone can connect and stream | Medium (add token validation) |

### HIGH PRIORITY (Should Fix for Public Launch)

| # | Gap | Competitor Standard | Fix Effort |
|---|---|---|---|
| 11 | **No SOC 2 compliance** | All major competitors have SOC 2 Type II | High (audit process) |
| 12 | **No GDPR compliance** | All EU-available competitors comply | High (legal + technical) |
| 13 | **No rate limiting** on most endpoints | Standard across all SaaS | Low (extend existing decorator) |
| 14 | **No pagination** on list endpoints | Standard in all APIs | Medium |
| 15 | **No audit logging** | Required for enterprise | Medium |
| 16 | **Collaboration uses in-memory storage** | All competitors persist | Low (add DB layer) |
| 17 | **BYOK test endpoint doesn't validate keys** | Fireflies validates real API calls | Low |
| 18 | **No mobile app** | 6/9 competitors have one | Very High |
| 19 | **No CRM real integration** (config only) | Otter/Fireflies have real sync | High |
| 20 | **No data backup/restore** mechanism | Standard in all SaaS | Medium |

### MEDIUM PRIORITY (Improve for Competitive Edge)

| # | Gap | Opportunity | Fix Effort |
|---|---|---|---|
| 21 | **No MCP server** for Claude/Cursor integration | Otter, Fireflies, Grain all offer this | Medium |
| 22 | **No Zapier/integration connectors** | Fireflies has 5000+ | High |
| 23 | **No transcription language support** (English only) | Fireflies supports 100+ languages | High |
| 24 | **No video recording** | All note-taking competitors offer this | High |
| 25 | **No team/organization management** | All enterprise competitors have this | High |
| 26 | **No SSO/SCIM** | Standard for enterprise tiers | High |
| 27 | **No structured error codes** (all return `{"error": str}`) | RESTful standard | Low |
| 28 | **No CI/CD pipeline** | Standard for production | Medium |
| 29 | **No integration tests** (only 3 test files) | Standard for production | Medium |
| 30 | **Feature modules silently degrade** on missing dependencies | Confusing UX | Low (add health checks) |

---

## Recommended Production Upgrade Roadmap

### Phase 1: Security Hardening (2-3 weeks)
1. **Add PostgreSQL/SQLite** for user data, conversations, job applications (replace JSON files)
2. **Enforce CORS origin whitelist** (remove `["*"]`)
3. **Add auth middleware** to all sensitive endpoints
4. **Fix Electron security**: Remove `webSecurity: false`, remove `allowRunningInsecureContent`
5. **Implement nonce-based CSP** (remove `unsafe-inline`)
6. **Add WebSocket auth** (token validation on connect)
7. **Enable HTTPS** with proper certificate management
8. **Change Neo4j default credentials** and require strong password

### Phase 2: Data & API Hardening (2-3 weeks)
9. **Add encryption at rest** for conversations and API keys (AES-256)
10. **Implement pagination** on all list endpoints
11. **Add rate limiting** to all endpoints (extend existing decorator)
12. **Add audit logging** for security-relevant operations
13. **Persist collaboration data** to database
14. **Fix BYOK test** to actually validate API keys
15. **Add structured error codes** (standardized error response format)
16. **Add data backup/restore** endpoints

### Phase 3: Competitive Features (4-6 weeks)
17. **CRM integration** (HubSpot, Salesforce real sync)
18. **MCP server** for Claude/Cursor integration
19. **Mobile app** (React Native or PWA)
20. **Video recording** alongside transcription
21. **Multi-language transcription** (leverage existing Whisper)
22. **Team/organization management** with role-based access
23. **SSO/SCIM** support (SAML, OIDC)
24. **SOC 2 Type II** audit preparation

### Phase 4: Polish & Scale (2-4 weeks)
25. **Feature health checks** UI (show which modules are available)
26. **CI/CD pipeline** (GitHub Actions for test, lint, build, deploy)
27. **Integration test suite** (expand from 3 test files)
28. **Performance monitoring** (APM, error tracking)
29. **Auto-scaling** (Docker, k8s ready)
30. **Documentation** (API docs, user guide, admin guide)

---

## Feature Inventory Summary

| Category | Implemented | Stubbed | Missing |
|---|---|---|---|
| AI Interaction | 10 modes, multi-provider, streaming | - | Video recording |
| Security | JWT, rate limiting (2 endpoints), sanitization | - | Full auth, encryption, compliance |
| Desktop (Electron) | Stealth, auto-screenshot, auto-update, hotkeys | - | Mobile app |
| Voice/TTS | Edge TTS, RVC, 6 gallery voices, browser fallback | True RVC training | Language support |
| Interview Prep | Simulator, shadow agent, mock library, performance analytics | - | Curriculum/lessons |
| Knowledge Graph | Neo4j full CRUD, entity extraction, prediction | - | Auto-ingest pipeline |
| Job Tracker | Full pipeline (20 endpoints) | - | Resume builder |
| Collaboration | Duo mode (6 endpoints) | Persistence | Team management |
| Analytics | Dashboard, skill progression, trends | - | Team analytics |
| Documents/RAG | Upload, chunk, embed, retrieve | - | Multi-format |
| Export/Import | JSON, Markdown, plain text | - | PDF, DOCX export |

**Total endpoints**: 100+  
**Feature-gated modules**: 12 (each gracefully degrades on missing dependencies)  
**Security-critical issues**: 10  
**Production-blocking issues**: 10  
**Competitive gaps**: 20

</details>

<a id="source-tasks-glm-5-1"></a>

## Source: TASKS_GLM-5.1.md

<details>
<summary>Read the original source record</summary>

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

</details>

<a id="source-tasks-kimi-k2-5"></a>

## Source: TASKS_KIMI-K2.5.md

<details>
<summary>Read the original source record</summary>

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

</details>

<a id="source-tasks-minimax-m2"></a>

## Source: TASKS_MINIMAX-M2.md

<details>
<summary>Read the original source record</summary>

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

</details>

<a id="source-task-assignment-by-model"></a>

## Source: TASK_ASSIGNMENT_BY_MODEL.md

<details>
<summary>Read the original source record</summary>

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

</details>

<a id="source-task-assignment-sheets"></a>

## Source: TASK_ASSIGNMENT_SHEETS.md

<details>
<summary>Read the original source record</summary>

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

</details>
