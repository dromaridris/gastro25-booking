"""Prepare transparent dept logo and regenerate favicon / PWA icons."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit('Pillow required: pip install Pillow') from exc

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'static' / 'logos' / 'jpmc_gastro_logo.png'
OUT = ROOT / 'static' / 'icons'
SIZES = (16, 32, 48, 64, 180, 192, 512)

# Black flood-fill tolerance — removes square canvas only, keeps inner emblem/text.
BG_FLOOD_THRESH = 28


def make_background_transparent(img: Image.Image, *, thresh: int = BG_FLOOD_THRESH) -> Image.Image:
    """Flood-fill outer black canvas to transparent; preserve inner emblem artwork."""
    rgba = img.convert('RGBA')
    w, h = rgba.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    for x, y in seeds:
        r, g, b, a = rgba.getpixel((x, y))
        if r <= thresh and g <= thresh and b <= thresh:
            ImageDraw.floodfill(rgba, (x, y), (0, 0, 0, 0), thresh=thresh)
    return rgba


def _square_rgba(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = max(w, h)
    canvas = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return canvas


def prepare_logo(source: Path, dest: Path | None = None) -> Path:
    dest = dest or SRC
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = make_background_transparent(Image.open(source))
    img.save(dest, format='PNG', optimize=True)
    return dest


def generate_icons(source: Path | None = None) -> None:
    source = source or SRC
    if not source.is_file():
        raise SystemExit(f'Missing source logo: {source}')
    OUT.mkdir(parents=True, exist_ok=True)
    base = _square_rgba(make_background_transparent(Image.open(source)))
    ico_sizes: list[tuple[int, int]] = []

    for size in SIZES:
        resized = base.resize((size, size), Image.Resampling.LANCZOS)
        name = {
            16: 'icon-16.png',
            32: 'icon-32.png',
            48: 'icon-48.png',
            64: 'icon-64.png',
            180: 'icon-180.png',
            192: 'icon-192.png',
            512: 'icon-512.png',
        }[size]
        resized.save(OUT / name, format='PNG', optimize=True)
        if size in (16, 32, 48):
            ico_sizes.append((size, size))

    # Multi-size ICO for browser tabs.
    ico_images = [base.resize((s, s), Image.Resampling.LANCZOS) for s in (16, 32, 48)]
    ico_images[1].save(OUT / 'favicon.ico', format='ICO', sizes=ico_sizes)
    print(f'Logo: {source}')
    print(f'Icons written to {OUT}')


def main() -> None:
    if len(sys.argv) > 1:
        incoming = Path(sys.argv[1]).resolve()
        if not incoming.is_file():
            raise SystemExit(f'File not found: {incoming}')
        prepare_logo(incoming, SRC)
    elif not SRC.is_file():
        raise SystemExit(f'Missing source logo: {SRC}')
    else:
        prepare_logo(SRC, SRC)
    generate_icons(SRC)


if __name__ == '__main__':
    main()
