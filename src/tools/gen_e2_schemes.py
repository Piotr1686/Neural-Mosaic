"""Regenerate the GUI scheme previews for bloom and pebbles (sprint E2).

Both original PNGs (from `gen_extra_shape_schemes`) advertise geometry the
engine does not draw -- the trap that already caught girih, poincare, truchet
and penrose_p2 (proposal tool != engine):

  * bloom drew the GOLDEN-angle Vogel lattice and carried its motif (the 21
    Fibonacci parastichy arms) in COLOUR. That lattice is `phyllotaxis`, so the
    scheme advertised a shape the mosaic already had; colour is nothing once
    photos replace it. The engine's bloom uses the LUCAS angle instead, whose
    arm count genuinely differs -- so the scheme must show that lattice.
  * pebbles drew a fixed 720-seed sample in a unit square. The engine derives
    the seed count from base_s, stops on the in-frame count and pads the margin
    with a scaffold ring, so its patch is a different density and crop.

Colouring is deliberately neutral (a per-cell hue ramp, no motif encoded), so
neither picture can carry a distinction the geometry does not have.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e2_schemes
"""
import colorsys
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import _gen_bloom, _gen_pebbles

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("bloom", _gen_bloom, 30, (0.06, 0.10)),      # warm sunflower hues
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
