# ANT product website

Static marketing website for the desktop app, deployed to https://ai-note-taker-five.vercel.app/ through the existing GitHub/Vercel connection. It contains product information, illustrative examples, downloads and documentation links. It does not host the browser app or call the backend.

```sh
npm run site:build
npm run site:preview
```

Open http://127.0.0.1:4178. The build requires only Node.js and copies an explicit public asset list to `apps/landing/dist`. The shared font and primitive styles come from `electron/renderer`; no renderer JavaScript or desktop runtime is published. Vercel skips dependency installation and uses this same build command.

`release.json` pins the published installer version independently of the evolving desktop package version. Before changing it, verify all six GitHub release artifacts and `SHA256SUMS.txt`. Keep source-only features and dated evidence distinct from the installers. `updated` is the date the information was reviewed.

The original visual design and artwork are retained; see [DESIGN.md](DESIGN.md) and [asset sources](assets/README.md). Old `/app` and sign-in links redirect to the downloads section. `retire-sw.js` replaces earlier PWA workers and removes only public `ant-cache-*` caches; it does not clear localStorage or IndexedDB.

Run `npm run site:test` after installing the repository's test dependencies. Use `ANT_BROWSER_CHANNEL=chrome` for installed Chrome or the default Playwright Chromium. The smoke test serves a local preview, checks desktop/mobile layouts, keyboard controls, examples, download links, accessibility, redirects and service-worker retirement. `ANT_AXE_MODULE` can select an externally installed `@axe-core/playwright` module.

Pushing to the connected production branch (`main`) triggers Vercel. Verify the GitHub deployment status, production HTML source-commit metadata, security headers and live smoke checks before reporting the update as deployed.
