# Expanded desktop capture investigation

Status: **DONE_WITH_CONCERNS**. The additional live capture paths passed on this
machine. Universal screenshot invisibility remains unverified.

## Symptom and hypothesis

The project requires protected content, including dropdowns, to remain absent
from screenshots and recordings. The previous ScreenCaptureKit test exercised
only single-window screenshots. Hypothesis: a recorder using full-display
capture or a continuous stream might still see the protected content.

No such leak was reproduced in the final run. No speculative production
workaround or change to the user's protection settings was applied.

## Changes

- Extended `qa/performance/renderer/capture-fixture.swift` with full-display
  screenshots and continuous SCStream capture. The recorder supplies no
  application/window exclusions. Display images are cropped in memory to the
  synthetic fixture region before writing evidence.
- Extended `protected-controls.cjs` to check every recorded frame, require
  multiple frames, verify an unprotected control for each capture mode, and
  fail if protected content appears. Accepted results contain only the blank
  window image or the synthetic green backdrop, within color tolerance.
- The synthetic backdrop extends beyond the fixture to cover rounded corners.
  Its color animation forces continuous frame delivery. The fixture button also
  animates opacity to exercise updates without moving the hover target.

## Final live evidence

Environment: macOS **27.2 (26B123)**, Electron **41.10.7**.

Command:

```sh
node qa/performance/renderer/protected-controls.cjs --capture --screen-capture-kit
```

| Capture path | Unprotected fixture fraction | Protected unexpected pixels | Result |
| --- | ---: | ---: | --- |
| ScreenCaptureKit single window | 0.964568 | 0 | Excluded |
| ScreenCaptureKit full display | 0.964979 | 0 | Excluded |
| ScreenCaptureKit continuous display | 0.963581 | 0 across all 18 frames | Excluded |
| macOS region screenshot | Visible control | Protected picker/tooltip excluded | Passed |

The final command exited successfully. Keyboard selection, hover/focus tooltip,
dynamic controls, scrolling, reload and protection-flag checks also passed.
The final recorded protected frame was visually inspected: only the synthetic
green backdrop remained. Desktop regression suite: **260 passed, 0 failed**.

Artifacts:
`/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-controls-CV0TB3`

Final source SHA-256:

```text
protected-controls.cjs 73d8a93b721ecd2f18c8a35014c3728edc3f35511edaeda3d603df03540ed353
capture-fixture.swift d31828c68be83471af8dde3de09b8211bff484c1b802410be884c36347977a76
```

## Investigation issues and limits

The first expanded run could not find the fixture through the on-screen-only
window inventory. The helper now queries the complete inventory; a visible
unprotected control is still mandatory, so a missing/hidden fixture cannot pass.
Another run detected pixels around the rounded test backdrop corners. Inspection
showed the desktop around that backdrop, not protected content. Enlarging the
opaque backdrop corrected the fixture instead of relaxing the pixel criterion.
A moving button initially prevented Playwright's stable hover; opacity animation
preserves frame updates and permits the real hover check.

These are live OS captures of an isolated Electron fixture using the app's real
preload, styles and selectors. They are not captures of the user's private app
contents. This pass does not test other OS versions, all third-party recorders,
privileged capture mechanisms, remote desktops or enabling protection midway
through an already-running unprotected recording. The stream is a bounded
1.2-second observation, not a long-duration guarantee. The earlier OS-level
limitation documented by Electron remains relevant beyond these observations.

Scope covered QA helpers and documentation, with read-only inspection of the
production protection lifecycle. No scope lock was acquired while the possible
source of the leak spanned QA, preload and native window protection. No
production files changed in this investigation.

Durable learning: a single-window screenshot is insufficient evidence for
full-display recording. Require visible controls, inspect every frame, and use
an oversized opaque fixture backdrop so rounded corners cannot contaminate
leak detection or save unrelated desktop pixels.
