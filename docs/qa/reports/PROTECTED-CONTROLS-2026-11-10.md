# Native dropdown and tooltip capture leak

The supplied Cmd+Shift+4 screenshot showed the protected main window absent while
the native model picker and its availability tooltip remained visible. These are
separate native popup surfaces and do not inherit BrowserWindow protection.

The shared Electron preload now uses Chromium's `base-select` picker on desktop
pages. Options, groups, disabled states and keyboard selection retain their HTML
select semantics, while the picker renders in the document's top layer. Menus
are bounded to the viewport and scroll internally. This applies to dynamically
added selects and all local pages using the shared preload, including overlays.

HTML title attributes are moved into document-rendered tooltips. Dynamic title
updates, focus and hover, Escape dismissal, scroll/resize dismissal, existing
accessible descriptions and icon-only accessible names are handled. Styling is
installed by preload so pages without the main stylesheet are covered. Opaque
popup colors have fallbacks because some overlay pages lack the shared tokens.

## Verification

- Before the fix, the real Electron regression failed: the Model control used
  `appearance: none` instead of the document-rendered picker.
- After the fix, `node qa/performance/renderer/protected-controls.cjs --capture`
  passed in Electron 41.10.7 on macOS. It checks the actual Model/Mode markup and
  shared stylesheet with the production preload in an isolated synthetic window.
- Keyboard selection, dynamic options, hover/focus tooltips, Escape, scrolling,
  reload and the native window protection flag passed.
- OS screenshots used `/usr/sbin/screencapture` on a bounded test-window region
  with an opaque synthetic backdrop. With protection off, the open picker was
  visible. With protection on, the window, open picker and tooltip were excluded;
  more than 99% of the capture matched the backdrop. A color tolerance accounts
  for macOS display color conversion. Renderer screenshots also confirmed the
  picker and tooltip render within the document.
- Desktop suite: 239 passed. Renderer validation: 84 asset references resolved,
  20 scripts syntax-checked. Preload syntax and CRLF-aware whitespace checks passed.

Artifacts from the passing capture run are under
`/var/folders/9h/t1d7p9094p77p_drkjffs2640000gn/T/ant-controls-Bl4SX4/`:
`model-picker.png`, `tooltip.png`, `os-unprotected-picker.png`,
`os-protected-picker.png`, and `os-protected-tooltip.png`.

## Scope

Restart the desktop process to load the preload change. No installer was built.
This validates the demonstrated dropdown/HTML-tooltip leak with macOS screenshot
capture; it does not certify every recorder, native file dialog or OS menu.
ScreenCaptureKit can bypass Electron's content protection. Full screen-reader,
axe and Windows capture checks were not run. The isolated fixture has no backend
access or user account data.
