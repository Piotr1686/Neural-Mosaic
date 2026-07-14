"""
src/tools/girih_audit.py
------------------------
Offline audit for the girih shape (`engine_smart._girih_patch`).

The plan for girih budgeted a frozen random seed plus an offline seed sweep,
because the scheme's greedy was seed-sensitive (coverage swung between 94% and
99%) and a per-frame seed could have given a clean 2K preview and a holey 16K
render. That whole problem was designed away: the decagon rosettes are seeded on
a quasi-lattice and the fill order is fixed, so girih now has NO randomness at
all. What is left to audit is whether the tiling is a partition, and whether it
still looks like girih rather than like a field of hexagons.

Reported:
  girih tiles  -- share of the picture made of real girih tiles; the rest is
                  traced leftovers (irregular blobs, so lower is prettier)
  rosettes     -- decagons; girih without khatam rosettes is not girih
  holes        -- background a render would actually leave, measured at
                  render_padding (1.02). Gate: no hole above ~0.05 unit^2
  overlap      -- cells painted twice, measured with cells pulled apart to 0.90
                  so PIL's shared boundary pixels do not fake it. Gate: ~0

Usage:
    python -m src.tools.girih_audit              # audit the shipped settings
    python -m src.tools.girih_audit --orders     # why bowtie-first (the table)
    python -m src.tools.girih_audit --time-16k   # cost at a 16K frame
"""
import argparse
import math
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label as nd_label

import src.engine_smart as E
from src.engine_smart import _girih_patch, _GIRIH_CELL_AREA, _GIRIH_MARGIN

CHECK_RAD = 30.0
CHECK_RES = 24.0        # verification raster: finer than the greedy's own
RENDER_PADDING = 1.02   # engine_smart._do_render, border_mode off
OVERLAP_SCALE = 0.90    # see coverage()


def poly_area(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        s += ax * by - bx * ay
    return abs(s) / 2.0


def _rasterise(cells, rad, res, scale):
    """Coverage-count raster of the cells, each scaled about its own centroid
    the way _polygon_sector scales them at paste time."""
    W = int(2.0 * rad * res) + 2
    acc = np.zeros((W, W), dtype=np.uint8)
    for poly in cells:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        pts = [((cx + (x - cx) * scale + rad) * res,
                (cy + (y - cy) * scale + rad) * res) for x, y in poly]
        x0 = max(0, int(min(p[0] for p in pts)) - 1)
        y0 = max(0, int(min(p[1] for p in pts)) - 1)
        x1 = min(W, int(max(p[0] for p in pts)) + 2)
        y1 = min(W, int(max(p[1] for p in pts)) + 2)
        if x1 <= x0 or y1 <= y0:
            continue
        buf = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(buf).polygon([(px - x0, py - y0) for px, py in pts], fill=1)
        acc[y0:y1, x0:x1] += np.asarray(buf, dtype=np.uint8)
    return acc


def _window(acc, rad, res, margin, aspect=(16, 9)):
    """The 16:9 RECTANGLE inscribed in the disc of radius rad-margin -- exactly
    how the engine inscribes the frame in the grown patch. (A SQUARE of
    half-width rad-margin reaches 1.41x that at its corners, far outside the
    patch, and counts the empty corners as holes: that mistake once reported
    17% holes on a patch that was fine.)"""
    W = acc.shape[0]
    r_use = (rad - margin) * res
    diag = math.hypot(*aspect)
    hw = int(r_use * aspect[0] / diag)
    hh = int(r_use * aspect[1] / diag)
    cc = W // 2
    return acc[cc - hh:cc + hh, cc - hw:cc + hw]


def coverage(cells, rad, res=CHECK_RES, margin=_GIRIH_MARGIN):
    """(hole_fraction, overlap_fraction), measured the way a RENDER sees them.

    holes   -- rasterised at render_padding, the size the engine actually paints
               a cell at, so a hole here is background the viewer would see.
    overlap -- rasterised at 0.90, i.e. cells pulled off each other. At scale
               1.0 PIL fills the boundary pixels of BOTH abutting cells, so even
               an exact partition reports ~perimeter/area (12-15%) of fake
               overlap. Pull them apart and what remains is a GENUINE overlap:
               two photographs fighting for the same pixels.
    """
    holes = _window(_rasterise(cells, rad, res, RENDER_PADDING), rad, res, margin)
    over = _window(_rasterise(cells, rad, res, OVERLAP_SCALE), rad, res, margin)
    return float((holes == 0).mean()), float((over > 1).mean())


def hole_sizes(cells, rad, res=CHECK_RES, margin=_GIRIH_MARGIN):
    """Areas (unit^2) of the background holes a render would leave, biggest
    first. A girih hexagon is 2.13 unit^2, so anything above ~0.05 reads as a
    visible patch of background; sub-0.01 dust is sealed by the padding."""
    win = _window(_rasterise(cells, rad, res, RENDER_PADDING), rad, res, margin)
    lab, n = nd_label(win == 0)
    if not n:
        return []
    return sorted((np.bincount(lab.ravel())[1:] / (res * res)).tolist(),
                  reverse=True)


def audit(rad=CHECK_RAD, label="", verbose=True):
    stats = {}
    t0 = time.perf_counter()
    cells = _girih_patch(rad, stats=stats)
    dt = time.perf_counter() - t0
    n_left = stats["leftover_cells"]
    tiles, leftover = cells[:len(cells) - n_left], cells[len(cells) - n_left:]
    a_tiles = sum(poly_area(p) for p in tiles)
    a_left = sum(poly_area(p) for p in leftover)
    tile_share = a_tiles / (a_tiles + a_left)
    holes, overlap = coverage(cells, rad)
    sizes = hole_sizes(cells, rad)
    worst = sizes[0] if sizes else 0.0
    if verbose:
        print(f"  {label or f'rad {rad:.0f}':<16} girih tiles {tile_share * 100:5.1f}% "
              f"of area   rosettes {stats['counts'].get('decagon', 0):4d}   "
              f"holes {holes * 100:6.4f}% (worst {worst:.3f} u2)   "
              f"overlap {overlap * 100:5.2f}%   cells {len(cells):6d}   {dt:5.2f}s")
    return {"tile_share": tile_share, "worst_hole": worst, "overlap": overlap,
            "stats": stats, "cells": len(cells), "time": dt}


def orders_table():
    """Why _GIRIH_ORDER is bowtie-first: the gaps a rosette lattice opens are
    mostly bowtie-shaped, and hexagons grabbing them first strands the rest."""
    trials = {
        "bowtie, hex, pent, rhomb (shipped)": ("bowtie", "hexagon", "pentagon", "rhomb"),
        "hexagon, bowtie, pent, rhomb": ("hexagon", "bowtie", "pentagon", "rhomb"),
        "pentagon, bowtie, hex, rhomb": ("pentagon", "bowtie", "hexagon", "rhomb"),
        "rhomb, bowtie, hex, pent": ("rhomb", "bowtie", "hexagon", "pentagon"),
    }
    keep = E._GIRIH_ORDER
    print("Fill order vs how much of the picture stays real girih "
          f"(radius {CHECK_RAD:.0f}):")
    try:
        for name, order in trials.items():
            E._GIRIH_ORDER = order
            stats = {}
            cells = _girih_patch(CHECK_RAD, stats=stats)
            n_left = stats["leftover_cells"]
            a_t = sum(poly_area(p) for p in cells[:len(cells) - n_left])
            a_l = sum(poly_area(p) for p in cells[len(cells) - n_left:])
            counts = {k: v for k, v in stats["counts"].items() if k != "decagon"}
            print(f"  {name:<36} girih tiles {a_t / (a_t + a_l) * 100:5.1f}%   "
                  f"leftovers {a_l / (a_t + a_l) * 100:5.2f}%   {counts}")
    finally:
        E._GIRIH_ORDER = keep


def main():
    ap = argparse.ArgumentParser(description="Girih audit")
    ap.add_argument("--orders", action="store_true",
                    help="compare fill orders (justifies _GIRIH_ORDER)")
    ap.add_argument("--time-16k", action="store_true",
                    help="cost and quality at a 16K frame")
    args = ap.parse_args()

    if args.orders:
        orders_table()
        return

    if args.time_16k:
        # 16K smart render = 15360x8640 at base_s = 100 (tile_scale 1.0)
        u = 100.0 / math.sqrt(_GIRIH_CELL_AREA)
        rad = math.hypot(15360, 8640) / (2.0 * u) + _GIRIH_MARGIN
        print(f"16K frame -> patch radius {rad:.1f} units")
        audit(rad, label="16K")
        return

    print("Girih audit (deterministic: no seed, no RNG)")
    for rad in (20.0, 30.0, 60.0):
        audit(rad)


if __name__ == "__main__":
    main()
