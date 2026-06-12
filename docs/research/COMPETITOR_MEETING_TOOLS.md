# Meeting Tools Competitive Analysis

**Analysis Date:** April 2026  
**Tools Covered:** MeetGeek, Fathom, Convo

---

## 1. MeetGeek - Feature Analysis

**Website:** https://meetgeek.ai/pricing  
**Pricing:** Free → $59/user/month (Enterprise)  
**User Base:** Not publicly disclosed  
**Unique Position:** AI Voice Agents that can autonomously lead meetings

### Core Features

#### Meeting Recording & Transcription
- [x] **100+ language support** with auto-detection
- [x] 95%+ transcription accuracy
- [x] Automatic speaker recognition
- [x] 3 months transcript storage (Free), unlimited (paid)
- [x] 1 month audio storage (Free), unlimited (paid)
- [x] **No-bot recording** via Chrome extension or Desktop app
- [x] **7,000+ integrations** (Slack, Salesforce, HubSpot, Notion, Jira)

#### AI Features
- [x] AI meeting summaries
- [x] AI Next Steps extraction
- [x] AI Chat - query meeting history
- [x] **Voice Agents** - join meetings autonomously
- [x] **Copilot Mode** - talk to MeetGeek during the call
- [x] Sales Mode with objection detection
- [x] Win/loss signals for sales calls
- [x] **MCP Server** - connects Claude/Cursor to meetings

#### AI Voice Agents (October 2025 Launch)
MeetGeek's breakthrough feature - AI agents that don't just record but **actively participate**:

**AI Screen Recruiter Template:**
- Conducts initial candidate screening autonomously
- Asks follow-up questions based on responses
- Generates detailed hiring scorecards
- Schedules qualified candidates for human interviews
- Can screen multiple candidates simultaneously

**AI Lead Discovery Agent:**
- Engages potential customers with discovery questions
- Documents pain points and captures context
- Identifies decision-makers
- Routes qualified leads to account executives
- CRM auto-sync (HubSpot, Salesforce)

**AI Customer Success Agent:**
- Leads client review sessions
- Identifies retention indicators
- Flags at-risk accounts
- Captures expansion opportunities

**AI Scrum Master Agent:**
- Leads standup meetings
- Tracks sprint progress
- Captures blockers and action items

### Pricing Comparison

| Plan | Price | Transcription | Storage | Voice Agents |
|------|-------|---------------|---------|--------------|
| **Free** | $0 | 3 hours/month | 3 months | ❌ |
| **Pro** | $15/mo | 20 hours/month | Unlimited | ❌ |
| **Business** | $29/mo | Unlimited | Unlimited | ✅ |
| **Enterprise** | $59/mo | Unlimited | Custom | ✅ + Custom models |

### Security & Compliance
- [x] SOC 2 Type II certified
- [x] GDPR compliant
- [x] HIPAA ready
- [x] On-premise storage option (Enterprise)
- [x] Zero/Custom data retention policies
- [x] SSO, SCIM support

---

## 2. Fathom - Feature Analysis

**Website:** https://fathom.video (now fathom.ai)  
**Pricing:** Free → $34/user/month  
**User Base:** 500K+ users  
**Unique Position:** Most generous free tier (unlimited recording)

### Core Features

#### Recording & Transcription
- [x] **Unlimited recording** (even on free plan)
- [x] Real-time transcription in 28+ languages
- [x] 95% accuracy with clear audio
- [x] Automatic speaker identification
- [x] Custom dictionary for company terminology
- [x] **Visible bot** joins as "Fathom Notetaker"

#### AI Summaries
- [x] Instant summaries within 30 seconds
- [x] **AI Action Items** (Premium+)
- [x] **14+ custom templates** (BANT, Sandler, etc.)
- [x] "Ask Fathom" - conversational AI for meeting history
- [x] 5 advanced summaries/month (Free), unlimited (Premium+)

#### Sales Features
- [x] CRM sync with HubSpot, Salesforce, Close
- [x] AI scorecards for coaching
- [x] Deal View for pipeline visibility
- [x] Customer View for account history
- [x] Global search across all meetings

#### Collaboration
- [x] Share clips and highlights
- [x] Playlists for training
- [x] Comments and @mentions
- [x] Team collaboration features

### Pricing Comparison

| Plan | Monthly Price | AI Summaries | CRM Sync | Team Features |
|------|--------------|--------------|----------|---------------|
| **Free** | $0 | 5/month | Basic (3 users) | ❌ |
| **Premium** | $20 | Unlimited | ✅ | ❌ |
| **Team** | $19/user | Unlimited | ✅ | ✅ |
| **Business** | $34/user | Unlimited | ✅ + Field sync | ✅ + AI scorecards |

### Security & Compliance
- [x] SOC 2 Type II audited
- [x] HIPAA compliant
- [x] GDPR compliant
- [x] AES-256 encryption at rest
- [x] TLS 1.3 in transit
- [x] Data never used for AI training

### Key Limitations
- ❌ **No stealth mode** - bot visible to all participants
- ❌ **No mobile app** - desktop only
- ❌ Cannot transcribe pre-recorded files
- ❌ Limited free AI summaries (5/month)

---

## 3. Convo - Feature Analysis

**Website:** https://www.itsconvo.com  
**Pricing:** Free → $19.99/month  
**User Base:** Not disclosed  
**Unique Position:** Real-time suggestions with stealth overlay

### Core Features

#### Real-Time Assistance
- [x] Real-time suggestions during calls
- [x] Automatic follow-up email drafting
- [x] Action item extraction
- [x] Conversation analytics (clarity, listening, time, collaboration, decisions)

#### Recording & Transcription
- [x] Automatic meeting transcription
- [x] Real-time meeting notes
- [x] Local audio processing
- [x] Supports Zoom, Teams, Google Meet, Slack, Webex

#### Stealth Mode
- [x] **"No bot joins your call"** - completely invisible
- [x] **Screen overlay** visible only to user
- [x] Audio stays on device
- [x] **Screen-only mode** - records nothing, just live suggestions
- [x] **Keystroke passthrough** - keyboard focus stays in IDE

#### CRM Integration
- [x] Syncs with Salesforce, HubSpot, Pipedrive
- [x] Pulls deal info and contact details
- [x] Pushes tasks to calendars and Slack
- [x] Routes tasks to connected tools

#### Interview Support
- [x] "Stay on script during interviews"
- [x] Auto-generate candidate summaries
- [x] Automated follow-ups with specific references

### Pricing Comparison

| Plan | Price | Models | Features |
|------|-------|--------|----------|
| **Free** | $0 | Standard | Basic features, trial |
| **Professional** | $19.99/mo | Claude Sonnet, GPT-5 | Premium models, full features |

### Security
- [x] AES-256 encryption
- [x] Local processing
- [x] No recording option available

---

## AI Note Taker vs Meeting Tools Comparison

### Features AI Note Taker HAS (✅ Parity or Better)

| Feature | MeetGeek | Fathom | Convo | AI Note Taker | Status |
|---------|----------|--------|-------|---------------|--------|
| Real-time transcription | ✅ | ✅ | ✅ | ✅ | **Parity** |
| AI summaries | ✅ | ✅ | ✅ | ✅ | **Parity** |
| Action items | ✅ | ✅ | ✅ | ✅ | **Parity** |
| Speaker identification | ✅ | ✅ | ✅ | ✅ | **Parity** |
| CRM integration | ✅ | ✅ | ✅ | ✅ | **Parity** |
| Stealth/overlay mode | ❌ | ❌ | ✅ | ✅ | **Parity** |
| Multi-provider AI | ❌ | ❌ | ✅ (2) | ✅ **(8+)** | **Advantage** |
| Screen capture protection | ❌ | ❌ | ✅ | ✅ | **Parity** |
| Editable summaries | ❌ | ❌ | ❌ | ✅ | **Advantage** |
| Document RAG | ❌ | ❌ | ❌ | ✅ | **Advantage** |
| Vision/screenshots | ❌ | ❌ | ❌ | ✅ | **Advantage** |
| Analytics dashboard | Basic | Basic | ✅ | ✅ **Advanced** | **Advantage** |
| Export formats | Limited | Limited | Limited | **MD/JSON/TXT** | **Advantage** |
| Import conversations | ❌ | ❌ | ❌ | ✅ | **Advantage** |
| Open source | ❌ | ❌ | ❌ | ✅ | **Advantage** |
| Price | $15-59/mo | $0-34/mo | $0-20/mo | **FREE** | **Advantage** |

### Features Meeting Tools HAVE that AI Note Taker LACKS (❌ Gaps)

#### HIGH PRIORITY
1. **AI Voice Agents** (MeetGeek)
   - MeetGeek: AI agents can autonomously lead meetings, ask questions, screen candidates
   - AI Note Taker: No autonomous agent capability
   - **Impact:** Very High - cutting-edge feature, massive differentiator
   - **Solution:** Implement AI Voice Agent prototype

2. **No-Bot Recording** (MeetGeek)
   - MeetGeek: Records without visible bot via Chrome extension
   - AI Note Taker: Desktop app only, requires local audio
   - **Impact:** High - more seamless user experience
   - **Solution:** Build Chrome extension for browser-based recording

3. **Meeting Templates** (Fathom)
   - Fathom: 14+ templates (BANT, Sandler, etc.)
   - AI Note Taker: Generic prompts only
   - **Impact:** Medium-High - saves time for sales users
   - **Solution:** Add template library

#### MEDIUM PRIORITY
4. **AI Scorecards** (Fathom)
   - Fathom: AI-generated coaching scorecards
   - AI Note Taker: Basic analytics only
   - **Impact:** Medium - sales coaching value
   - **Solution:** Enhance analytics with scoring

5. **Deal/Customer View** (Fathom)
   - Fathom: Pipeline visibility and account history
   - AI Note Taker: No CRM visualization
   - **Impact:** Medium - sales workflow integration
   - **Solution:** Add deal tracking UI

6. **MCP Server** (MeetGeek)
   - MeetGeek: Connects Claude/Cursor to meetings
   - AI Note Taker: No IDE integration
   - **Impact:** Medium - developer workflow
   - **Solution:** Build MCP server for IDE integration

#### LOW PRIORITY
7. **Custom Dictionary** (Fathom)
   - Fathom: Company-specific terminology recognition
   - AI Note Taker: Generic transcription
   - **Impact:** Low - nice to have
   - **Solution:** Add vocabulary customization

8. **Global Search** (Fathom, MeetGeek)
   - Fathom: Search across all team meetings
   - AI Note Taker: Individual history only
   - **Impact:** Low - team feature
   - **Solution:** Add search functionality

9. **Clip Sharing** (Fathom)
   - Fathom: Share meeting highlights
   - AI Note Taker: Export full notes only
   - **Impact:** Low - collaboration feature
   - **Solution:** Add snippet export

---

## Competitive Advantage Summary

| Aspect | MeetGeek | Fathom | Convo | AI Note Taker |
|--------|----------|--------|-------|---------------|
| **Price** | $15-59/mo | $0-34/mo | $0-20/mo | **FREE** ✅ |
| **AI Voice Agents** | ✅ **Unique** | ❌ | ❌ | ❌ Gap |
| **Stealth Mode** | ❌ | ❌ | ✅ | ✅ **Parity** |
| **Multi-Provider AI** | ❌ | ❌ | Partial | **8+** ✅ |
| **No-Bot Recording** | ✅ | ❌ | ❌ | ❌ Gap |
| **Document RAG** | ❌ | ❌ | ❌ | ✅ **Advantage** |
| **Vision AI** | ❌ | ❌ | ❌ | ✅ **Advantage** |
| **Editable Summaries** | ❌ | ❌ | ❌ | ✅ **Advantage** |
| **Open Source** | ❌ | ❌ | ❌ | ✅ **Advantage** |
| **Analytics** | Basic | Basic | Good | **Advanced** ✅ |
| **Local Processing** | Partial | Cloud | ✅ | **Full** ✅ |
| **Meeting Templates** | ❌ | ✅ | ❌ | ❌ Gap |

**Verdict:**
- **MeetGeek** leads with AI Voice Agents (autonomous meeting participation)
- **Fathom** leads with generous free tier and sales templates
- **Convo** leads with stealth overlay mode
- **AI Note Taker** leads in flexibility (multi-provider AI, document RAG, vision, editable notes, open source, free)

---

## Recommendations for AI Note Taker

### Must-Have (High Impact)

1. **AI Voice Agent Prototype**
   ```
   Feature: Basic Voice Agent
   - Pre-recorded audio responses
   - Join meetings via browser automation
   - Ask predefined questions
   - Capture responses
   ```

2. **Meeting Templates**
   ```
   Feature: Template Library
   - Sales: BANT, SPIN, Challenger
   - Interview: Behavioral, Technical, Case Study
   - Meeting: Standup, Retro, 1:1
   - Custom template creation
   ```

3. **No-Bot Chrome Extension**
   ```
   Feature: Browser Extension
   - Record Zoom/Meet/Teams without bot
   - Capture audio from browser
   - Stream to AI Note Taker backend
   ```

### High Value (Differentiation)

4. **AI Scorecards**
   ```
   Feature: Meeting Analytics Scoring
   - Talk ratio analysis
   - Question detection
   - Engagement scoring
   - Sentiment tracking over time
   ```

5. **MCP Server**
   ```
   Feature: Model Context Protocol
   - Allow Claude/Cursor to query meetings
   - IDE integration for coding interviews
   - Meeting context in code editor
   ```

### Nice-to-Have

6. **Clip Sharing**
   - Export audio snippets from transcripts
   - Share highlights with team

7. **Global Search**
   - Search across all stored conversations
   - Filter by date, type, content

8. **Custom Dictionary**
   - Add company/product terminology
   - Improve transcription accuracy

---

## Feature Implementation Priority

### Critical (Revolutionary)
- [ ] **AI Voice Agent** - MeetGeek's killer feature, could leapfrog competition

### High (Competitive Necessity)
- [ ] **Chrome Extension** (no-bot recording)
- [ ] **Meeting Templates** (sales workflows)

### Medium (Sales Enablement)
- [ ] **AI Scorecards** (coaching insights)
- [ ] **Deal Tracking** (CRM visualization)
- [ ] **MCP Server** (developer integration)

### Low (Enhancement)
- [ ] **Clip Sharing** (collaboration)
- [ ] **Global Search** (usability)
- [ ] **Custom Dictionary** (transcription quality)

---

## Unique Opportunity: AI Voice Agent

MeetGeek's AI Voice Agents represent a paradigm shift from **passive recording** to **active participation**. This is the most significant gap for AI Note Taker.

**Technical Challenge:**
- Browser automation for meeting platforms
- Real-time TTS (text-to-speech) for responses
- STT (speech-to-text) for understanding responses
- Conversation flow management

**Potential Use Cases:**
1. **Mock Interview Agent** - AI conducts practice interviews
2. **Screening Agent** - Initial candidate filtering
3. **Sales Qualification Agent** - Discovery call automation
4. **Standup Agent** - Captures team updates

**Recommendation:** Prioritize a basic voice agent prototype - this could be a massive differentiator.

---

**Sources:**
- [MeetGeek Pricing](https://meetgeek.ai/pricing)
- [MeetGeek AI Voice Agents Launch](https://www.globenewswire.com/news-release/2025/10/31/3178600/0/en/MeetGeek-Announces-Launch-of-AI-Voice-Agents-to-Autonomously-Participate-in-Virtual-Meetings.html)
- [Fathom Pricing](https://fathom.video/pricing)
- [Fathom Review 2026](https://max-productive.ai/ai-tools/fathom/)
- [Convo Features](https://www.itsconvo.com/features)
