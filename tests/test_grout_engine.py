"""Tests for the SmartEngine hierarchical grout pass (border overlay).

Two concerns:
  * cell generation (``_grout_cells_*``) reproduces the reviewed grouping and,
    for hexagons, that the derived offset->axial conversion yields spatially
    contiguous sub7 flowers (a wrong linear map still groups into 7s, so this
    is verified geometrically, not just by count);
  * the pass is a pure overlay — ``grout_preset=None`` is byte-identical to the
    baseline render, a preset adds black grout, and an unsupported shape is a
    silent no-op.
"""
import math
import threading
from collections import Counter

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.engine_smart import (SHAPE_MODES, SmartEngine, _poincare_cells,
                              _gen_penrose_p2, _gen_pebbles, _gen_bloom,
                              _gen_phyllotaxis, _gen_stagger_tri, _gen_braid,
                              _gen_moire, _gen_puzzle_classic,
                              _gen_puzzle_ribbon, _gen_puzzle_hex,
                              _gen_dragon, _gen_koch_island,
                              _gen_koch_snowflake, _twindragon_boundary,
                              _gen_gereh, _gen_rosette, _gen_scales,
                              _gen_nautilus, _gen_sunburst,
                              _gen_rosette_fractal, _gen_sierpinski,
                              _gen_sierpinski_d, _gen_sierpinski_carpet,
                              _sierpinski_cells, _tri_outside,
                              _GOLDEN_ANGLE, _LUCAS_ANGLE)
from src.grout import classify_edges
from tests.test_golden_shapes import _build_library, _make_target


def _engine():
    return SmartEngine(index_path="__none__.pkl")


def _centroid(poly):
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def _poly_area(poly):
    n = len(poly)
    s = 0.0
    for k in range(n):
        x0, y0 = poly[k]
        x1, y1 = poly[(k + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


# ---------------------------------------------------------------------------
# cell generation / grouping
# ---------------------------------------------------------------------------
def test_square_blocks_partition_3x3_and_9x9():
    cells = _engine()._grout_cells_square(600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    # every level-2 block collects at most 3x3 = 9 tiles; interior blocks full
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 9
    l3 = Counter(g3 for _, _, g3 in cells)
    assert max(l3.values()) == 81           # 9x9 block


def test_hexagon_sub7_flowers_are_spatially_contiguous():
    # THE conversion check: offset->axial q = c - (r-(r&1))//2 must make every
    # sub7 flower a compact 7-hex cluster. A wrong map still yields groups of 7
    # but geometrically scattered, so we assert on inter-member distance.
    base_s = 60
    cells = _engine()._grout_cells_hexagon(600, 600, base_s)
    groups = {}
    for poly, g2, _ in cells:
        groups.setdefault(g2, []).append(_centroid(poly))

    full = [pts for pts in groups.values() if len(pts) == 7]
    assert full, "expected at least one complete 7-flower"
    # a correct flower spans two hex steps (opposite neighbours ~2*base_s apart)
    for pts in full:
        dmax = max(math.hypot(a[0] - b[0], a[1] - b[1])
                   for a in pts for b in pts)
        assert dmax < 2.5 * base_s, f"flower not contiguous: span {dmax:.1f}"


def test_hexagon_level3_is_sub7_of_level2():
    cells = _engine()._grout_cells_hexagon(600, 600, 60)
    # each level-3 group gathers up to 7 level-2 flowers -> up to 49 hexes
    l3 = Counter(g3 for _, _, g3 in cells)
    assert max(l3.values()) <= 49


def test_triangle_owner_groups_are_hexagons_of_six():
    cells = _engine()._grout_cells_triangle(600, 600, 80)
    assert cells and all(len(poly) == 3 for poly, _, _ in cells)
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 6            # 6 triangles meet at a class-0 corner


def test_kites_level2_is_parent_hexagon_of_six():
    cells = _engine()._grout_cells_kites(600, 600, 80)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 6            # 6 kites per hexagon


def test_poincare_hierarchy_g2_is_kite_g3_is_heptagon():
    # Poincare grout re-yields the step-2 hyperbolic quad mesh: L1 = quad
    # sub-cell, L2 = khatam kite (g2 = (hi, k)), L3 = 7-kite heptagon (g3 = hi).
    # KEY distinction vs kites: g2 groups the nd^2 SUB-cells of a kite (not the
    # kite itself), and the 7 kites of a heptagon share one g3. Assert on the
    # central heptagon (hi == 0), which is always fully on-frame.
    base_s = 60
    cells = _engine()._grout_cells_poincare(600, 450, base_s)
    assert cells and all(len(poly) >= 3 for poly, _, _ in cells)

    central = [(g2, g3) for _, g2, g3 in cells if g3 == 0]
    assert central, "central heptagon (hi=0) missing"
    # one g3, seven kites
    assert {g3 for _, g3 in central} == {0}
    kite_counts = Counter(g2 for g2, _ in central)
    assert len(kite_counts) == 7, f"expected 7 kites, got {len(kite_counts)}"
    # g2 must be the (hi, k) pair, k in 0..6
    assert {g2 for g2, _ in central} == {(0, k) for k in range(7)}
    # every kite carries the same nd^2 sub-cells, and nd^2 > 1 proves g2 groups
    # sub-cells rather than tagging a single kite polygon
    counts = set(kite_counts.values())
    assert len(counts) == 1, f"kites have unequal sub-cell counts: {kite_counts}"
    nsq = counts.pop()
    assert nsq > 1 and int(nsq ** 0.5) ** 2 == nsq, f"nd^2 not a square >1: {nsq}"


def test_poincare_grout_all_three_levels_populated():
    # On real poincare geometry classify_edges must return non-empty L1, L2 AND
    # L3. This is the anti-collapse check: if the constructive snapping failed to
    # make adjacent cells emit identical seam segments, shared interior seams
    # would fragment into frame boundaries (L3) and L1/L2 would be near-empty.
    # (The formal zero-unpaired-interior-segment partition proof is step 4.)
    cells = _engine()._grout_cells_poincare(600, 450, 60)
    by_level = classify_edges(cells)
    assert by_level[1], "no L1 sub-cell seams — snapping likely broken"
    assert by_level[2], "no L2 kite seams — kites not sharing edges"
    assert by_level[3], "no L3 heptagon/frame boundaries"


@pytest.mark.parametrize("w,h,base_s", [
    (600, 450, 60),      # 4:3
    (900, 400, 60),      # wide band
    (400, 700, 60),      # tall
    (384, 288, 100),     # the golden frame
    (1920, 480, 75),     # 4:1 panorama slice
])
def test_poincare_is_an_exact_partition(w, h, base_s):
    # THE anti-T-junction proof (step 2's constructive snapping, now locked in
    # CI). Collapse all cells to one group so classify_edges routes EVERY
    # unpaired seam to level 3 (an edge with a single owner). A T-junction or a
    # float mismatch between two heptagons of different nd would leave an
    # interior seam unpaired — a level-3 segment with BOTH endpoints well inside
    # the frame. Unpaired seams that touch the frame edge are legitimate (the
    # band tiling is clipped there, cells extend past the border), so only
    # strictly-interior unpaired segments count as failures. Must be zero.
    PAD = 2.0
    cells = [(list(poly), 0, 0)
             for poly, _, _ in _poincare_cells(w, h, base_s)]
    by_level = classify_edges(cells)
    interior_unpaired = [
        (a, b) for a, b in by_level[3]
        if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD for p in (a, b))
    ]
    assert not interior_unpaired, (
        f"{len(interior_unpaired)} interior T-junction(s) at {w}x{h} "
        f"base_s={base_s}: {interior_unpaired[:3]}")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square — the case that exposed the unmatched-rim holes
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_penrose_p2_covers_the_frame(w, h, base_s):
    # Halves with no mirror twin are dropped, and EVERY boundary makes them —
    # the sun's own rim and the prune box alike. Sizing the sun to just cover
    # the frame (3 px of margin) put that rim inside it: a 42 px band of holes
    # along one edge that the tile counts and areas looked perfectly fine
    # through. Only rasterised coverage catches it, so it is locked here.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in _gen_penrose_p2(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon(poly, fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (640, 640, 80),
])
def test_penrose_p2_is_an_exact_partition(w, h, base_s):
    # P2 is edge-to-edge, so no interior seam may be unpaired. Same collapse
    # trick as the poincare proof: one group => classify_edges routes every
    # unpaired seam to level 3. Seams near the frame edge are legitimate (the
    # cull keeps tiles overlapping the border), so only strictly-interior ones
    # count. Guards the Robinson cut direction: the mirror cut |CU| would leave
    # hundreds of unmatched halves instead of zero.
    PAD = 2.0
    cells = [(list(poly), 0, 0) for poly in _gen_penrose_p2(None, w, h, base_s)]
    by_level = classify_edges(cells)
    interior_unpaired = [
        (a, b) for a, b in by_level[3]
        if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD for p in (a, b))
    ]
    assert not interior_unpaired, (
        f"{len(interior_unpaired)} interior T-junction(s) at {w}x{h} "
        f"base_s={base_s}: {interior_unpaired[:3]}")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (640, 640, 80),      # the case that exposed the empty-margin holes (5.3%)
    (500, 500, 40),
])
def test_pebbles_covers_the_frame(w, h, base_s):
    # The blobs live inside the frame, so the density leaves the margin nearly
    # empty; without the uniform scaffold ring the border cells come out
    # unbounded, get dropped, and open holes. Trimming the batch to the n-th
    # in-frame seed (needed for cell size) is what starves the margin, so the
    # ring and the trim must be tested together — this is that test.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in _gen_pebbles(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes <= 64, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


_VORONOI_FAMILY = ["voronoi", "pebbles", "phyllotaxis", "bloom",
                   "sunflower_grande", "sunflower_grande_xl",
                   "sunflower_grande_soft", "sunflower_grande_inverse",
                   "sunflower_soft", "sunflower_rings", "sunflower_disc"]


@pytest.mark.parametrize("name", _VORONOI_FAMILY)
@pytest.mark.parametrize("w,h,base_s", [
    (384, 288, 100),     # the golden frame at a coarse tile
    (300, 300, 120),     # the sunflower_disc worst case (was 41.6% holes)
    (500, 375, 100),     # the voronoi worst case (was 16.0% holes)
])
def test_voronoi_family_covers_coarse_frames(name, w, h, base_s):
    # The coarse regime is the seed floor (max(16, ...)) binding: few seeds
    # mean the unbounded hull cells reach INTO the frame, and dropping them
    # (pre-fix _voronoi_cells) left 5-41.6% holes across the family. Small
    # frame + large base_s is exactly the PREVIEW profile, so a shape that
    # holes here loses the final selection to a bug, not to aesthetics. The
    # mirrored second pass must keep every frame fully covered — for every
    # member, since they all share _emit_cells.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in SHAPE_MODES[name].generator(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px for {name} at {w}x{h} base_s={base_s}"


def test_pebbles_cell_sizes_vary_more_than_uniform_voronoi():
    # The whole point of pebbles: density varies, so cell SIZE varies — that is
    # what survives photo substitution. If a refactor ever flattened the blobs,
    # pebbles would silently become `voronoi` (the kepler_ty/bloom failure).
    from src.engine_smart import _gen_voronoi

    def _spread(gen):
        areas = []
        for poly in gen(None, 800, 600, 60):
            a = 0.0
            for i in range(len(poly)):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % len(poly)]
                a += x1 * y2 - x2 * y1
            areas.append(abs(a) / 2)
        mean = sum(areas) / len(areas)
        var = sum((a - mean) ** 2 for a in areas) / len(areas)
        return math.sqrt(var) / mean

    assert _spread(_gen_pebbles) > _spread(_gen_voronoi) * 1.3


def test_bloom_geometry_differs_from_phyllotaxis():
    # bloom exists only because its divergence angle differs: the scheme drew
    # the same lattice as phyllotaxis and carried the motif in COLOUR, which is
    # nothing once photos replace it (the kepler_ty failure). Radii are shared
    # (r = c*sqrt(n)), so cell-area stats CANNOT tell them apart — the seed
    # angles must be compared instead.
    assert _LUCAS_ANGLE != _GOLDEN_ANGLE
    a = [tuple(round(v, 6) for v in p)
         for poly in _gen_bloom(None, 400, 400, 40) for p in poly]
    b = [tuple(round(v, 6) for v in p)
         for poly in _gen_phyllotaxis(None, 400, 400, 40) for p in poly]
    assert a != b, "bloom reproduced phyllotaxis — the Lucas angle is not applied"


# --- stagger_tri vs the triangle lattice ------------------------------------
# stagger_tri is the triangle cell stacked at a CONSTANT row phase. The only
# thing separating it from the `triangle` grid mode is that phase, so the gate
# has to be translation-invariant: shifting the phase by s/2 instead rebuilds
# `triangle` exactly but displaced by s/2, and a raw coordinate diff (the
# bloom/phyllotaxis pattern above) would call that "different" — every single
# coordinate does differ. Hence _max_overlap over candidate translations.

def _tri_strips(target_w, target_h, s, phase):
    """Triangle rows of side `s`; `phase(r)` is row r's x-offset."""
    h = s * math.sqrt(3) / 2.0
    for r in range(-2, int(target_h / h) + 3):
        y0 = r * h
        y1 = y0 + h
        off = phase(r)
        for c in range(-2, int(target_w / s) + 3):
            x = c * s + off
            yield [(x, y0), (x + s, y0), (x + s / 2, y1)]
            yield [(x + s, y0), (x + s / 2, y1), (x + 3 * s / 2, y1)]


def _canon(poly, dx=0.0, dy=0.0):
    return tuple(sorted((round(x + dx, 3), round(y + dy, 3)) for x, y in poly))


def _max_overlap(a_cells, b_cells, window):
    """Largest fraction of `a_cells` inside `window` reproduced by `b_cells`
    under ANY translation.

    Exhaustive without scanning a grid of offsets: a translation that matches
    the two tilings must carry one fixed cell of A onto some cell of B, so the
    candidate offsets are exactly the centroid differences from that anchor.
    B is generated past the window on every side, so a shifted B still covers
    it and the count is free of border bias.
    """
    x0, y0, x1, y1 = window
    a_win = [p for p in a_cells if x0 <= _centroid(p)[0] <= x1
             and y0 <= _centroid(p)[1] <= y1]
    assert len(a_win) >= 40, "window too small to be evidence"
    anchor = _centroid(a_win[0])
    best = 0.0
    for b in b_cells:
        cb = _centroid(b)
        dx, dy = cb[0] - anchor[0], cb[1] - anchor[1]
        shifted = {_canon(p, dx, dy) for p in b_cells}
        hit = sum(1 for p in a_win if _canon(p) in shifted)
        best = max(best, hit / len(a_win))
    return best


def test_triangle_grid_shifts_phase_half_a_base_every_row():
    # Anchors the claim below in the engine rather than in the test's own
    # re-derivation: `triangle` looks phase-constant (offset_odd_row_x stays 0)
    # and carries the shift in its (c+r)%2 flip rule instead. On the (a*w/2,
    # b*h) vertex lattice that shows up as the parity of `a` alternating line
    # to line — i.e. the regular vertex-to-vertex lattice, no T-junctions.
    w, h = 60.0, float(int(60 * 0.866))
    cells = _engine()._grout_cells_triangle(600, 600, 60)
    lines = {}
    for poly, _own, _sub in cells:
        for (x, y) in poly:
            lines.setdefault(round(y / h), set()).add(round(x / (w / 2)) % 2)
    interior = sorted(k for k in lines if 1 <= k <= 8)
    parities = [lines[k] for k in interior]
    assert all(len(p) == 1 for p in parities), (
        "a triangle row line carries both vertex parities — the grid would have "
        "T-junctions and would not be the regular lattice")
    assert all(parities[i] != parities[i + 1] for i in range(len(parities) - 1)), (
        "vertex parity does not alternate — triangle is not phase-shifting rows")


def test_stagger_tri_rows_slip_and_are_not_triangle_under_any_translation():
    # The gate the pool turns on. `stagger_tri` holds the phase constant, so
    # every row line is a slip line carrying BOTH parities (T-junctions) and no
    # translation can turn it into the regular lattice.
    base_s = 60
    s = 2.0 * base_s / (3.0 ** 0.25)
    h = s * math.sqrt(3) / 2.0
    stagger = [list(p) for p in _gen_stagger_tri(None, 900, 900, base_s)]

    lines = {}
    for poly in stagger:
        for (x, y) in poly:
            lines.setdefault(round(y / h), set()).add(round(x / (s / 2)) % 2)
    assert all(len(lines[k]) == 2 for k in range(1, 8)), (
        "a stagger_tri row line carries a single vertex parity — the rows "
        "interlock, so this is the regular lattice, not a slip")

    regular = list(_tri_strips(900, 900, s, lambda r: (s / 2) * (r % 2)))
    window = (1.5 * s, 1.5 * h, 7 * s, 9 * h)
    assert _max_overlap(stagger, regular, window) < 0.99, (
        "stagger_tri reproduced the triangle lattice")


def test_translation_gate_catches_the_half_base_phase_duplicate():
    # Teeth for the gate above, and the trap it exists for: shifting alternate
    # rows by s/2 — the obvious "make it staggered" fix — IS the triangle
    # lattice displaced by s/2. Every coordinate differs, so a raw diff passes
    # it; the translation-invariant gate must still score a full match.
    base_s = 60
    s = 2.0 * base_s / (3.0 ** 0.25)
    h = s * math.sqrt(3) / 2.0
    half = list(_tri_strips(900, 900, s, lambda r: (s / 2) * ((r + 1) % 2)))
    regular = list(_tri_strips(900, 900, s, lambda r: (s / 2) * (r % 2)))
    window = (1.5 * s, 1.5 * h, 7 * s, 9 * h)

    raw_a = sorted(_canon(p) for p in half)
    raw_b = sorted(_canon(p) for p in regular)
    assert raw_a != raw_b, "the two phasings should differ coordinate-wise"
    assert _max_overlap(half, regular, window) == 1.0, (
        "the gate failed to see through a pure translation — it would have "
        "green-lit a duplicate of triangle")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_stagger_tri_covers_the_frame(w, h, base_s):
    # Coverage is what makes the constant phase safe to ship: each row
    # partitions its own slab, so slipping the rows sideways cannot open a gap
    # no matter the phase. The wedge rows/cols start at -1 for the left/top
    # edge (the down cell of c=-1 is what fills x in [0, s/2]).
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in _gen_stagger_tri(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


def test_stagger_tri_mean_cell_area_is_base_s_squared():
    # Pool convention (cairo/spectre): the scale is picked so a cell averages
    # base_s^2. The `triangle` grid mode instead reads base_s as the side
    # (area 0.433*base_s^2), so porting the scheme's `s = base_s` verbatim
    # would have shipped cells less than half the pool's size.
    base_s = 60
    areas = []
    for poly in _gen_stagger_tri(None, 900, 900, base_s):
        (x1, y1), (x2, y2), (x3, y3) = poly
        areas.append(abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.01)


# --- braid vs a single-orientation running bond -----------------------------
# braid is basketweave: 2x1 bricks in alternating horizontal/vertical pairs on
# a 2x2 checkerboard. The open risk (the stagger_tri class) is that it only
# *looks* new next to `brick_wall` — both are rectangles, so the difference
# lives in the LAYOUT, not the cell, and a raw coordinate diff is not evidence.
# The reference is therefore a running bond built from braid's OWN 2u x u brick
# (same cell, single orientation): if braid were just a restagger of one
# orientation the translation-invariant gate would match it. It cannot, because
# half of braid's bricks stand vertical and no translation turns a horizontal
# brick into a vertical one. Comparing against brick_wall at its pool scale
# would be trivially distinct (different cell size) and would not test the
# layout — the same-cell bond is what isolates it.

def _running_bond(target_w, target_h, u):
    """All-horizontal 2u x u bricks, rows offset half a brick (running bond)."""
    for j in range(-2, int(target_h / u) + 3):
        y = j * u
        off = u if j % 2 else 0.0            # half-brick (= u) row shift
        for i in range(-2, int(target_w / (2 * u)) + 3):
            x = i * 2 * u + off
            yield [(x, y), (x + 2 * u, y), (x + 2 * u, y + u), (x, y + u)]


def _braid_parity_flipped(target_w, target_h, base_s):
    """braid with the H/V choice inverted (I+J odd -> horizontal). The obvious
    "restagger", which is in fact braid translated by one block."""
    u = base_s / math.sqrt(2.0)
    ni = int(target_w / (2.0 * u)) + 2
    nj = int(target_h / (2.0 * u)) + 2
    for I in range(-1, ni):
        for J in range(-1, nj):
            x, y = 2 * I * u, 2 * J * u
            if (I + J) % 2 == 1:                      # flipped: horizontal pair
                yield [(x, y), (x + 2 * u, y),
                       (x + 2 * u, y + u), (x, y + u)]
                yield [(x, y + u), (x + 2 * u, y + u),
                       (x + 2 * u, y + 2 * u), (x, y + 2 * u)]
            else:                                     # flipped: vertical pair
                yield [(x, y), (x + u, y),
                       (x + u, y + 2 * u), (x, y + 2 * u)]
                yield [(x + u, y), (x + 2 * u, y),
                       (x + 2 * u, y + 2 * u), (x + u, y + 2 * u)]


def test_braid_is_not_a_running_bond_under_any_translation():
    # The gate the pool turns on for braid. A horizontal-only running bond can
    # match at most braid's horizontal bricks (half the cells); its vertical
    # bricks are an orientation the bond has not got, so no translation lifts
    # the overlap near 1.
    base_s = 60
    u = base_s / math.sqrt(2.0)
    braid = [list(p) for p in _gen_braid(None, 900, 900, base_s)]
    bond = list(_running_bond(900, 900, u))
    window = (2 * u, 2 * u, 16 * u, 16 * u)
    assert _max_overlap(braid, bond, window) < 0.99, (
        "braid collapsed onto a single-orientation running bond — its vertical "
        "bricks are not a real distinction from brick_wall")


def test_braid_parity_flip_is_a_pure_translation_duplicate():
    # Teeth for the gate, and the trap it exists for: swapping which blocks run
    # horizontal is the obvious "restagger", but it is braid shifted by one
    # block — every coordinate differs while the tiling is identical. A raw diff
    # calls it new; the translation-invariant gate must score a full match.
    base_s = 60
    u = base_s / math.sqrt(2.0)
    braid = [list(p) for p in _gen_braid(None, 900, 900, base_s)]
    flipped = [list(p) for p in _braid_parity_flipped(900, 900, base_s)]
    window = (2 * u, 2 * u, 16 * u, 16 * u)

    raw_a = sorted(_canon(p) for p in braid)
    raw_b = sorted(_canon(p) for p in flipped)
    assert raw_a != raw_b, "the two parities should differ coordinate-wise"
    assert _max_overlap(braid, flipped, window) == 1.0, (
        "the gate failed to see through a one-block translation of braid — it "
        "would have green-lit a duplicate")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_braid_covers_the_frame(w, h, base_s):
    # Each 2x2 block is partitioned by its two bricks and the blocks tile the
    # plane, so coverage is exact at any phase. Blocks start at -1 so the
    # down/left wedge blocks fill the top and left edges.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in _gen_braid(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


def test_braid_mean_cell_area_is_base_s_squared():
    # Pool convention: every 2x1 brick has area 2 in block units, so the unit
    # u = base_s/sqrt(2) makes a cell average base_s^2.
    base_s = 60
    areas = []
    for poly in _gen_braid(None, 900, 900, base_s):
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = poly
        # shoelace for the 4-gon
        a = abs((x1 * y2 - x2 * y1) + (x2 * y3 - x3 * y2)
                + (x3 * y4 - x4 * y3) + (x4 * y1 - x1 * y4)) / 2
        areas.append(a)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.01)


# --- moire must not collapse to `square` ------------------------------------
# The whole point of the geometric moire (vs the trivial coloured grid that
# reads as `square` once photos land) is that the CELL geometry warps. The pool
# convention after kepler_ty is to prove that on the geometry, not the scheme:
# a plain square lattice has every cell equal and axis-aligned, so
# non-degeneracy = real spread in cell area AND edges that are mostly not
# axis-aligned.

def _moire_edge_axis_fraction(polys):
    axis = total = 0
    for p in polys:
        n = len(p)
        for k in range(n):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % n]
            ang = math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0)))
            if min(ang, 90 - ang) < 0.5:      # within 0.5 deg of an axis
                axis += 1
            total += 1
    return axis / total


def test_moire_does_not_degenerate_to_square():
    polys = [list(p) for p in _gen_moire(None, 900, 900, 60)]
    areas = np.array([_poly_area(p) for p in polys])
    cv = areas.std() / areas.mean()
    axis_frac = _moire_edge_axis_fraction(polys)
    # a square lattice would score cv == 0 and axis_frac == 1.0 exactly.
    assert cv > 0.1, f"moire cells are near-uniform in area (cv={cv:.3f}) — it collapsed to a grid"
    assert axis_frac < 0.5, (
        f"{axis_frac:.2f} of moire edges are axis-aligned — the cells are "
        "square, not warped")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_moire_covers_the_frame(w, h, base_s):
    # A < 0.5 keeps every vertex inside its neighbour, so the displaced grid is
    # a valid partition; running it two cells past every edge means the wavy
    # outer boundary still covers the frame.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in _gen_moire(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


def test_moire_mean_cell_area_is_about_base_s_squared():
    # Pitch = base_s; the sinusoidal warp is only area-preserving to first
    # order, so at A=0.42 the mean cell biases ~3% high — still "~base_s^2" per
    # the pool convention (cairo/weave use the same approximate wording).
    base_s = 60
    areas = [_poly_area(p) for p in _gen_moire(None, 900, 900, base_s)]
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.05)


# --- puzzle family (sprint P, 2026-07-19) -----------------------------------
# A jigsaw tab is a per-EDGE polyline shared by both neighbouring cells, so
# the partition is exact by construction. The gates mirror the pool's curved-
# shape precedent (poincare/penrose_p2): a FORMAL partition test via
# classify_edges instead of a 1:1 binary raster — Pillow's 1:1 scanline fill
# loses whole rows on curve chains whose vertices land on a scanline
# (measured: 784 false "hole" px for classic at 800x600 while the partition
# is provably exact), so the binary raster is the wrong instrument here. Area
# coverage is instead measured the way the ENGINE actually rasterises:
# ss=4 masks + BOX downsample (the _LazyMask path). Calibration: shipped
# voderberg scores min_cov=0.502 / 210 px below 0.9 on this instrument;
# the puzzle family scores the same or better (133-134 px below 0.9).

_PUZZLE_GENS = {"puzzle_classic": _gen_puzzle_classic,
                "puzzle_ribbon": _gen_puzzle_ribbon,
                "puzzle_hex": _gen_puzzle_hex}


@pytest.mark.parametrize("name", sorted(_PUZZLE_GENS))
@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (384, 288, 100),     # the golden frame
])
def test_puzzle_family_is_an_exact_partition(name, w, h, base_s):
    # Collapse all cells to one group: classify_edges then routes every
    # unpaired seam segment to level 3. A tab polyline NOT shared identically
    # by both neighbours (float drift, wrong direction, differing jitter)
    # would leave interior unpaired segments; zero proves the shared-edge
    # construction. This also proves full coverage: cells are closed and
    # extend past the frame, so with every interior seam paired the union's
    # boundary lies outside the frame.
    PAD = 2.0
    cells = [(list(poly), 0, 0) for poly in _PUZZLE_GENS[name](None, w, h, base_s)]
    by_level = classify_edges(cells)
    interior_unpaired = [
        (a, b) for a, b in by_level[3]
        if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD for p in (a, b))
    ]
    assert not interior_unpaired, (
        f"{len(interior_unpaired)} unpaired interior seam segment(s) for "
        f"{name} at {w}x{h} base_s={base_s}: {interior_unpaired[:3]}")


@pytest.mark.parametrize("name", sorted(_PUZZLE_GENS))
def test_puzzle_family_covers_via_engine_masks(name):
    # Float coverage on the engine's own rasterisation path (ss=4 + BOX). A
    # real hole (a lost tab lobe) is a 0.0-coverage region; sub-pixel seam
    # dust from Pillow's boundary rules bottoms out at ~0.5 (voderberg, the
    # shipped worst case, measures 0.502) — hence the 0.45 floor.
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _PUZZLE_GENS[name](None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    below = int((acc < 0.45).sum())
    assert below == 0, (
        f"{name}: {below} px under 45% engine-mask coverage "
        f"(min={acc.min():.3f}) — real holes, not seam dust")


def test_puzzle_ribbon_warp_differs_from_classic_lattice():
    # The distinctness gate for the pair sharing the tab machinery. Metric on
    # the lattice CORNERS (poly[0] is always a lattice corner, never a tab
    # point), so tab jitter cannot blur it, and nearest-neighbour distances
    # are translation-invariant by construction (the stagger_tri lesson):
    # classic corners are the exact square lattice (CV == 0), ribbon's are
    # warped by the sine field (CV ~ 0.046 measured).
    def corner_cv(gen):
        corners = [list(p)[0] for p in gen(None, 900, 900, 60)]
        interior = [c for c in corners
                    if 120 <= c[0] <= 780 and 120 <= c[1] <= 780]
        dists = []
        for c in interior:
            best = min((c[0] - o[0]) ** 2 + (c[1] - o[1]) ** 2
                       for o in corners if o != c
                       and abs(o[0] - c[0]) < 150 and abs(o[1] - c[1]) < 150)
            dists.append(math.sqrt(best))
        arr = np.array(dists)
        return arr.std() / arr.mean()

    assert corner_cv(_gen_puzzle_classic) < 0.005, (
        "classic corners left the exact lattice")
    assert corner_cv(_gen_puzzle_ribbon) > 0.02, (
        "ribbon warp collapsed onto the classic lattice — it would be a "
        "duplicate of puzzle_classic")


def test_puzzle_cells_have_tab_curves_not_plain_polygons():
    # Distinctness from square/hexagon/moire in one cheap invariant: every
    # boundary is a die-cut curve, so cells carry hundreds of vertices
    # (plain lattices have 4-6; measured: 224/224/336).
    for name, gen in _PUZZLE_GENS.items():
        vmin = min(len(list(p)) for p in gen(None, 600, 600, 60))
        assert vmin > 150, f"{name}: min vertices {vmin} — tabs missing"


@pytest.mark.parametrize("name,rel", [("puzzle_classic", 0.02),
                                      ("puzzle_ribbon", 0.03),
                                      ("puzzle_hex", 0.02)])
def test_puzzle_mean_cell_area_is_base_s_squared(name, rel):
    # Tabs swap area pairwise, so the mean stays base_s^2; the residue is the
    # outer ring of the generated block, whose outward tabs have no partner.
    base_s = 60
    areas = []
    for poly in _PUZZLE_GENS[name](None, 900, 900, base_s):
        p = list(poly)
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=rel)


# --- E4: rep-tile / Koch fractals (2026-07-19) ------------------------------
# dragon and koch_island walk INTEGER lattices (axis-aligned unit edges,
# bit-identical shared coastlines), so the classic 1:1 binary raster is a
# valid coverage instrument for them — unlike the curved puzzle seams.
# koch_snowflake's big and small flakes approximate their SHARED limit
# boundary from different bases, so its seams do not pair exactly at finite
# depth: it is gated on the engine-mask float-coverage instrument instead
# (sprint P precedent; measured min 0.686 vs voderberg's shipped 0.502).

@pytest.mark.parametrize("gen", [_gen_dragon, _gen_koch_island],
                         ids=["dragon", "koch_island"])
@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_reptile_fractals_cover_the_frame(gen, w, h, base_s):
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in gen(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


@pytest.mark.parametrize("gen", [_gen_dragon, _gen_koch_island],
                         ids=["dragon", "koch_island"])
def test_reptile_fractals_mean_cell_area_is_exactly_base_s_squared(gen):
    # Both are area-preserving rep-tiles on a 16-unit lattice with
    # u = base_s/16, and every generated tile is a full translate — the mean
    # is base_s^2 EXACTLY, not approximately.
    base_s = 60
    areas = []
    for poly in gen(None, 900, 900, base_s):
        p = list(poly)
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=1e-9)


def test_dragon_boundary_is_a_fractal_coastline():
    # 246 unit segments for order 8 — the jagged coastline IS the shape; a
    # refactor that simplified it to the bounding square would pass area and
    # coverage, so the vertex count is locked (with slack) here.
    loop = _twindragon_boundary(8)
    assert len(loop) > 200
    assert len(set(loop)) == len(loop), "boundary revisits a vertex"


def test_koch_island_period_is_lattice_not_bbox():
    # The 2026-07-03 trap: the coastline overshoots the underlying square, so
    # tiling by bbox leaves diagonal gaps. The generator must place tiles at
    # the 16-unit lattice period: adjacent tiles' point sets, shifted by one
    # period, must coincide exactly (translated copies).
    base_s = 64                      # u = 4 px -> period 64 px
    polys = [sorted(list(p)) for p in _gen_koch_island(None, 300, 200, base_s)]
    first = polys[0]
    shifted = sorted((x + 64.0, y) for x, y in first)
    assert any(all(abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9
                   for a, b in zip(shifted, q)) for q in polys), (
        "no tile equals its neighbour translated by one 16-unit period")


def test_koch_snowflake_covers_via_engine_masks():
    # Float coverage on the engine's own rasterisation path (sprint P
    # instrument): a missing flake is a 0.0 region; finite-depth seam shading
    # bottoms out at 0.686 (measured), comfortably above the 0.45 floor.
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _gen_koch_snowflake(None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    below = int((acc < 0.45).sum())
    over = int((acc > 1.5).sum())
    assert below == 0, f"{below} px under 45% coverage — a flake is missing"
    assert over == 0, f"{over} px over 150% coverage — flakes overlap"


def test_koch_snowflake_two_sizes_in_exact_area_balance():
    # 1 big + 2 small per lattice cell, small = big/3 (scale 1/sqrt(3)); the
    # big flake is the pool's dominant tile at ~base_s^2 (depth-4 polygon
    # sits ~1.5% inside the limit fractal).
    base_s = 60
    areas = []
    for poly in _gen_koch_snowflake(None, 800, 600, base_s):
        p = list(poly)
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    big = [a for a in areas if a > 2000]
    small = [a for a in areas if a <= 2000]
    assert len(small) == pytest.approx(2 * len(big), abs=len(big) * 0.35)
    assert np.mean(big) == pytest.approx(base_s ** 2, rel=0.03)
    assert np.mean(big) / np.mean(small) == pytest.approx(3.0, rel=0.01)


# --- E5: Islamic star partitions (2026-07-19) -------------------------------
# gereh (4.8.8, octagons split into 16 kites + gap diamonds) and rosette
# (3.12.12, dodecagons split into 36 cells + interstitial triangles). All
# edges are straight segments, so the 1:1 binary raster is the right
# coverage instrument (the instrument ladder from sprint P). gereh's
# octagon-vs-square T-junctions are legal (the tip lies exactly on the
# square's straight side — stagger_tri precedent), which is also why the
# formal classify_edges partition test is NOT used here: it would flag
# every legal T-junction as unpaired.

@pytest.mark.parametrize("gen", [_gen_gereh, _gen_rosette],
                         ids=["gereh", "rosette"])
@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),      # 4:3
    (1200, 300, 50),     # wide band
    (640, 640, 80),      # square
    (500, 500, 40),      # dense
    (384, 288, 100),     # the golden frame
])
def test_star_partitions_cover_the_frame(gen, w, h, base_s):
    # For gereh this gate is what caught the scheme's own bug: the proposal
    # drew the 4.8.8 gap square axis-aligned (phase pi/4), which overlaps the
    # octagons at its corners and leaves triangular holes at its edge
    # midpoints (11k px at 800x600) — invisible under the PNG's outlines.
    # The true gap is the DIAMOND whose corners are octagon vertices.
    acc = np.zeros((h, w), dtype=np.uint16)
    for poly in gen(None, w, h, base_s):
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in poly], fill=1)
        acc += np.asarray(m, dtype=np.uint16)
    holes = int((acc == 0).sum())
    assert holes == 0, f"{holes} uncovered px at {w}x{h} base_s={base_s}"


def test_gereh_cells_are_all_quads_unlike_trunc_square():
    # The audit's cleared distinction from trunc_square (same 4.8.8 lattice):
    # there the octagon is ONE 8-gon cell, here it is 16 kites — so every
    # gereh cell must be a quad, and the mean must sit at base_s^2 (17 cells
    # per period cell of area (3+2*sqrt(2))*s^2).
    base_s = 60
    polys = [list(p) for p in _gen_gereh(None, 900, 900, base_s)]
    assert {len(p) for p in polys} == {4}, "gereh emitted a non-quad cell"
    areas = []
    for p in polys:
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.01)


def test_rosette_cells_are_tris_and_quads_unlike_trunc_hex():
    # Distinction from trunc_hex (same 3.12.12 lattice): the dodecagon there
    # is ONE 12-gon cell, here 12 kites + 12 petals + 12 edge triangles, plus
    # the interstitial triangles — so cells are only tris and quads, both
    # kinds present, mean ~ base_s^2 (38 cells per lattice cell).
    base_s = 60
    polys = [list(p) for p in _gen_rosette(None, 900, 900, base_s)]
    counts = {len(p) for p in polys}
    assert counts == {3, 4}, f"unexpected cell vertex counts: {counts}"
    areas = []
    for p in polys:
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.03)


def test_rosette_interstitial_triangles_fill_the_lattice_holes():
    # The 2026-07-04 black-wedge bug class: a hole whose rosette centre falls
    # outside the drawing window must still get its triangle. The engine
    # anchors holes at lattice-triangle centroids analytically, so every
    # in-frame hole is covered — proven by zero holes in the coverage gate —
    # and the triangle count matches the two-per-lattice-cell construction.
    polys = [list(p) for p in _gen_rosette(None, 900, 900, 60)]
    tris = [p for p in polys if len(p) == 3]
    quads = [p for p in polys if len(p) == 4]
    # per full dodecagon: 12 edge tris; per lattice cell: +2 interstitial.
    # quads per dodecagon: 24. So tris/quads ~ (12+2)/24 for interior cells.
    assert 0.4 < len(tris) / len(quads) < 0.8


def test_poincare_grout_via_dispatcher_is_hierarchical():
    # The dedicated branch must fire from _grout_cells BEFORE the generic polygon
    # fallthrough (which would hand back flat (0, 0) cells), and poincare must be
    # registered hierarchical so graded L1<L2<L3 widths apply.
    e = _engine()
    cells = e._grout_cells("poincare", 600, 450, 60)
    assert cells
    assert {(g2, g3) for _, g2, g3 in cells} != {(0, 0)}, (
        "poincare fell through to the flat generic branch")
    assert "poincare" in e._HIERARCHICAL_GROUT


def test_unsupported_shapes_return_none():
    e = _engine()
    # only shapes absent from the SHAPE_MODES registry hit the dispatcher's
    # default None path (the caller then skips the pass). Deliberately fake
    # names: every real planned shape eventually joins the registry (penrose
    # did exactly that and broke the previous version of this test).
    for shape in ("no_such_shape", "definitely_not_a_shape"):
        assert e._grout_cells(shape, 400, 300, 100) is None, shape


def test_polygon_registry_shapes_get_flat_cells():
    # Registry polygon shapes without an explicit branch fall through to the
    # generic case: their SHAPE_MODES generator re-yields the tile polygons as
    # flat cells (uniform group ids -> L1 seams, L3 frame).
    e = _engine()
    for shape in ("voronoi", "phyllotaxis", "sunflower_grande", "rhombs_star"):
        cells = e._grout_cells(shape, 400, 300, 100)
        assert cells, shape
        assert all(len(poly) >= 3 for poly, _, _ in cells), shape
        assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}, shape


def test_polygon_grout_cells_match_render_geometry():
    # The grout pass re-runs the same generator with the same dimensions, so
    # the cells must be identical polys to what the render used (seeded
    # voronoi included) — grout lines land exactly on the tile seams.
    from src.engine_smart import SHAPE_MODES
    e = _engine()
    for shape in ("voronoi", "sunflower_grande"):
        gen_polys = [list(p) for p in
                     SHAPE_MODES[shape].generator(e, 400, 300, 100)]
        cells = e._grout_cells(shape, 400, 300, 100)
        assert [poly for poly, _, _ in cells] == gen_polys, shape


def test_spectre_flat_cells_share_one_group():
    # Flat grout: every spectre monotile carries the SAME (g2, g3) so
    # classify_edges leaves interior seams at L1 and only the frame boundary at
    # L3. A per-tile group id here would silently promote every seam to L3.
    cells = _engine()._grout_cells("spectre", 600, 600, 60)
    assert cells, "spectre grout cells missing"
    assert all(len(poly) >= 3 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}


def test_romb_flat_cells_share_one_group():
    cells = _engine()._grout_cells("romb", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}


def test_romb_adjacent_diamonds_share_edges():
    # THE float-th check: with tile_h = FLOAT base_s*1.5 the diamonds tessellate
    # and interior seams are shared -> classify_edges puts them at L1. If tile_h
    # were int()-truncated the seams would split by <1 px, every edge would be a
    # frame boundary (L3) and L1 would be nearly empty. Assert L1 dominates.
    cells = _engine()._grout_cells("romb", 600, 600, 60)
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3]), (
        f"interior seams not shared: L1={len(by_level[1])} L3={len(by_level[3])} "
        f"(tile_h likely truncated to int)")


def test_rectangle_3x1_flat_cells_share_one_group():
    cells = _engine()._grout_cells("rectangle_3x1", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    # clean abutting grid: interior edges shared (L1), only the true frame is L3
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3])


def test_brick_wall_flat_cells_share_one_group():
    # brick_wall's half-brick offset means horizontal mortar meets vertical
    # edges at T-junctions, so those seams are not shared (they land at L3). That
    # is fine for flat grout -- assert only the uniform group id and that the
    # bricks are the right 2:1 shape (tile_h = base_s//2).
    cells = _engine()._grout_cells("brick_wall", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    w = cells[0][0][1][0] - cells[0][0][0][0]
    h = cells[0][0][2][1] - cells[0][0][1][1]
    assert w == 60 and h == 30


def test_hexagon_romb_three_rhombi_per_hexagon():
    # Variant 2: each hexagon becomes three rhombi (its three composite photos)
    # that share the centre vertex -> an internal "Y". Cells come in triples
    # whose first vertex is that shared centre.
    cells = _engine()._grout_cells("hexagon_romb", 600, 600, 60)
    assert cells and len(cells) % 3 == 0
    assert all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    for k in range(0, len(cells), 3):
        c0 = cells[k][0][0]
        assert cells[k + 1][0][0] == c0 and cells[k + 2][0][0] == c0


def test_hexagon_romb_edges_are_shared():
    # Internal spokes (shared by two rhombi of one hexagon) and outer edges
    # (shared by adjacent hexagons) must land at L1; wrong th would split the
    # outer edges into frame boundaries. Assert L1 dominates.
    cells = _engine()._grout_cells("hexagon_romb", 600, 600, 60)
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3])


# ---------------------------------------------------------------------------
# render integration: overlay semantics
# ---------------------------------------------------------------------------
def _small_engine(tmp_path):
    paths, feats = _build_library(tmp_path)
    e = _engine()
    e.paths = paths
    e.features = feats
    e.settings = {"allow_mirror": False, "edge_aware": False, "freq_penalty": 30.0}
    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    return e


def _preview(e, tmp_path, shape, grout_preset=None):
    tgt = _make_target()
    p = tmp_path / "target.png"
    tgt.save(p)
    return e.render_preview(str(p), short_edge=200, shape_mode=shape,
                            tile_scale=1.0, grout_preset=grout_preset)


def test_grout_none_is_identical_to_baseline(tmp_path):
    e = _small_engine(tmp_path)
    base = _preview(e, tmp_path, "square", grout_preset=None)
    again = _preview(e, tmp_path, "square", grout_preset=None)
    assert np.array_equal(np.asarray(base), np.asarray(again))


def test_grout_preset_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "square", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "square", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_spectre_adds_black_lines(tmp_path):
    # Flat grout on an aperiodic shape: no grouping, but the seams still get a
    # uniform-width overlay, so the grouted render differs from the baseline and
    # gains black pixels.
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "spectre", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "spectre", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_romb_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "romb", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "romb", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_rectangle_3x1_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "rectangle_3x1", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "rectangle_3x1", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_brick_wall_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "brick_wall", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "brick_wall", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_hexagon_romb_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "hexagon_romb", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "hexagon_romb", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_voronoi_adds_black_lines(tmp_path):
    # A registry polygon shape (generic grout branch): seams get the flat
    # uniform-width overlay, same semantics as spectre/romb above.
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "voronoi", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "voronoi", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_is_noop_for_unsupported_shape():
    # A shape with no grout geometry leaves the mosaic untouched (the None path
    # in _apply_grout). Checked directly on a blank canvas -- no render needed.
    e = _engine()
    img = Image.new("RGB", (200, 150), "white")
    before = np.asarray(img).copy()
    e._apply_grout(img, "no_such_shape", 200, 150, 60, "medium")
    assert np.array_equal(before, np.asarray(img))


# ---------------------------------------------------------------------------
# decorative stroke styles + colour palette (2026-07-19)
# ---------------------------------------------------------------------------
from src.grout import (GROUT_COLORS, classify_edges as _classify,
                       color_names, draw_grout as _draw, resolve_color,
                       style_names)


def _style_canvas():
    """Small synthetic scene: 2x2 squares on a mid-gray canvas -- fast, no
    render, exercises horizontal, vertical and frame seams."""
    cells = []
    for i in range(2):
        for j in range(2):
            x, y = i * 100, j * 100
            cells.append(([(x, y), (x + 100, y), (x + 100, y + 100),
                           (x, y + 100)], 0, 0))
    img = Image.new("RGB", (200, 200), (120, 120, 120))
    return img, _classify(cells)


def test_style_names_start_with_solid_and_cover_the_verdict():
    names = style_names()
    assert names[0] == "solid"
    assert set(names[1:]) == {"zigzag", "squiggle", "double", "stitch",
                              "beads", "rope", "bevel", "neon", "kintsugi",
                              "brush"}, "accepted style set drifted"


def test_solid_default_is_the_classic_pass():
    # style="solid" must be byte-identical to calling draw_grout without the
    # style argument at all -- the classic path is the regression anchor.
    img_a, by_level = _style_canvas()
    img_b, _ = _style_canvas()
    _draw(img_a, by_level, {1: 6})
    _draw(img_b, by_level, {1: 6}, style="solid")
    assert np.array_equal(np.asarray(img_a), np.asarray(img_b))


@pytest.mark.parametrize("style", style_names()[1:])
def test_each_style_differs_from_solid_and_is_deterministic(style):
    img_solid, by_level = _style_canvas()
    _draw(img_solid, by_level, {1: 6})
    outs = []
    for _ in range(2):
        img, lvl = _style_canvas()
        _draw(img, lvl, {1: 6}, style=style)
        outs.append(np.asarray(img).copy())
    assert not np.array_equal(outs[0], np.asarray(img_solid)), (
        f"style {style!r} rendered identically to solid")
    assert np.array_equal(outs[0], outs[1]), (
        f"style {style!r} is not deterministic")
    assert not np.array_equal(outs[0], np.full_like(outs[0], 120)), (
        f"style {style!r} drew nothing")


def test_short_segments_fall_back_to_solid_capsule_not_garbage():
    # Densely polygonised curved seams hand the styles segments of a few px;
    # the contract is a thin solid capsule, so the seam stays a clean line.
    img = Image.new("RGB", (60, 60), (120, 120, 120))
    pts = [(10 + i * 2.0, 30 + (i % 2)) for i in range(20)]
    by_level = {1: list(zip(pts, pts[1:])), 2: [], 3: []}
    _draw(img, by_level, {1: 6}, style="zigzag")
    arr = np.asarray(img)
    assert (arr.sum(axis=2) < 90).sum() > 20, "fallback drew no line at all"


def test_grout_color_palette_resolves_and_rejects():
    assert resolve_color("black") == (0, 0, 0)
    assert resolve_color("gold") == GROUT_COLORS["gold"]
    assert len(color_names()) == len(GROUT_COLORS)
    with pytest.raises(ValueError):
        resolve_color("chartreuse")


def test_unknown_style_raises_value_error():
    img, by_level = _style_canvas()
    with pytest.raises(ValueError):
        _draw(img, by_level, {1: 6}, style="glitter")


def test_solid_gold_paints_the_palette_color():
    img, by_level = _style_canvas()
    _draw(img, by_level, {1: 6}, color=resolve_color("gold"), style="solid")
    arr = np.asarray(img)
    gold = np.array(GROUT_COLORS["gold"])
    hits = (np.abs(arr.astype(int) - gold).sum(axis=2) < 12).sum()
    assert hits > 500, "gold grout pixels missing"


def test_engine_render_accepts_style_and_color(tmp_path):
    # End-to-end through _apply_grout: a styled, coloured render differs from
    # the solid/black one and from the baseline; determinism is covered at the
    # draw_grout level above.
    e = _small_engine(tmp_path)
    tgt = _make_target()
    p = tmp_path / "target.png"
    tgt.save(p)
    base = np.asarray(e.render_preview(str(p), short_edge=200,
                                       shape_mode="square", tile_scale=1.0,
                                       grout_preset="thick"))
    styled = np.asarray(e.render_preview(str(p), short_edge=200,
                                         shape_mode="square", tile_scale=1.0,
                                         grout_preset="thick",
                                         grout_style="kintsugi",
                                         grout_color="gold"))
    assert base.shape == styled.shape
    assert not np.array_equal(base, styled)
    gold = np.array(GROUT_COLORS["gold"])
    hits = (np.abs(styled.astype(int) - gold).sum(axis=2) < 40).sum()
    assert hits > 50, "gold kintsugi pixels missing in the render"


# --- E6: scales (fish scales) ----------------------------------------------
# Curved seams shared CONSTRUCTIONALLY (each bite arc is literally the
# neighbour's dome quarter, same _sun_arc call), so per the coverage-instrument
# ladder (MEMORY 2026-07-19) the gates are: a FORMAL partition test via
# classify_edges + FLOAT coverage on the engine's own ss=4 + BOX path. A 1:1
# binary raster would LIE here (whole rows lost on curve chains).

@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (384, 288, 100),
])
def test_scales_is_an_exact_partition(w, h, base_s):
    PAD = 2.0
    cells = [(list(poly), 0, 0) for poly in _gen_scales(None, w, h, base_s)]
    by_level = classify_edges(cells)
    interior_unpaired = [
        (a, b) for a, b in by_level[3]
        if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD for p in (a, b))
    ]
    assert not interior_unpaired, (
        f"{len(interior_unpaired)} unpaired interior seam segment(s) at "
        f"{w}x{h} base_s={base_s}: {interior_unpaired[:3]}")


def test_scales_covers_via_engine_masks():
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _gen_scales(None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    below = int((acc < 0.45).sum())
    assert below == 0, (
        f"scales: {below} px under 45% engine-mask coverage "
        f"(min={acc.min():.3f}) — real holes, not seam dust")


def test_scales_mean_area_is_base_s_squared():
    # Cell = disk minus two tangent lenses -> 2*r^2 = lattice determinant.
    # r = base_s/sqrt(2) is what makes that base_s^2 (the pool's convention).
    base_s = 60
    areas = []
    for p in _gen_scales(None, 900, 900, base_s):
        p = list(p)
        s = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            s += x0 * y1 - x1 * y0
        areas.append(abs(s) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.02)


def test_scales_arc_pitch_keeps_the_dome_smooth():
    # The truchet_hex trap: a base_s-derived pitch would facet an arc whose
    # radius does NOT grow with the frame. Assert the sagitta of every chord
    # stays sub-pixel, and that the cell therefore carries many vertices.
    base_s = 60
    r = base_s / math.sqrt(2.0)
    polys = [list(p) for p in _gen_scales(None, 600, 600, base_s)]
    worst = 0.0
    for p in polys[:200]:
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            worst = max(worst, math.hypot(x1 - x0, y1 - y0))
    sagitta = worst ** 2 / (8.0 * r)
    assert sagitta < 0.5, f"chord {worst:.2f}px -> sagitta {sagitta:.2f}px"
    assert min(len(p) for p in polys) >= 12


def test_scales_has_no_consecutive_duplicate_vertices():
    # Arc chains always join end-to-end; a leftover duplicate flips Pillow's
    # scanline parity and stripes the render (sprint P lesson).
    for p in _gen_scales(None, 600, 600, 60):
        p = list(p)
        for k in range(len(p)):
            a, b = p[k], p[(k + 1) % len(p)]
            assert math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-9, (
                f"duplicate vertex at index {k}: {a}")


# --- E6: nautilus (log-spiral chambers, pole outside the frame) -------------
# Per-ring phase (swirl + brick offset) means a ring arc is cut differently on
# its two sides: LEGAL T-junctions, the voderberg/sunburst precedent. So per
# the ladder the gate is FLOAT coverage only — a formal partition test would
# be the wrong instrument and would fail on a correct shape.

def test_nautilus_covers_via_engine_masks():
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _gen_nautilus(None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    below = int((acc < 0.45).sum())
    assert below == 0, (
        f"nautilus: {below} px under 45% engine-mask coverage "
        f"(min={acc.min():.3f}) — real holes, not seam dust")


def test_nautilus_pole_lies_outside_the_frame():
    # THE distinctness gate against sunburst (same log-polar machinery). The
    # smallest cell always sits closest to the pole; sunburst's pole is the
    # frame centre, nautilus's is beyond the top-left corner. Measured in
    # half-diagonals: nautilus 0.97, sunburst 0.22.
    def smallest_cell_offset(gen):
        w, h = 800, 600
        best = None
        for poly in gen(None, w, h, 60):
            poly = list(poly)
            cx = sum(q[0] for q in poly) / len(poly)
            cy = sum(q[1] for q in poly) / len(poly)
            if not (0 <= cx < w and 0 <= cy < h):
                continue
            a = 0.0
            for k in range(len(poly)):
                x0, y0 = poly[k]
                x1, y1 = poly[(k + 1) % len(poly)]
                a += x0 * y1 - x1 * y0
            a = abs(a) / 2.0
            if best is None or a < best[0]:
                best = (a, cx, cy)
        _, cx, cy = best
        return math.hypot(cx - w / 2, cy - h / 2) / math.hypot(w / 2, h / 2)

    assert smallest_cell_offset(_gen_nautilus) > 0.7, "nautilus pole drifted inward"
    assert smallest_cell_offset(_gen_sunburst) < 0.4, "sunburst is no longer centred"


def test_nautilus_has_no_shrinking_singularity():
    # The 'good centre' rule. A log-polar field ALWAYS has a size gradient
    # (cell size ~ r); what the outside pole buys is that the visible radius
    # band is bounded AWAY FROM ZERO, so no cell collapses. With the pole at
    # the frame centre (sunburst) the inner cells would tend to nothing and
    # only a cap fan saves them. Measured smallest chamber: 0.39*base_s.
    base_s = 60
    areas = []
    for poly in _gen_nautilus(None, 800, 600, base_s):
        poly = list(poly)
        cx = sum(q[0] for q in poly) / len(poly)
        cy = sum(q[1] for q in poly) / len(poly)
        if not (0 <= cx < 800 and 0 <= cy < 600):
            continue
        a = 0.0
        for k in range(len(poly)):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % len(poly)]
            a += x0 * y1 - x1 * y0
        areas.append(abs(a) / 2.0)
    assert math.sqrt(min(areas)) > 0.3 * base_s, "a chamber collapsed"


def test_nautilus_chambers_are_square_in_log_polar():
    # THE invariant behind g = 1 + 2*pi/nsec: the radial depth of a chamber
    # equals its arc width at the same radius, so cells read as ~square at
    # every radius even though they grow outward. This is what makes the size
    # gradient acceptable rather than a distortion.
    for poly in _gen_nautilus(None, 800, 600, 60):
        poly = list(poly)
        px, py = -0.55 * 400.0, -0.30 * 300.0
        rs = [math.hypot(x - px, y - py) for x, y in poly]
        r_in, r_out = min(rs), max(rs)
        depth = r_out - r_in
        # arc width at mid radius: the inner arc's polyline length
        inner = [p for p, r in zip(poly, rs) if r < (r_in + r_out) / 2]
        width = sum(math.hypot(inner[k + 1][0] - inner[k][0],
                               inner[k + 1][1] - inner[k][1])
                    for k in range(len(inner) - 1))
        width *= ((r_in + r_out) / 2) / r_in          # scale to mid radius
        assert 0.8 < depth / width < 1.25, (
            f"chamber aspect {depth / width:.2f} — g/nsec relation broken")


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (900, 900, 60),
])
def test_nautilus_mean_area_tracks_base_s(w, h, base_s):
    # Looser than the lattice shapes' 2-5%: a log-polar field has a genuine
    # 2x linear size gradient across the frame, so `base_s` sets the MEAN
    # chamber, and the aspect ratio shifts which part of the radius band is
    # visible (measured 0.90-1.05 linear across the pool's test frames).
    areas = []
    for poly in _gen_nautilus(None, w, h, base_s):
        poly = list(poly)
        cx = sum(q[0] for q in poly) / len(poly)
        cy = sum(q[1] for q in poly) / len(poly)
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        a = 0.0
        for k in range(len(poly)):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % len(poly)]
            a += x0 * y1 - x1 * y0
        areas.append(abs(a) / 2.0)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.25)


def test_nautilus_arcs_stay_smooth():
    # _arc_pitch per ring: sagitta under a pixel on every chord, both sides of
    # a shared ring arc using the SAME pitch (same radius -> same call).
    # Only ARC chords are checked: the two long radial seams joining the inner
    # and outer arcs are STRAIGHT by construction and have no sagitta at all
    # (measuring them was this test's first, wrong, formulation).
    px, py = -0.55 * 400.0, -0.30 * 300.0
    worst = 0.0
    for poly in _gen_nautilus(None, 800, 600, 60):
        poly = list(poly)
        rs = [math.hypot(x - px, y - py) for x, y in poly]
        for k in range(len(poly)):
            j = (k + 1) % len(poly)
            if abs(rs[k] - rs[j]) > 1e-6:
                continue                      # radial seam, not an arc chord
            chord = math.hypot(poly[j][0] - poly[k][0], poly[j][1] - poly[k][1])
            worst = max(worst, chord ** 2 / (8.0 * rs[k]))
    assert worst < 0.5, f"arc sagitta {worst:.3f} px — visible faceting"


# --- E6: rosette_fractal (spiral aloe) --------------------------------------
# Every seam is an _edge polyline addressed by (ring, vertex) pairs in each
# ring's own units, so both cells generate the same points -> shared polylines
# -> the FORMAL partition test is the right instrument here (unlike nautilus,
# whose ring phase makes legal T-junctions).

def _areas_inside(gen, w, h, base_s):
    out = []
    for poly in gen(None, w, h, base_s):
        poly = list(poly)
        cx = sum(q[0] for q in poly) / len(poly)
        cy = sum(q[1] for q in poly) / len(poly)
        if not (0 <= cx < w and 0 <= cy < h):
            continue
        a = 0.0
        for k in range(len(poly)):
            x0, y0 = poly[k]
            x1, y1 = poly[(k + 1) % len(poly)]
            a += x0 * y1 - x1 * y0
        out.append(abs(a) / 2.0)
    return out


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (384, 288, 50),
])
def test_rosette_fractal_is_an_exact_partition(w, h, base_s):
    PAD = 2.0
    cells = [(list(poly), 0, 0)
             for poly in _gen_rosette_fractal(None, w, h, base_s)]
    by_level = classify_edges(cells)
    interior_unpaired = [
        (a, b) for a, b in by_level[3]
        if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD for p in (a, b))
    ]
    assert not interior_unpaired, (
        f"{len(interior_unpaired)} unpaired interior seam segment(s) at "
        f"{w}x{h} base_s={base_s}: {interior_unpaired[:3]}")


def test_rosette_fractal_covers_via_engine_masks():
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _gen_rosette_fractal(None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    below = int((acc < 0.45).sum())
    assert below == 0, (
        f"rosette_fractal: {below} px under 45% engine-mask coverage "
        f"(min={acc.min():.3f}) — real holes, not seam dust")


def test_rosette_fractal_rings_per_doubling_keep_cells_square():
    # THE fix over the scheme. Within a doubling period N is constant while r
    # doubles, so the radial depth r*(g-1) doubles; at the doubling N halves
    # the tangential size but not the depth, so a FIXED m makes the aspect
    # ratio double every period. Derived m = round(ln2/ln(1+2pi/N)) — the
    # sunburst square-cell relation snapped onto the doubling grid — holds it
    # flat. Over 8 doublings: fixed m=3 reaches 64:1, derived stays under 1.01.
    def aspects(fixed):
        N, out = 12, []
        for _ in range(8):
            m = 3 if fixed else max(
                1, round(math.log(2.0) / math.log(1.0 + 2.0 * math.pi / N)))
            out.append(N * (2.0 ** (1.0 / m) - 1.0) / (2.0 * math.pi))
            N *= 2
        return out

    assert max(aspects(fixed=False)) < 1.01
    assert min(aspects(fixed=False)) > 0.75
    assert max(aspects(fixed=True)) > 50.0, (
        "the scheme's fixed m=3 no longer diverges — re-check the derivation")
    # m=3 must still fall out naturally at N=24 (the scheme's own value)
    assert round(math.log(2.0) / math.log(1.0 + 2.0 * math.pi / 24)) == 3


def test_rosette_fractal_cell_size_resets_at_each_doubling():
    # The pole fix, measured on the real generator: cell size oscillates
    # within a period and RESETS at every doubling, so the spread stays
    # bounded (~1.8x linear) instead of growing with the frame — contrast
    # nautilus, whose pole-outside field has a monotone 4.4x gradient.
    areas = _areas_inside(_gen_rosette_fractal, 900, 900, 60)
    spread = math.sqrt(max(areas) / min(areas))
    assert spread < 2.2, f"linear cell-size spread {spread:.2f}x"


@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60),
    (1200, 300, 50),
    (900, 900, 60),
    (1600, 1200, 80),
])
def test_rosette_fractal_mean_area_is_base_s_squared(w, h, base_s):
    areas = _areas_inside(_gen_rosette_fractal, w, h, base_s)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.12)


def test_rosette_fractal_scales_to_16k_within_budget():
    # A log-polar field doubling outward could explode; the derived m keeps
    # the ring count logarithmic. 16K measured: ~42k cells, all small polys.
    n, max_verts = 0, 0
    for poly in _gen_rosette_fractal(None, 16384, 12288, 75):
        n += 1
        max_verts = max(max_verts, len(poly))
    assert n < 120000, f"{n} cells at 16K — RAM budget (A1) at risk"
    assert max_verts < 64


# --- E7: Sierpinski family --------------------------------------------------
# T-JUNCTIONS BY CONSTRUCTION, and deliberately so: a hole is ONE cell (one
# large photo — the whole point of the shape) while the gasket triangles
# around it are subdivided by their own recursion, so a level-d hole edge
# faces 2^(d-1) segments. A formal partition test is therefore the WRONG
# instrument. All edges are straight, so coverage is exact: min == 1.000, no
# gaps and no seam dust at all.

_SIERP_GENS = {"sierpinski": _gen_sierpinski,
               "sierpinski_d": _gen_sierpinski_d,
               "sierpinski_carpet": _gen_sierpinski_carpet}


@pytest.mark.parametrize("name", sorted(_SIERP_GENS))
def test_sierpinski_family_covers_the_frame_exactly(name):
    w, h, base_s, ss = 800, 600, 60, 4
    acc = np.zeros((h, w), dtype=np.float64)
    for poly in _SIERP_GENS[name](None, w, h, base_s):
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        acc += np.asarray(m.resize((w, h), Image.BOX), dtype=np.float64) / 255.0
    assert acc.min() == pytest.approx(1.0, abs=1e-9), (
        f"{name}: min coverage {acc.min():.4f} — straight-edged cells must "
        f"tile the frame with no gaps and no seam dust")


@pytest.mark.parametrize("name", sorted(_SIERP_GENS))
@pytest.mark.parametrize("w,h,base_s", [
    (800, 600, 60), (1200, 300, 50), (900, 900, 60),
])
def test_sierpinski_family_mean_area_tracks_base_s(name, w, h, base_s):
    areas = _areas_inside(_SIERP_GENS[name], w, h, base_s)
    assert sum(areas) / len(areas) == pytest.approx(base_s ** 2, rel=0.25)


def test_sierpinski_brick_stagger_adds_no_t_junctions():
    # The stagger is S/2 = four of the eight sub-segments a depth-3 edge is
    # cut into, so the shifted row's subdivision points land on the row
    # below's. Verified by sweeping the offset: S/2 costs nothing over no
    # stagger at all, while offsets that are NOT multiples of S/8 add ~20
    # extra unpaired seams. (The 102 baseline is the inherent hole ones.)
    w, h, base_s, PAD = 800, 600, 60, 2.0

    def unpaired(frac):
        S = base_s * math.sqrt(160.0 / math.sqrt(3.0))
        H = S * math.sqrt(3.0) / 2.0
        cells = []
        for r in range(-1, int(h / H) + 2):
            y0 = r * H
            xoff = (S * frac) if (r % 2) else 0.0
            for c in range(-2, int(w / S) + 3):
                x0 = c * S + xoff
                up = (complex(x0, y0), complex(x0 + S, y0),
                      complex(x0 + S / 2, y0 + H))
                dn = (complex(x0 + S / 2, y0 + H),
                      complex(x0 + 1.5 * S, y0 + H), complex(x0 + S, y0))
                for tri in (up, dn):
                    if _tri_outside(tri, w, h):
                        continue
                    out = []
                    _sierpinski_cells(tri[0], tri[1], tri[2], 3, out)
                    for cell in out:
                        cells.append(([(z.real, z.imag) for z in cell], 0, 0))
        by_level = classify_edges(cells)
        return len([1 for a, b in by_level[3]
                    if all(PAD < p[0] < w - PAD and PAD < p[1] < h - PAD
                           for p in (a, b))])

    assert unpaired(0.5) == unpaired(0.0), "S/2 stagger misaligned the rows"
    assert unpaired(1.0 / 3.0) > unpaired(0.5)
    assert unpaired(0.2) > unpaired(0.5)


def test_sierpinski_d_checkerboard_spreads_the_big_holes():
    # Variant D's reason to exist: carrier = (t + r) % 2 offsets the largest
    # holes row to row instead of stacking them into columns. Measured on the
    # BIG cells (area > 4x the mean): their x-positions must not collapse
    # onto a few columns the way an unshifted carrier would.
    w, h, base_s = 1200, 900, 55
    polys = [list(p) for p in _gen_sierpinski_d(None, w, h, base_s)]
    big = []
    for p in polys:
        a = 0.0
        for k in range(len(p)):
            x0, y0 = p[k]
            x1, y1 = p[(k + 1) % len(p)]
            a += x0 * y1 - x1 * y0
        a = abs(a) / 2.0
        cx = sum(q[0] for q in p) / len(p)
        cy = sum(q[1] for q in p) / len(p)
        if a > 4.0 * base_s ** 2 and 0 <= cx < w and 0 <= cy < h:
            big.append((cx, cy))
    assert len(big) >= 4, "no big holes found — carrier logic broken"
    S = base_s * math.sqrt(184.0 / math.sqrt(3.0))
    bands = {}
    for cx, cy in big:
        bands.setdefault(round(cy / (S * math.sqrt(3.0) / 2.0)), []).append(cx)
    keys = sorted(k for k, v in bands.items() if len(v) >= 2)
    assert len(keys) >= 2, "big holes confined to one row band"
    # within a band the big holes sit one lattice period apart...
    for k in keys:
        xs = sorted(bands[k])
        assert xs[1] - xs[0] == pytest.approx(S, rel=0.02)
    # ...and consecutive bands are offset by HALF a period — that is the
    # checkerboard doing its job (measured: 283.4 vs 566.9 with S = 566.9).
    phase = [sorted(bands[k])[0] % S for k in keys[:2]]
    assert abs(phase[0] - phase[1]) == pytest.approx(S / 2.0, rel=0.05), (
        f"big holes stack into columns: phases {phase} with S={S:.1f}")


def test_sierpinski_family_scales_to_16k_within_budget():
    # Pruning matters here: an unpruned depth-4 carpet emits 4681 cells per
    # lattice position regardless of how little shows (42k cells for the ~155
    # that touch an 800x600 frame). With pruning all three stay ~40k at 16K.
    for name, gen in _SIERP_GENS.items():
        n = sum(1 for _ in gen(None, 16384, 12288, 75))
        assert n < 120000, f"{name}: {n} cells at 16K — RAM budget (A1) at risk"


def test_sierpinski_carpet_pruning_keeps_only_relevant_cells():
    # The pruning must not change WHAT is drawn, only how much is built: the
    # frame stays fully covered (asserted above) while the cell count drops by
    # two orders of magnitude.
    n = sum(1 for _ in _gen_sierpinski_carpet(None, 800, 600, 60))
    assert n < 1000, f"{n} cells — recursion pruning is not firing"
