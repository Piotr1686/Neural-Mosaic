"""Regenerate the GUI scheme preview for stagger_tri (sprint E3).

The original PNG (from `gen_extra_shape_schemes`) advertised a distinction the
engine cannot draw -- the trap that already caught kepler_ty, bloom, girih,
poincare, truchet and penrose_p2 (proposal tool != engine). Its `on = (ci & rj)
== 0` flag picked a PALETTE, and colour is nothing once photos fill the cells.

The audit concluded from that flag that the geometry underneath was the plain
`triangle` mode and had to be differentiated. Measurement says the opposite:
the scheme's rows all share one x-phase, whereas `triangle` shifts the phase by
half a base every row (its (c+r)%2 flip rule IS that shift). So the geometry
was already distinct -- constant phase turns every row line into a slip line of
T-junctions -- and it is what the engine now draws, unchanged. Shifting
alternate rows by s/2 instead, as planned, would have rebuilt `triangle`
exactly, displaced by s/2.

The one real change is scale: the scheme used s = base_s (the `triangle`
convention), the engine uses s = 2*base_s/3^(1/4) so a cell averages base_s^2
like the rest of the pool.

Colouring is deliberately neutral (a per-cell position ramp, no motif encoded),
so the picture cannot carry a distinction the geometry does not have.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e3_schemes
"""
import colorsys
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import _gen_braid, _gen_stagger_tri

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("stagger_tri", _gen_stagger_tri, 45, (0.03, 0.09)),   # terracotta hues
    ("braid", _gen_braid, 60, (0.55, 0.63)),               # cool blue hues
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
