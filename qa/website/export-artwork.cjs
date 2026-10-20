/** Resize/re-encode the existing ANT artwork for the website; no cropping or redrawing.
 * Run manually when source art changes: node qa/website/export-artwork.cjs
 * Uses the same Chromium install as the website smoke checks; not needed by site:build.
 */
const { chromium } = require("playwright");
const { readFile, writeFile, copyFile, chmod } = require("node:fs/promises");
const path = require("node:path");
const root = path.resolve(__dirname, "../..");
const output = path.join(root, "apps/landing/assets");
const artwork = [
  ["Gemini_Generated_Image_q6ekdzq6ekdzq6ek.png", "ant-queen"],
  ["Gemini_Generated_Image_k0vl0ok0vl0ok0vl.png", "ant-knowledge"],
];

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    for (const [source, name] of artwork) {
      const data = await readFile(path.join(root, "Ant Images", source));
      for (const width of [640, 1280]) {
        const encoded = await page.evaluate(
          async ({ data, width }) => {
            const img = new Image();
            img.src = `data:image/png;base64,${data}`;
            await img.decode();
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = Math.round((width * img.height) / img.width);
            const ctx = canvas.getContext("2d");
            ctx.imageSmoothingQuality = "high";
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL("image/webp", 0.84).split(",")[1];
          },
          { data: data.toString("base64"), width },
        );
        const file = `${name}-${width}.webp`;
        const bytes = Buffer.from(encoded, "base64");
        await writeFile(path.join(output, file), bytes);
        console.log(`${file}: ${bytes.length} bytes`);
      }
    }
    for (const [shade, name] of [
      ["navy blue", "ant-mark"],
      ["sky blue", "ant-mark-light"],
    ]) {
      await copyFile(
        path.join(root, "assets/design/source", `ant horizontal rightside facing - ${shade}.png`),
        path.join(output, `${name}.png`),
      );
      await chmod(path.join(output, `${name}.png`), 0o644);
    }
    let share = await readFile(path.join(output, "social-preview.svg"), "utf8");
    for (const [file, mime] of [
      ["ant-mark.png", "image/png"],
      ["ant-queen-1280.webp", "image/webp"],
    ]) {
      const data = await readFile(path.join(output, file));
      share = share.replace(
        `href="${file}"`,
        `href="data:${mime};base64,${data.toString("base64")}"`,
      );
    }
    const font = await readFile(path.join(root, "apps/web/assets/fonts/Inter-Latin.woff2"));
    await page.setViewportSize({ width: 1200, height: 630 });
    await page.setContent(`<style>
      @font-face {font-family:Inter;src:url(data:font/woff2;base64,${font.toString("base64")})}
      body {margin:0} svg {display:block}
    </style>${share}`);
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(
        [...document.querySelectorAll("image")].map((el) => {
          const image = new Image();
          image.src = el.getAttribute("href");
          return image.decode();
        }),
      );
    });
    await page.screenshot({ path: path.join(output, "social-preview.png") });
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
