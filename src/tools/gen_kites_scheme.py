"""Regenerate assets/shape_schemes/kites.png faithful to the engine geometry.

The original 9 core-shape scheme generators lived in a lost scratchpad (lesson
learned 2026-07-02: commit generators). This tool re-creates ONLY the kites
scheme, mirroring the deltoidal-trihexagonal grid of `engine_smart` INCLUDING
the 2026-07-04 fix (r-window centred on -q/2) that removes the black wedge in
the bottom-right corner.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_kites_scheme
"""
import math

import numpy as np

from src.tools.gen_fable_shape_schemes import ASSETS_DIR, render, vary

SIZE_W = 720

# bright pastel per kite index k (matches the original scheme's look)
KITE_PAL = [(150, 136, 238), (240, 126, 126), (126, 224, 136),
            (134, 232, 232), (238, 228, 126), (232, 136, 232)]


def _kite_poly(cx, cy, s, k):
    """Same construction as SmartEngine._get_kite_poly (no engine import: the
    engine needs a pickled index to instantiate)."""
    r3 = math.sqrt(3)

    def P(idx):
        a = math.radians(idx * 60)
        return (cx + s * math.cos(a), cy + s * math.sin(a))

    def M(idx):
        a = math.radians(idx * 60 + 30)
        return (cx + s * r3 / 2 * math.cos(a), cy + s * r3 / 2 * math.sin(a))

    return [(cx, cy), M((k - 1) % 6), P(k), M(k)]


def gen_kites(target_w=SIZE_W, target_h=SIZE_W, s=44):
    rng = np.random.default_rng(9)
    r3 = math.sqrt(3)
    range_q = int(target_w / (1.5 * s)) + 3
    range_r = int(target_h / (r3 * s)) + 3
    polys = []
    for q in range(-range_q, range_q):
        r_mid = -(q // 2)          # the 2026-07-04 fix: recentre the cy band
        for r in range(r_mid - range_r, r_mid + range_r):
            cx = 1.5 * s * q
            cy = r3 * s * (r + q / 2.0)
            if -2 * s < cx < target_w + 2 * s and -2 * s < cy < target_h + 2 * s:
                for k in range(6):
                    poly = _kite_poly(cx, cy, s, k)
                    cent_x = sum(p[0] for p in poly) / 4
                    cent_y = sum(p[1] for p in poly) / 4
                    # scheme swatch: keep every kite that touches the canvas so
                    # the picture has no boundary bite (the engine's stricter
                    # centroid test only trims sub-pixel edge slivers)
                    if -s <= cent_x < target_w + s and -s <= cent_y < target_h + s:
                        polys.append((poly, vary(rng, KITE_PAL[k], 12)))
    return polys, (0, 0, target_w, target_h)


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    polys, world = gen_kites()
    img = render(polys, world)
    out = ASSETS_DIR / "kites.png"
    img.save(out)
    print(f"[gen] {len(polys)} kites -> {out}")


if __name__ == "__main__":
    main()
