# Design assets — UI/UX

| Folder | Purpose |
| --- | --- |
| [artwork/](artwork/) | Original generated ANT artwork and source animation, previously in `Ant Images/` |
| [source/](source/) | Reusable ant marks, icons, vector references, and frame samples |
| [prototypes/](prototypes/) | Standalone UI experiments; excluded from application bundles |
| `local-reference/` | Preserved, ignored local reference copies and working media |

The [website artwork exporter](../../qa/website/export-artwork.cjs) reads originals
from `artwork/` and marks from `source/`, then writes production exports to
`apps/landing/assets/`. Run it only when the source artwork changes:

```sh
node qa/website/export-artwork.cjs
```

`prototypes/status-bar.js` is a development simulation with hypothetical IPC
messages. It is reference material, not a runtime entry point.

See the [UI/UX charter](../../OWNERS.uiux.md) and [role map](../../docs/ROLES.md).
