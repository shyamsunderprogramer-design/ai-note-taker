# Cluely - Detailed Feature Analysis

**Website:** https://cluely.com/pricing  
**User Base:** 100K+ users  
**Pricing:** Free (limited) → $20-75/month

---

## Complete Feature List

### 1. Real-Time AI Assistance
- [x] Live AI help during calls
- [x] "Meeting AI that helps during the call, not after"
- [x] Live notes functionality
- [x] Real-time transcription
- [x] ~300ms response time
- [x] Instant answers to questions

### 2. Invisible Overlay System
- [x] Translucent overlay interface
- [x] Sits on top of screen
- [x] **Screen share undetectability** (Pro+ $75/mo tier)
- [x] Visible only to user
- [x] Minimal UI footprint

**Note:** Screen protection is PAID feature at $75/month. AI Note Taker offers this FREE.

### 3. AI Meeting Notes & Summaries
- [x] Auto-generated detailed notes
- [x] AI drafted next steps
- [x] Full transcripts
- [x] Speaker identification
- [x] Meeting summaries
- [x] **Editable summaries** (click to edit)
- [x] Shareable public links
- [x] "Ask AI about all your past meetings"
- [x] Key Insights (important takeaways, decisions)
- [x] View Transcript + Copy to clipboard

### 4. Meeting Activity Section
- [x] Activity dashboard
- [x] Resume Session feature (continue listening)
- [x] Meeting metrics (date, duration)
- [x] Delete meetings
- [x] Next Steps tracking
- [x] Manual edit summaries

### 5. Document Sync & Retrieval (RAG)
- [x] Upload sales decks
- [x] Upload product sheets
- [x] Upload FAQs
- [x] Smart retrieval during calls
- [x] Context matching based on conversation
- [x] Supports PDFs, Docs, Slides

**Limits:**
- Starter (Free): Up to 3 files
- Pro ($20/mo): Unlimited files

### 6. Sales Objection Handling
- [x] Live objection handler
- [x] **Instant prompts** (rebuttals when keywords detected)
- [x] Auto-generated battlecards
- [x] Competitor comparisons
- [x] Adaptive scripts personalized to pitch
- [x] Talk tracks
- [x] Buyer persona mapping
- [x] Analytics tracking (objection handling, pacing, tone)

### 7. Customization & Controls
- [x] Custom keybinds
- [x] Custom prompting
- [x] Unlimited customization (paid tiers)

### 8. Conversation Analytics & Coaching
- [x] Performance reports (clarity, tone, pacing)
- [x] Progress tracking over time
- [x] Personalized AI coaching
- [x] Objection handling analytics
- [x] Win rate improvement insights

### 9. Platform Support
- [x] Desktop app (macOS)
- [x] Mobile app (iOS)
- [x] Cloud sync
- [x] Works with: Zoom, Microsoft Teams, Google Meet

### 10. Supported Use Cases
Cluely supports 20+ scenarios:
1. Interview
2. Coffee chat
3. Brainstorm
4. Lecture
5. Therapy Session
6. Standup
7. Workshop
8. Doctor Visit
9. Seminar
10. Catch-up
11. Client Call
12. Pitch
13. Campus Event
14. Advising Session
15. Client Debrief
16. Dinner
17. Class
18. Note to Self

### 11. Security & Compliance
- [x] SOC 2 compliance
- [x] GDPR alignment
- [x] End-to-end encryption
- [x] No data storage without permission
- [x] Local-only processing option

---

## Pricing Breakdown

| Plan | Price | Key Features | Limitations |
|------|-------|--------------|-------------|
| **Starter (Free)** | $0 | Limited AI responses, limited meeting notes, up to 3 files | Limited usage |
| **Pro** | $20/mo | Unlimited AI, unlimited notes, unlimited files, priority support | No screen share protection |
| **Pro + Undetectability** | $75/mo | Everything + screen share hidden | Expensive for one feature |

---

## AI Note Taker Comparison

### Features AI Note Taker HAS (✅ Parity or Better)

| Feature | Cluely | AI Note Taker | Status |
|---------|--------|---------------|--------|
| Real-time AI assistance | ✅ | ✅ | **Parity** |
| Stealth/Overlay mode | ✅ | ✅ | **Parity** |
| Meeting notes | ✅ | ✅ | **Parity** |
| Action items | ✅ | ✅ | **Parity** |
| Speaker identification | ✅ | ✅ | **Parity** |
| Editable summaries | ✅ | ✅ | **Parity** |
| Document RAG | ✅ | ✅ | **Parity** |
| Sales objection handling | ✅ | ✅ | **Parity** |
| Analytics | ✅ | ✅ | **Better** (more detailed) |
| Screen protection | ⚠️ $75/mo | ✅ **FREE** | **Better** |
| Export formats | Web links only | **MD/JSON/TXT** | **Better** |
| Import conversations | ❌ | ✅ | **Better** |
| Vision/screenshots | ❌ | ✅ | **Better** |
| Multi-provider AI | ❌ | **8+ providers** | **Better** |
| Open source | ❌ | ✅ | **Better** |
| Local processing | Partial | **Full** | **Better** |
| CRM Integration | Partial | **Full (webhook)** | **Better** |
| Price | $20-75/mo | **FREE** | **Better** |

### Features Cluely HAS that AI Note Taker LACKS (❌ Gaps)

#### MEDIUM PRIORITY
1. **Mobile Native App (iOS)**
   - Cluely has native iOS app
   - AI Note Taker has PWA (web-based)
   - **Impact:** Medium - PWA is sufficient
   - **Solution:** Could build React Native wrapper

2. **Public Share Links**
   - Cluely: One-click public links
   - AI Note Taker: Export to file only
   - **Impact:** Medium - convenient for sharing
   - **Solution:** Add "Generate shareable link" feature

3. **Resume Session Feature**
   - Cluely: Continue listening for extended meetings
   - AI Note Taker: Auto-stop at 60min
   - **Impact:** Low - manual restart works
   - **Solution:** Add "Extend session" button

4. **20+ Use Case Templates**
   - Cluely: Pre-configured for therapy, doctor visits, etc.
   - AI Note Taker: Generic interview/meeting focus
   - **Impact:** Low - customization possible
   - **Solution:** Add prompt templates for different scenarios

5. **Cloud Sync Across Devices**
   - Cluely: Notes synced online
   - AI Note Taker: Local storage
   - **Impact:** Low - can export/import
   - **Solution:** Add cloud sync option

#### LOW PRIORITY
6. **Mac Native App**
   - Cluely: Native macOS app
   - AI Note Taker: Electron (cross-platform)
   - **Impact:** Low - Electron works fine

7. **Buyer Persona Mapping**
   - Cluely: Maps responses to personas
   - AI Note Taker: Generic sales objection
   - **Impact:** Low - advanced sales feature

---

## Recommendations for AI Note Taker

### Quick Wins (Low Effort, High Value)
1. **Public Share Links**
   - Generate temporary URLs for sharing notes
   - Host on simple static page

2. **Session Extension**
   - "Extend" button when timer warning shows
   - Simple 30-min extension

### Medium Effort
3. **Use Case Templates**
   - Add dropdown: Interview, Sales Call, Meeting, etc.
   - Pre-load different prompt templates
   - Change UI colors per scenario

4. **Mobile App (Optional)**
   - React Native wrapper around PWA
   - Or improve PWA to feel more native

### Not Critical
5. **Cloud Sync**
   - Optional feature for cross-device
   - Encrypt data

---

## Competitive Advantage Summary

| Aspect | Cluely | AI Note Taker |
|--------|--------|---------------|
| **Price** | $20-75/mo | **FREE** ✅ |
| **Screen Protection** | ⚠️ $75/mo | **FREE** ✅ |
| **Document RAG** | ✅ (3-∞) | ✅ (unlimited) ✅ |
| **Sales Objection** | ✅ (advanced) | ✅ (basic) |
| **Mobile** | ✅ Native iOS | ⚠️ PWA |
| **Vision AI** | ❌ | ✅ **Advantage** |
| **Multi-Provider** | ❌ | ✅ **Advantage** |
| **Open Source** | ❌ | ✅ **Advantage** |
| **Local Processing** | Partial | ✅ **Advantage** |
| **Export Formats** | Web links | **MD/JSON/TXT** ✅ |
| **CRM Integration** | Partial | **Full** ✅ |
| **Analytics** | Basic | **Advanced** ✅ |

**Verdict:** AI Note Taker exceeds Cluely in most areas. Only gaps are mobile native app and public share links.

---

## Feature Implementation Priority

### High (To Exceed Cluely)
- [ ] Public share links for notes

### Medium (Nice to Have)
- [ ] Session extension button
- [ ] Use case templates (therapy, sales, etc.)

### Low (Optional)
- [ ] React Native mobile app
- [ ] Cloud sync
- [ ] Buyer persona mapping

---

**Sources:**
- [Cluely Pricing](https://cluely.com/pricing)
- [Cluely Mobile](https://cluely.com/mobile)
- [Cluely Guide - Meeting Notes](https://docs.cluely.com/feature/postcall)
- [Cluely AI Features](https://cluelyai.org/cluely-ai-features/)
