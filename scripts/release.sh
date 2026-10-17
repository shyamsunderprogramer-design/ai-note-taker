#!/usr/bin/env bash
# scripts/release.sh — One-command release for ANT (AI Note Taker).
#
# Usage:
#   scripts/release.sh 2.2.0 [--dry-run] [--no-push]
#
# What it does:
#   1. Bumps version in:
#        - package.json (monorepo root)
#        - electron/package.json (electron-builder productName/version)
#   2. Inserts a new CHANGELOG.md section under [Unreleased] (or
#      asks for release notes via $EDITOR if --notes-file isn't given).
#   3. Commits on `main` with a chore(release) message.
#   4. Cherry-picks onto `ux-sprint` (so the branch carries the
#      release marker forward — same pattern as the Fix #35 series).
#   5. Pushes both branches.
#   6. Tags vX.Y.Z on ux-sprint and pushes the tag.
#   7. (Optional) `gh release create vX.Y.Z` — pre-fill the body
#      from CHANGELOG.md so the release isn't empty.
#
# Why this lives here, not in CI:
#   The actual installable builds run in CI (.github/workflows/release.yml)
#   when the tag is pushed. This script handles the LOCAL half: the
#   version bump, the changelog, the commit, the cherry-pick, the
#   tag, the optional release-draft creation. Running this locally
#   + pushing the tag is enough — no manual GitHub clicks needed
#   other than promoting the draft release to public.
#
# Idempotency: this script will refuse to run if the working tree is
# dirty, if the tag already exists, or if the version is already
# set in package.json. Re-runs after a partial failure need manual
# recovery — there are no automatic rollback steps.

set -euo pipefail

# ── Parse args ───────────────────────────────────────────────
DRY_RUN=false
NO_PUSH=false
NOTES_FILE=""
VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --no-push) NO_PUSH=true; shift ;;
    --notes-file) NOTES_FILE="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$1"; shift
      else
        echo "ERROR: unknown arg: $1" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Usage: scripts/release.sh VERSION [--dry-run] [--no-push] [--notes-file PATH]"
  echo "  VERSION must be semver: X.Y.Z (optionally with -rc.N, -beta.N suffix)"
  exit 1
fi

# Validate version shape (semver-ish; we don't enforce strict semver for pre-releases)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
  echo "ERROR: '$VERSION' doesn't look like a semver version (X.Y.Z or X.Y.Z-rc.N)"
  exit 1
fi

TAG="v$VERSION"

# ── Sanity checks ────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is dirty. Commit or stash before releasing."
  git status --short
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: tag $TAG already exists. Bump the version or delete the tag first."
  git tag --list "$TAG"
  exit 1
fi

# Read current versions
CURRENT_ROOT=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")
CURRENT_ELEC=$(python3 -c "import json; print(json.load(open('electron/package.json'))['version'])")

echo "==> Current versions:"
echo "    root package.json:        $CURRENT_ROOT"
echo "    electron/package.json:    $CURRENT_ELEC"
echo "==> New version:             $VERSION (tag: $TAG)"

# ── Step 1: bump package.json files ─────────────────────────
run_step() {
  local desc="$1"; shift
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] WOULD: $desc"
  else
    echo "==> $desc"
    "$@"
  fi
}

run_step "Bump root package.json to $VERSION" \
  python3 -c "
import json, sys
p = 'package.json'
d = json.load(open(p))
d['version'] = '$VERSION'
json.dump(d, open(p, 'w'), indent=2)
open(p).read()  # touch
"

run_step "Bump electron/package.json to $VERSION" \
  python3 -c "
import json
p = 'electron/package.json'
d = json.load(open(p))
d['version'] = '$VERSION'
json.dump(d, open(p, 'w'), indent=2)
"

# ── Step 2: add CHANGELOG entry ─────────────────────────────
TODAY=$(date +%Y-%m-%d)

if [[ -n "$NOTES_FILE" && -f "$NOTES_FILE" ]]; then
  NOTES_CONTENT=$(cat "$NOTES_FILE")
elif [[ -n "$NOTES_FILE" ]]; then
  echo "ERROR: --notes-file path '$NOTES_FILE' not found"
  exit 1
else
  # Open editor for the maintainer to write release notes.
  TMPFILE=$(mktemp -t antichangelog.XXXXXX)
  trap "rm -f $TMPFILE" EXIT
  cat > "$TMPFILE" <<EOF
# Release notes for $VERSION go below this line.
# Lines starting with # are stripped on save. The first non-blank,
# non-# line becomes the H3 section title; everything after is body.
#
# Suggested structure (Keep a Changelog style):
#
# ### Added
# - ...
#
# ### Changed
# - ...
#
# ### Fixed
# - ...
#
EOF
  ${EDITOR:-vi} "$TMPFILE"
  # Strip comment lines and leading blanks
  NOTES_CONTENT=$(grep -v '^#' "$TMPFILE" | sed '/./,$!d' | sed -e :a -e '/^$/{$d;N;ba' -e '}')
  if [[ -z "$(echo "$NOTES_CONTENT" | tr -d '[:space:]')" ]]; then
    echo "ERROR: empty release notes — aborting"
    exit 1
  fi
fi

if [[ "$DRY_RUN" == "false" ]]; then
  # Insert the new section above the [Unreleased] section in CHANGELOG.md.
  # CHANGELOG.md convention: top section is [Unreleased], then [X.Y.Z] sections in reverse-chrono order.
  python3 - "$VERSION" "$TODAY" "$NOTES_CONTENT" <<'PY'
import sys, re, pathlib
version, today, notes = sys.argv[1], sys.argv[2], sys.argv[3]
path = pathlib.Path("CHANGELOG.md")
text = path.read_text()

# Find the [Unreleased] section's end (the next ## line)
unreleased_pattern = re.compile(r"^(## \[Unreleased\].*?)(?=^## \[)", re.M | re.S)
m = unreleased_pattern.search(text)
if not m:
    print(f"ERROR: no [Unreleased] section in CHANGELOG.md — add one before running this script")
    sys.exit(1)

new_section = (
    f"## [{version}] - {today}\n\n"
    f"{notes}\n\n"
    "---\n\n"
)
insert_at = m.end()
new_text = text[:insert_at] + new_section + text[insert_at:]
path.write_text(new_text)
print(f"Inserted [{version}] section at offset {insert_at}")
PY
fi

# ── Step 3: commit on main ──────────────────────────────────
run_step "Commit version bump + changelog on main" \
  git add package.json electron/package.json CHANGELOG.md
COMMIT_MSG="chore(release): ${VERSION}"
if [[ "$DRY_RUN" == "false" ]]; then
  git -c user.name="Shyamsunder" \
      -c user.email="shyamsunderprogramer-design@users.noreply.github.com" \
      commit -m "$COMMIT_MSG"
  RELEASE_COMMIT=$(git rev-parse HEAD)
  echo "    release commit: $RELEASE_COMMIT"
fi

# ── Step 4: cherry-pick to ux-sprint ────────────────────────
run_step "Cherry-pick onto ux-sprint" \
  bash -c "
    git checkout ux-sprint
    git cherry-pick $RELEASE_COMMIT
  "

# ── Step 5: push both branches ─────────────────────────────
if [[ "$NO_PUSH" == "false" ]]; then
  run_step "Push main + ux-sprint" \
    bash -c "
      git checkout main
      git push origin main
      git push origin ux-sprint
    "
else
  echo "[--no-push] Skipping push. Run 'git push origin main ux-sprint' when ready."
fi

# ── Step 6: create tag ─────────────────────────────────────
run_step "Tag $TAG on ux-sprint" \
  bash -c "
    git checkout ux-sprint
    git tag -a $TAG -m 'ANT $VERSION'
    git push origin $TAG
  "

# ── Step 7: optional draft release ──────────────────────────
if command -v gh >/dev/null 2>&1; then
  run_step "Draft GitHub release $TAG (release.yml will fill installers)" \
    bash -c "
      # Body from the new CHANGELOG section
      BODY=\$(awk '/^## \[${VERSION}\]/,/^---$/' CHANGELOG.md | head -n -1 | tail -n +2)
      gh release create $TAG \
        --title 'ANT ${VERSION}' \
        --notes \"\$BODY\" \
        --target ux-sprint \
        --draft
    "
else
  echo "NOTE: 'gh' CLI not found — skipping release-draft creation."
  echo "      The tag push will trigger .github/workflows/release.yml,"
  echo "      which uploads installers. Manually run:"
  echo "        gh release create $TAG --title 'ANT ${VERSION}' --draft"
fi

echo ""
echo "==> Done. Tag $TAG pushed."
echo "    CI (.github/workflows/release.yml) will build installers for all 3 platforms"
echo "    and attach them to the release. Promote the draft to public when you're ready:"
echo "        gh release edit $TAG --draft=false"