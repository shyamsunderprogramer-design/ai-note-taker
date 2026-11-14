# Web Fonts (Inter + JetBrains Mono)

**Added:** 2026-06-09
**Why:** User reported "I can't see the fonts on the AI response." Root cause was
that the CSS referenced `"Segoe UI Variable", "Segoe UI", system-ui, sans-serif`
(Windows-first stack) and `'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace`
(no font was actually loaded). On macOS the body text was rendering in San
Francisco (the `system-ui` fallback) and code blocks in Monaco, with the assistant
bubble at only 8% white-on-glass over a navy background — text was technically
visible but looked washed out and "wrong" to the user.

## What's here

- `Inter-Latin.woff2` (~48KB) — Inter variable font, weights 100–900
- `JetBrainsMono-Latin.woff2` (~31KB) — JetBrains Mono variable font, weights 100–800

Both latin subset only. The project is English-only; full Unicode subsets would
inflate the bundle ~10x for no real benefit.

## How they're loaded

- `@font-face` declarations in `../style.css` (lines ~165–185) using
  `font-display: swap` so text never blocks on font load
- Two CSS variables in `:root`:
  - `--font-family-base` — Inter first, then platform fonts in priority order
  - `--font-mono-base` — JetBrains Mono first, then platform mono fonts
- All `font-family` declarations in the project now reference these variables

## How to update

If you need to update the fonts (e.g. new Inter release, want more weights):

```bash
# 1. Download the latest Inter variable woff2 (latin subset)
#    Pick the latin URL from the @font-face block where
#    unicode-range: U+0000-00FF, ...
curl -L -A "Mozilla/5.0 Safari" \
  -o Inter-Latin.woff2 \
  'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7W0Q5nw.woff2'

# 2. Same for JetBrains Mono
curl -L -A "Mozilla/5.0 Safari" \
  -o JetBrainsMono-Latin.woff2 \
  'https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbv2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKwBNntkaToggR7BYRbKPxDcwg.woff2'

# 3. Bump the cache buster in index.html (style.css?v=28 → ?v=29, etc.)
```

If Google ever reorganizes the URLs, use
<https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap>
with a Safari UA and grab the latin subset URL for each family.
