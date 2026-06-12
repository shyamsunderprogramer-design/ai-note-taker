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
