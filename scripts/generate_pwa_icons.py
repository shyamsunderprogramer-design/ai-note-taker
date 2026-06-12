#!/usr/bin/env python3
"""
Generates PWA icon sizes from the master source icon.

Source: assets/design/source/Ant_App_icon.png (2990x1408, RGBA)
Output: apps/web/icon-<size>x<size>.png (7 sizes per manifest.json)

The source is non-square (wider than tall — it's the ant logo with
the wordmark). We crop to a square first (centered crop) so the
generated icons are square as PWA spec requires.

Sizes come from apps/web/manifest.json. If you add new sizes to
the manifest, also add them to the SIZES list below.

Usage: python3 scripts/generate_pwa_icons.py
       (or: `make pwa-icons` once the Makefile lands)
"""
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "assets" / "design" / "source" / "Ant_App_icon.png"
OUT_DIR = REPO / "apps" / "web"

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]


def main():
    if not SRC.is_file():
        raise SystemExit(f"source icon missing: {SRC}")

    img = Image.open(SRC).convert("RGBA")
    w, h = img.size
    if w != h:
        # Centered square crop (PWA spec requires square icons)
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        print(f"[pwa-icons] cropped to square: {side}x{side}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        out = OUT_DIR / f"icon-{size}x{size}.png"
        # LANCZOS resampling = high-quality downscale
        thumb = img.resize((size, size), Image.LANCZOS)
        thumb.save(out, format="PNG", optimize=True)
        kb = out.stat().st_size / 1024
        print(f"[pwa-icons] wrote {out.relative_to(REPO)} ({kb:.1f} KB)")

    print(f"[pwa-icons] OK — {len(SIZES)} icons generated in {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
