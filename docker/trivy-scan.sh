#!/usr/bin/env bash
# docker/trivy-scan.sh — Container image vulnerability scanner.
#
# Scans the ANT backend Docker image for known CVEs using Trivy.
# Run locally or in CI (gated, non-blocking) to surface
# vulnerabilities before they reach production.
#
# Usage:
#   ./docker/trivy-scan.sh                          # Scan default image
#   IMAGE=myregistry/myimage:tag ./docker/trivy-scan.sh
#   SEVERITY=CRITICAL ./docker/trivy-scan.sh        # Only critical
#   OUTPUT=json ./docker/trivy-scan.sh              # JSON output
#   EXIT_ON=CRITICAL ./docker/trivy-scan.sh         # Exit non-zero on critical
#
# Install trivy:
#   brew install trivy  (macOS)
#   apt-get install trivy  (Debian/Ubuntu)
#   See https://aquasecurity.github.io/trivy/latest/getting-started/

set -uo pipefail

IMAGE="${IMAGE:-ant-backend:latest}"
SEVERITY="${SEVERITY:-HIGH,CRITICAL}"
OUTPUT="${OUTPUT:-table}"
EXIT_ON="${EXIT_ON:-}"

# ── Pre-flight checks ─────────────────────────────────────────────────────
if ! command -v trivy >/dev/null 2>&1; then
  echo "❌ Trivy is not installed. See https://aquasecurity.github.io/trivy/latest/getting-started/" >&2
  exit 127
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "ℹ️  Image '$IMAGE' not found locally. Attempting to pull..."
  if ! docker pull "$IMAGE"; then
    echo "❌ Could not pull image: $IMAGE" >&2
    exit 1
  fi
fi

# ── Run scan ──────────────────────────────────────────────────────────────
echo "🔍 Scanning $IMAGE (severity: $SEVERITY, output: $OUTPUT)..."
TRIVY_ARGS=(
  image
  --severity "$SEVERITY"
  --format "$OUTPUT"
  --ignore-unfixed
  "$IMAGE"
)

# Add exit-on threshold if specified
if [[ -n "$EXIT_ON" ]]; then
  TRIVY_ARGS+=(--exit-code 1)
  # Override severity to just the threshold
  TRIVY_ARGS=("${TRIVY_ARGS[@]/$SEVERITY/$EXIT_ON}")
fi

# shellcheck disable=SC2086
trivy "${TRIVY_ARGS[@]}"
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "✅ No vulnerabilities found at severity $SEVERITY"
    ;;
  1)
    echo "⚠️  Vulnerabilities found at severity $SEVERITY" >&2
    ;;
  *)
    echo "❌ Trivy scan failed with exit code $EXIT_CODE" >&2
    ;;
esac

exit $EXIT_CODE
