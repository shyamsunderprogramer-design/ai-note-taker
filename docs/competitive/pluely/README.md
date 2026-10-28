# Pluely comparison and desktop adaptation

This guide merges the root-level comparison, post-fix comparison, adaptation plan, implementation report, and critical-gap report. All source comparisons are dated April 2026.

## Architecture and decision

The source records compare Pluely's Tauri/Rust approach with ANT's Electron/Python approach. Their main tradeoff is desktop runtime size and resource use versus the Python transcription and AI ecosystem. Retain that tradeoff as design context; the original numerical comparisons are not current benchmarks.

## Adaptation areas

| Area | What the earlier documents discuss | Where to verify |
| --- | --- | --- |
| Desktop lifecycle | Autostart, tray behavior, portable mode, and shortcuts | [Electron runtime](../../../electron/main.js) |
| Storage | SQLite consolidation and user migration | [Database](../../../backend/core/database.py) |
| Audio | System-audio capture, silence, and cleanup | [Electron runtime](../../../electron/main.js) and [voice modules](../../../backend/modules/voice/) |
| Responsiveness | Splash feedback, deferred work, and streaming | [Performance guide](../../business/PERFORMANCE.md) |
| Overlay protection | OS capture behavior and visibility | [Security docs](../../devsecops/README.md) |

## Validation

Use a real installed build and test startup, backend reuse, window visibility, permissions, audio input, database persistence, and shutdown. Measure on the target OS. Verify capture protection with the actual sharing application. Completion claims in a historical implementation summary do not demonstrate those behaviors in a new build.

For normal setup and usage, follow the [project README](../../../README.md). For general competitor research, use the [competitive guide](../README.md).

## Historical references

The overlapping source documents are preserved in one [dated reference record](../../archive/pluely-adaptation.md). Use that record for original technical examples and planning context, not current setup or status.
