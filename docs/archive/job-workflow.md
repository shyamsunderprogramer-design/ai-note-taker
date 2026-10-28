# Job applications and browser extension — historical source records

These are dated source records preserved during documentation consolidation. Their prices, legal statements, feature completion claims, paths, and benchmark numbers have not been revalidated. They are not current setup instructions or release acceptance results.

Current guide: [Job applications and browser extension](../business/JOB_APPLICATION_WORKFLOW.md).

## Source index
- [JOB_APPLICATION_WORKFLOW.md](#source-job-application-workflow)
- [JOB_PORTAL_GUIDELINES.md](#source-job-portal-guidelines)
- [BROWSER_EXTENSION_SAFETY.md](#source-browser-extension-safety)

<a id="source-job-application-workflow"></a>

## Source: JOB_APPLICATION_WORKFLOW.md

<details>
<summary>Read the original source record</summary>

# Complete Job Application Workflow

## Overview
This document outlines the complete job application tracking workflow from job discovery to onboarding.

## Workflow Stages

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Job Page   │───▶│Select Job   │───▶│  Save Job   │───▶│   Apply     │
│  (Browse)   │    │  (Browse)   │    │  (Capture)  │    │  (Submit)   │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                   │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────▼──────┐
│ Onboarding  │◀───│  Drug Test  │◀───│Background   │◀───│   1st Round   │
│             │    │             │    │   Check     │    │   Interview   │
└─────────────┘    └─────────────┘    └─────────────┘    └───────┬───────┘
                                                                  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌───────▼───────┐
│Congratulations│◀──│  Offer      │◀───│ Final Round │◀───│   Technical   │
│             │    │  Accepted   │    │  Interview  │    │   Screening   │
└─────────────┘    └─────────────┘    └─────────────┘    └───────┬───────┘
                                                                  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌───────▼───────┐
│   Update    │◀───│ Availability│◀───│   Screening │◀───│Recruiter Email│
│   Status    │    │  Request    │    │    Call     │    │               │
└─────────────┘    └─────────────┘    └─────────────┘    └───────────────┘
```

## Stage Details

### 1. Job Discovery
- Browse job portals (LinkedIn, Indeed, Glassdoor, iCIMS, etc.)
- Extension detects job page automatically
- Extracts: Company, Role, Location, Job URL

### 2. Save Job (Bookmark)
**Status:** `saved`
- Click "🐜 Save Job" button
- Stores job details without applying
- Tracks: Job URL, Salary range, Job description
- **Actions:** 
  - Add notes
  - Set priority (high/medium/low)
  - Add tags
  - Schedule apply-by date

### 3. Apply
**Status:** `applied`
- Submit application through company portal
- Upload resume & cover letter
- Fill application form
- **Tracks:**
  - Application date
  - Resume version used
  - Cover letter used
  - Portal used (LinkedIn Easy Apply, Company website, etc.)
  - Application confirmation number
  - Screenshot of application submitted

### 4. Recruiter Email
**Status:** `recruiter_contact`
- Automated email confirmations
- Recruiter reaching out
- **Tracks:**
  - Email content
  - Recruiter name & contact
  - Response required?
  - Follow-up date

### 5. Screening Call
**Status:** `phone_screen`
- Initial recruiter call (15-30 min)
- Discuss basic qualifications, salary expectations
- **Tracks:**
  - Scheduled date/time
  - Recruiter name
  - Call notes
  - Questions asked
  - Salary discussed
  - Next steps

### 6. Availability Request
**Status:** `availability_requested`
- Request for interview availability
- **Tracks:**
  - Slots provided
  - Preferred dates/times
  - Time zone
  - Format (phone/video/in-person)

### 7. First Round Interview
**Status:** `first_round`
Types:
- **Technical:** Coding, system design, problem solving
- **HR:** Culture fit, behavioral questions
- **Manager:** Team fit, experience discussion
- **Coding:** Live coding session
- **Hands-on:** Practical assessment

**Tracks:**
- Interview type
- Interviewer names
- Date & duration
- Questions asked
- Your responses
- Performance rating
- Feedback received
- Next round scheduled?

### 8. Background Check (BG)
**Status:** `background_check`
- Employment verification
- Education verification
- Criminal record check
- **Tracks:**
  - BG check initiated date
  - Provider (Checkr, HireRight, etc.)
  - Documents requested
  - Status updates
  - Completion date

### 9. Drug Test
**Status:** `drug_test`
- Pre-employment screening
- **Tracks:**
  - Test scheduled date
  - Location
  - Type (urine, hair, saliva)
  - Results received
  - Pass/fail status

### 10. Onboarding
**Status:** `onboarding`
- Paperwork completion
- Equipment shipment
- Account setup
- **Tracks:**
  - Start date
  - Documents signed
  - IT setup status
  - Orientation scheduled

### 11. Offer Accepted
**Status:** `accepted`
- Signed offer letter
- Start date confirmed

### 12. Congratulations! 🎉
**Status:** `hired`
- New job started!
- Move to "Accepted Offers" view

## Status Flow

```
saved → applied → recruiter_contact → phone_screen → availability_requested → 
first_round → [second_round] → [third_round] → background_check → drug_test → 
offer → accepted/rejected → onboarding → hired
```

Alternative paths:
- `saved` → `withdrawn`
- `applied` → `rejected`
- `applied` → `ghosted` (no response >30 days)
- `first_round` → `rejected`
- `offer` → `rejected`

## Key Features Needed

### Application Tracking
- [x] Company name
- [x] Job title
- [x] Location
- [x] Status
- [x] Applied date
- [ ] Resume version
- [ ] Cover letter
- [ ] Job description snapshot
- [ ] Salary range
- [ ] Job URL
- [ ] Application portal
- [ ] Confirmation number

### Interview Tracking
- [ ] Interview type (technical/HR/manager/coding)
- [ ] Interviewer names
- [ ] Scheduled date/time
- [ ] Duration
- [ ] Questions asked
- [ ] Your answers
- [ ] Performance notes
- [ ] Feedback received

### Communication Log
- [ ] Email thread tracking
- [ ] Recruiter contacts
- [ ] Follow-up reminders
- [ ] Response templates

### Document Management
- [ ] Resume versions
- [ ] Cover letters
- [ ] Portfolio/work samples
- [ ] Certifications
- [ ] Transcripts

### Timeline View
- Visual timeline of all touchpoints
- Days between stages
- Response time analytics

### Notifications
- Interview reminders (24h, 1h before)
- Follow-up reminders (if no response)
- Application deadline alerts
- Status change notifications

</details>

<a id="source-job-portal-guidelines"></a>

## Source: JOB_PORTAL_GUIDELINES.md

<details>
<summary>Read the original source record</summary>

# Job Portal Integration Guidelines

## Current Implementation Status: SAFE ✓

Your ANT browser extension uses a **passive, user-initiated approach** that is safe from account blocking on LinkedIn, Indeed, Glassdoor, and other job portals.

---

## How It Works (Safe Method)

### Browser Extension Approach
The extension uses **content scripts** that:
1. **Read-only**: Only reads already-loaded page content (DOM queries)
2. **User-initiated**: Only activates when YOU click the "Save Job" button
3. **No API calls to job portals**: Never accesses LinkedIn/Indeed APIs directly
4. **Local only**: Sends data to your local ANT backend (127.0.0.1:8000)

### What Makes It Safe

| Risk Factor | Our Approach | Safe? |
|-------------|--------------|-------|
| Automated requests to job portals | None - only reads page you're already viewing | ✓ |
| Login/session manipulation | None - uses your existing logged-in session | ✓ |
| Rapid/automated actions | User must click button for each job | ✓ |
| Data extraction volume | Limited to pages you manually visit | ✓ |
| API rate limits | Not applicable - no API calls | ✓ |

---

## Supported Job Portals

### Fully Supported (Tested)
- **LinkedIn** - Jobs pages, company pages
- **Indeed** - Job listings, company pages  
- **Glassdoor** - Job listings, saved jobs
- **Greenhouse** - Job application pages
- **Lever** - Job application pages

### How to Use
1. Visit a job listing on any supported site
2. The "🐜 Save Job" button appears automatically
3. Click the button to save to your ANT Job Tracker
4. Data is extracted and sent to your local tracker

---

## What Would Be UNSAFE (Avoid These)

### ❌ Automated Scraping
```javascript
// DON'T DO THIS - Will get blocked
for (let page = 1; page <= 100; page++) {
    await fetch(`https://linkedin.com/jobs?page=${page}`);
    // This triggers bot detection!
}
```

### ❌ API Abuse
```javascript
// DON'T DO THIS - Violates ToS
const jobs = await fetch('https://api.linkedin.com/v2/jobs', {
    headers: { 'Authorization': 'Bearer token' }
});
```

### ❌ Rapid Actions
```javascript
// DON'T DO THIS - Bot-like behavior
setInterval(() => {
    document.querySelector('.apply-button').click();
}, 1000);
```

### ❌ Credential Stuffing
```javascript
// DON'T DO THIS - Security violation
const passwords = ['password123', 'admin', ...];
for (const pass of passwords) {
    await tryLogin(username, pass);
}
```

---

## Safety Mechanisms in Place

### 1. Manifest Permissions (Minimal)
```json
{
  "permissions": ["activeTab", "scripting", "storage"],
  "host_permissions": [
    "*://*.linkedin.com/*",
    "*://*.indeed.com/*",
    "*://*.glassdoor.com/*"
  ]
}
```
- Only requests access when you click the extension
- No background automation
- No cross-site tracking

### 2. Content Script Design
- Runs at `document_idle` (page fully loaded)
- No mutation observers for automation
- No request interception
- No form auto-fill

### 3. Rate Limiting (Built-in)
- One save per user click
- No batch operations
- 2-second cooldown between saves

---

## Platform-Specific Guidelines

### LinkedIn
- **Safe**: Saving jobs you manually browse
- **Safe**: Reading job details from open pages
- **Unsafe**: Automated connection requests
- **Unsafe**: Mass profile viewing
- **Unsafe**: Automated messaging

### Indeed
- **Safe**: Capturing job details from listings
- **Safe**: Reading company information
- **Unsafe**: Automated applications
- **Unsafe**: Resume spam

### Glassdoor
- **Safe**: Reading salary/company data from visible pages
- **Unsafe**: Bypassing login walls
- **Unsafe**: Automated review scraping

---

## Troubleshooting

### Extension Not Detecting Jobs
1. Refresh the page after installing extension
2. Check if you're on a supported URL pattern
3. Try clicking the extension icon in toolbar

### "Failed to Save" Error
1. Ensure ANT backend is running (`python main.py`)
2. Check backend is on port 8000
3. Verify no firewall blocking localhost

### Button Not Appearing
1. Some SPA (single page) sites need refresh
2. Check browser console for errors
3. Try popup mode instead (click extension icon)

---

## Future Enhancements (Still Safe)

These features would also be safe:
- ✓ Export job data to CSV
- ✓ Interview scheduling reminders
- ✓ Application deadline notifications
- ✓ Company research aggregation
- ✓ Resume matching suggestions

These would NOT be safe:
- ✗ Auto-apply to jobs
- ✗ Mass message recruiters
- ✗ Automated profile viewing
- ✗ Bypassing premium features

---

## Questions?

If you're unsure whether a feature is safe:
1. Ask: "Does it require automated actions on the job portal?"
2. If yes → Unsafe
3. If no → Likely safe

**Remember**: If you can do it manually while browsing, the extension can help capture that data. If it requires automation, it's unsafe.

</details>

<a id="source-browser-extension-safety"></a>

## Source: BROWSER_EXTENSION_SAFETY.md

<details>
<summary>Read the original source record</summary>

# Browser Extension Safety

## Account Safety: CONFIRMED SAFE ✓

Your accounts on LinkedIn, Indeed, Glassdoor, and other job portals are **NOT at risk** of being blocked by the ANT browser extension.

---

## Why It's Safe

### 1. No Automated Requests
The extension **NEVER** makes automated requests to job portals. It only reads content from pages you're already viewing in your browser.

### 2. User-Initiated Only
Every action requires YOU to click:
- Click extension icon → Open popup
- Click "Save Job" button → Save job
- No automatic saving, no background scraping

### 3. Local Data Only
Captured job data goes to your local ANT app:
```
Browser Extension → Local Backend (127.0.0.1:8000)
                          ↓
                   Your Job Tracker
```

No data sent to external servers.

### 4. No Session Manipulation
- Doesn't modify cookies
- Doesn't fake user agents
- Doesn't spoof location
- Uses your natural browsing session

---

## Comparison: Safe vs Unsafe Extensions

| Feature | ANT (Safe) | Unsafe Extensions |
|---------|------------|-------------------|
| **Data Collection** | Manual per-job | Automated mass scraping |
| **API Usage** | None | Unofficial APIs |
| **Action Timing** | User-clicked | Bot-scheduled |
| **Request Rate** | Human speed | Machine speed (100x+) |
| **Account Risk** | Zero | High (bans common) |
| **Detection Risk** | Zero | Bot detection triggered |

---

## What Triggers Account Blocks

### LinkedIn Will Block For:
- ❌ Sending >100 connection requests/day
- ❌ Viewing >500 profiles/day  
- ❌ Using automation tools (Selenium, Puppeteer)
- ❌ Scraping with unofficial APIs
- ❌ Auto-messaging

### ANT Does NOT Do These:
- ✅ Only saves jobs you manually view
- ✅ No connection requests
- ✅ No profile viewing
- ✅ No messaging
- ✅ No automation

---

## Technical Safeguards

### Content Security
```javascript
// Extension only activates on user action
browser.action.onClicked.addListener(() => {
    // User clicked - safe
});

// NOT like this (unsafe):
setInterval(() => { 
    // Auto-runs - would trigger detection
}, 5000);
```

### DOM Interaction
```javascript
// Safe: Read-only queries
const title = document.querySelector('h1').textContent;

// Unsafe: Automated actions (NOT IMPLEMENTED)
button.click();  // Would trigger bot detection
```

### Rate Limiting (User-Side)
- No batch operations
- One job per click
- Natural human pacing

---

## Detection Evasion (Not Needed)

Some extensions try to "hide" from detection:
- Randomizing mouse movements
- Spoofing user agents
- Bypassing security checks

**ANT doesn't need this** because it's not doing anything that triggers detection in the first place.

---

## Privacy & Security

### What Data is Collected
| Data | Collected? | Stored? |
|------|------------|---------|
| Job title | ✓ | Local only |
| Company name | ✓ | Local only |
| Job location | ✓ | Local only |
| Job URL | ✓ | Local only |
| Your login credentials | ✗ | Never |
| Your browsing history | ✗ | Never |
| Your personal data | ✗ | Never |

### Data Flow
```
Job Portal Page → Browser Extension → Local ANT App → Local Database
                                                        ↓
                                              No external servers
```

---

## FAQ

### Q: Can LinkedIn detect the extension?
**A:** Extensions cannot be detected unless they modify page behavior. ANT is read-only and undetectable.

### Q: What if I save 100 jobs in a day?
**A:** Still safe. Each save is user-initiated. You're just organizing jobs faster.

### Q: Does it work with LinkedIn Premium?
**A:** Yes, works with all account types (Free, Premium, Recruiter).

### Q: Can I get banned for using this?
**A:** No. You're performing manual actions the extension helps organize.

### Q: Is it against Terms of Service?
**A:** Read-only access of public pages is generally permitted. Automated actions are not - and ANT doesn't do those.

---

## Red Flags (Not in ANT)

If you see these features elsewhere, AVOID:
- ⚠️ "Auto-apply to jobs"
- ⚠️ "Mass connect with recruiters"
- ⚠️ "Profile view automation"
- ⚠️ "Bypass LinkedIn limits"
- ⚠️ "Unlimited profile searches"

These will get your account banned.

---

## Best Practices

1. **Use normally** - Browse jobs as usual
2. **Click to save** - Extension captures what you choose
3. **No bulk actions** - Save jobs one at a time
4. **Keep logged in** - Don't logout/login repeatedly
5. **Update extension** - Keep to latest version

---

## Need Help?

If you experience any issues:
1. Check browser console for errors
2. Ensure ANT backend is running
3. Verify extension permissions

**Your accounts are safe. Extension only helps organize, never automates.**

</details>
