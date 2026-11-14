# Desktop renderer

This directory contains the HTML, JavaScript, CSS and assets loaded by Electron.
It is part of the desktop application, not a standalone website or PWA.

Run `npm run electron:start` from the repository root. Electron starts the local
Python backend and loads `signin.html`, followed by `index.html`. Auxiliary pages
and overlays share the Electron preload bridge and window protection policy.

`npm run renderer:check` validates local assets and script syntax.
`npm run renderer:test` runs renderer unit tests. Desktop packaging copies this
directory into `Resources/renderer`, excluding tests, development files and data.
