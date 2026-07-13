"""Regenerate the GUI scheme previews for truchet / truchet_hex.

The original PNGs (commit 2ec504c) were LINE DRAWINGS — thin arcs over a faint
grid. That is what a Truchet pattern looks like on paper, but not what the
engine renders: the engine's cells are the REGIONS the arcs cut out (two
quarter discs + an S-band per square; three pie slices + a curved middle per
hexagon), each filled with one photograph. A scheme that shows curves the
mosaic cannot draw is a lie, so both PNGs are rebuilt from the engine's own
generators (`_gen_truchet`, `_gen_truchet_hex`) — one source of geometry.

Two-tone palette: the arc-corner cells get the accent colour, the middle cells
the dark base, so the Truchet curves still read as the boundary between them.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_truchet_schemes
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
BG = (16, 16, 20)
OUTLINE = (8, 8, 10)

# (shape, base_s, accent, base) — base_s picked so the panel shows a patch of a
# few cells, like the other scheme PNGs.
PANELS = [
    ("truchet", 96.0, (232, 176, 54), (38, 56, 68)),
    ("truchet_hex", 96.0, (120, 214, 178), (34, 60, 62)),
]


def vary(rng, col, amount=16):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255))
                 for c in col)


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for name, base_s, accent, base in PANELS:
        rng = np.random.default_rng(21)
        w = h = SIZE
        img = Image.new("RGB", (w * SS, h * SS), BG)
        d = ImageDraw.Draw(img)
        n = 0
        for poly in SHAPE_MODES[name].generator(None, w, h, base_s):
            # corner cells (quarter disc / pie slice) start at their arc centre
            # and are small; the middle cell is the big one -> split by area.
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            span = max(max(xs) - min(xs), max(ys) - min(ys))
            col = accent if span < 0.75 * base_s else base
            d.polygon([(p[0] * SS, p[1] * SS) for p in poly],
                      fill=vary(rng, col), outline=OUTLINE, width=3)
            n += 1
        out = ASSETS_DIR / f"{name}.png"
        img.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(out)
        print(f"[gen] {name}: {n} cells -> {out}")


if __name__ == "__main__":
    main()
