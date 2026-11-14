# Desktop-only conversion, answer routing and capture protection

Status: DONE_WITH_CONCERNS. Changes are local source changes; no release installer
was built or published, and no hosted deployment was deleted.

The desktop interface moved from `apps/web` to `electron/renderer`, retaining
existing uncommitted interface changes. Electron development paths, packaging,
authentication origin checks, tests and CI now use that directory. Removed the
standalone landing site, copied documentation site, Vercel configuration, website
build/preview scripts, PWA manifest/service worker and Vite workspace dependencies.
The desktop continues to use its local Python backend. The local HTTP harness in
`e2e` exists only for testing the bundled renderer.

Existing edited website material was backed up before removal at
`/tmp/ant-removed-website-backup.tar.gz`. This is a temporary local backup.

## Root causes and fixes

- Answer routing waited for model inventory to refresh after 30 seconds. It now
  reuses inventory up to five minutes old while refreshing in the background and
  starts discovery while desktop preferences load. Provider/model opt-outs are
  still checked for every question. This removes a discovery wait, not inference,
  network, screen OCR or model cold-start time.
- Saved capture protection was applied after backend initialization. Its intent
  is now restored before any desktop window is constructed.
- A failed protection request could stop the loop before later windows were
  protected, and new-window failures could throw. Every window is now attempted;
  a window whose native protection cannot be applied stays hidden.
- Tray restore previously disabled protection. It now restores the protected
  window without changing protection intent. All renderers receive state changes.
- A real Electron probe showed that a native `show` event can arrive after the
  visibility method returns. Show, inactive show, restore, maximize and fullscreen
  methods now check protection before calling the native method. Navigation and
  lifecycle handlers also recheck it. Scrolling remains within the protected
  native window and requires no periodic hide/show loop.

## Verification

| Check | Result and scope |
| --- | --- |
| Desktop unit tests | 238 passed, using localhost access required by authentication fixtures |
| Renderer unit tests | 29 passed; six PWA-only tests removed with the service worker |
| Packaged renderer asset validation | 84 references resolved; 20 scripts syntax-checked |
| Renderer smoke test | Five actual bundled pages passed in installed Chrome with synthetic backend responses |
| Native Electron/macOS probe | Passed startup, two windows, scroll, navigation, hide/restore, repair of a deliberately cleared native flag, and explicit disable |
| Workflow YAML and lockfile | Parsed; obsolete web workspace absent and desktop renderer workspace present |
| Whitespace | Passed with CRLF-aware `git diff --check` |

The initial regression run reproduced five failures before fixes. The native
visibility probe independently exposed the asynchronous show-event gap and passed
after guarding native visibility methods. Probe output is saved locally at
`/tmp/ant-protection-live-result.json`.

The smoke command is `node qa/performance/renderer/browser-smoke.mjs --chrome`.
Without `--chrome`, CI uses its installed Playwright Chromium. The first local
attempt lacked that Playwright browser; installed Chrome supplied the verification.

## Limits

These checks establish application behavior and native protection flags, not
external recorder exclusion. Windows capture behavior was unit-tested, not tested
on Windows hardware. macOS ScreenCaptureKit can capture protected windows, as
[Electron documents](https://github.com/electron/electron/blob/main/docs/api/browser-window.md#winsetcontentprotectionenable-macos-windows).
Linux capture exclusion remains unsupported. No absolute invisibility claim is
made for OS dialogs, external browser windows or recording software.

No real-provider end-to-end latency measurement was performed in this run.
Sub-second complete AI answers cannot be guaranteed across providers and models.

## Learning

A BrowserWindow show-event handler alone cannot enforce protection before native
presentation. Guard the visibility method itself and verify against real Electron;
a synchronous event-emitter mock does not reproduce native event timing.
