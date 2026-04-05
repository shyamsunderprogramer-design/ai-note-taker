# 2-Month Aggressive Sprint Plan
## "Minimum Unclonable Product" (MUP)

**Goal:** Build features that competitors cannot copy in 6+ months
**Timeline:** 8 weeks (60 days)
**Strategy:** Parallel execution, ruthless prioritization, working prototypes over perfection

---

## Week 1-2: Foundation Sprint (Days 1-14)
**Theme:** Build the data moat

### Parallel Track A: Cognitive Graph (Lead Dev)
**Day 1-3:**
- [ ] Install Neo4j, set up schema
- [ ] Create basic ingestion script
- [ ] Test with 5 sample conversations

**Day 4-7:**
- [ ] Build entity extraction (use OpenAI API, skip training)
- [ ] Create 3 demo queries
- [ ] Simple HTML UI for testing

**Day 8-14:**
- [ ] Ingest all existing conversations
- [ ] Optimize queries (target: <200ms)
- [ ] Merge to main app

**Success:** Can ask "What did I say about React?" and get real answers

---

### Parallel Track B: Predictions Engine (Same Dev or Second)
**Day 1-4:**
- [ ] Scrape Glassdoor (top 50 companies only)
- [ ] Build simple CSV database
- [ ] Create keyword matching algorithm

**Day 5-10:**
- [ ] Add company patterns (easy/medium/hard ratios)
- [ ] Build basic UI (company dropdown, show predictions)
- [ ] Test with 5 known interviews

**Day 11-14:**
- [ ] Integrate with pre-interview flow
- [ ] Add preparation checklist
- [ ] Merge to main

**Success:** Before any interview, shows "80% chance they'll ask X"

---

## Week 3-4: Voice Sprint (Days 15-28)
**Theme:** The "wow" feature

### Voice Clone Agent
**Day 15-17:**
- [ ] Set up RVC (use prebuilt, don't train from scratch)
- [ ] Test with 3 voice samples
- [ ] Build recording UI

**Day 18-21:**
- [ ] Integrate TTS (Coqui or Piper)
- [ ] Connect LLM responses to voice
- [ ] Add simple emotion control (slow/fast)

**Day 22-28:**
- [ ] Build "Practice Mode" UI
- [ ] Record 2-minute demo video
- [ ] Stress test latency (target: <1s)

**Success:** AI speaks as you, 5 beta testers say "this sounds like me"

---

## Week 5-6: Shadow Agent MVP (Days 29-42)
**Theme:** Autonomous capability

### Shadow Interview Agent (MVP)
**Day 29-32:**
- [ ] Build always-on-top transparent overlay
- [ ] Capture screen text (OCR or DOM parsing)
- [ ] Trigger on interview platform detection

**Day 33-36:**
- [ ] Generate responses using Cognitive Graph context
- [ ] Show 3 suggestions in overlay
- [ ] Add hotkey insertion (Ctrl+1, Ctrl+2, Ctrl+3)

**Day 37-42:**
- [ ] Integrate Voice Clone (optional speak mode)
- [ ] Polish UI (minimal, fast)
- [ ] Demo video of full flow

**Success:** During mock interview, AI suggests answers that user accepts

---

## Week 7-8: Polish & Integration (Days 43-60)
**Theme:** Ship it

### Integration Week (Days 43-49)
**Day 43-45:**
- [ ] Merge all features to main branch
- [ ] Feature flags for beta users
- [ ] Fix critical bugs only

**Day 46-49:**
- [ ] Onboard 10 beta testers
- [ ] Collect feedback
- [ ] Quick fixes (1 day max per issue)

### Launch Week (Days 50-60)
**Day 50-53:**
- [ ] Create demo video for landing page
- [ ] Write "What's New" blog post
- [ ] Update README with unique features

**Day 54-57:**
- [ ] Soft launch (Twitter, Reddit, HN)
- [ ] Monitor crash logs
- [ ] Hotfix critical issues

**Day 58-60:**
- [ ] Measure metrics (signups, retention)
- [ ] Plan next sprint based on feedback
- [ ] Celebrate!

---

## Feature Cut List (What We're NOT Building)

To hit 2 months, skip these (add later):

❌ **Skip Phase 1:**
- Behavioral Fingerprint (nice to have, not moat)
- Complex graph queries (start simple)

❌ **Skip Phase 2:**
- Cross-Platform Memory (use local storage for now)
- Advanced Voice emotions (basic speed only)

❌ **Skip Phase 3+:**
- AR Copilot (too early, hardware not ready)
- Biofeedback (hardware dependent)
- Quantum Crypto (overkill for now)
- Everything Phase 4-5

**Keep ONLY:** Cognitive Graph + Predictions + Voice Clone + Shadow Agent MVP

---

## Resource Requirements

### Team (Minimum)
- **1 Full-stack dev (you):** Core features, integration
- **1 ML contractor (optional):** Voice clone tuning (2 weeks only)
- **1 Designer (optional):** UI polish (1 week only)

### Infrastructure
- **Neo4j:** Free community edition (local)
- **OpenAI API:** $100-200/month for embeddings + queries
- **RVC:** Free, runs on consumer GPU
- **Hosting:** Existing infrastructure

### Budget
- **Total:** $500-1000 for 2 months
- **If tight:** Skip contractor, use prebuilt models only

---

## Daily Rhythm

### Morning (2 hours)
- Review yesterday's commits
- Set 3 priorities for today
- Check beta tester feedback

### Deep Work (4-6 hours)
- One major feature only
- No context switching
- Commit every 2 hours

### Evening (1 hour)
- Deploy to staging
- Quick smoke tests
- Document progress
- Plan tomorrow

---

## Success Metrics (Day 60)

| Metric | Target | Why |
|--------|--------|-----|
| Cognitive Graph | 100+ conversations | Data moat established |
| Prediction Accuracy | 60%+ | Better than nothing |
| Voice Clone MOS | >3.0 | Recognizable as user |
| Shadow Agent Latency | <2s | Usable in real interviews |
| Beta Users | 10+ | Validation |
| Retention (Week 2) | 50%+ | Product-market fit signal |

---

## Risk Mitigation

### Week 1-2 Risk: Graph too complex
**Plan B:** Use SQLite + FAISS (simpler, faster)

### Week 3-4 Risk: Voice quality poor
**Plan B:** Use ElevenLabs API (paid but works instantly)

### Week 5-6 Risk: Shadow Agent doesn't work
**Plan B:** Simplify to "suggestion sidebar" only

### Week 7-8 Risk: Integration hell
**Plan B:** Launch features separately (not integrated)

---

## Why This Creates Moat

By Day 60, you have:

1. **Data Moat:** 100+ conversations in graph (competitors start from zero)
2. **Tech Moat:** Voice clone working (requires ML expertise + time)
3. **Feature Moat:** Shadow Agent MVP (complex integration, hard to replicate)
4. **Time Moat:** 2 months ahead minimum

**Competitors would need:**
- 3-6 months to catch up
- ML expertise (rare/expensive)
- User data (impossible to replicate)

---

## Next Actions (Today)

**Right Now:**
1. [ ] Read `UNIQUE_FEATURES_Q1_PLAN.md` Week 1 details
2. [ ] Install Neo4j locally
3. [ ] Create branch `aggressive-sprint`

**This Week:**
- Get Cognitive Graph working (even basic)
- Scrape 50 companies for predictions
- Test RVC voice clone

**Goal:** By end of Week 2, have working demos of all 4 features (even if rough)

---

## Motivation

"The best time to plant a tree was 20 years ago. The second best time is now."

You have 2 months to create a 6-month lead. **Move fast.**

---

**Ready? Start with Task #16 (Cognitive Graph) and Task #18 (Predictions) in parallel.**
