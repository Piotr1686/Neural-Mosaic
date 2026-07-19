"""Regenerate the GUI scheme previews for sprint E5 (Islamic stars).

Drawn FROM THE ENGINE generators (the girih/poincare/truchet lesson — and
E5's own: the proposal's gereh drew the 4.8.8 gap square axis-aligned, a real
overlap+holes bug hidden by the PNG outlines; the engine draws the diamond).
Colouring is a neutral per-cell position ramp.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e5_schemes
"""
import colorsys
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import _gen_gereh, _gen_rosette

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("gereh", _gen_gereh, 42, (0.06, 0.13)),      # amber
    ("rosette", _gen_rosette, 34, (0.52, 0.60)),  # blue
]


def _centroid(poly):
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_dir = Path(__file__).resolve().parents[2] / "assets" / "shape_schemes"

    for name, gen, base_s, (h0, h1) in SHAPES:
        img = Image.new("RGB", (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        polys = [[tuple(p) for p in poly] for poly in gen(None, SIZE, SIZE, base_s)]
        for i, poly in enumerate(polys):
            cx, cy = _centroid(poly)
            t = ((cx / SIZE) * 0.6 + (cy / SIZE) * 0.4) % 1.0
            hue = h0 + (h1 - h0) * t
            val = 0.55 + 0.35 * ((i * 7) % 5) / 4.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.62, val)
            draw.polygon(poly, fill=(int(r * 255), int(g * 255), int(b * 255)),
                         outline=OUTLINE)
        path = out_dir / f"{name}.png"
        img.save(path)
        log.info("Saved: %s  (%d cells)", path, len(polys))


if __name__ == "__main__":
    main()
