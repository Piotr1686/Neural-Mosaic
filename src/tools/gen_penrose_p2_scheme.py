"""Regenerate the GUI scheme preview for penrose_p2.

The original PNG (from `gen_extra_shape_schemes`) drew a FIXED unit square: sun
radius 2.2, depth 6, window R=1.0. The engine does not do that. `_gen_penrose_p2`
derives depth from base_s (the sun must cover the frame, ceil keeps the leg
exact) and prunes triangles against the frame as it deflates, so its patch is a
different scale and a different crop. Keeping the old PNG would advertise a
patch the mosaic never produces -- the trap that already caught girih, poincare
and truchet (proposal tool != engine). So this is rebuilt straight from the
engine's own `_gen_penrose_p2`, the single source of truth.

Colouring separates the two prototiles, since that split is exactly what makes
P2 distinct from the P3 rhombs of `penrose`:
  * KITES warm, hue stepped by axis orientation mod 5 -> suns and decagonal
    rosettes read as 5-tone pinwheels;
  * DARTS dark blue -> the five dart tips meeting at a star vertex read as the
    classic dark 5-point star.
Kite vs dart is decided geometrically (a dart is the non-convex one), not from
generator bookkeeping, so the picture cannot drift from the rendered geometry.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_penrose_p2_scheme
"""
import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw

from src.engine_smart import _gen_penrose_p2

log = logging.getLogger(__name__)

SIZE = 720
BASE_S = 46
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)
PAL_KITE = [(214, 158, 62), (198, 122, 64), (222, 180, 96),
            (182, 96, 70), (206, 142, 84)]
PAL_DART = (58, 76, 108)


def _is_convex(poly):
    """A P2 dart is the non-convex quad; the kite is convex."""
    n = len(poly)
    sign = None
    for i in range(n):
        a, b, c = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) < 1e-9:
            continue
        if sign is None:
            sign = cross > 0
        elif (cross > 0) != sign:
            return False
    return True


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    kites = darts = 0
    for poly in _gen_penrose_p2(None, SIZE, SIZE, BASE_S):
        if _is_convex(poly):
            # poly is (apex, t1, axis-end, t2): the axis runs apex -> poly[2]
            ang = math.atan2(poly[2][1] - poly[0][1], poly[2][0] - poly[0][0])
            bucket = int((ang % (2 * math.pi)) / (2 * math.pi) * 10 + 0.5) % 5
            col = PAL_KITE[bucket]
            kites += 1
        else:
            col = PAL_DART
            darts += 1
        draw.polygon(poly, fill=col, outline=OUTLINE)

    out = Path(__file__).resolve().parents[2] / "assets" / "shape_schemes" / "penrose_p2.png"
    img.save(out)
    ratio = kites / darts if darts else 0.0
    log.info("Saved: %s", out)
    log.info("  cells=%d  kites=%d  darts=%d  ratio=%.3f (phi=%.3f)",
             kites + darts, kites, darts, ratio, (1 + math.sqrt(5)) / 2)


if __name__ == "__main__":
    main()
