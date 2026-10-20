/** Product-site smoke tests against the actual built output and Vercel routes.
 * Run npm run site:build first. No live backend or real user profile is used.
 */
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const path = require("node:path");
const { readFileSync } = require("node:fs");
const { chromium, firefox } = require("playwright");
const root = path.resolve(__dirname, "../..");
const port = Number(process.env.ANT_SITE_TEST_PORT || 4186);
const base = `http://127.0.0.1:${port}`;
const { version } = require("../../electron/package.json");

(async () => {
  const server = spawn(process.execPath, ["scripts/preview-site.mjs"], {
    cwd: root,
    env: { ...process.env, PORT: String(port) },
    stdio: ["ignore", "pipe", "inherit"],
  });
  let browser;
  try {
    // Check the actual entry files: Vercel serves the filesystem before rewrites.
    assert.match(
      readFileSync(path.join(root, "apps/web/dist/index.html"), "utf8"),
      /data-ant-product-site/,
    );
    assert.match(
      readFileSync(path.join(root, "apps/web/dist/browser-app.html"), "utf8"),
      /js\/core\/auth-helper.js/,
    );
    await Promise.race([
      once(server.stdout, "data"),
      once(server, "exit").then(([code]) => {
        throw Error(`Preview exited with ${code}`);
      }),
      new Promise((_, reject) => {
        const timer = setTimeout(() => reject(Error("Preview startup timed out")), 15000);
        timer.unref();
      }),
    ]);
    const requests = [
      "/",
      "/app",
      "/index.html",
      "/signin",
      "/signin.html",
      "/cognitive-graph",
      "/manifest.json",
      "/sw.js",
      "/site/assets/architecture.svg",
      "/site/assets/social-preview.png",
      "/site/assets/ant-mark.png",
      "/site/assets/ant-mark-light.png",
      "/robots.txt",
      "/sitemap.xml",
    ];
    for (const route of requests) assert.equal((await fetch(base + route)).status, 200, route);
    for (const name of ["ant-queen", "ant-knowledge"]) {
      for (const width of [640, 1280]) {
        const response = await fetch(`${base}/site/assets/${name}-${width}.webp`);
        assert.equal(response.status, 200);
        assert.equal(response.headers.get("content-type"), "image/webp");
      }
    }
    assert.equal(
      (await fetch(base + "/site/missing.js")).status,
      404,
      "missing scripts must not return HTML",
    );
    assert.equal(
      (await fetch(base + "/missing-page")).status,
      404,
      "missing pages must not return the app",
    );
    assert.equal((await (await fetch(base + "/manifest.json")).json()).start_url, "/app");
    assert.equal(
      (await fetch(base + "/index.html", { redirect: "manual" })).headers.get("location"),
      "/app",
    );

    for (const engine of [chromium, firefox]) {
      browser = await engine.launch();
      for (const theme of ["light", "dark"]) {
        for (const width of [1440, 390, 320]) {
          const context = await browser.newContext({
            viewport: { width, height: 900 },
            colorScheme: theme,
            reducedMotion: "reduce",
            serviceWorkers: "block",
          });
          const page = await context.newPage();
          const errors = [];
          const failedAssets = [];
          const externalRequests = [];
          page.on("pageerror", (e) => errors.push(e.message));
          page.on("response", (response) => {
            if (response.status() >= 400) failedAssets.push(response.url());
          });
          page.on("request", (request) => {
            if (!request.url().startsWith(base)) externalRequests.push(request.url());
          });
          await page.goto(base, { waitUntil: "networkidle" });
          // The responsive hero and theme-specific original ant mark must decode
          // from the built site, not silently render as broken image placeholders.
          await page
            .locator(".hero-artwork img, .site-header .brand-mark img")
            .evaluateAll((images) => Promise.all(images.map((image) => image.decode())));
          assert.equal(await page.locator("h1").count(), 1);
          assert.equal(
            await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
            true,
            `${engine.name()} ${theme} ${width}: reflow`,
          );
          assert.deepEqual(errors, []);
          assert.deepEqual(failedAssets, []);
          assert.deepEqual(
            externalRequests,
            [],
            "the product site must not contact a backend or tracker",
          );
          assert.equal(await page.locator('a[href*="releases/download/"]').count(), 7);
          for (const href of await page
            .locator('a[href*="releases/download/"]')
            .evaluateAll((links) => links.map((link) => link.href)))
            assert.ok(href.includes(`/v${version}/`), href);
          for (const href of await page
            .locator('a[href^="#"]')
            .evaluateAll((links) => links.map((link) => link.getAttribute("href"))))
            assert.equal(await page.locator(href).count(), 1, `missing anchor ${href}`);
          await page.keyboard.press("Tab");
          assert.equal(await page.evaluate(() => document.activeElement.className), "skip-link");
          await page.keyboard.press("Enter");
          assert.equal(await page.evaluate(() => document.activeElement.id), "main");
          const meeting = page.getByRole("tab", { name: "Meeting notes" });
          await meeting.focus();
          await page.keyboard.press("ArrowRight");
          assert.equal(
            await page.getByRole("tab", { name: "Screen questions" }).getAttribute("aria-selected"),
            "true",
          );
          assert.equal(new URL(page.url()).searchParams.get("example"), "screen");
          await page.keyboard.press("End");
          assert.equal(
            await page.getByRole("tab", { name: "Interview prep" }).getAttribute("aria-selected"),
            "true",
          );
          await page.goBack();
          assert.equal(
            await page.getByRole("tab", { name: "Screen questions" }).getAttribute("aria-selected"),
            "true",
          );
          await page.reload();
          assert.equal(
            await page.getByRole("tabpanel", { name: "Screen questions" }).isVisible(),
            true,
          );
          for (const summary of await page.locator(".faq-list summary").all()) {
            await summary.focus();
            await page.keyboard.press("Enter");
            assert.equal(await summary.locator("..").getAttribute("open"), "");
          }
          await page.locator(".closing img").scrollIntoViewIfNeeded();
          await page.locator(".closing img").evaluate((image) => image.decode());
          assert.deepEqual(failedAssets, []);
          if (width < 851) {
            const menu = page.getByRole("button", { name: "Menu", exact: true });
            await menu.click();
            assert.equal(await menu.getAttribute("aria-expanded"), "true");
            await page.keyboard.press("Escape");
            assert.equal(await menu.getAttribute("aria-expanded"), "false");
            assert.equal(await menu.evaluate((el) => document.activeElement === el), true);
            await menu.click();
            await page
              .getByRole("navigation", { name: "Main navigation" })
              .getByRole("link", { name: "Privacy", exact: true })
              .click();
            assert.equal(await menu.getAttribute("aria-expanded"), "false");
            assert.ok(
              (await page.locator("#privacy").boundingBox()).y >= 72,
              "sticky header must not cover the section",
            );
          }
          await context.close();
        }
      }
      // Exercise the public /app entry and both login URLs with a fake backend.
      const context = await browser.newContext({ serviceWorkers: "block" });
      await context.route("http://127.0.0.1:8000/**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ auth_required: true, status: "healthy", models: [] }),
        }),
      );
      const page = await context.newPage();
      await page.goto(base + "/app");
      await page.waitForURL("**/signin.html");
      await page.getByRole("textbox", { name: "Username", exact: true }).waitFor();
      assert.equal(await page.locator("#auth-login-overlay").count(), 0);
      await page.goto(base + "/signin");
      await page.getByRole("textbox", { name: "Username", exact: true }).waitFor();
      assert.equal(await page.locator("#auth-login-overlay").count(), 0);
      await context.close();
      await browser.close();
      browser = null;
      console.log(
        `${engine.name()}: 6 responsive/theme states, keyboard, examples, history, FAQ, navigation and app sign-in passed.`,
      );
    }
    // A static visitor still gets usable downloads without scripting.
    browser = await chromium.launch();
    const context = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    const page = await context.newPage();
    await page.goto(base);
    assert.equal(
      await page.getByRole("link", { name: "Apple Silicon", exact: true }).isVisible(),
      true,
    );
    assert.equal(await page.locator('a[href*="releases/download/"]').count(), 7);
    console.log(
      "Built routes, missing assets, manifest, download links and no-JavaScript downloads passed.",
    );
  } finally {
    await browser?.close();
    server.kill("SIGTERM");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
