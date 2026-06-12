#!/usr/bin/env node
/**
 * generate-icons.js
 *
 * Generate platform-specific icon files (icon.ico, icon.icns) for Electron
 * builds from a single 1024×1024 source PNG.
 *
 * electron-builder requires:
 *   - assets/icon.ico  (Windows)
 *   - assets/icon.icns (macOS)
 *   - assets/icons/*   (Linux)
 *
 * Source: assets/icons/icon.png  (1024×1024 is ideal; smaller is accepted)
 *
 * Usage:
 *   node scripts/generate-icons.js
 *   npm run icons
 *
 * Requires (install once):
 *   npm install --save-dev sharp png-to-ico
 *   # macOS only: brew install --cask xquartz (for iconutil — already on macOS)
 *
 * If dependencies are missing, the script will:
 *   1. Print a clear, actionable error
 *   2. NOT modify the existing icons
 *   3. Provide the commands to install + run
 *
 * Why this lives in scripts/ and not at the repo root:
 *   The electron/ folder is the standalone desktop-app workspace. Anything
 *   build-related stays in here.
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const ASSETS_DIR = path.resolve(__dirname, "..", "assets");
const SOURCE_PNG = path.join(ASSETS_DIR, "icons", "icon.png");
const OUTPUT_ICO = path.join(ASSETS_DIR, "icon.ico");
const OUTPUT_ICNS = path.join(ASSETS_DIR, "icon.icns");
const ICONSET_DIR = path.join(ASSETS_DIR, "icon.iconset");

const PLATFORM = process.platform;
const IS_MAC = PLATFORM === "darwin";
const IS_WIN = PLATFORM === "win32";
const IS_LINUX = PLATFORM === "linux";

function log(msg) {
  console.log(`[generate-icons] ${msg}`);
}
function warn(msg) {
  console.warn(`[generate-icons] WARN: ${msg}`);
}
function fatal(msg, code = 1) {
  console.error(`[generate-icons] ERROR: ${msg}`);
  if (code === 2) {
    console.error("");
    console.error("Install the required tooling and re-run:");
    console.error("  npm install --save-dev sharp png-to-ico");
    if (IS_MAC) {
      console.error("  # iconutil ships with macOS — no install needed");
    }
  }
  process.exit(code);
}

// ── Pre-flight ───────────────────────────────────────────────────
if (!fs.existsSync(SOURCE_PNG)) {
  fatal(`Source PNG not found: ${SOURCE_PNG}\n` +
        `Place a 1024×1024 PNG at that path (or pass --source=...).`, 1);
}

log(`Source: ${SOURCE_PNG}`);
log(`Target: ${OUTPUT_ICO} (Windows), ${OUTPUT_ICNS} (macOS)`);

// ── Optional deps ────────────────────────────────────────────────
let sharp = null;
let pngToIco = null;
try { sharp = require("sharp"); } catch { /* ok */ }
try { pngToIco = require("png-to-ico"); } catch { /* ok */ }

if (IS_WIN || (!IS_MAC && !IS_LINUX)) {
  if (!pngToIco || !sharp) {
    fatal("Missing dependencies for ICO generation.\n" +
          "  npm install --save-dev sharp png-to-ico", 2);
  }
}

if (IS_MAC) {
  if (!sharp) {
    fatal("Missing dependency for ICNS generation.\n" +
          "  npm install --save-dev sharp", 2);
  }
}

// ── Generate .ico (Windows) ──────────────────────────────────────
async function buildIco() {
  log("Building icon.ico (Windows multi-resolution)...");
  const sizes = [16, 24, 32, 48, 64, 128, 256];
  const pngs = await Promise.all(
    sizes.map(async (size) => {
      return await sharp(SOURCE_PNG)
        .resize(size, size, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
        .png()
        .toBuffer();
    })
  );
  const icoBuffer = await pngToIco(pngs);
  fs.writeFileSync(OUTPUT_ICO, icoBuffer);
  log(`  → ${OUTPUT_ICO} (${(icoBuffer.length / 1024).toFixed(1)} KB)`);
}

// ── Generate .icns (macOS, via iconutil) ──────────────────────────
async function buildIcns() {
  log("Building icon.icns (macOS multi-resolution)...");
  if (fs.existsSync(ICONSET_DIR)) {
    fs.rmSync(ICONSET_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(ICONSET_DIR, { recursive: true });

  // macOS .iconset filenames are exact — see Apple Icon Composer docs
  const sizes = [
    { name: "icon_16x16.png",         size: 16  },
    { name: "icon_16x16@2x.png",      size: 32  },
    { name: "icon_32x32.png",         size: 32  },
    { name: "icon_32x32@2x.png",      size: 64  },
    { name: "icon_128x128.png",       size: 128 },
    { name: "icon_128x128@2x.png",    size: 256 },
    { name: "icon_256x256.png",       size: 256 },
    { name: "icon_256x256@2x.png",    size: 512 },
    { name: "icon_512x512.png",       size: 512 },
    { name: "icon_512x512@2x.png",    size: 1024 },
  ];

  for (const { name, size } of sizes) {
    const buf = await sharp(SOURCE_PNG)
      .resize(size, size, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
      .png()
      .toBuffer();
    fs.writeFileSync(path.join(ICONSET_DIR, name), buf);
  }

  // iconutil is built into macOS
  try {
    execSync(`iconutil -c icns "${ICONSET_DIR}" -o "${OUTPUT_ICNS}"`, { stdio: "pipe" });
    log(`  → ${OUTPUT_ICNS}`);
  } catch (err) {
    fatal(`iconutil failed: ${err.message}\n` +
          `Make sure you are on macOS, then re-run.`, 1);
  } finally {
    fs.rmSync(ICONSET_DIR, { recursive: true, force: true });
  }
}

// ── Main ─────────────────────────────────────────────────────────
(async () => {
  try {
    if (IS_WIN) {
      await buildIco();
    } else if (IS_MAC) {
      await buildIco();   // also build .ico for cross-platform builds
      await buildIcns();
    } else if (IS_LINUX) {
      log("Skipping ICO/ICNS generation on Linux (use `npm run icons:win` or `npm run icons:mac` from the respective host).");
      log("Linux uses assets/icons/*.png directly — already in place.");
    } else {
      log(`Unknown platform ${PLATFORM}, attempting both ICO and ICNS generation...`);
      await buildIco();
    }
    log("Done ✓");
  } catch (err) {
    fatal(err.message, 1);
  }
})();
