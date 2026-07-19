"""Regenerate the GUI scheme previews for the puzzle family (sprint P).

Drawn FROM THE ENGINE generators (the girih/poincare/truchet lesson: a
proposal tool can advertise a pattern the engine does not draw), so the PNGs
in assets/shape_schemes are exactly what a render produces. The proposal
schematics that won the user's verdict stay in assets/proposals as history.

Colouring is a neutral per-cell position ramp (no motif encoded) — the
distinction of these shapes is the die-cut tab geometry itself.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_puzzle_schemes
"""
import colorsys
import logging
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import (_gen_puzzle_classic, _gen_puzzle_hex,
                              _gen_puzzle_ribbon)

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("puzzle_classic", _gen_puzzle_classic, 96, (0.03, 0.10)),  # terracotta
    ("puzzle_ribbon", _gen_puzzle_ribbon, 96, (0.55, 0.62)),    # blue
    ("puzzle_hex", _gen_puzzle_hex, 88, (0.30, 0.38)),          # green
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
