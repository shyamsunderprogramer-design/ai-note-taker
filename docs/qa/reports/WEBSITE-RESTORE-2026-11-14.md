# Product website restoration — 14 November 2026

Restored the original ANT marketing design from Git history and updated it for the desktop application. The website is an information/download surface, independent of the desktop renderer and backend.

## Content and deployment contract

- Describe supported account connections, source-only response-preparation changes, Enter/numeric rendering fixes, capture limits, storage and provider data flow.
- Separate published v2.3.0-rc.2 installers from newer source changes. GitHub's release API confirmed all six installer files and SHA256SUMS.txt exist on 14 November.
- Replace the old browser-app architecture diagram with current desktop process descriptions and link the full build guide.
- Build only allowlisted public files into `apps/landing/dist`, using Node built-ins. Vercel does not install desktop/backend dependencies.
- Redirect `/app`, `/browser-app.html` and sign-in routes to downloads. Replace the former PWA worker with a retirement worker that removes only `ant-cache-*` public caches; localStorage and IndexedDB are not cleared.
- Tighten website CSP and disable microphone/camera permissions. The marketing page makes no AI or backend calls.

## Local checks performed

Command: `ANT_BROWSER_CHANNEL=chrome npm run site:test`, after `npm run site:build`.

Six viewport/theme combinations passed: widths 1440, 390 and 320, each in light and dark, with reduced motion. Checks covered:

- One H1, local anchor targets, no horizontal overflow, six distinct release downloads.
- Skip link and focus, keyboard tabs with arrows/Home/End, example URL state and Back.
- Mobile menu open/Escape/focus restoration; FAQ activation with the keyboard.
- Axe WCAG 2 A/AA, 2.1 A/AA and 2.2 AA tags: zero violations in checked page and open-menu states.
- No observed page exceptions or failed same-origin asset responses.
- Legacy-route redirects, absent app/private files, security headers.
- Old worker retirement: ANT public caches removed; a saved-note localStorage fixture and an unrelated cache preserved.

Screenshots were inspected for desktop light hero, desktop dark privacy, phone light hero and phone dark source updates. Original artwork, palette and theme behavior are retained. The outdated diagram was intentionally replaced with semantic text steps.

Local artifacts: `/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-website-aoU9mt`.

Documentation local links and anchors passed. Script syntax and whitespace checks passed. These checks do not certify the native app, all assistive technologies, every browser, installer behavior or universal screenshot invisibility. VoiceOver and live provider calls were not exercised for this website change. Production deployment and live verification are checked separately after pushing.
