# Electron Build

This folder builds the ANT (AI Note Taker) desktop app for Windows, macOS, and Linux.

## Quick start

```bash
npm install
npm run icons            # one-time: generate platform icons from icon.png
npm run build            # build for the current platform
```

For all platforms from a single macOS host:
```bash
npm run build:mac
npm run build:win        # requires Wine; easier from a Windows host
npm run build:linux
```

## Prerequisites

| Platform | Tooling |
|----------|---------|
| macOS    | Xcode Command Line Tools (`xcode-select --install`) — provides `iconutil` |
| Windows  | None beyond Node — `png-to-ico` runs natively |
| Linux    | `dpkg` for `.deb`; `fakeroot` for AppImage |

## Icon pipeline

The build expects:
- `assets/icon.ico`  — Windows
- `assets/icon.icns` — macOS
- `assets/icons/*`   — Linux (multi-size PNG directory)

These are **not** checked into git (regeneratable from `assets/icons/icon.png`).
Run `npm run icons` to generate them on demand. The script requires:

```bash
npm install --save-dev sharp png-to-ico
```

It produces:
- `assets/icon.ico`  — Windows multi-resolution (16, 24, 32, 48, 64, 128, 256 px)
- `assets/icon.icns` — macOS .iconset rendered to .icns via `iconutil`
- `assets/icons/*`   — Linux PNGs (already in git, no generation needed)

## Code signing

| Platform | State | To enable |
|----------|-------|-----------|
| Windows  | Unsigned | Set `CSC_LINK` + `CSC_KEY_PASSWORD` env vars (`.pfx` cert) |
| macOS    | Unsigned (notarized: false) | Set `CSC_LINK`, `CSC_KEY_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` |
| Linux    | N/A — Linux distros don't sign |

When `CSC_LINK` is set, electron-builder automatically picks it up.

## Hardened runtime (macOS)

The macOS build uses Hardened Runtime (`mac.hardenedRuntime: true`).
Entitlements are in `build/entitlements.mac.plist` and include:

- JIT + unsigned memory (for V8/Chromium)
- Microphone access (for voice transcription)
- Network client (for cloud AI calls)
- Files user-selected (for export/import)
- Optional: automation, screen-capture (off by default)

If you change entitlements, re-sign with:
```bash
codesign --sign "Developer ID Application: Your Name" \
  --entitlements build/entitlements.mac.plist \
  --deep --force dist/mac/ANT\ \(AI\ Note\ Taker\).app
```

## What gets packaged

The `extraResources` config copies these into the app bundle:

| From | To | Why |
|------|----|-----|
| `../apps/web`     | `apps/web`     | Renderer files (the floating overlay UI) |
| `../backend`      | `backend`      | FastAPI server (Python source only — no venv) |

**Explicitly excluded from the build:**
- `node_modules` (the renderer builds into the asar)
- `dist/` (Vite output is for web-only deployment)
- All `*.db`, `users.json`, `audit.jsonl` (live user data)
- `__pycache__/`, `.pyc`, `venv/`, `AINT_Venv/`
- `tests/`, `coverage.xml`

**The user installs their own Python environment** — the bundle includes
`backend/requirements.txt` and `start_server.py`; the app prompts the user
to install dependencies on first run, or you can ship a pre-baked venv by
uncommenting the AINT_Venv entry in `package.json#build.extraResources`
(but this adds ~4 GB to the installer).

## Output

`dist/` is git-ignored. Format:
- `dist/ANT (AI Note Taker)-1.0.0-win-x64.exe`       (NSIS installer)
- `dist/ANT (AI Note Taker)-1.0.0-win-x64.exe`        (portable)
- `dist/ANT (AI Note Taker)-1.0.0-mac-x64.dmg`       (Intel)
- `dist/ANT (AI Note Taker)-1.0.0-mac-arm64.dmg`     (Apple Silicon)
- `dist/ANT (AI Note Taker)-1.0.0-linux-x64.AppImage`
- `dist/ant-ainotetaker_1.0.0_amd64.deb`
