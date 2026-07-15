"""Regenerate the GUI scheme preview for poincare.

The original PNG (from `gen_fable_shape_schemes`) drew the DISC model: a circular
{7,3} tiling with a radial triangular fan inside each heptagon. The engine does
not draw that. `_gen_poincare` uses the BAND model -- heptagons laid in a
horizontal strip, each split into 7 khatam kites, each kite subdivided by a
hyperbolic transfinite QUAD mesh (no radial fan, no pole). Keeping the old disc
scheme would advertise a pattern the mosaic never produces -- the exact trap the
girih scheme rebuild warned about (proposal tool != engine). So this is rebuilt
straight from the engine's own `_poincare_cells`, the single source of truth.

Colouring encodes the grout hierarchy so all three levels read at a glance:
  * each HEPTAGON (g3) gets a distinct hue via the golden-angle rotation
    (137.5 deg/step), so neighbouring heptagons never collide -> the {7,3}
    tiling is legible;
  * within a heptagon each of the 7 KITES (g2) is a slightly different value,
    so the khatam split shows;
  * the nd^2 sub-cells of a kite share the kite colour, and only the black
    OUTLINE reveals the quad mesh -> L1 sub-cell / L2 kite / L3 heptagon in one
    picture.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_poincare_scheme
"""
import colorsys
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.engine_smart import _poincare_cells

logger = logging.getLogger(__name__)

ASSETS_DIR = Path("assets/shape_schemes")
SIZE = 720
SS = 2
BASE_S = 58.0
BG = (16, 16, 20)
OUTLINE = (10, 10, 12)


def heptagon_rgb(hi, k):
    """Distinct hue per heptagon (golden-angle) + value shade per kite."""
    hue = (hi * 137.507) % 360.0 / 360.0
    sat = 0.52
    # 7 kites span a modest value band so the khatam split is visible but the
    # heptagon still reads as one colour family
    val = 0.62 + 0.05 * (k - 3)
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return (int(r * 255), int(g * 255), int(b * 255))


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    d = ImageDraw.Draw(img)

    n = 0
    hepts = set()
    for poly, hi, k in _poincare_cells(SIZE, SIZE, BASE_S):
        d.polygon([(p[0] * SS, p[1] * SS) for p in poly],
                  fill=heptagon_rgb(hi, k), outline=OUTLINE, width=2)
        hepts.add(hi)
        n += 1

    out = ASSETS_DIR / "poincare.png"
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out)
    print(f"[gen] poincare: {n} cells, {len(hepts)} heptagons -> {out}")


if __name__ == "__main__":
    main()
