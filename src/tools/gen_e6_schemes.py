"""Regenerate the GUI scheme previews for sprint E6 (arcs and radials).

Drawn FROM THE ENGINE generators (the girih/poincare/truchet lesson, and E5's
own: a proposal PNG's outlines hid a real overlap+holes bug in gereh). For
`scales` this matters twice over — the cell boundary is a chain of quarter
arcs, so only the engine's own polygonisation shows the true silhouette.

Colouring is a neutral per-cell position ramp; the row index drives the value
so the imbrication reads as depth.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e6_schemes
"""
import colorsys
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import (_gen_nautilus, _gen_rosette_fractal,
                              _gen_scales)

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("scales", _gen_scales, 46, (0.47, 0.55)),      # teal -> sea blue
    ("nautilus", _gen_nautilus, 44, (0.05, 0.12)),  # shell amber
    ("rosette_fractal", _gen_rosette_fractal, 40, (0.22, 0.32)),  # aloe
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
        row_h = base_s / math.sqrt(2.0)
        for idx, poly in enumerate(polys):
            cx, cy = _centroid(poly)
            t = ((cx / SIZE) * 0.6 + (cy / SIZE) * 0.4) % 1.0
            hue = h0 + (h1 - h0) * t
            if name == "scales":
                band = int(round(cy / row_h))
            elif name == "rosette_fractal":
                # leaf/gap alternation IS the motif (the aloe's leaves and the
                # shadows between them): cells are emitted leaf-then-gap, so
                # the emission parity separates them; radius only tints.
                band = (idx % 2) * 3
            else:                       # chamber index from the pole
                band = int(math.hypot(cx + 0.55 * SIZE / 2,
                                      cy + 0.30 * SIZE / 2) / row_h)
            val = 0.52 + 0.34 * (band % 4) / 3.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.58, val)
            draw.polygon(poly, fill=(int(r * 255), int(g * 255), int(b * 255)),
                         outline=OUTLINE)
        path = out_dir / f"{name}.png"
        img.save(path)
        log.info("Saved: %s  (%d cells)", path, len(polys))


if __name__ == "__main__":
    main()
