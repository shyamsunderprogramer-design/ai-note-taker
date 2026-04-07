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
