# Local security patch

This private adapter is used by the monorepo dependency overrides. It is not an upstream release. Original vendored licenses are retained.

Uses patched image-size 2.0.4 while preserving the callable export consumed by Metro 0.73. This avoids silently breaking asset builds with the newer object export.
