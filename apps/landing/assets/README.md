# Website brand assets

These are web exports of the owner's existing ANT artwork, not new generated illustrations.
Source files remain unchanged.

| Website asset | Original repository file |
| --- | --- |
| `ant-queen-{640,1280}.webp` | `Ant Images/Gemini_Generated_Image_q6ekdzq6ekdzq6ek.png` |
| `ant-knowledge-{640,1280}.webp` | `Ant Images/Gemini_Generated_Image_k0vl0ok0vl0ok0vl.png` |
| `ant-mark.png` | `assets/design/source/ant horizontal rightside facing - navy blue.png` |
| `ant-mark-light.png` | `assets/design/source/ant horizontal rightside facing - sky blue.png` |
| `social-preview.png` | `social-preview.svg`, using the original ant mark and crowned artwork |

Re-export from the repository root with `node qa/website/export-artwork.cjs` using the
Chromium installation already used for website smoke checks. Set `PLAYWRIGHT_BROWSERS_PATH`
if the browsers are installed outside Playwright's default cache. This only scales and
re-encodes the art, without cropping, retouching or changing colors. The small ant marks
are exact file copies. Social preview composition is editable in `social-preview.svg`.

The page uses responsive image sources, explicit dimensions and descriptive alt text.
Only the hero image is prioritized; the closing image is lazy-loaded. Header and footer
marks switch to the sky-blue source in dark mode. The illustrative workspace keeps the
light mark on its dark surface.
