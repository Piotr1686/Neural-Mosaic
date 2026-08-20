"""Regenerate the GUI scheme preview for pebbles (sprint E2).

The original PNG (from `gen_extra_shape_schemes`) advertises geometry the
engine does not draw -- the trap that already caught girih, poincare, truchet
and penrose_p2 (proposal tool != engine):

  * pebbles drew a fixed 720-seed sample in a unit square. The engine derives
    the seed count from base_s, stops on the in-frame count and pads the margin
    with a scaffold ring, so its patch is a different density and crop.

Colouring is deliberately neutral (a per-cell hue ramp, no motif encoded), so
the picture cannot carry a distinction the geometry does not have.

(E2's other shape, `bloom`, was cut from the registry on 2026-08-20 as a
near-duplicate of `phyllotaxis`; only its Lucas divergence angle set it
apart and that was not legible under photographs.)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e2_schemes
"""
import colorsys
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import _gen_pebbles

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("pebbles", _gen_pebbles, 30, (0.07, 0.13)),  # sandy pebble hues
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
            # hue from the cell's own position: no motif is encoded, so the
            # picture shows the tessellation and nothing else
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
