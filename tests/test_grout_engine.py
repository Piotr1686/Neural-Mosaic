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
                              _gen_moire, _GOLDEN_ANGLE, _LUCAS_ANGLE)
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
