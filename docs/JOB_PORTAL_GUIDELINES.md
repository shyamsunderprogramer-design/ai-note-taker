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
