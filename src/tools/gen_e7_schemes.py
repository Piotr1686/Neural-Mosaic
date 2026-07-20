"""Regenerate the GUI scheme previews for sprint E7 (Sierpinski family).

Drawn FROM THE ENGINE generators (the girih/poincare/truchet lesson). The
colouring encodes the shape's whole idea: a cell's tone comes from its AREA,
because in a render the holes become progressively larger single photos while
the leaves stay the dense fine texture. Flat colour per level would hide that.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_e7_schemes
"""
import colorsys
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import (_gen_sierpinski, _gen_sierpinski_carpet,
                              _gen_sierpinski_d)

log = logging.getLogger(__name__)

SIZE = 720
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)

SHAPES = [
    ("sierpinski", _gen_sierpinski, 26),
    ("sierpinski_d", _gen_sierpinski_d, 26),
    ("sierpinski_carpet", _gen_sierpinski_carpet, 9),
]


def _area(poly):
    s = 0.0
    for k in range(len(poly)):
        x0, y0 = poly[k]
        x1, y1 = poly[(k + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_dir = Path(__file__).resolve().parents[2] / "assets" / "shape_schemes"

    for name, gen, base_s in SHAPES:
        img = Image.new("RGB", (SIZE, SIZE), BG)
        draw = ImageDraw.Draw(img)
        polys = [[tuple(p) for p in poly] for poly in gen(None, SIZE, SIZE, base_s)]
        areas = [_area(p) for p in polys]
        a_min = min(areas)
        for poly, a in zip(polys, areas):
            # level = how many times bigger than the smallest leaf (log4 for
            # triangles, log9 for the carpet — both halve/third per level)
            lvl = math.log(max(a / a_min, 1.0)) / math.log(3.0)
            t = min(lvl / 3.5, 1.0)
            if t < 0.12:                      # leaves: warm amber texture
                r, g, b = colorsys.hsv_to_rgb(0.09, 0.60, 0.86)
            else:                             # holes: cooler and darker
                r, g, b = colorsys.hsv_to_rgb(0.09 + 0.52 * t,
                                              0.42 + 0.20 * t,
                                              0.72 - 0.36 * t)
            draw.polygon(poly, fill=(int(r * 255), int(g * 255), int(b * 255)),
                         outline=OUTLINE)
        path = out_dir / f"{name}.png"
        img.save(path)
        log.info("Saved: %s  (%d cells)", path, len(polys))


if __name__ == "__main__":
    main()
