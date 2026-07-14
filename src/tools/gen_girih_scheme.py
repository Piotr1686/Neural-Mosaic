"""Regenerate the GUI scheme preview for girih.

The original PNG (commit e6c55f4) came from `gen_fable_shape_schemes.gen_girih`,
whose greedy discovered its decagons as it grew. That algorithm does not scale:
at frame size it produced a field of hexagons with almost no rosettes, and ~12%
of the picture as leftover blobs. The engine now seeds the rosettes on a 10-fold
quasi-lattice and fills between them, so the PNG has to be rebuilt from the
engine's own generator (`_gen_girih`) or the scheme would advertise a pattern
the mosaic does not draw -- the lesson from the grout pixelation, where the
proposal tool rasterised differently from the engine and the flaw only surfaced
after the look had been approved.

Cells are coloured by tile type, recovered from the cell's area (every girih
tile has a distinct one): rosette kites gold, hexagons terracotta, bowties
green, rhombs violet, pentagons blue. The traced leftovers -- the few percent
the greedy cannot cover with real girih tiles -- are drawn in grey, honestly.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_girih_scheme
"""
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from src.engine_smart import SHAPE_MODES

logger = logging.getLogger(__name__)

ASSETS_DIR = Path("assets/shape_schemes")
SIZE = 720
SS = 2
BASE_S = 92.0
BG = (16, 16, 20)
OUTLINE = (10, 10, 12)

# unit-edge areas of the girih tiles, in the engine's own unit space
AREAS = {
    "kite": (0.7694, (206, 162, 78)),        # 1/10 of a decagon rosette
    "rhomb": (0.9511, (150, 110, 150)),
    "bowtie": (1.3143, (110, 150, 110)),
    "pentagon": (1.7205, (96, 130, 165)),
    "hexagon": (2.1266, (168, 96, 82)),
}
LEFTOVER = (74, 74, 82)


def vary(rng, col, amount=14):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255))
                 for c in col)


def poly_area(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        s += ax * by - bx * ay
    return abs(s) / 2.0


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    d = ImageDraw.Draw(img)
    # px area of a unit^2, so a cell's area can be read back in unit space
    unit_px = BASE_S * BASE_S / 2.1266
    n = 0
    tally = {}
    for poly in SHAPE_MODES["girih"].generator(None, SIZE, SIZE, BASE_S):
        a = poly_area(poly) / unit_px
        name, (_, col) = min(AREAS.items(), key=lambda kv: abs(kv[1][0] - a))
        if abs(AREAS[name][0] - a) > 0.10:        # matches no girih tile
            name, col = "leftover", LEFTOVER
        tally[name] = tally.get(name, 0) + 1
        d.polygon([(p[0] * SS, p[1] * SS) for p in poly],
                  fill=vary(rng, col), outline=OUTLINE, width=3)
        n += 1
    out = ASSETS_DIR / "girih.png"
    img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out)
    print(f"[gen] girih: {n} cells -> {out}")
    print(f"      {tally}")


if __name__ == "__main__":
    main()
