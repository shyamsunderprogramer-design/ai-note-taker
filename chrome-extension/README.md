# ANT Chrome Extension

AI Note Taker browser extension for job tracking and meeting assistance.

## Features

### Job Tracking
- Auto-detect job pages on LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, Workday, iCIMS
- Extract job details (title, company, location, salary, description)
- One-click save to ANT backend
- Duplicate detection

### Meeting Assistance
- Detect Zoom, Google Meet, Microsoft Teams, WebEx meetings
- Floating overlay with real-time suggestions
- Screenshot capture for vision AI analysis
- Participant count tracking

### Browser Integration
- Popup UI with connection status and stats
- Host permissions for job sites and localhost
- Manifest V3 compliant (service worker)

## Installation (Developer Mode)

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer Mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder
5. Extension appears in toolbar with ANT icon

## Configuration

The extension connects to `http://localhost:8000` by default. Ensure the ANT backend is running.

### Permissions
- `activeTab` - Access current tab content
- `storage` - Store extension settings
- `scripting` - Inject content scripts
- `notifications` - Show alerts
- Host permissions for job sites and localhost

## Files

```
chrome-extension/
├── manifest.json      # Extension manifest (V3)
├── background.js      # Service worker
├── popup.html         # Popup UI
├── popup.js           # Popup logic
├── content.js        # Injected into job/meeting pages
├── content.css       # Overlay styles
└── README.md          # This file
```

## Icon Requirements

Replace placeholder icons with proper PNG files:
- `icon16.png` - 16x16 toolbar icon
- `icon48.png` - 48x48 extension page icon
- `icon128.png` - 128x128 store icon

## Privacy

All data is stored locally and sent only to your configured ANT backend instance.
