# Electron build entry point

Use the maintained [end-to-end project build guide](../docs/PROJECT-BUILD-GUIDE.md) for setup, architecture, configuration, testing, packaging, release steps and troubleshooting. Its [packaging chapter](../docs/PROJECT-BUILD-GUIDE.md#10-how-to-build-desktop-packages) replaces the previous instructions in this file.

The executable authorities are [package.json](package.json), the [standalone Python builder](../scripts/build_desktop_runtime.py), and the [release workflow](../.github/workflows/release.yml).

## Prepare a build

From the repository root, with Python 3.12 available as `python`:

```bash
npm ci
npm run renderer:check
python scripts/build_desktop_runtime.py
```

The runtime builder selects the current host architecture, verifies the pinned download, installs backend dependencies into `AINT_Python`, and refuses to overwrite an existing destination. `AINT_Venv` is for development; it is not the packaged Python runtime. Use a native build host for each release target.

## Build one target

Enter `electron/`, then run the command matching the host:

| Host | Command |
| --- | --- |
| Apple Silicon Mac | `npx electron-builder --mac --arm64 --publish never` |
| Intel Mac | `npx electron-builder --mac --x64 --publish never` |
| Windows x64 | `npx electron-builder --win --x64 --publish never` |
| Linux x64 | `npx electron-builder --linux --x64 --publish never` |

Outputs are under `electron/dist`: Mac ZIP archives, Windows NSIS/portable EXEs, Linux AppImage/DEB files. The generic desktop `build` script uses `-mwl`; it does not mean “current platform only.”

## Package contents and native resources

- Bundled interface: `renderer` → `resources/renderer`.
- Filtered backend source: `../backend` → `resources/backend`.
- Standalone Python: `../AINT_Python` → `resources/python`.
- Mac helpers: `audiotee` and `ant-screen-capture`.
- Main/preload/stealth code, libraries, features, assets and runtime dependencies are included according to the builder configuration.

Live data, databases and environment files are excluded by the configured resource filters. Review those filters when adding a resource. Tracked icons already exist; regeneration is optional. The icon generator needs additional `sharp`/`png-to-ico` tooling, which is not part of the declared desktop development dependencies.

Mac source builds need Xcode Command Line Tools. The `beforePack` hook compiles the screen-capture helper; installed users do not compile that helper. Native OCR uses a different lazy compilation/fallback path.

## Signing state

Current Mac settings are **ad-hoc signing**, `hardenedRuntime: false` and `notarize: false`. Entitlements live in `assets/entitlements.mac.plist`. The `afterPack` hook also ad-hoc signs nested Mach-O runtime/helper binaries. A Developer ID/notarization pipeline requires coordinated changes to the hook and builder configuration; setting signing environment variables alone does not establish it.

## Verify

From the repository root after building:

```bash
python scripts/verify_desktop_package.py
```

If multiple unpacked builds exist, pass `--resources` with the exact new package Resources directory. The verifier checks packaged runtime imports, disposable backend authentication/storage, and the Mac helper where applicable. It does not replace GUI, permissions, audio, AI-provider or upgrade testing. See the full guide's [acceptance steps](../docs/PROJECT-BUILD-GUIDE.md#9-how-to-test-the-application).
