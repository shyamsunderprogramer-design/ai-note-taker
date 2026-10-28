# Web build budget

Run `npm run benchmark:web` from the repository root after installing dependencies.
The command builds the production app, checks local script/link/image references
in every generated HTML page plus PWA assets/icons, and exits nonzero for missing
files, build failure, or a build taking over 15 seconds. CI runs this gate.

| Date | Build including npm startup | Asset references | Missing |
|---|---:|---:|---:|
| 2026-09-12 | 0.599 s | 71 | 0 |
| 2026-09-12 (after service-worker fix) | 0.514 s | 71 | 0 |

This is one local warm-dependency run, not a latency percentile or browser load
measurement. Hardware and filesystem affect timing. The check does not execute
scripts or validate dynamically constructed URLs. Classic scripts retain their
original names and global execution semantics; a future module migration could
reduce duplicated assets in the output.
