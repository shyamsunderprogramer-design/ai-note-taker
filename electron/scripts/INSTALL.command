#!/bin/bash
# ANT (AI Note Taker) — INSTALL.command
# v2.1.8: Helper for unsigned macOS builds. macOS Gatekeeper sets
# com.apple.quarantine on apps inside downloaded DMGs, which silently
# blocks first launch (the process is terminated by syspolicyd before
# any user code runs). This script strips the quarantine xattr recursively
# from the installed bundle, then launches the app.
#
# Standard pattern for unsigned Mac apps — same approach used by Homebrew
# Cask, Notion beta, Figma beta, and most indie dev tools until they
# enroll in the Apple Developer Program.
#
# Usage: Double-click INSTALL.command from inside the mounted DMG window.
set -e

APP_NAME="ANT (AI Note Taker).app"
DMG_APP="$(dirname "$0")/${APP_NAME}"
DEST_APP="/Applications/${APP_NAME}"

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

echo "→ Copying ${APP_NAME} to /Applications..."
rm -rf "$DEST_APP" 2>/dev/null || true
cp -R "$DMG_APP" "$DEST_APP"

echo "→ Removing Gatekeeper quarantine attribute..."
# -d delete, -r recursive. Without -r, nested files keep their quarantine
# flag and Gatekeeper still kills the launch.
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true

echo "→ Launching ${APP_NAME}..."
open "$DEST_APP"

echo ""
echo "Done! ANT (AI Note Taker) is installed and running."
echo "You can quit this Terminal window."
echo ""
read -p "Press Enter to close."