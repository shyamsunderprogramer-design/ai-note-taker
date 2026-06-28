#!/bin/bash
# ANT (AI Note Taker) — INSTALL.command
# v2.1.9: Helper for unsigned macOS builds. macOS Gatekeeper silently
# blocks first launch for apps inside downloaded DMGs (syspolicyd
# terminates the process before any user code runs). This script:
#   1. Copies ANT to /Applications (or ~/Applications as fallback)
#   2. Ad-hoc codesigns the installed bundle
#   3. Recursively strips ALL extended attributes (including
#      com.apple.quarantine and com.apple.provenance)
#   4. Opens the app
#
# Standard pattern for unsigned Mac apps — same approach used by Homebrew
# Cask, Notion beta, Figma beta, and most indie dev tools until they
# enroll in the Apple Developer Program.
#
# Usage: Double-click INSTALL.command from inside the mounted DMG window.
#
# IMPORTANT: Even with this script, macOS will show a Gatekeeper dialog
# ("ANT (AI Note Taker) is from an unidentified developer") on the very
# first launch. You MUST click "Open" in that dialog. If you click
# Cancel or close the dialog, the app dies silently and looks like a
# crash. To re-trigger the dialog after Cancel: right-click the app in
# /Applications and choose "Open" — that one-click bypasses the dialog
# forever.
set -e

APP_NAME="ANT (AI Note Taker).app"
DMG_APP="$(dirname "$0")/${APP_NAME}"
SYSTEM_APP="/Applications/${APP_NAME}"
USER_APP="${HOME}/Applications/${APP_NAME}"

echo "============================================="
echo "  ANT (AI Note Taker) — installer helper"
echo "============================================="
echo ""

if [ ! -d "$DMG_APP" ]; then
  echo "ERROR: Could not find ${APP_NAME} next to this script."
  echo "Make sure you double-clicked INSTALL.command from inside the mounted"
  echo "DMG window, not from a folder where you copied it elsewhere."
  echo ""
  read -p "Press Enter to close."
  exit 1
fi

# Decide install destination. Prefer /Applications; fall back to
# ~/Applications if the user can't write to /Applications (e.g. on a
# managed Mac, or if sudo would be required). ~/Applications is a real
# Launch Services path on macOS — apps installed there work identically.
DEST_APP="$SYSTEM_APP"
if [ ! -w "/Applications" ]; then
  echo "→ No write access to /Applications, installing to ~/Applications instead."
  mkdir -p "${HOME}/Applications"
  DEST_APP="$USER_APP"
fi

echo "→ Copying ${APP_NAME} to $(dirname "$DEST_APP")..."
rm -rf "$DEST_APP" 2>/dev/null || true
cp -R "$DMG_APP" "$DEST_APP"

echo "→ Ad-hoc codesigning installed bundle..."
# Ad-hoc signing silences the Gatekeeper "no usable signature" rejection
# path even though it can't satisfy the Developer ID requirement. Done
# AFTER copy so the signature covers the final on-disk layout.
codesign --force --deep --sign - "$DEST_APP" 2>&1 | sed 's/^/   /'

echo "→ Removing all extended attributes (quarantine + provenance)..."
# -c clears ALL attrs (safer than -d which only removes the named one).
# Without -r, nested files keep their attrs and Gatekeeper still kills
# the launch. We use -cr to be belt-and-suspenders against any future
# attrs Apple adds.
xattr -cr "$DEST_APP" 2>/dev/null || true

echo "→ Verifying signature..."
if codesign --verify --verbose=2 "$DEST_APP" 2>&1 | sed 's/^/   /'; then
  echo "   ✓ signature OK"
else
  echo "   ⚠ signature verification failed (Gatekeeper may still complain)"
fi

echo ""
echo "→ Launching ${APP_NAME}..."
echo ""
echo "============================================="
echo "  ⚠  IMPORTANT — READ THIS CAREFULLY"
echo "============================================="
echo "macOS will show a Gatekeeper dialog asking whether to open the app"
echo "(this is normal for unsigned apps). YOU MUST CLICK 'Open' in that"
echo "dialog. If you click Cancel — or close the dialog without choosing"
echo "— the app will exit silently within 5 seconds and look like a crash."
echo ""
echo "If you missed the dialog (or clicked Cancel):"
echo "  1. Quit this Terminal window"
echo "  2. In Finder, go to $(dirname "$DEST_APP")"
echo "  3. Right-click (or Control-click) ${APP_NAME}"
echo "  4. Choose 'Open' from the menu"
echo "  5. Click 'Open' in the dialog"
echo ""
echo "After the first successful Open, the app is whitelisted and will"
echo "launch normally from now on."
echo "============================================="
echo ""

# Open the app via 'open' (Launch Services). The Gatekeeper dialog is
# shown by Launch Services itself; the app does NOT start until the
# user clicks Open.
open "$DEST_APP"

echo ""
echo "✓ Done! Look for the Gatekeeper dialog and click Open."
echo ""
read -p "Press Enter to close this Terminal window."