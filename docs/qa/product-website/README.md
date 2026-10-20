# Product website verification — 2026-10-19

The new homepage introduces ANT and links to the existing browser application at `/app`. Sources and routing decisions: [landing README](../../../apps/landing/README.md), [design notes](../../../apps/landing/DESIGN.md).

## Verification

- Production build: `npm run site:build` passed. Existing browser renderer and runtime assets remain in the same output directory.
- `npm --workspace ant-web test`: 28 passed, including auth aliases, remembered-session coverage and service-worker caching boundaries.
- `npm run test:security`: 8 passed.
- `node qa/website/smoke.cjs`: Chromium and Firefox passed at 1440, 390 and 320 px in light/dark themes. Exercises keyboard skip link, example tabs/arrow keys, URL state and Back, reload, FAQ disclosures, menu dismissal/focus, downloads, internal anchors, missing files and app/sign-in routes. No live backend or user account is used.
- The smoke tests verify that the product page makes no backend/tracker requests. Downloads remain usable with JavaScript disabled.
- Axe WCAG A/AA checks covered the three examples and expanded menu/FAQ states at desktop and mobile widths in both themes. The one finding (logo label not matching its visible subtitle) was fixed by using the visible text as its accessible name. Final full-page confirmation: zero violations at all four viewport/theme combinations.
- Viewport screenshots inspected for the hero, feature section, architecture, platform downloads and expanded navigation. Reduced motion enabled; no horizontal page overflow at 320 px.
- All six download URLs and the checksum URL match the published `v2.3.0-rc.2` release assets from GitHub's API.

These checks verify the website and its routing. They do not constitute a fresh desktop-release certification or a screen-reader user study. The current release's existing limits are shown beside the downloads and in the FAQ.

## Preview-server follow-up — 2026-10-20

GitHub CodeQL identified a path-based file check/read race in the local preview server. The server now opens the file once, checks and reads the same handle, rejects final-component symlinks, and closes the handle in a `finally` block. Both-browser smoke checks passed again after this change. The preview server is local tooling, not the Vercel production server.

## Vercel entry-file follow-up — 2026-10-20

Live verification caught Vercel serving the existing `index.html` before the root rewrite. The website composer now preserves the built application as `browser-app.html` and places the marketing page at the actual deployed index. The preview server models filesystem precedence, and the smoke test checks both physical entry files. `web:build` and the source renderer remain independent.

## Visual references

[Desktop](desktop.png) · [Mobile](mobile.png)

The product illustrations are explicitly labeled examples, not captures of a real user's meeting. The social sharing image's editable source is `apps/landing/assets/social-preview.svg`.
