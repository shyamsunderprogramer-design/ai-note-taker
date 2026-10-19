# ANT product website

Persuade: people who want to stay present in meetings and prepare for conversations; a clear blue-and-ink editorial layout, with an interactive example of ANT's floating workspace as the memorable element.

Reuse ANT's blue, green, Inter font, spacing and radius scales from `apps/web/css/base/variables.css`. Extend them with opaque marketing surfaces and accessible content pairs, without loading app component styles. White/cool gray/ink by day, slate/white by night. Follow the OS theme. Inter headings 40–76 px, body 16–19 px. Use rules and whitespace; elevated containers are reserved for the example and downloads. No fabricated testimonials, counters, logos or decorative glow.

Layout: navigation → split hero with example → three benefits → feature story → setup steps → local/cloud explanation → architecture → downloads → FAQ → open-source footer. Primary action: download. Secondary: existing browser app at `/app`.

Examples use canned content, explicitly labeled, without microphone or screen access. Tabs support arrows, Home/End, deep links and Back. Mobile navigation is a disclosure; Escape closes it and restores focus. FAQ uses native details. All downloads work without JavaScript. Build derives the release version from `electron/package.json`.

Keep the existing GitHub/Vercel project. `/` serves `product.html`; `/app` and legacy `/index.html` serve the current browser app. Assets and existing app routes stay in place. `site:build` adds the marketing site after the normal web build; desktop packaging stays independent.

QA: 1440×900, 390×844 and 320 px, both themes, reduced motion, keyboard, example deep links/Back, menu, FAQ, six downloads, app/sign-in routes, legacy service worker, metadata, missing assets, axe. Capture hero, architecture, downloads and mobile menu. Never use real conversations as fixtures.
