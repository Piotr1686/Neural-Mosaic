"""
src/engine_smart.py
-------------------
Colour-matched photomosaic engine (SmartEngine).

Supports multiple tile geometries including the per-tile deltoidal kite
grid ("kites") and the chiral aperiodic "spectre" monotile (src/spectre_tiling.py).
Each sector of the target image is matched to the best-fitting tile from
the pre-built CIELAB feature index with spatial anti-repetition enforcement.

Index schema "5x5_edge" (79-dim) enables edge-aware matching: 4 extra
features (mean L of each border strip) are appended to the standard 75-dim
LAB vector and scaled by EDGE_WEIGHT so boundary lightness contributes ~15%
of the total Euclidean distance. With edge_aware=False the engine silently
slices the first 75 dimensions, so old and new indexes are both accepted.
"""
import numpy as np
import pickle
import math
import cmath
import json
import threading
import heapq
from collections import deque
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from tqdm import tqdm
from scipy.spatial import cKDTree, Voronoi
from scipy.ndimage import (label as nd_label, find_objects as nd_find_objects,
                           binary_dilation)
import skimage.color
from skimage.measure import find_contours, approximate_polygon

from .spectre_tiling import generate_spectre_tiling
from .render_control import RenderCancelled
from .grout import classify_edges, draw_grout, scale_widths, sub7

# Hi-res tile overlay directory. When a file with the same basename as a
# library tile exists here, the assembly loop pastes THIS copy instead of the
# (downscaled) library original — see _resolve_tile_path. Anchored to the repo
# root so it is independent of the process working directory. This dir must
# NEVER be added to src/library_dirs.LIBRARY_DIRS: the indexer would index the
# overlay as separate tiles and the optimiser would crush it back to 250 px.
# When the dir is absent/empty the overlay is a no-op and renders stay bit-
# identical to the pre-overlay behaviour (golden invariant).
HIRES_DIR = Path(__file__).resolve().parents[1] / "data" / "tiles_hires"

# Shapes whose sub7/block grouping was reviewed and approved (2026-07-05): the
# grout pass draws hierarchical L1/L2/L3 lines for these. Other shapes fall
# back to flat single-level grout (follow-up) or skip the pass.
GROUT_HIERARCHICAL = ("square", "hexagon", "triangle", "kites", "poincare")

# Must match EDGE_WEIGHT in indexer_smart.py.
EDGE_WEIGHT = 2.0


def _euclid_f32(chunk, feats, feat_sq):
    """Euclidean distances (float32) via the GEMM identity
    ||a||^2 + ||b||^2 - 2 a.b, computed in place to keep a single matrix resident.

    Drop-in for ``scipy.cdist(chunk, feats, 'euclidean')`` but without the float64
    promotion: ``chunk`` and ``feats`` must be float32, ``feat_sq`` the precomputed
    row-wise squared norm of ``feats``. For a 16K render vs ~455k tiles the per-chunk
    matrix drops from ~1.8 GB (cdist float64) to ~0.25 GB. Rankings are identical
    (sqrt is monotonic); the returned values are true euclidean distances, so the
    freq_penalty score downstream stays numerically equivalent (within float32).
    """
    d = chunk @ feats.T                                   # (rows, n_lib) float32
    d *= -2.0
    d += feat_sq[np.newaxis, :]
    d += np.einsum("ij,ij->i", chunk, chunk)[:, np.newaxis]
    np.maximum(d, 0.0, out=d)                             # guard tiny negatives
    np.sqrt(d, out=d)
    return d


class _LazyMask:
    """Deferred polygon mask for kite/spectre sectors.

    Each non-grid sector used to keep a fully rasterised "L" mask resident in
    sectors_data from build time until the composite pass — at 16K that is the
    dominant *resident* RAM cost (grid masks are shared references, so cheap).
    Storing the polygon instead and re-rasterising on demand cuts that to a
    handful of float pairs per sector.

    ``render()`` reproduces the original rasterisation byte-for-byte: kites draw
    at native resolution (``aa == 1``); spectres supersample by ``aa`` then
    downsample with LANCZOS (anti-aliased edge), exactly as the build pass did.
    The same render() output feeds both the feature computation and the final
    putalpha, so matching and pixels are unchanged.
    """

    __slots__ = ("poly", "bw", "bh", "aa")

    def __init__(self, poly, bw, bh, aa=1):
        self.poly = poly      # polygon in mask-local (unscaled) coordinates
        self.bw = bw
        self.bh = bh
        self.aa = aa

    def render(self):
        if self.aa == 1:
            m = Image.new("L", (self.bw, self.bh), 0)
            ImageDraw.Draw(m).polygon(self.poly, fill=255)
            return m
        m = Image.new("L", (self.bw * self.aa, self.bh * self.aa), 0)
        scaled = [(x * self.aa, y * self.aa) for (x, y) in self.poly]
        ImageDraw.Draw(m).polygon(scaled, fill=255)
        return m.resize((self.bw, self.bh), Image.Resampling.LANCZOS)


# ==========================================================================
# SHAPE REGISTRY  (single source of truth for the shape list + geometry)
# ==========================================================================
def _gen_kites(engine, target_w, target_h, base_s):
    """Yield per-kite polygons of the deltoidal trihexagonal grid, in image
    space (y down).

    Each hexagon on the flat-topped grid splits into 6 kites; every kite is its
    own sector. The (q, r, k) iteration order is a pure function of geometry, so
    preview and render stay reproducible (no RNG). The Cartesian kites are built
    y-up, filtered by their (unflipped) centroid, then each vertex is flipped to
    image space here — the y-flip stays inside the generator so `_polygon_sector`
    is orientation-agnostic (see PLAN_SHAPES.md Sprint 2, contract point 2).
    """
    s = base_s
    r3 = math.sqrt(3)
    range_q = int(target_w / (1.5 * s)) + 3
    range_r = int(target_h / (r3 * s)) + 3

    for q in range(-range_q, range_q):
        # centre the r-window on -q/2: cy = r3*s*(r + q/2), so a fixed window
        # scans a cy band displaced by q/2 at large |q| and leaves the far
        # corner without hexagons (black wedge bottom-right, fixed 2026-07-04)
        r_mid = -(q // 2)
        for r in range(r_mid - range_r, r_mid + range_r):
            cx = 1.5 * s * q
            cy = r3 * s * (r + q / 2.0)
            if -2 * s < cx < target_w + 2 * s and -2 * s < cy < target_h + 2 * s:
                for k in range(6):
                    poly = engine._get_kite_poly(cx, cy, s, k)
                    cent_x = sum(p[0] for p in poly) / 4
                    cent_y = sum(p[1] for p in poly) / 4
                    if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                        yield [(px, target_h - py) for px, py in poly]


def _gen_spectre(engine, target_w, target_h, base_s):
    """Yield the chiral aperiodic spectre monotiles as image-space polygons.

    `generate_spectre_tiling` already emits points in image space (y down), so
    the generator is a thin adaptor over it.
    """
    for spec in generate_spectre_tiling(target_w, target_h, base_s):
        yield list(spec.points)


# --- Phyllotaxis / Voronoi geometry (sunflower + rhombs family) ------------
# Ported from src/tools/gen_sunflower_schemes.py (the verified scheme geometry;
# PLAN_SHAPES.md: port it into the engine, do not reinvent). Only the GEOMETRY
# is ported -- the scheme's per-cell colour (vary/palette) is a scheme-only
# concern, so preview and render stay a pure function of (w, h, base_s), no RNG.
_GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))   # 137.508 deg


def _vogel_points(n_pts, c, power):
    """Vogel phyllotaxis lattice r = c*n**power, theta = n*golden angle.
    Returns a list of (x, y) tuples in world space (y up)."""
    idx = np.arange(1, n_pts + 1, dtype=np.float64)
    rr = c * idx ** power
    aa = idx * _GOLDEN_ANGLE
    return list(zip(rr * np.cos(aa), rr * np.sin(aa)))


def _clip_square(poly, R):
    """Sutherland-Hodgman clip of an (x, y) polygon to the square [-R, R]^2.
    Returns the clipped vertex list (possibly empty)."""
    def clip(pts, inside, inter):
        out = []
        m = len(pts)
        for i in range(m):
            a, b = pts[i], pts[(i + 1) % m]
            ina, inb = inside(a), inside(b)
            if ina:
                out.append(a)
                if not inb:
                    out.append(inter(a, b))
            elif inb:
                out.append(inter(a, b))
        return out

    def ix(a, b, t):
        (ax, ay), (bx, by) = a, b
        f = (t - ax) / (bx - ax)
        return (t, ay + f * (by - ay))

    def iy(a, b, t):
        (ax, ay), (bx, by) = a, b
        f = (t - ay) / (by - ay)
        return (ax + f * (bx - ax), t)

    pts = poly
    for inside, inter in (
        (lambda p: p[0] >= -R, lambda a, b: ix(a, b, -R)),
        (lambda p: p[0] <= R,  lambda a, b: ix(a, b, R)),
        (lambda p: p[1] >= -R, lambda a, b: iy(a, b, -R)),
        (lambda p: p[1] <= R,  lambda a, b: iy(a, b, R)),
    ):
        if not pts:
            return pts
        pts = clip(pts, inside, inter)
    return pts


def _voronoi_cells(pts, R=1.0):
    """Yield bounded Voronoi cells of `pts`, each clipped to [-R, R]^2 (>= 3
    vertices). Unbounded cells (generators past the corners) are skipped; the
    frame stays covered by their bounded neighbours."""
    vor = Voronoi(np.asarray(pts, dtype=np.float64))
    for i in range(len(pts)):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue
        poly = [tuple(vor.vertices[v]) for v in reg]
        cl = _clip_square(poly, R)
        if len(cl) >= 3:
            yield cl


def _poly_centroid(cl):
    """Area centroid of a simple (x, y) polygon; None if degenerate."""
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(cl, cl[1:] + cl[:1]):
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    if abs(a) < 1e-12:
        return None
    return (cx / (3 * a), cy / (3 * a))


def _lloyd_relax(pts, iters, clip=1.6, freeze_r=None):
    """Lloyd relaxation: move each generator to its Voronoi-cell centroid.
    Rounds seeds toward even 'pebbles' while the phyllotaxis spiral arms
    survive. Unbounded cells stay put.

    ``freeze_r`` (None to disable): points with max(|x|, |y|) >= freeze_r are
    held fixed. Used by the uniform-Voronoi shape to anchor its outer ring so
    frame-edge cells stay covered while the interior relaxes evenly. When None
    (the sunflower callers) the loop is bit-for-bit the original."""
    pts = np.asarray(pts, dtype=np.float64)
    frozen = (np.max(np.abs(pts), axis=1) >= freeze_r
              if freeze_r is not None else None)
    for _ in range(iters):
        vor = Voronoi(pts)
        new = pts.copy()
        for i in range(len(pts)):
            if frozen is not None and frozen[i]:
                continue
            reg = vor.regions[vor.point_region[i]]
            if not reg or -1 in reg:
                continue
            poly = [tuple(vor.vertices[v]) for v in reg]
            cl = _clip_square(poly, clip)
            if len(cl) < 3:
                continue
            cen = _poly_centroid(cl)
            if cen is not None:
                new[i] = cen
        pts = new
    return [tuple(p) for p in pts]


# Seed density: Vogel seeds reach r ~ 1.86 while the frame is [-1, 1], so only
# ~1/K of the seeds yield an in-frame cell. K compensates so the mean in-frame
# cell area stays ~ base_s^2 and tile_scale sizes cells like it sizes lattice
# tiles (the scheme's fixed N=1500 would be one huge cell per ~130 px at 16K).
# One constant across the whole family: the per-power spill differences only
# shift the mean cell size by ~+/-15%, which reads as the patterns' character.
_SUNFLOWER_CELL_DENSITY = 2.6


def _sunflower_n_seeds(target_w, target_h, base_s):
    """Seed count so the mean in-frame Voronoi cell area stays ~ base_s^2."""
    n = int(_SUNFLOWER_CELL_DENSITY * target_w * target_h / (base_s * base_s))
    return max(16, n)


def _emit_cells(pts, target_w, target_h, R=1.0):
    """Voronoi-partition `pts` and map each world-space [-R, R]^2 cell affinely
    onto the target rectangle, folding in the y-flip (world y up -> image y
    down). An affine image of a Voronoi diagram is still an exact partition, so
    the tessellation survives a non-square stretch."""
    sx = target_w / (2.0 * R)
    sy = target_h / (2.0 * R)
    for cl in _voronoi_cells(pts, R):
        yield [((x + R) * sx, (R - y) * sy) for x, y in cl]


def _graded_sunflower(target_w, target_h, base_s, power, lloyd_iters=0):
    """Shared body of the Vogel-lattice sunflowers: r = c*n^power seeds
    (optionally Lloyd-relaxed) -> Voronoi cells mapped to the frame. Fully
    deterministic (no RNG) so preview and render agree for equal dimensions."""
    n = _sunflower_n_seeds(target_w, target_h, base_s)
    c = (math.sqrt(2.0) + 0.45) / (n ** power)
    pts = _vogel_points(n, c, power=power)
    if lloyd_iters:
        pts = _lloyd_relax(pts, lloyd_iters)
    yield from _emit_cells(pts, target_w, target_h)


def _gen_sunflower_grande(engine, target_w, target_h, base_s):
    """Growth-graded head, r = c*n^0.66 (bigger seeds toward the rim)."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.66)


def _gen_sunflower_grande_xl(engine, target_w, target_h, base_s):
    """Steeper growth r = c*n^0.75: tiny centre, huge rim seeds."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.75)


def _gen_sunflower_grande_soft(engine, target_w, target_h, base_s):
    """grande geometry + 1 Lloyd pass: rounder cells, gentler size ramp."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.66,
                                 lloyd_iters=1)


def _gen_sunflower_grande_inverse(engine, target_w, target_h, base_s):
    """Reversed gradient r = c*n^0.40: large centre seeds shrinking to a
    fine rim."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.40)


def _gen_sunflower_soft(engine, target_w, target_h, base_s):
    """Classic uniform head (r = c*sqrt(n)) after 2 Lloyd passes: rounder,
    even 'pebble' seeds with the spiral arms preserved."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.5,
                                 lloyd_iters=2)


def _gen_sunflower_rings(engine, target_w, target_h, base_s):
    """Classic head with seed radii softly snapped into concentric courses,
    so the seeds line up in circular rows (reference photo look)."""
    n = _sunflower_n_seeds(target_w, target_h, base_s)
    c = (math.sqrt(2.0) + 0.45) / math.sqrt(n)
    d = 1.9 * c                                  # course (row) spacing
    pts = []
    for k in range(1, n + 1):
        rr = c * math.sqrt(k)
        row = int(rr / d)
        # 70% snap toward the row centre keeps courses visible without making
        # generators exactly co-circular (Voronoi stays numerically stable).
        rr = 0.7 * (d * (row + 0.5)) + 0.3 * rr
        aa = k * _GOLDEN_ANGLE
        pts.append((rr * math.cos(aa), rr * math.sin(aa)))
    yield from _emit_cells(pts, target_w, target_h)


def _gen_sunflower_disc(engine, target_w, target_h, base_s):
    """Two-zone head: fine disc florets in the centre, coarser seeds outside
    (real flower-head anatomy). K florets fill a disc of radius 0.42 at
    area-uniform spacing; the rim continues area-uniform but 1.7x coarser.
    K/N is fixed at ~1/7.5 so the two zones keep their proportion at any
    seed count."""
    n = _sunflower_n_seeds(target_w, target_h, base_s)
    disc_r = 0.42
    K = max(4, int(n / 7.487))
    c1 = disc_r / math.sqrt(K)
    c2 = 1.7 * c1
    pts = []
    for k in range(1, n + 1):
        if k <= K:
            rr = c1 * math.sqrt(k)
        else:
            rr = math.sqrt(disc_r ** 2 + c2 ** 2 * (k - K))
        aa = k * _GOLDEN_ANGLE
        pts.append((rr * math.cos(aa), rr * math.sin(aa)))
    yield from _emit_cells(pts, target_w, target_h)


# --- Log-spiral rhombus mesh (rhombs family) -------------------------------
# Ported from gen_sunflower_schemes. Seeds r = r0*exp(k*n), theta = n*golden
# angle give a SELF-SIMILAR quad mesh (every cell a rotated+scaled copy of its
# neighbour), so a fixed parastichy pair (F1, F2) stays embedded at every
# radius and the inner hole ALWAYS has F1+F2 boundary edges regardless of the
# density k. That invariant lets base_s scale k freely: the mesh densifies
# while the centre closures (funnel rings / star rosette), which only touch the
# F1+F2-edge boundary loop, stay valid. tile_scale is honoured by solving k so
# the in-frame cell count ~ frame_area / base_s^2 (count ~ 1/k^2).
def _emit_polys(polys, target_w, target_h, R=1.0):
    """Clip explicit world-space [-R, R]^2 polygons to the frame and map them
    affinely onto the target rectangle (y-flip folded in). Unlike _emit_cells
    these polygons are already a partition (mesh quads / closure cells), so no
    Voronoi step -- just clip + map."""
    sx = target_w / (2.0 * R)
    sy = target_h / (2.0 * R)
    for poly in polys:
        cl = _clip_square(poly, R)
        if len(cl) >= 3:
            yield [((x + R) * sx, (R - y) * sy) for x, y in cl]


def _log_quads(F1, F2, r0, k, N0, N, pole):
    """Self-similar mesh quads as world-space 4-vertex polygons (no loop)."""
    quads = []
    for n in range(N0, N + 1):
        pts = []
        for m in (n, n + F1, n + F1 + F2, n + F2):
            rr = r0 * math.exp(k * m)
            aa = m * _GOLDEN_ANGLE
            pts.append((pole[0] + rr * math.cos(aa), pole[1] + rr * math.sin(aa)))
        quads.append((n, pts))
    return quads


def _log_mesh(F1, F2, r0, k, N0, N, pole):
    """Return (quad_polys, loop): the mesh quads plus the ordered inner-boundary
    vertex loop (F1+F2 vertices walked CCW around the pole)."""
    quads = _log_quads(F1, F2, r0, k, N0, N, pole)
    edge_count = {}
    for _, q in quads:
        for a, b in zip(q, q[1:] + q[:1]):
            edge_count[tuple(sorted((a, b)))] = edge_count.get(tuple(sorted((a, b))), 0) + 1
    r_inner = r0 * math.exp(k * (N0 + F1 + F2)) * 1.25
    binner = {}
    for (a, b), cnt in edge_count.items():
        if cnt != 1:
            continue
        da = math.hypot(a[0] - pole[0], a[1] - pole[1])
        db = math.hypot(b[0] - pole[0], b[1] - pole[1])
        if da < r_inner and db < r_inner:
            binner.setdefault(a, []).append(b)
            binner.setdefault(b, []).append(a)
    start = next(iter(binner))
    loop, prev, cur = [start], None, start
    while True:
        nxt = [v for v in binner[cur] if v != prev][0]
        if nxt == start:
            break
        loop.append(nxt)
        prev, cur = cur, nxt
    area2 = sum(x1 * y2 - x2 * y1
               for (x1, y1), (x2, y2) in zip(loop, loop[1:] + loop[:1]))
    if area2 < 0:
        loop.reverse()
    return [q for _, q in quads], loop


def _group_loop(L, T):
    """Split L boundary edges into T contiguous groups of ~2 edges each."""
    sizes = [2] * T
    extra = L - 2 * T
    i = 0
    while extra != 0:
        step = 1 if extra > 0 else -1
        sizes[i % T] += step
        extra -= step
        i += 1
    bounds, acc = [], 0
    for s in sizes:
        bounds.append((acc, acc + s))
        acc += s
    return bounds


def _align_rot(anchors, T):
    """Rotation best aligning T uniformly spaced vertices with `anchors`."""
    step = 2 * math.pi / T
    sc = ss = 0.0
    for j, (x, y) in enumerate(anchors):
        d = math.atan2(y, x) - j * step
        sc += math.cos(d)
        ss += math.sin(d)
    return math.atan2(ss, sc)


def _circle_pts(T, radius, rot):
    step = 2 * math.pi / T
    return [(radius * math.cos(rot + j * step),
             radius * math.sin(rot + j * step)) for j in range(T)]


def _rosette(m, r_side, rot):
    """Rosette of m TRUE rhombi meeting at the pole (apex 2*pi/m, side r_side).
    Returns (cells, zigzag outer boundary of 2m vertices)."""
    step = 2 * math.pi / m
    S = [(r_side * math.cos(rot + j * step),
          r_side * math.sin(rot + j * step)) for j in range(m)]
    F = [(S[j][0] + S[(j + 1) % m][0], S[j][1] + S[(j + 1) % m][1])
         for j in range(m)]
    cells = [[(0.0, 0.0), S[j], F[j], S[(j + 1) % m]] for j in range(m)]
    zig = []
    for j in range(m):
        zig.extend((S[j], F[j]))
    return cells, zig


def _bridge(loop, target, bands=1):
    """Ring cells connecting the jagged mesh boundary `loop` to `target` (a
    polygon of len(target) vertices). Loop edges group ~2 per target edge;
    intermediate bands interpolate. Returns world-space polygons (no colour)."""
    L, T = len(loop), len(target)
    bounds = _group_loop(L, T)
    anchors = [loop[a] for a, _ in bounds]
    levels = []
    for lev in range(1, bands + 1):
        t = lev / bands
        levels.append([(ax + (zx - ax) * t, ay + (zy - ay) * t)
                       for (ax, ay), (zx, zy) in zip(anchors, target)])
    cells = []
    inner = levels[0]
    for j, (a, b) in enumerate(bounds):
        outer = [loop[kk % L] for kk in range(b, a - 1, -1)]
        cells.append([inner[j], inner[(j + 1) % T]] + outer)
    for lev in range(1, bands):
        out_pts, in_pts = levels[lev - 1], levels[lev]
        for j in range(T):
            cells.append([in_pts[j], in_pts[(j + 1) % T],
                          out_pts[(j + 1) % T], out_pts[j]])
    return cells


def _solve_k(build_count, n_target, k0, iters=4):
    """Solve for the log-mesh density k so the in-frame cell count ~ n_target,
    exploiting count ~ 1/k^2 (each Newton-ish step multiplies k by the sqrt of
    the count ratio). Converges in a few steps; guarded against empty meshes."""
    k = k0
    for _ in range(iters):
        c = build_count(k)
        if c <= 0:
            break
        k *= math.sqrt(c / n_target)
    return k


def _rhombs_n_target(target_w, target_h, base_s):
    return max(40, int(target_w * target_h / (base_s * base_s)))


def _count_in_frame(polys):
    return sum(1 for p in polys if len(_clip_square(p, 1.0)) >= 3)


def _gen_rhombs_nopole(engine, target_w, target_h, base_s):
    """Centre variant 1: the pole sits OUTSIDE the frame (nautilus precedent),
    so the frame holds nothing but proper mesh rhombi. Dense parastichy pair
    (34, 55) keeps the swirl visible far from the pole."""
    F1, F2, r0, pole = 34, 55, 0.055, (-1.35, -1.28)

    def mesh(k):
        N0 = int(math.log(0.30 / r0) / k) - (F1 + F2)
        N = int(math.log(3.7 / r0) / k)
        return _log_quads(F1, F2, r0, k, N0, N, pole)

    n_target = _rhombs_n_target(target_w, target_h, base_s)
    k = _solve_k(lambda kk: _count_in_frame([q for _, q in mesh(kk)]),
                 n_target, 0.0015)
    yield from _emit_polys([q for _, q in mesh(k)], target_w, target_h)


# Funnel/star share the tight (21, 34) mesh centred on the origin; the central
# hole is kept at a fixed world radius as k varies so the closure keeps scale.
_RH_F1, _RH_F2, _RH_r0 = 21, 34, 0.055
_RH_HOLE, _RH_OUTER = 0.34, math.sqrt(2.0) + 0.6


def _rh_mesh_k(k):
    N0 = int(math.log(_RH_HOLE / _RH_r0) / k) - (_RH_F1 + _RH_F2)
    N = int(math.log(_RH_OUTER / _RH_r0) / k)
    return _log_mesh(_RH_F1, _RH_F2, _RH_r0, k, N0, N, (0.0, 0.0))


def _rh_solve_k(target_w, target_h, base_s):
    n_target = _rhombs_n_target(target_w, target_h, base_s)

    def count(k):
        polys, _ = _rh_mesh_k(k)
        return _count_in_frame(polys)

    return _solve_k(count, n_target, 0.0042)


def _gen_rhombs_funnel(engine, target_w, target_h, base_s):
    """Centre variant 2: funnel of quad rings 28 -> 14 -> 7 (each ring halves
    the count so cells keep the mesh aspect) closed by one small 7-gon pole
    tile."""
    k = _rh_solve_k(target_w, target_h, base_s)
    polys, loop = _rh_mesh_k(k)
    r_mean = sum(math.hypot(*v) for v in loop) / len(loop)
    cells = list(polys)
    cur = loop
    for T, frac in [(28, 0.80), (14, 0.55), (7, 0.28)]:
        rot = _align_rot([cur[a] for a, _ in _group_loop(len(cur), T)], T)
        target = _circle_pts(T, frac * r_mean, rot)
        cells.extend(_bridge(cur, target, bands=1))
        cur = target
    cells.append(cur)                              # single pole tile (7-gon)
    yield from _emit_polys(cells, target_w, target_h)


def _gen_rhombs_star(engine, target_w, target_h, base_s):
    """Centre variant 3: rosette of 14 TRUE rhombi meeting at the pole, bridged
    to the mesh by two interpolated quad rings."""
    k = _rh_solve_k(target_w, target_h, base_s)
    polys, loop = _rh_mesh_k(k)
    r_mean = sum(math.hypot(*v) for v in loop) / len(loop)
    cells = list(polys)
    rot = _align_rot([loop[a] for a, _ in _group_loop(len(loop), 28)], 28)
    rosette, zig = _rosette(14, 0.36 * r_mean, rot)
    cells.extend(_bridge(loop, zig, bands=2))
    cells.extend(rosette)
    yield from _emit_polys(cells, target_w, target_h)


# --- Uniform Voronoi + canonical phyllotaxis (PLAN_SHAPES S5) ---------------
def _shape_seed(base_s, target_w, target_h):
    """Deterministic RNG seed from the render dimensions. The geometry is a
    pure function of (base_s, w, h): identical dims reproduce it exactly, while
    a preview at a different size gets its own stable tiling (same contract as
    spectre). NEVER seed from global random -- preview and render would drift."""
    return ((base_s * 73856093) ^ (target_w * 19349663)
            ^ (target_h * 83492791)) & 0x7FFFFFFF


def _gen_voronoi(engine, target_w, target_h, base_s):
    """Uniform random Voronoi: Lloyd-relaxed random seeds (even cells, no
    slivers). Seeds are generated past the [-1, 1] frame so every in-frame cell
    stays bounded (unbounded border cells are dropped). Cell count ~ frame area
    / base_s^2 so tile_scale sizes the cells."""
    n = max(16, int(target_w * target_h / (base_s * base_s)))
    margin = 1.30                                # generate past the frame edge
    n_gen = int(n * margin * margin)
    rng = np.random.default_rng(_shape_seed(base_s, target_w, target_h))
    pts = [tuple(p) for p in rng.uniform(-margin, margin, size=(n_gen, 2))]
    # Freeze the outer ring so frame-edge cells stay covered (no black slivers
    # at coarse cell counts); relax only the interior toward even cells.
    pts = _lloyd_relax(pts, iters=2, clip=margin, freeze_r=1.05)
    yield from _emit_cells(pts, target_w, target_h)


def _gen_phyllotaxis(engine, target_w, target_h, base_s):
    """Canonical golden-angle phyllotaxis: Voronoi of r = c*sqrt(n) Vogel seeds
    (area-uniform cells) with no relaxation, so the raw spiral courses stay
    crisp -- distinct from sunflower_soft (Lloyd-rounded) and _rings (snapped)."""
    yield from _graded_sunflower(target_w, target_h, base_s, power=0.5)


# --- Deterministic Fable tessellations (pinwheel/cairo/floret/gosper) -------
# Geometry ported from src/tools/gen_fable_shape_schemes.py (visually verified
# there; the scheme renderer maps world y straight to canvas y, i.e. y-down,
# so the coordinates below live directly in image space and the on-screen
# chirality matches the assets/shape_schemes PNGs). All four are pure
# constructions (no RNG): scale is chosen so the tile area ~ base_s^2 and the
# lattice ranges cover the frame; polygons sticking past the frame are cropped
# (or skipped) by _polygon_sector, exactly like the kites/spectre edge tiles.
def _lattice_mn_range(t1, t2, target_w, target_h, pad):
    """Index ranges (m0, m1, n0, n1) so lattice points m*t1 + n*t2 (complex,
    image px) cover the frame expanded by `pad` px on every side."""
    det = t1.real * t2.imag - t1.imag * t2.real
    ms, ns = [], []
    for c in (complex(-pad, -pad), complex(target_w + pad, -pad),
              complex(-pad, target_h + pad),
              complex(target_w + pad, target_h + pad)):
        ms.append((c.real * t2.imag - c.imag * t2.real) / det)
        ns.append((t1.real * c.imag - t1.imag * c.real) / det)
    return (math.floor(min(ms)), math.ceil(max(ms)),
            math.floor(min(ns)), math.ceil(max(ns)))


def _pin_sub(A, B, C):
    """Subdivide a 1:2:sqrt5 right triangle (right angle at A, |AB| = 2|AC|)
    into 5 similar copies (Conway-Radin substitution)."""
    d = C - B
    F = B + ((A - B).real * d.real + (A - B).imag * d.imag) / abs(d) ** 2 * d
    M1 = (A + F) / 2
    M2 = (F + B) / 2
    M3 = (A + B) / 2
    return [(F, A, C), (M1, M3, A), (M2, B, M3), (F, M2, M1), (M3, M1, M2)]


def _gen_pinwheel(engine, target_w, target_h, base_s):
    """Conway-Radin pinwheel: 1:2:sqrt5 right triangles subdivided until the
    short leg ~ base_s. The seed rectangle is tilted 13 degrees (scheme
    decision: new orientation classes emerge only at unrenderable depths, so
    the two dominant families are taken off-axis instead) and sized to cover
    the frame at any tilt. Fully-outside triangles are pruned DURING
    subdivision (children stay inside the parent), so the oversized seed
    patch never explodes the tile count."""
    ctr = complex(target_w / 2.0, target_h / 2.0)
    R = math.hypot(target_w, target_h) / 2.0 + 2.0 * base_s
    L = 2.0 * R                     # 2L x L rect centred on ctr covers radius R
    rot = cmath.exp(1j * math.radians(13))

    def _t(z):                      # seed-rect coords -> tilted image coords
        return ctr + (z - complex(L, L / 2.0)) * rot

    tris = [(_t(0j), _t(complex(2 * L, 0)), _t(complex(0, L))),
            (_t(complex(2 * L, L)), _t(complex(0, L)), _t(complex(2 * L, 0)))]
    depth = max(1, round(math.log(L / base_s) / math.log(math.sqrt(5.0))))
    pad = float(base_s)
    for _ in range(depth):
        nxt = []
        for (A, B, C) in tris:
            if (max(A.real, B.real, C.real) < -pad
                    or min(A.real, B.real, C.real) > target_w + pad
                    or max(A.imag, B.imag, C.imag) < -pad
                    or min(A.imag, B.imag, C.imag) > target_h + pad):
                continue
            nxt += _pin_sub(A, B, C)
        tris = nxt
    for (A, B, C) in tris:
        yield [(A.real, A.imag), (B.real, B.imag), (C.real, C.imag)]


def _gen_cairo(engine, target_w, target_h, base_s):
    """Cairo pentagonal tiling: 4 congruent equilateral-parameter pentagons
    around every (i+j even) node of a unit square lattice. Pentagon area is
    1/2 lattice unit, so scale s = base_s*sqrt(2) keeps tile area ~ base_s^2."""
    d = (math.sqrt(7.0) - 1.0) / 6.0
    s = base_s * math.sqrt(2.0)
    ni = int(target_w / s) + 2
    nj = int(target_h / s) + 2
    for i in range(-2, ni + 1):
        for j in range(-2, nj + 1):
            if (i + j) % 2 != 0:
                continue
            v1 = (i + .5, j + .5 - d)
            v2 = (i + .5, j + .5 + d)
            w1r = (i + 1.5 - d, j + .5)   # right neighbour pair, left point
            w2l = (i - 0.5 + d, j + .5)   # left neighbour pair, right point
            p1u = (i + .5 - d, j + 1.5)   # upper neighbour pair
            p2u = (i + .5 + d, j + 1.5)
            q1d = (i + .5 - d, j - .5)    # lower neighbour pair
            q2d = (i + .5 + d, j - .5)
            pents = [
                [v1, (i + 1, j), w1r, (i + 1, j + 1), v2],           # right
                [(i, j), v1, v2, (i, j + 1), w2l],                   # left
                [v2, (i + 1, j + 1), p2u, p1u, (i, j + 1)],          # up
                [v1, (i, j), q1d, q2d, (i + 1, j)],                  # down
            ]
            for p in pents:
                yield [(x * s, y * s) for x, y in p]


def _gen_floret(engine, target_w, target_h, base_s):
    """Floret pentagonal (dual snub hexagonal): 6-petal pinwheel flowers on a
    hex lattice. Petal area is ~1.01 lattice units, so scale s = base_s."""
    s = float(base_s)
    petal = [0j, complex(1, 1 / math.sqrt(3)),
             complex(1.5, 0.5 / math.sqrt(3)),
             complex(1.5, -0.5 / math.sqrt(3)),
             complex(1, -1 / math.sqrt(3))]
    t1 = complex(2.5, math.sqrt(3) / 2) * s
    t2 = complex(2.0, -math.sqrt(3)) * s
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h,
                                       pad=2.0 * s)   # flower radius ~1.8 units
    rots = [cmath.exp(1j * math.pi / 3 * k) for k in range(6)]
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            centre = m * t1 + n * t2
            for rot in rots:
                yield [((centre + v * rot * s).real,
                        (centre + v * rot * s).imag) for v in petal]


def _gosper_edge(a, b, depth):
    """Replace segment a->b with the Gosper island generator, recursively."""
    if depth == 0:
        return [a]
    v = b - a
    r = 1 / math.sqrt(7.0)
    m1 = r * cmath.exp(1j * math.radians(19.1066))
    m2 = r * cmath.exp(1j * math.radians(-40.8934))
    p1 = a + v * m1
    p2 = p1 + v * m2
    return (_gosper_edge(a, p1, depth - 1)
            + _gosper_edge(p1, p2, depth - 1)
            + _gosper_edge(p2, b, depth - 1))


def _gen_gosper(engine, target_w, target_h, base_s):
    """Gosper islands (hexflake): hexagons with a depth-3 fractal boundary
    (162-gon) on the triangular lattice they tile. Island area equals the
    base hexagon's (3*sqrt(3)/2 units), so s = base_s/sqrt(3*sqrt(3)/2)
    keeps tile area ~ base_s^2."""
    s = base_s / math.sqrt(1.5 * math.sqrt(3.0))
    hexv = [cmath.exp(1j * math.radians(30 + 60 * k)) for k in range(6)]
    island = []
    for k in range(6):
        island += _gosper_edge(hexv[k], hexv[(k + 1) % 6], 3)
    t1 = complex(math.sqrt(3.0), 0) * s
    t2 = complex(math.sqrt(3.0) / 2, 1.5) * s
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h,
                                       pad=1.5 * s)   # boundary bulge ~1.2 units
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            centre = m * t1 + n * t2
            yield [((centre + p * s).real, (centre + p * s).imag)
                   for p in island]


# --- Archimedean tessellations + sunburst (rebuilt from the scheme PNGs) ----
# The original Opus scratchpad for these five was lost; only the approved
# assets/shape_schemes PNGs remained, so the geometry below is a fresh
# derivation matched visually against those PNGs (orientation, proportions).
# Same conventions as the Fable four: image space y-down, tile area ~ base_s^2
# (keyed to the DOMINANT tile of mixed tilings), pure constructions (no RNG).
def _gen_trunc_square(engine, target_w, target_h, base_s):
    """Truncated square tiling 4.8.8: axis-aligned regular octagons on a
    square lattice + 45deg-rotated squares in the gaps. Octagon area
    2(1+sqrt2)a^2 = base_s^2; lattice pitch = octagon across-flats a(1+sqrt2)."""
    a = base_s / math.sqrt(2.0 + 2.0 * math.sqrt(2.0))
    p = a * (1.0 + math.sqrt(2.0))
    r8 = a / (2.0 * math.sin(math.pi / 8.0))
    oct_pts = [(r8 * math.cos(math.radians(22.5 + 45.0 * k)),
                r8 * math.sin(math.radians(22.5 + 45.0 * k))) for k in range(8)]
    hs = a / math.sqrt(2.0)          # gap square: vertices on the axes
    sq_pts = [(hs, 0.0), (0.0, hs), (-hs, 0.0), (0.0, -hs)]
    ni = int(target_w / p) + 2
    nj = int(target_h / p) + 2
    for i in range(-1, ni):
        for j in range(-1, nj):
            cx, cy = i * p, j * p
            yield [(cx + x, cy + y) for x, y in oct_pts]
            cx, cy = cx + p / 2.0, cy + p / 2.0
            yield [(cx + x, cy + y) for x, y in sq_pts]


def _gen_trunc_hex(engine, target_w, target_h, base_s):
    """Truncated hexagonal tiling 3.12.12: regular dodecagons on a triangular
    lattice + upward/downward triangles in the two per-cell holes. Dodecagon
    area 3(2+sqrt3)a^2 = base_s^2; pitch = across-flats a(2+sqrt3). Triangle
    vertices sit at hole_centre + (a/sqrt3) in the directions worked out from
    the shared dodecagon edges (see the hole-angle derivation in the tests)."""
    a = base_s / math.sqrt(3.0 * (2.0 + math.sqrt(3.0)))
    p = a * (2.0 + math.sqrt(3.0))
    t1 = complex(p, 0.0)
    t2 = complex(p / 2.0, p * math.sqrt(3.0) / 2.0)
    r12 = a / (2.0 * math.sin(math.pi / 12.0))
    dodec = [(r12 * math.cos(math.radians(15.0 + 30.0 * k)),
              r12 * math.sin(math.radians(15.0 + 30.0 * k))) for k in range(12)]
    rt = a / math.sqrt(3.0)
    tri_up = [(rt * math.cos(math.radians(t)), rt * math.sin(math.radians(t)))
              for t in (30.0, 150.0, 270.0)]
    tri_dn = [(rt * math.cos(math.radians(t)), rt * math.sin(math.radians(t)))
              for t in (90.0, 210.0, 330.0)]
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h, pad=p)
    h1 = (t1 + t2) / 3.0
    h2 = 2.0 * (t1 + t2) / 3.0
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            c = m * t1 + n * t2
            yield [(c.real + x, c.imag + y) for x, y in dodec]
            yield [((c + h1).real + x, (c + h1).imag + y) for x, y in tri_up]
            yield [((c + h2).real + x, (c + h2).imag + y) for x, y in tri_dn]


def _gen_rhombitrihex(engine, target_w, target_h, base_s):
    """Rhombitrihexagonal tiling 3.4.6.4: hexagons + squares on every hex
    edge + triangles in the holes. Hexagon area (3sqrt3/2)a^2 = base_s^2;
    pitch a(1+sqrt3). Scheme orientation: flat-top hexagons (squares sit on
    the horizontal edges), i.e. lattice neighbours at 30/90/150 degrees."""
    a = base_s / math.sqrt(1.5 * math.sqrt(3.0))
    p = a * (1.0 + math.sqrt(3.0))
    t1 = p * cmath.exp(1j * math.radians(30.0))
    t2 = p * cmath.exp(1j * math.radians(90.0))
    hex_pts = [a * cmath.exp(1j * math.radians(60.0 * k)) for k in range(6)]
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h, pad=p)
    h1 = (t1 + t2) / 3.0
    h2 = 2.0 * (t1 + t2) / 3.0
    sq_dirs = [cmath.exp(1j * math.radians(t)) for t in (30.0, 90.0, 150.0)]
    rot30p = cmath.exp(1j * math.radians(30.0))
    rot30m = cmath.exp(1j * math.radians(-30.0))
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            c = m * t1 + n * t2
            yield [((c + v).real, (c + v).imag) for v in hex_pts]
            # one square per shared edge, emitted from the lower-index side
            for d in sq_dirs:
                nb = c + p * d
                quad = [c + a * d * rot30m, c + a * d * rot30p,
                        nb - a * d * rot30m, nb - a * d * rot30p]
                yield [(z.real, z.imag) for z in quad]
            # triangles: one vertex contributed by each of the 3 hexagons
            # around the hole (the hex vertex pointing at the hole centre)
            for h, offs in ((c + h1, (c, c + t1, c + t2)),
                            (c + h2, (c + t1, c + t2, c + t1 + t2))):
                tri = [nb + a * (h - nb) / abs(h - nb) for nb in offs]
                yield [(z.real, z.imag) for z in tri]


def _multigrid_dual(N, zeta, gamma, target_w, target_h, s):
    """De Bruijn multigrid dual -> aperiodic rhombic tiling, unit edge scaled
    to `s` px, centred on the frame centre (image space, no flip — the scheme
    tool rendered y-down too). Ported from the validated gen_ammann_beenker
    construction (incl. its Cramer solution — the sign convention there is the
    documented multigrid trap; do not rederive).

    Every grid-line intersection (k,l,m,n) duals to one rhomb at ~(N/2)*p
    (the standard sum identity for symmetric star vectors), so the p-window is
    the frame rect shrunk by N/2 (+2 units slack) and the line indices only
    need to reach the window's diagonal — that bound is what makes 16K frames
    iterate in ~1e5 intersections instead of ~1e6."""
    cx, cy = target_w / 2.0, target_h / 2.0
    hw = cx / s + 1.5                    # world half-extents (+ tile pad)
    hh = cy / s + 1.5
    dual = N / 2.0
    pw = hw / dual + 2.0                 # p-window half-extents
    ph = hh / dual + 2.0
    mrange = int(math.hypot(pw, ph)) + 2
    for k in range(N):
        ak = zeta[k].conjugate()
        for l in range(k + 1, N):
            al = zeta[l].conjugate()
            det = ak.real * al.imag - ak.imag * al.real
            if abs(det) < 1e-12:
                continue
            for m in range(-mrange, mrange + 1):
                bk = m + gamma[k]
                for n in range(-mrange, mrange + 1):
                    bl = n + gamma[l]
                    px = (bk * al.imag - bl * ak.imag) / det
                    py = (bk * al.real - bl * ak.real) / det
                    if abs(px) > pw or abs(py) > ph:
                        continue
                    p = complex(px, py)
                    K = [0] * N
                    for j in range(N):
                        if j == k or j == l:
                            continue
                        K[j] = math.ceil((p * zeta[j].conjugate()).real
                                         - gamma[j])
                    basev = sum(K[j] * zeta[j] for j in range(N)
                                if j not in (k, l))
                    verts = [basev + (m + a) * zeta[k] + (n + b) * zeta[l]
                             for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
                    xs = [v.real for v in verts]
                    ys = [v.imag for v in verts]
                    if (max(xs) < -hw or min(xs) > hw
                            or max(ys) < -hh or min(ys) > hh):
                        continue
                    yield [(cx + v.real * s, cy + v.imag * s) for v in verts]


def _gen_ammann_beenker(engine, target_w, target_h, base_s):
    """Ammann-Beenker (8-fold): squares + 45deg rhombs, multigrid N=4.
    Mean tile area ~0.83*edge^2 -> edge = 1.1*base_s."""
    zeta = [cmath.exp(1j * math.pi * k / 4) for k in range(4)]
    gamma = [0.13, 0.27, 0.41, 0.19]     # validated generic offsets (scheme)
    yield from _multigrid_dual(4, zeta, gamma, target_w, target_h,
                               1.1 * base_s)


def _gen_penrose(engine, target_w, target_h, base_s):
    """Penrose P3 (5-fold): fat 72deg + thin 36deg rhombs, pentagrid N=5.
    gamma sums to 1.0 (the canonical class). Mean tile area ~0.81*edge^2."""
    zeta = [cmath.exp(2j * math.pi * k / 5) for k in range(5)]
    gamma = [0.05, 0.15, 0.25, 0.35, 0.20]
    yield from _multigrid_dual(5, zeta, gamma, target_w, target_h,
                               1.1 * base_s)


_PHI = (1 + math.sqrt(5)) / 2


def _p3_half_deflate(tris):
    """One P3 Robinson-triangle deflation step (Preshing scheme).

    (colour, A, B, C): 0 = half-THIN rhomb (acute 36-72-72, apex A, legs
    AB=AC=L, base BC=L/phi), 1 = half-FAT rhomb (gnomon 36-36-108, apex A,
    legs AB=AC=L, base BC=L*phi). Every child leg is a fixed fraction of a
    parent leg, so edge split points agree across parent boundaries -- this
    is why the P3 route is used instead of a hand-derived P2 substitution,
    which produced T-junctions in two earlier attempts (2026-07-04).
    """
    out = []
    for colour, A, B, C in tris:
        if colour == 0:
            P = A + (B - A) / _PHI
            out += [(0, C, P, B), (1, P, C, A)]
        else:
            Q = B + (A - B) / _PHI
            R_ = B + (C - B) / _PHI
            out += [(1, R_, C, A), (1, Q, R_, B), (0, R_, Q, A)]
    return out


def _gen_penrose_p2(engine, target_w, target_h, base_s):
    """Penrose P2 (5-fold): whole KITES and DARTS -- deliberately distinct
    from `penrose`, which is P3 rhombs from the pentagrid.

    P2 and P3 are mutually locally derivable via Robinson A/B-tiles
    (BS = AL, BL = AL + AS): deflate the P3 'sun', then convert B-halves to
    A-halves -- every half-thin IS a half-kite; every half-fat splits at U
    (|BU| = leg) into half-kite + half-dart. That cut direction is the one
    consistent with the P2 matching rules; the mirror cut |CU| leaves 410
    unmatched halves. Halves merge into whole tiles by mirror-twin matching
    (same kind + shared leg + common apex); matching degree-1 vertices first
    resolves the even cycles at sun/star vertices. Exact edge-to-edge
    partition: no gaps, no overlaps, no background.

    Depth follows base_s rather than being fixed: the sun must cover the
    frame (its decagon inradius is Rd*cos(pi/10)), and ceil() on the depth
    keeps the leg exact while never under-covering. Triangles are pruned
    against the frame after every deflation -- children stay inside their
    parent, so dropping a parent that misses the frame is safe and keeps the
    tile count proportional to the frame, not to the whole sun.

    Mean tile area over the kite/dart mix is leg^2/2, so the leg is
    base_s*sqrt(2) to honour the registry-wide convention that a cell
    averages base_s^2 (measured: penrose 3536, cairo 3600 at base_s=60).

    ⚠ Halves with no twin are dropped, and every boundary creates them --
    both the sun's own rim and the prune box. The scheme could ignore this
    (sun 2.2 vs a drawn square reaching 1.41), but sizing the sun to *just*
    cover the frame puts that unmatched rim inside it: a 3 px coverage
    margin left a 42 px band of holes along one edge. Hence PRUNE_LEGS
    (rim lands well outside the frame) > CULL_LEGS (keep tiles overlapping
    the frame edge), and the sun must cover the prune box, not the frame.
    """
    Rd = 2.2
    PRUNE_LEGS, CULL_LEGS = 3.0, 1.0
    leg = base_s * math.sqrt(2.0)
    cos10 = math.cos(math.pi / 10)
    prune_pad = PRUNE_LEGS * leg
    half_diag = math.hypot(target_w / 2.0 + prune_pad, target_h / 2.0 + prune_pad)
    k_min = half_diag / (Rd * cos10)
    depth = max(1, math.ceil(math.log(k_min * Rd / leg) / math.log(_PHI)))
    k = leg * _PHI ** depth / Rd

    # prune box (generous) and cull box (tight), both in scheme units
    hw = (target_w / 2.0 + prune_pad) / k
    hh = (target_h / 2.0 + prune_pad) / k
    cw = (target_w / 2.0 + CULL_LEGS * leg) / k
    ch = (target_h / 2.0 + CULL_LEGS * leg) / k

    def _hits_frame(A, B, C):
        return not (min(A.real, B.real, C.real) > hw or
                    max(A.real, B.real, C.real) < -hw or
                    min(A.imag, B.imag, C.imag) > hh or
                    max(A.imag, B.imag, C.imag) < -hh)

    tris = []
    for i in range(10):
        B = cmath.rect(Rd, (2 * i - 1) * math.pi / 10)
        C = cmath.rect(Rd, (2 * i + 1) * math.pi / 10)
        if i % 2 == 0:
            B, C = C, B          # mirror alternate halves -> consistent pairs
        tris.append((0, 0j, B, C))
    for _ in range(depth):
        tris = _p3_half_deflate(tris)
        tris = [t for t in tris if _hits_frame(t[1], t[2], t[3])]

    # B-tiles -> A-tiles: 0 = AL half-kite, 1 = AS half-dart
    a_tiles = []
    for colour, A, B, C in tris:
        if colour == 0:
            a_tiles.append((0, A, B, C))
        else:
            U = B + (C - B) / _PHI
            a_tiles.append((0, B, A, U))
            a_tiles.append((1, U, C, A))

    def rp(z):
        return (round(z.real, 6), round(z.imag, 6))

    cand = {}
    for idx, (kind, A, B, C) in enumerate(a_tiles):
        for other in (B, C):
            cand.setdefault((kind,) + tuple(sorted((rp(A), rp(other)))), []).append(idx)
    alive = {}
    for ids in cand.values():
        if len(ids) == 2:
            i, j = ids
            if rp(a_tiles[i][1]) == rp(a_tiles[j][1]):
                alive.setdefault(i, set()).add(j)
                alive.setdefault(j, set()).add(i)
    pairs = []

    def commit(i, j):
        pairs.append((i, j))
        for x in (i, j):
            for nb in alive.pop(x, set()):
                if nb in alive:
                    alive[nb] -= {i, j}

    while alive:
        deg1 = [i for i, ps in alive.items() if len(ps) == 1]
        if deg1:
            i = deg1[0]
            commit(i, next(iter(alive[i])))
            continue
        iso = [i for i, ps in alive.items() if not ps]
        if iso:
            for i in iso:
                alive.pop(i)
            continue
        i = next(iter(alive))    # only sun/star cycles remain: any choice valid
        commit(i, next(iter(alive[i])))

    cx, cy = target_w / 2.0, target_h / 2.0
    for i, j in pairs:
        kind, A, B, C = a_tiles[i]
        pts_j = {rp(a_tiles[j][1]), rp(a_tiles[j][2]), rp(a_tiles[j][3])}
        X = B if rp(B) in pts_j else C            # shared leg = tile axis
        t1 = C if X is B else B
        t2 = next(v for v in a_tiles[j][2:] if rp(v) not in (rp(A), rp(X)))
        ctr = (A + X) / 2
        if abs(ctr.real) > cw or abs(ctr.imag) > ch:
            continue
        yield [(cx + k * v.real, cy + k * v.imag) for v in (A, t1, X, t2)]


def _gen_pythagorean(engine, target_w, target_h, base_s):
    """Pythagorean tiling: axis-aligned big (b) and small (b/2) squares in the
    classic staircase pattern, lattice t1=(b, s), t2=(-s, b). Mean tile area
    (b^2 + s^2)/2 = base_s^2 -> b = base_s*sqrt(8/5)."""
    b = base_s * math.sqrt(8.0 / 5.0)
    s = b / 2.0
    t1 = complex(b, s)
    t2 = complex(-s, b)
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h, pad=b + s)
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            c = m * t1 + n * t2
            yield [(c.real, c.imag), (c.real + b, c.imag),
                   (c.real + b, c.imag + b), (c.real, c.imag + b)]
            # the s x s hole between the four big squares at c, c+t1, c+t2,
            # c+t1+t2 is exactly [b-s, b] x [b, b+s] relative to c
            yield [(c.real + b - s, c.imag + b), (c.real + b, c.imag + b),
                   (c.real + b, c.imag + b + s), (c.real + b - s, c.imag + b + s)]


def _sun_arc(r, a0, a1, cx, cy, seg_px):
    """Polygonised arc from angle a0 to a1 at radius r (image-space points).
    The segment pitch is fixed in px, so the sagitta of every chord stays
    sub-pixel and abutting rings rasterise without visible slivers even
    though their chord endpoints differ (T-junctions on ring arcs, the
    accepted voderberg precedent)."""
    n = max(2, int(abs(a1 - a0) * r / seg_px) + 1)
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n),
             cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def _gen_sunburst(engine, target_w, target_h, base_s):
    """Sunburst: log-polar grid about the frame centre — a constant sector
    count with geometric ring radii gives ~square, self-similar cells whose
    radial seams line up into rays; a constant extra twist per ring bends the
    rays into gentle spirals (the scheme's look). The pole is closed by a
    small wedge fan (same-shape cells meeting at the centre, per the approved
    'good centre' pattern). tile_scale sets the cell size at mid-radius."""
    cx, cy = target_w / 2.0, target_h / 2.0
    r_max = math.hypot(cx, cy) * 1.01
    nsec = max(12, round(2.0 * math.pi * (0.45 * r_max) / base_s))
    g = 1.0 + 2.0 * math.pi / nsec              # square cells: dr = arc
    seg = max(4.0, base_s / 3.0)
    twist = -0.18 * (2.0 * math.pi / nsec)      # per-ring twist: rays stay
    # readable as continuous spokes but bend into gentle log-spirals
    # (negative = counter-clockwise lean, matching the approved scheme)
    cap_r = 1.6 * base_s
    radii = [r_max]
    while radii[-1] / g > cap_r:
        radii.append(radii[-1] / g)
    for k in range(len(radii) - 1):
        r_out, r_in = radii[k], radii[k + 1]
        base_a = k * twist
        for i in range(nsec):
            a0 = base_a + 2.0 * math.pi * i / nsec
            a1 = a0 + 2.0 * math.pi / nsec
            yield (_sun_arc(r_in, a0, a1, cx, cy, seg)
                   + _sun_arc(r_out, a1, a0, cx, cy, seg))
    ncap = 7                                    # odd: no seam lock with ring 1
    base_a = (len(radii) - 1) * twist
    r_in = radii[-1]
    for i in range(ncap):
        a0 = base_a + 2.0 * math.pi * i / ncap
        a1 = a0 + 2.0 * math.pi / ncap
        yield [(cx, cy)] + _sun_arc(r_in, a0, a1, cx, cy, seg)


# --- Voderberg / escher_lizard / weave (last three Fable shapes) -----------
# voderberg + escher_lizard are ported straight from gen_fable_shape_schemes.py
# (image space, y-down, so the on-screen chirality matches the scheme PNGs);
# only the hard-coded scheme scale is replaced by a base_s-driven one.
def _gen_voderberg(engine, target_w, target_h, base_s):
    """Voderberg-style spiral of bent slivers: concentric rings about the frame
    centre, each ring split into its OWN wedge count (~2*pi*r_mid / tangential
    size), so cells keep a constant size at every radius and the centre is a
    ring of same-shaped slivers converging at the pole (the approved 'good
    centre' pattern; ring 0 starts at r = 0, so `arc_in` is empty there).

    Two scheme constants must become radius-relative in the engine, or they
    break at frame scale: the radial edge bow was a fixed 5 deg (its lateral
    size would then grow with r and the slivers would flatten into arcs), and
    the ring radii were a fixed list. Here the ring thickness is constant
    (sqrt(2)*base_s) and the bow is a fixed fraction of it, giving ~2:1 slivers
    of area ~ base_s^2 everywhere. The two radial edges of a wedge are the same
    curve shifted by one angular step, so they can never cross.

    Ring boundaries are circles shared by rings with different wedge counts ->
    T-junctions on the arcs, which is fine for a partition (the sunburst /
    sierpinski-row precedent) as long as both sides polygonise the arc with the
    same sub-pixel pitch: `_sun_arc`.
    """
    cx, cy = target_w / 2.0, target_h / 2.0
    r_max = math.hypot(cx, cy) * 1.02
    tang = base_s / math.sqrt(2.0)          # tangential cell size
    thick = base_s * math.sqrt(2.0)         # radial ring thickness (2:1 sliver)
    seg = max(4.0, base_s / 3.0)
    nseg = max(6, int(thick / seg) + 1)     # radial edge polyline steps
    base_off = 0.0
    for m in range(int(math.ceil(r_max / thick))):
        rin, rout = m * thick, (m + 1) * thick
        r_mid = (rin + rout) / 2.0
        nw = max(8, int(round(2.0 * math.pi * r_mid / tang)))
        step = 2.0 * math.pi / nw
        twist = step / 2.0                  # spiral shear, accumulates per ring
        bow = min(0.5, 0.35 * thick / r_mid)

        def radial(a):
            pts = []
            for i in range(nseg + 1):
                t = i / nseg
                r = rin + (rout - rin) * t
                th = a + twist * t + bow * math.sin(math.pi * t)
                pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
            return pts

        for k in range(nw):
            a0 = base_off + k * step
            a1 = a0 + step
            arc_out = _sun_arc(rout, a0 + twist, a1 + twist, cx, cy, seg)[1:-1]
            arc_in = ([] if rin == 0.0
                      else _sun_arc(rin, a1, a0, cx, cy, seg)[1:-1])
            yield radial(a0) + arc_out + list(reversed(radial(a1))) + arc_in
        base_off += twist


def _gen_escher(engine, target_w, target_h, base_s):
    """Escher-style p1 'critter': a unit hexagon whose three independent edges
    are deformed by a wavy polyline and copied, reversed and translated, onto
    the three opposite edges (Conway criterion, translations only) -> an exact
    tiling on the hex lattice. The deformation is area-preserving in the sense
    that matters here: every tile is one lattice cell, so its area is the
    hexagon's (3*sqrt(3)/2 units) and s = base_s / sqrt(3*sqrt(3)/2)."""
    s = base_s / math.sqrt(1.5 * math.sqrt(3.0))
    h = [cmath.exp(1j * math.radians(30 + 60 * k)) for k in range(6)]
    off0 = [0.05, 0.20, 0.31, 0.29, 0.13, -0.09, -0.05]   # round head + neck dip
    off1 = [0.13, -0.09, 0.17, -0.11, 0.11, -0.05]        # two stubby legs
    off2 = [-0.09, -0.22, -0.15, 0.09, 0.25, 0.13]        # tail swoosh

    def wavy(a, b, offsets):
        v = b - a
        n = v * 1j                      # left normal
        m = len(offsets) + 1
        return [a + v * (i / m) + n * off for i, off in enumerate(offsets, 1)]

    e0 = [h[0]] + wavy(h[0], h[1], off0)
    e1 = [h[1]] + wavy(h[1], h[2], off1)
    e2 = [h[2]] + wavy(h[2], h[3], off2)
    # each opposite edge = its partner reversed, translated by -(sum of the
    # partner's endpoints): h[0]-(h[0]+h[1]) = -h[1] = h[4], etc.
    boundary = e0 + e1 + e2
    boundary += [z - (h[0] + h[1]) for z in reversed(e0 + [h[1]])][:-1]
    boundary += [z - (h[1] + h[2]) for z in reversed(e1 + [h[2]])][:-1]
    boundary += [z - (h[2] + h[3]) for z in reversed(e2 + [h[3]])][:-1]

    t1 = complex(math.sqrt(3.0), 0) * s
    t2 = complex(math.sqrt(3.0) / 2, 1.5) * s
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h,
                                       pad=2.0 * s)   # critter bulge ~1.35 units
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            c = m * t1 + n * t2
            yield [((c + z * s).real, (c + z * s).imag) for z in boundary]


def _gen_weave(engine, target_w, target_h, base_s):
    """Plain over/under basketweave, rebuilt as a TRUE partition.

    The scheme (gen_fable_shape_schemes.gen_weave, rev 2026-07-13) drew whole
    ribbon cells and faked the interlacing by paint order: crossing squares were
    painted twice and the gaps between four ribbons stayed background. Both are
    illegal in the engine (overlapping sectors = two photos fighting for the
    same pixels; holes = black squares), so the cells are the VISIBLE pieces:

      * ribbon width w = 0.74 * pitch; a ribbon is hidden exactly at its
        under-crossings, so its visible piece runs from one under-crossing to
        the next -> a w x (2*pitch - w) rectangle centred on the over-crossing
        it covers. Parity (i + j) % 2 decides which ribbon is on top, so every
        crossing square is claimed exactly once.
      * the (pitch - w)^2 square left between four ribbons becomes a 'knot'
        cell of its own (the small tile of a mixed tiling, as in rhombitrihex).

    Dominant tile = the ribbon cell, area w*(2*pitch - w) = 0.9324*pitch^2, so
    pitch = base_s / sqrt(0.9324) keeps it at ~ base_s^2.
    """
    pitch = base_s / math.sqrt(0.9324)
    w = 0.74 * pitch
    half = w / 2.0
    arm = pitch - half                  # cell half-length along the ribbon
    ni = int(target_w / pitch) + 3
    nj = int(target_h / pitch) + 3
    for i in range(-1, ni):
        for j in range(-1, nj):
            xc, yc = i * pitch, j * pitch
            if (i + j) % 2 == 1:        # vertical ribbon on top here
                yield [(xc - half, yc - arm), (xc + half, yc - arm),
                       (xc + half, yc + arm), (xc - half, yc + arm)]
            else:                       # horizontal ribbon on top here
                yield [(xc - arm, yc - half), (xc + arm, yc - half),
                       (xc + arm, yc + half), (xc - arm, yc + half)]
            # knot: the square gap between the four ribbons up-right of (i, j)
            yield [(xc + half, yc + half), (xc + pitch - half, yc + half),
                   (xc + pitch - half, yc + pitch - half),
                   (xc + half, yc + pitch - half)]


# --- Truchet (square + hex) ------------------------------------------------
# PLAN_SHAPES listed these as "Tier B" needing a curved-mask class; the
# 2026-07-11 review dropped that (see MEMORY): an arc polygonised with a
# sub-pixel sagitta and aa=4 in _LazyMask rasterises like a true curve, and
# `_sun_arc` already does exactly that for sunburst/voderberg. So a Truchet
# tile is an ordinary `polygon` shape: the arcs cut each square/hexagon into
# cells, and neighbouring cells that share an arc call `_sun_arc` with the SAME
# arguments, so the shared boundary is sampled identically (exact partition).
#
# Orientation is NOT drawn from an RNG: it is a hash of the lattice index, so
# the same cell gets the same orientation at every resolution -- the preview
# shows the pattern the 16K render will have ("the same pattern, just more of
# it", the girih seed lesson), and the shape stays reproducible bit-for-bit.
def _arc_pitch(r, tol=0.35):
    """Chord pitch (px) for `_sun_arc` that keeps the sagitta under `tol` px on
    an arc of radius r: sagitta ~ pitch^2 / (8r). Sunburst/voderberg can use a
    base_s-derived pitch because their arc radius grows with the frame; a
    Truchet arc has radius ~ base_s/2 at ANY resolution, so a pitch of base_s/3
    would leave a visible 1-3 px facet on every cell."""
    return max(2.0, math.sqrt(8.0 * r * tol))


def _truchet_flip(i, j):
    """Deterministic 0/1 orientation for lattice cell (i, j) (integer hash)."""
    h = ((i * 73856093) ^ (j * 19349663)) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h & 1


def _gen_truchet(engine, target_w, target_h, base_s):
    """Classic (Smith) Truchet: each square is cut by two quarter-circle arcs of
    radius s/2 centred on OPPOSITE corners -> three cells: two quarter discs and
    the S-shaped middle band. The arcs meet the square's edges at their
    midpoints at a right angle, so they join into continuous curves across the
    whole frame whichever way each square is flipped.

    Dominant cell = the middle band, area s^2*(1 - pi/8) -> s = base_s /
    sqrt(1 - pi/8); the quarter discs are the small tile of the mixed tiling
    (pi/16 s^2, as in rhombitrihex)."""
    s = base_s / math.sqrt(1.0 - math.pi / 8.0)
    r = s / 2.0
    seg = _arc_pitch(r)
    for i in range(-1, int(target_w / s) + 2):
        for j in range(-1, int(target_h / s) + 2):
            x0, y0 = i * s, j * s
            x1, y1 = x0 + s, y0 + s
            if _truchet_flip(i, j) == 0:            # arcs at top-left/bottom-right
                a_tl = _sun_arc(r, 0.0, math.pi / 2, x0, y0, seg)
                a_br = _sun_arc(r, math.pi, 1.5 * math.pi, x1, y1, seg)
                yield [(x0, y0)] + a_tl
                yield [(x1, y1)] + a_br
                yield ([(x1, y0)] + list(reversed(a_br))
                       + [(x0, y1)] + list(reversed(a_tl)))
            else:                                   # arcs at top-right/bottom-left
                a_tr = _sun_arc(r, math.pi / 2, math.pi, x1, y0, seg)
                a_bl = _sun_arc(r, 1.5 * math.pi, 2.0 * math.pi, x0, y1, seg)
                yield [(x1, y0)] + a_tr
                yield [(x0, y1)] + a_bl
                yield ([(x0, y0)] + list(reversed(a_tr))
                       + [(x1, y1)] + list(reversed(a_bl)))


def _gen_truchet_hex(engine, target_w, target_h, base_s):
    """Hexagonal Truchet: three arcs of radius a/2 centred on ALTERNATE vertices
    of each hexagon, each joining the midpoints of that vertex's two edges. Every
    edge has exactly one of its endpoints in the chosen alternating triple, so
    every edge midpoint is an arc endpoint in BOTH neighbouring hexagons and the
    curves always continue across edges (the arc meets the edge at a right
    angle: the radius runs along the edge).

    Cells: three 120-degree pie slices at the chosen vertices + the curved
    middle. Dominant = middle, area a^2*(3*sqrt(3)/2 - pi/4) -> a from base_s."""
    a = base_s / math.sqrt(1.5 * math.sqrt(3.0) - math.pi / 4.0)
    r = a / 2.0
    seg = _arc_pitch(r)
    t1 = complex(math.sqrt(3.0), 0) * a
    t2 = complex(math.sqrt(3.0) / 2, 1.5) * a
    m0, m1, n0, n1 = _lattice_mn_range(t1, t2, target_w, target_h, pad=1.2 * a)
    corner = [cmath.exp(1j * math.radians(30 + 60 * k)) * a for k in range(6)]
    for m in range(m0, m1 + 1):
        for n in range(n0, n1 + 1):
            c = m * t1 + n * t2
            v = [c + z for z in corner]
            mid = [(v[k] + v[(k + 1) % 6]) / 2 for k in range(6)]   # mid[k]: v[k]-v[k+1]
            odd = _truchet_flip(m, n)                # which alternating triple
            arcs, middle = {}, []
            for k in range(6):
                if k % 2 == odd:                     # vertex v[k] carries an arc
                    p, q = mid[(k - 1) % 6], mid[k]  # its two edge midpoints
                    a0 = cmath.phase(p - v[k])
                    a1 = cmath.phase(q - v[k])
                    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi   # short way
                    arcs[k] = _sun_arc(r, a0, a0 + d, v[k].real, v[k].imag, seg)
                    middle += arcs[k]
                else:                                # vertex stays a corner
                    middle += [(mid[(k - 1) % 6].real, mid[(k - 1) % 6].imag),
                               (v[k].real, v[k].imag),
                               (mid[k].real, mid[k].imag)]
            for k, arc in arcs.items():
                yield [(v[k].real, v[k].imag)] + arc
            yield middle


# --- Girih (rosette quasi-lattice + greedy fill) ----------------------------
# Ported from src/tools/gen_fable_shape_schemes.py::_girih_attempt, but the
# scheme's algorithm does not survive being scaled up to a frame, and three of
# its four pillars had to go (audit: src/tools/girih_audit.py):
#   1. `commit()` rebuilt the ENTIRE occupancy raster after every tile. Harmless
#      on a 572px scheme, hundreds of GB of memcpy at 16K. Now it ORs a
#      bbox-sized buffer into the raster.
#   2. The patch radius now follows the frame diagonal, so cell size tracks
#      base_s at every resolution (invariant: dominant cell area ~ base_s^2).
#   3. Convex-hull hole filling is gone: the holes are concave corridors, so
#      their hulls swallowed whole neighbouring tiles (7-11% of the frame
#      painted twice). Holes are now traced and emitted as they are.
#   4. The decagons are SEEDED on a quasi-lattice instead of being discovered by
#      the greedy, which is what finally made the shape look like girih at all
#      (see the block by the seeding code) — and that in turn removed the last
#      of the randomness, so there is no RNG and no frozen seed anywhere here.
_GIRIH_RES = 26           # occupancy raster resolution (px per unit edge). A
# coarser raster (16) fakes collisions between tiles that actually fit and
# costs ~3 points of coverage; a finer one buys nothing. It is not a speed
# knob — the raster work is negligible next to the growth loop.
_GIRIH_CELL_AREA = 2.1266  # area of the girih hexagon: the cell that takes the
# largest share of the picture, so it is the one the mixed-tiling scale rule
# pins to base_s^2. The rosette kites (0.77) are the most NUMEROUS cell and are
# deliberately finer — that is what makes a rosette read as a rosette.
_GIRIH_MARGIN = 10.0      # units of patch grown BEYOND the frame corner. The
# growth front is ragged (edges past rad-2 are dropped), so it must fall
# outside the frame: at margin 3 the frame still caught 1-2 unit^2 holes.
# Which tile gets first refusal when filling BETWEEN the rosettes. Bowtie-first
# is not a taste call, it is what the lattice wants: a decagon pair one rhomb
# edge apart is bridged by a hexagon, but every other gap the quasi-lattice
# opens is bowtie-shaped, and letting hexagons grab those first strands the
# leftovers. Measured over the whole frame (src/tools/girih_audit.py):
#   bowtie-first : 95.3% real girih tiles, 3.1% traced leftovers
#   hexagon-first: 84.5% real girih tiles, 11.3% traced leftovers
# The order is FIXED, so girih carries no RNG and no frozen seed at all — the
# plan budgeted for a seed sweep, and seeding the rosettes deterministically
# made the whole question disappear.
_GIRIH_ORDER = ("bowtie", "hexagon", "pentagon", "rhomb")
_GIRIH_PROBE = 0.15       # dead-edge probe depth (< 0.81, the smallest inward
# extent of any prototype at an edge midpoint), which makes the probe exact:
# it rejects an edge only when a tile glued to it would provably overlap.


def _girih_turtle(angles):
    """Unit-edge polygon from its interior angles (degrees), CCW."""
    pts = [complex(0.0, 0.0)]
    heading = 0.0
    for ang in angles[:-1]:
        pts.append(pts[-1] + cmath.exp(1j * math.radians(heading)))
        heading += 180.0 - ang
    return pts


# The five classic girih tiles (all edges of length 1).
_GIRIH_PROTOS = {
    "decagon":  _girih_turtle([144] * 10),
    "pentagon": _girih_turtle([108] * 5),
    "hexagon":  _girih_turtle([72, 144, 144, 72, 144, 144]),
    "bowtie":   _girih_turtle([72, 72, 216, 72, 72, 216]),
    "rhomb":    _girih_turtle([72, 108, 72, 108]),
}
_GIRIH_SHRINK = 0.90      # collision test: candidate shrunk toward its centroid
_GIRIH_SEAL = 0.99        # commit: tile written to the raster nearly full size
_GIRIH_HOLE_GROW = 1      # raster px a traced hole is dilated by (see below)


def _girih_tables(shrink=_GIRIH_SHRINK):
    """Precompute every (tile type, edge) candidate ONCE, in a frame where the
    glued edge runs from 0 to 1. Gluing tile edge j onto the open edge (B, A)
    is then the single affine map z -> z*(A - B) + B, so a candidate's vertices
    are one complex multiply — and all 31 candidates can be built and tested
    against the occupancy raster in a handful of numpy calls per edge.

    Returns (order_index, verts, probes):
      order_index : {tile name: (first_row, n_rows)}
      verts       : list of (n,) complex arrays, one per row (the tile itself)
      probes      : (31, C) complex array of interior sample points -- the
                    shrunk vertices plus the centroid, padded by repeating a
                    point (a duplicate sample is harmless, a ragged array is not)
    """
    index, verts, probes = {}, [], []
    cmax = max(len(t) for t in _GIRIH_PROTOS.values()) + 1
    for name, tpl in _GIRIH_PROTOS.items():
        index[name] = (len(verts), len(tpl))
        for j in range(len(tpl)):
            pj, pj1 = tpl[j], tpl[(j + 1) % len(tpl)]
            m = np.array([(z - pj) / (pj1 - pj) for z in tpl], dtype=complex)
            c = m.mean()
            s = np.concatenate([c + (m - c) * shrink, [c]])
            verts.append(m)
            probes.append(np.pad(s, (0, cmax - len(s)), mode="edge"))
    return index, verts, np.array(probes)


_GIRIH_INDEX, _GIRIH_VERTS, _GIRIH_PROBES = _girih_tables()


def _girih_patch(rad, res=_GIRIH_RES, stats=None):
    """Build a girih patch of radius `rad` (in unit edges) about the origin and
    return its cells as polygons in unit space.

    Two stages. First the decagon rosettes are laid on a 10-fold quasi-lattice
    (see the seeding block). Then a greedy fills the space between them: take
    the most boxed-in open edge, try the tile types in _GIRIH_ORDER, keep the
    first that does not overlap the occupancy raster.

    Every decagon is split into its 10 khatam kites — a whole decagon is several
    times bigger than any other cell, which is the 'impractical centre' the user
    rejected elsewhere — and whatever the greedy still fails to cover is traced
    and emitted as its own cell, so the frame has no background holes.

    Fully deterministic: same rad, same patch. `stats`: optional dict, filled
    with tile counts / coverage / leftover count for src/tools/girih_audit.py.
    """
    res = float(res)
    W = int(2.0 * rad * res) + 2
    occ = np.zeros((W, W), dtype=bool)

    def to_px(z):
        return ((z.real + rad) * res, (z.imag + rad) * res)

    def shrunk(poly, f):
        c = sum(poly) / len(poly)
        return [c + (z - c) * f for z in poly]

    def raster(poly, f):
        """(x0, y0, mask) for the f-shrunk polygon, or None if out of bounds."""
        pts = [to_px(z) for z in shrunk(poly, f)]
        x0 = int(min(p[0] for p in pts)) - 1
        y0 = int(min(p[1] for p in pts)) - 1
        x1 = int(max(p[0] for p in pts)) + 2
        y1 = int(max(p[1] for p in pts)) + 2
        if x0 < 0 or y0 < 0 or x1 > W or y1 > W:
            return None
        buf = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(buf).polygon([(px - x0, py - y0) for px, py in pts],
                                    fill=255)
        return x0, y0, np.asarray(buf, dtype=bool)

    def free_at(z):
        px, py = to_px(z)
        ix, iy = int(px), int(py)
        if ix < 0 or iy < 0 or ix >= W or iy >= W:
            return False
        return not occ[iy, ix]

    def fits(poly):
        r = raster(poly, _GIRIH_SHRINK)
        if r is None:
            return False
        x0, y0, m = r
        h, w = m.shape
        return not np.any(occ[y0:y0 + h, x0:x0 + w] & m)

    def commit(poly):
        r = raster(poly, _GIRIH_SEAL)
        if r is None:
            return
        x0, y0, m = r
        h, w = m.shape
        occ[y0:y0 + h, x0:x0 + w] |= m

    placed = []
    open_edges = []
    seq = [0]

    def pocket_score(A, B):
        """How boxed-in this edge is: how many of the probe points just beyond
        its two ENDS are already covered. An edge with both ends walled in sits
        in a pocket that only shrinks — if the front closes over it before it is
        tried, the pocket becomes dead space. Serving the most boxed-in edges
        first is the classic most-constrained-first heuristic."""
        d = (B - A) / abs(B - A)
        nrm = -1j * d
        return sum(not free_at(p) for p in
                   (A + nrm * 0.25 - d * 0.15, B + nrm * 0.25 + d * 0.15,
                    (A + B) / 2.0 + nrm * 0.60))

    def push(A, B):
        seq[0] += 1
        heapq.heappush(open_edges, (-pocket_score(A, B), seq[0], B, A))

    def place(name, poly):
        placed.append((name, poly))
        commit(poly)
        n = len(poly)
        for i in range(n):
            # push(A, B) with A, B in polygon order: the tile glued to this edge
            # is then built on (B, A), i.e. REVERSED, so it grows OUTWARD
            push(poly[i], poly[(i + 1) % n])

    # ---- the rosettes are the WARP, not something the greedy grows into ----
    # Letting the greedy discover decagons does not work: it was offered one on
    # 1610 edges and had room on 10 of them. Edge-by-edge growth never leaves a
    # virgin pocket the size of a decagon, so the patch came out as a field of
    # hexagons — girih without its khatam rosettes, which is the one thing the
    # shape exists for.
    #
    # Real girih is laid out the other way round: the decagons sit on a 10-fold
    # quasi-lattice and the small tiles fill what is left between them. Penrose
    # P3 vertices ARE that lattice, and the two constructions lock together
    # exactly. With rhomb edge d = apothem / sin(18deg):
    #   * neighbours one rhomb EDGE apart (distance d) leave a gap of exactly
    #     the girih hexagon's width between two parallel edges (1.902), so a
    #     hexagon bridges them;
    #   * neighbours across a thin rhomb's SHORT DIAGONAL (0.618*d, the golden
    #     ratio) land at exactly 2 apothems, so those two decagons meet
    #     edge-to-edge.
    # Both are legal girih adjacencies, so every decagon pair the lattice
    # produces is one the tile set can actually resolve. The rhombs' edges run
    # along 36k degrees while a decagon's edge normals run along 18+36k, hence
    # the 18-degree turn.
    apo = abs((_GIRIH_PROTOS["decagon"][0] + _GIRIH_PROTOS["decagon"][1]) / 2.0
              - sum(_GIRIH_PROTOS["decagon"]) / 10.0)
    d_lat = apo / math.sin(math.pi / 10.0)
    zeta = [cmath.exp(2j * math.pi * k / 5) for k in range(5)]
    gamma = [0.05, 0.15, 0.25, 0.35, 0.20]     # canonical class, sums to 1
    seeds = set()
    for rhomb in _multigrid_dual(5, zeta, gamma, 2.0 * rad, 2.0 * rad, d_lat):
        for x, y in rhomb:
            seeds.add((round(x - rad, 6), round(y - rad, 6)))

    dec = [z * cmath.exp(1j * math.radians(18.0))
           for z in _GIRIH_PROTOS["decagon"]]
    dec = [z - sum(dec) / len(dec) for z in dec]          # centred on origin
    for x, y in sorted(seeds, key=lambda p: p[0] * p[0] + p[1] * p[1]):
        c = complex(x, y)
        if abs(c) > rad - 2.0:
            continue
        rosette = [z + c for z in dec]
        if fits(rosette):
            place("decagon", rosette)

    while open_edges:
        negscore, _, B, A = heapq.heappop(open_edges)
        mid = (A + B) / 2.0
        if abs(mid) > rad - 2.0:
            continue
        # lazy re-prioritisation: the edge may have been walled in further since
        # it was pushed. Scores only ever rise (occupancy never shrinks) and are
        # capped at 3, so an edge can bounce at most three times.
        score = pocket_score(A, B)
        if score > -negscore:
            heapq.heappush(open_edges, (-score, seq[0], B, A))
            seq[0] += 1
            continue
        # O(1) dead-edge test: anything glued to this edge would cover the
        # point just outside its midpoint (see _GIRIH_PROBE)
        d = B - A
        if not free_at(mid - 1j * d / abs(d) * _GIRIH_PROBE):
            continue
        # Test all 31 candidates at once: sample the interior points of each
        # (shrunk vertices + centroid) against the occupancy raster. A sample
        # point lies inside the shrunk candidate, so an occupied sample proves
        # the raster test would reject it — this is a pre-filter, not a
        # different rule, and it turns ~25 python polygon builds per edge into
        # four numpy calls.
        pts = _GIRIH_PROBES * (A - B) + B
        ix = ((pts.real + rad) * res).astype(np.int32)
        iy = ((pts.imag + rad) * res).astype(np.int32)
        inb = (ix >= 0) & (iy >= 0) & (ix < W) & (iy < W)
        free = inb & ~occ[np.where(inb, iy, 0), np.where(inb, ix, 0)]
        cand_ok = free.all(axis=1)

        hit = False
        for name in _GIRIH_ORDER:
            first, n = _GIRIH_INDEX[name]
            for k in range(first, first + n):
                if not cand_ok[k]:
                    continue
                cand = list(_GIRIH_VERTS[k] * (A - B) + B)
                if fits(cand):
                    place(name, cand)
                    hit = True
                    break
            if hit:
                break

    cells = []
    for name, poly in placed:
        if name == "decagon":
            c = sum(poly) / len(poly)
            n = len(poly)
            mids = [(poly[i] + poly[(i + 1) % n]) / 2.0 for i in range(n)]
            for i in range(n):
                cells.append([(z.real, z.imag)
                              for z in (c, mids[(i - 1) % n], poly[i], mids[i])])
        else:
            cells.append([(z.real, z.imag) for z in poly])

    # Close the slivers greedy growth leaves behind (~5-9% of the patch): label
    # the empty raster, drop the component touching the border (that is the
    # outside), and emit each interior hole as one more cell.
    #
    # The scheme emitted the hole's CONVEX HULL, inflated by 1.10. Neither is
    # usable here. Dropping the inflation was not enough: the holes are
    # concave, corridor-shaped leftovers, so their convex hulls swallow whole
    # neighbouring tiles — measured 7-11% of the frame painted twice, i.e. two
    # photographs fighting for the same pixels (the greedy tiles on their own
    # rasterise as an exact partition: 0.001% overlap). The scheme got away
    # with it because it painted the hulls last, under black outlines.
    #
    # So the hole is emitted as the hole: marching squares on its raster, then
    # polyline simplification. The cell is exactly the leftover region, which
    # keeps the tiling a partition — no double-painted pixels, no background.
    #
    # Holes are searched for inside the USABLE DISC only (the frame plus a
    # little), never by asking whether a component touches the raster border.
    # The scheme's border rule says "the component that reaches the edge is the
    # outside" — but the empty space percolates: a corridor can run from a hole
    # in the middle of the patch out to the ragged growth front, and then the
    # whole component, interior included, is written off as outside. That is
    # how salts 12/26/48 came out of the sweep with 6-9 unit^2 of bare
    # background. Clipping to the disc instead cannot leak: every empty pixel
    # the frame can see gets a cell, whatever the corridor does past the edge.
    n_tiles = len(cells)
    fill_r = (rad - _GIRIH_MARGIN + 2.0) * res
    yy, xx = np.ogrid[:W, :W]
    usable = (xx - W / 2.0) ** 2 + (yy - W / 2.0) ** 2 <= fill_r ** 2
    lab, nlab = nd_label(~occ & usable)
    if nlab:
        min_px = max(8, int(0.10 * res * res))     # ignore sub-cell seam dust
        # find_objects gives each label its bounding box, so a hole is scanned
        # inside its own bbox. (Scanning `lab == li` over the FULL raster once
        # per label is O(labels x frame) — the same shape of mistake as the
        # scheme's commit(), and it cost 8.9 s of an 11.2 s patch.)
        for li, sl in enumerate(nd_find_objects(lab), start=1):
            if sl is None:
                continue
            sub = lab[sl] == li
            if int(sub.sum()) < min_px:
                continue
            # Grow the hole by one raster pixel before tracing it. The tiles
            # were sealed into the raster at _GIRIH_SEAL, so the empty run
            # between two tiles is a hair wider than the true seam and a
            # traced contour would sit just INSIDE the hole, leaving a thin
            # background seam. Better to have the hole cell bite ~1 raster
            # pixel into its neighbours (invisible: the cell is painted over
            # ~140 px of tile at 16K) than to leave background showing.
            # The zero pad MUST stay wider than the dilation: a grown mask that
            # reaches the array edge gives find_contours an open, clipped curve
            # instead of a closed ring, and the cell comes out as garbage.
            grown = binary_dilation(np.pad(sub, _GIRIH_HOLE_GROW + 1),
                                    iterations=_GIRIH_HOLE_GROW)
            contours = find_contours(grown.astype(float), 0.5)
            if not contours:
                continue
            outline = approximate_polygon(max(contours, key=len), tolerance=0.75)
            if len(outline) < 4:               # closed ring: first point repeats
                continue
            off = _GIRIH_HOLE_GROW + 1
            x_off, y_off = sl[1].start - off, sl[0].start - off
            cells.append([((x + x_off) / res - rad, (y + y_off) / res - rad)
                          for y, x in outline[:-1]])

    if stats is not None:
        counts = {}
        for name, _ in placed:
            counts[name] = counts.get(name, 0) + 1
        # Greedy coverage of the inscribed DISC of radius rad-3 — the engine
        # inscribes the frame rectangle in that disc, so this is the region a
        # render actually uses. (A square window of half-width rad-3 would
        # reach 1.41x(rad-3) at its corners — far outside the grown patch —
        # and understate the coverage by the empty corner area.)
        c = W / 2.0
        rr = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / res      # radius in units
        disc = rr <= (rad - 3.0)
        stats["counts"] = counts
        stats["greedy_coverage"] = float(occ[disc].mean())
        # how the greedy holds up as the patch grows outward
        edges = np.linspace(0.0, rad - 3.0, 8)
        stats["profile"] = [
            (float(a), float(b), float(occ[(rr >= a) & (rr < b)].mean()))
            for a, b in zip(edges[:-1], edges[1:])]
        stats["leftover_cells"] = len(cells) - n_tiles
        stats["cells"] = len(cells)
    return cells


def _gen_girih(engine, target_w, target_h, base_s):
    """Girih: the five Persian strapwork tiles grown edge-to-edge, decagons
    split into khatam kites. The patch is built once in unit space (radius from
    the frame diagonal) and mapped to the frame by a single scale — so the cell
    size is set by base_s alone and a preview shows the very pattern the full
    render will have."""
    u = base_s / math.sqrt(_GIRIH_CELL_AREA)          # px per unit edge
    rad = math.hypot(target_w, target_h) / (2.0 * u) + _GIRIH_MARGIN
    cx, cy = target_w / 2.0, target_h / 2.0
    for poly in _girih_patch(rad):
        yield [(cx + x * u, cy + y * u) for x, y in poly]


# ==========================================
# POINCARE {7,3} — hyperbolic band model
# ==========================================
# The Poincare disk maps conformally onto an infinite horizontal strip by
# w = (2/pi)*log((1+z)/(1-z))  (|Im w| < 1), so the same {7,3} tiling runs
# left-right forever with no circular horizon; cell size depends only on the
# distance from the strip midline (factor ~cos(pi*y/2)), and capping the
# window at |y| <= _POINCARE_W bounds the smallest cells at ~1/3 of the
# centre row. Reflections stay in the DISK (circle inversions are cheap and
# exact); only the keep/expand test is mapped to band coordinates. The scheme
# tool's disk-space cutoffs do NOT survive wide frames: at band-x = 3.2 (a
# 4:1 panorama) centre-row heptagons sit at |z| ~ 0.987 where their disk
# diameter ~0.0155 already falls below the tool's old `diam < 0.02` cutoff,
# i.e. the cutoff was culling REAL tiles — it is deliberately absent here.
# (Plan (b++) 2026-07-15; source geometry: gen_fable_shape_schemes.py.)

_POINCARE_W = 0.80        # band window half-height (|y| <= W maps to frame)
_POINCARE_MARGIN = 0.25   # band-units bbox inflation for the keep/expand
                          # test — covers geodesic edges bowing toward the
                          # midline slightly outside the vertex bbox


def _poincare_band(z):
    """Disk -> band strip, conformal: w = (2/pi) log((1+z)/(1-z))."""
    return (2.0 / math.pi) * cmath.log((1.0 + z) / (1.0 - z))


def _poincare_geo_circle(z1, z2):
    """Circle through z1, z2 orthogonal to the unit circle (the support of
    the disk geodesic). None -> the geodesic is a diameter (straight line)."""
    a1, b1, c1 = 2 * z1.real, 2 * z1.imag, abs(z1) ** 2 + 1
    a2, b2, c2 = 2 * z2.real, 2 * z2.imag, abs(z2) ** 2 + 1
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-9:
        return None
    cx = (c1 * b2 - c2 * b1) / det
    cy = (a1 * c2 - a2 * c1) / det
    c = complex(cx, cy)
    r2 = abs(c) ** 2 - 1
    if r2 <= 0.0:
        # only reachable for (near-)degenerate input (z1 ~ z2): a true
        # orthogonal circle always has |c| > 1 — fall back to the line case
        return None
    return c, math.sqrt(r2)


def _poincare_reflect(z, circ):
    """Inversion in the geodesic circle (hyperbolic reflection)."""
    c, r = circ
    return c + r * r / (z - c).conjugate()


def _poincare_edge_arc(z1, z2, n):
    """n samples of the geodesic arc z1 -> z2 at t = 0 .. (n-1)/n (t = 1 is
    excluded: the next edge's t = 0 supplies that vertex). Sampling is uniform
    in arc angle, so the sample SET is direction-independent — the neighbour
    traversing the shared edge z2 -> z1 polygonises it through the very same
    points (exact partition). n must be EVEN so index n//2 is the t = 0.5
    edge midpoint where the khatam kite split lands."""
    circ = _poincare_geo_circle(z1, z2)
    if circ is None:
        return [z1 + (z2 - z1) * t / n for t in range(n)]
    c, r = circ
    a1 = cmath.phase(z1 - c)
    a2 = cmath.phase(z2 - c)
    if a2 - a1 > math.pi:
        a2 -= 2 * math.pi
    if a1 - a2 > math.pi:
        a2 += 2 * math.pi
    return [c + r * cmath.exp(1j * (a1 + (a2 - a1) * t / n)) for t in range(n)]


def _poincare_heptagons(x_max):
    """Reflection BFS of the {7,3} tiling, pruned in BAND space.

    Runs entirely in the disk; a tile is kept AND expanded iff its band-space
    vertex bbox intersects the window [-x_max, x_max] x [-W, W] inflated by
    _POINCARE_MARGIN. The window is geodesically convex (the band metric
    factor 1/cos(pi*y/2) is smallest on the midline, so geodesics bow toward
    it and never leave the box spanned by their endpoints), hence every tile
    that meets the window is reachable from the centre through kept tiles —
    this prune is exact, not heuristic, and it turns the otherwise
    exponential BFS (~3.6M tiles at depth 14) into a set linear in the window
    area. {7,3} has NO translational symmetry along the band axis (7 is odd),
    so a wide window genuinely requires the full BFS — a panorama cannot be
    stitched from copies of one segment.

    Returns [(7 disk vertices, disk hyperbolic centre)], deterministic order
    (deque BFS, zero RNG); the central heptagon is first. Dedup keys are disk
    centroids rounded to 1e-4 — distinct tiles stay >= ~1e-3 apart out to
    band-x ~ 7 (aspect ~8.7:1), far beyond any real frame."""
    p, q = 7, 3
    # hyperbolic circumradius from the characteristic right triangle:
    # cosh R = cot(pi/p) * cot(pi/q)
    coshR = 1.0 / (math.tan(math.pi / p) * math.tan(math.pi / q))
    r0 = math.tanh(math.acosh(coshR) / 2.0)
    central = [r0 * cmath.exp(1j * (math.pi / 2 + 2 * math.pi * k / p))
               for k in range(p)]
    W = _POINCARE_W
    m = _POINCARE_MARGIN
    # The y margin must stay strictly below the |y| = 1 horizon: tiles shrink
    # to dust as |y| -> 1, so a keep-band reaching the horizon would let the
    # BFS chase degenerate slivers until the depth cap (W + 0.25 = 1.05 > 1
    # disabled the y prune entirely on the first run — sqrt domain error in
    # _poincare_geo_circle on a collapsed edge).
    m_y = min(m, 0.5 * (1.0 - W))
    # Belt-and-braces depth cap (the band prune already bounds the patch):
    # hyperbolic distance to the frame corner is (pi/2)*x_max + ~1.85 for
    # W = 0.80; adjacent heptagon centres sit 2*r_in ~ 1.09 apart; x2 covers
    # the staircase path, +6 is cushion. 4:3 -> 13, 4:1 panorama -> 19.
    d_max = (math.pi / 2.0) * x_max + 1.85
    depth_cap = int(math.ceil(d_max / 1.09 * 2.0)) + 6

    out = []
    seen = set()
    queue = deque([(central, 0j, 0)])
    while queue:
        poly, hc, depth = queue.popleft()
        ctr = sum(poly) / p
        key = (round(ctr.real, 4), round(ctr.imag, 4))
        if key in seen:
            continue
        seen.add(key)
        b = [_poincare_band(v) for v in poly]
        if (min(v.real for v in b) > x_max + m or
                max(v.real for v in b) < -x_max - m or
                min(v.imag for v in b) > W + m_y or
                max(v.imag for v in b) < -W - m_y):
            continue
        out.append((poly, hc))
        if depth >= depth_cap:
            continue
        for k in range(p):
            z1, z2 = poly[k], poly[(k + 1) % p]
            circ = _poincare_geo_circle(z1, z2)
            if circ is None:
                # diameter geodesic: reflect across the line through z1
                # with direction u
                u = (z2 - z1) / abs(z2 - z1)
                newp = [z1 + ((z - z1) / u).conjugate() * u for z in poly]
                newc = z1 + ((hc - z1) / u).conjugate() * u
            else:
                newp = [_poincare_reflect(z, circ) for z in poly]
                newc = _poincare_reflect(hc, circ)
            queue.append((newp, newc, depth + 1))
    return out


def _poincare_hyp_frac(z1, z2, t):
    """Point at hyperbolic fraction t of the geodesic z1 -> z2 (disk coords).

    Mobius-translate z1 to the origin, walk tanh(t * atanh(r)) of the image
    radius (hyperbolic distance from 0 is 2*atanh(r), so this is exactly the
    fraction t of the distance), translate back. Exact and cheap; the same
    (z1, z2, t) triple always yields the same point, which is what the shared
    subdivision rays rely on."""
    a = (z2 - z1) / (1.0 - z1.conjugate() * z2)
    r = abs(a)
    if r < 1e-15:
        return z1
    w = a / r * math.tanh(t * math.atanh(r))
    return (w + z1) / (1.0 + z1.conjugate() * w)


def _poincare_cells(target_w, target_h, base_s):
    """Yield (pixel polygon, heptagon index, kite index) for the subdivided
    {7,3} band tiling — step 2 of plan (b++).

    Every kite [C, M_prev, V, M_next] carries an nd x nd transfinite quad
    mesh built with hyperbolic fractions (_poincare_hyp_frac), so the band
    map's conformality keeps the sub-cells near-isotropic at every |y|. A
    quad mesh has no pole: C is the corner of ONE sub-cell per kite (7 meet
    there across the heptagon — the approved 'good centre' pattern), unlike
    a polar fan whose innermost wedges thin toward 4:1.

    nd adapts PER HEPTAGON (largest kite radial extent / base_s), so every
    cell lands near base_s at any resolution. Differing nd between
    neighbouring heptagons cannot open T-junctions by construction:

      * outer arcs — the mesh splits an arc only AT samples of the global
        step-1 grid (indices snapped via round(j*half/nd)), and every cell
        emits ALL grid samples along its arc stretch as vertices, so both
        sides of an edge yield the identical segment set even with different
        nd (segment-level matching beats the per-edge-count rule: there is
        no count threshold left to flicker);
      * rays C -> M — shared only between kites of the SAME heptagon, both
        sides evaluate _poincare_hyp_frac on the same float endpoints with
        the same nd;
      * interior nodes are private to their kite.

    Cell count ~ frame_area / base_s^2 (e.g. ~24k at 16K 16:9, under girih's
    51k); zero RNG, deterministic emission order (BFS, k, i, j)."""
    W = _POINCARE_W
    scale = target_h / (2.0 * W)              # px per band unit
    x_max = (target_w / 2.0) / scale          # = W * aspect
    cx, cy = target_w / 2.0, target_h / 2.0
    p = 7

    hepts = _poincare_heptagons(x_max)

    # One global, EVEN arc-sample count per render, sized from the longest
    # edge of the central heptagon (the centre row has the largest band-space
    # cells): ~base_s/3 px per polyline segment, the sunburst precedent.
    c0 = [_poincare_band(v) for v in hepts[0][0]]
    lmax = max(abs(c0[k] - c0[(k + 1) % p]) for k in range(p))
    seg = max(4.0, base_s / 3.0)              # px per polyline segment
    n = max(6, 2 * int(math.ceil(lmax * scale / (2.0 * seg))))
    half = n // 2

    def to_px(z):
        w = _poincare_band(z)
        return (cx + w.real * scale, cy + w.imag * scale)

    for hi, (poly, hc) in enumerate(hepts):
        # edge sample lists INCLUDING the far endpoint: n + 1 points
        edges = []
        for k in range(p):
            e = _poincare_edge_arc(poly[k], poly[(k + 1) % p], n)
            e.append(poly[(k + 1) % p])
            edges.append(e)
        mids = [edges[k][half] for k in range(p)]

        wc_band = _poincare_band(hc)
        kite_px = max(abs(_poincare_band(m) - wc_band) for m in mids) * scale
        nd = max(1, int(round(kite_px / base_s)))
        nd = min(nd, half)        # snapped arc splits must stay strictly
                                  # increasing (half >= ~3*nd in practice)

        for k in range(p):
            e_prev = edges[(k - 1) % p]       # ... -> V = e_prev[n]
            e_next = edges[k]                 # V = e_next[0] -> ...
            m_prev, m_next = mids[(k - 1) % p], mids[k]

            # (nd+1)^2 node lattice over the kite quad:
            # N[0][0]=C, N[nd][0]=M_prev, N[0][nd]=M_next, N[nd][nd]=V
            N = [[None] * (nd + 1) for _ in range(nd + 1)]
            for i in range(nd + 1):
                N[i][0] = _poincare_hyp_frac(hc, m_prev, i / nd)
            for j in range(nd + 1):
                N[0][j] = _poincare_hyp_frac(hc, m_next, j / nd)
            # arc rows overwrite the i=nd / j=nd lattice lines with the
            # canonical shared grid samples (snapped indices)
            ap = [half + round(j * half / nd) for j in range(nd + 1)]
            for j in range(nd + 1):
                N[nd][j] = e_prev[ap[j]]
            an = [half - round(i * half / nd) for i in range(nd + 1)]
            for i in range(nd + 1):
                N[i][nd] = e_next[an[i]]
            for i in range(1, nd):
                for j in range(1, nd):
                    N[i][j] = _poincare_hyp_frac(N[i][0], N[i][nd], j / nd)

            for i in range(nd):
                for j in range(nd):
                    pts = [N[i][j], N[i + 1][j]]
                    if i + 1 == nd:           # east side runs along e_prev
                        pts += [e_prev[t]
                                for t in range(ap[j] + 1, ap[j + 1] + 1)]
                    else:
                        pts.append(N[i + 1][j + 1])
                    if j + 1 == nd:           # north side runs along e_next
                        pts += [e_next[t]
                                for t in range(an[i + 1] + 1, an[i] + 1)]
                    else:
                        pts.append(N[i][j + 1])

                    cell = [to_px(z) for z in pts]
                    xs = [q[0] for q in cell]
                    ys = [q[1] for q in cell]
                    if (min(xs) > target_w or max(xs) < 0.0 or
                            min(ys) > target_h or max(ys) < 0.0):
                        continue              # cell fully off-frame
                    yield cell, hi, k


def _gen_poincare(engine, target_w, target_h, base_s):
    """Poincare {7,3} in the band model: heptagons split into 7 khatam kites
    [hyperbolic centre, edge-mid k-1, vertex k, edge-mid k] (centre carried
    through the BFS reflections, mids = the t = 0.5 arc samples shared by
    both sides — exact partition, the girih khatam mechanism), and each kite
    subdivided to ~base_s cells by the hyperbolic quad mesh of
    _poincare_cells."""
    for cell, _hi, _k in _poincare_cells(target_w, target_h, base_s):
        yield cell


@dataclass(frozen=True)
class ShapeSpec:
    """Descriptor for one tile shape.

    kind      : "grid"    -> axis-aligned crop + shared mask (grid branch).
                "polygon" -> per-tile polygon via `_polygon_sector`.
    generator : callable(engine, target_w, target_h, base_s) -> iterable[poly],
                each poly a list of (x, y) vertices in image space (y down).
                None for grid shapes.
    aa        : anti-aliasing supersample for the polygon mask (1 = native).
    seeded    : reserved for variable-cell shapes that need a deterministic
                RNG seed (voronoi; poincare turned out fully deterministic).
    """
    kind: str
    generator: object = None
    aa: int = 1
    seeded: bool = False


# Ordered registry — GUI dropdown, CLI --shape choices, make_showcase and the
# benchmark all read the names from `shape_names()` so adding a shape is a
# one-line edit here (the earlier kite->kites rename touched five files).
SHAPE_MODES = {
    "square":        ShapeSpec("grid"),
    "rectangle_3x1": ShapeSpec("grid"),
    "brick_wall":    ShapeSpec("grid"),
    "hexagon":       ShapeSpec("grid"),
    "hexagon_romb":  ShapeSpec("grid"),
    "romb":          ShapeSpec("grid"),
    "triangle":      ShapeSpec("grid"),
    "kites":         ShapeSpec("polygon", _gen_kites, aa=1),
    "spectre":       ShapeSpec("polygon", _gen_spectre, aa=4),
    "sunflower_grande":         ShapeSpec("polygon", _gen_sunflower_grande, aa=4),
    "sunflower_grande_xl":      ShapeSpec("polygon", _gen_sunflower_grande_xl, aa=4),
    "sunflower_grande_soft":    ShapeSpec("polygon", _gen_sunflower_grande_soft, aa=4),
    "sunflower_grande_inverse": ShapeSpec("polygon", _gen_sunflower_grande_inverse, aa=4),
    "sunflower_soft":           ShapeSpec("polygon", _gen_sunflower_soft, aa=4),
    "sunflower_rings":          ShapeSpec("polygon", _gen_sunflower_rings, aa=4),
    "sunflower_disc":           ShapeSpec("polygon", _gen_sunflower_disc, aa=4),
    "rhombs_nopole":            ShapeSpec("polygon", _gen_rhombs_nopole, aa=4),
    "rhombs_funnel":            ShapeSpec("polygon", _gen_rhombs_funnel, aa=4),
    "rhombs_star":              ShapeSpec("polygon", _gen_rhombs_star, aa=4),
    "voronoi":                  ShapeSpec("polygon", _gen_voronoi, aa=4, seeded=True),
    "phyllotaxis":              ShapeSpec("polygon", _gen_phyllotaxis, aa=4),
    "pinwheel":                 ShapeSpec("polygon", _gen_pinwheel, aa=4),
    "cairo":                    ShapeSpec("polygon", _gen_cairo, aa=4),
    "floret":                   ShapeSpec("polygon", _gen_floret, aa=4),
    "gosper":                   ShapeSpec("polygon", _gen_gosper, aa=4),
    "trunc_square":             ShapeSpec("polygon", _gen_trunc_square, aa=4),
    "trunc_hex":                ShapeSpec("polygon", _gen_trunc_hex, aa=4),
    "rhombitrihex":             ShapeSpec("polygon", _gen_rhombitrihex, aa=4),
    "pythagorean":              ShapeSpec("polygon", _gen_pythagorean, aa=4),
    "sunburst":                 ShapeSpec("polygon", _gen_sunburst, aa=4),
    "penrose":                  ShapeSpec("polygon", _gen_penrose, aa=4),
    "penrose_p2":               ShapeSpec("polygon", _gen_penrose_p2, aa=4),
    "ammann_beenker":           ShapeSpec("polygon", _gen_ammann_beenker, aa=4),
    "voderberg":                ShapeSpec("polygon", _gen_voderberg, aa=4),
    "escher_lizard":            ShapeSpec("polygon", _gen_escher, aa=4),
    "weave":                    ShapeSpec("polygon", _gen_weave, aa=4),
    "truchet":                  ShapeSpec("polygon", _gen_truchet, aa=4),
    "truchet_hex":              ShapeSpec("polygon", _gen_truchet_hex, aa=4),
    "girih":                    ShapeSpec("polygon", _gen_girih, aa=4),
    "poincare":                 ShapeSpec("polygon", _gen_poincare, aa=4),
}


def shape_names():
    """Ordered list of registered shape-mode names (single source of truth)."""
    return list(SHAPE_MODES.keys())


class SmartEngine:
    def __init__(self, index_path="data/smart_index.pkl"):
        print(f"Loading Smart Index: {index_path}...")
        try:
            with open(index_path, "rb") as f:
                data = pickle.load(f)

            self.paths = data["paths"]
            self.features = data["features"]

            actual_dim = self.features.shape[1] if self.features.ndim == 2 else 0
            if actual_dim not in (75, 79):
                print(f"ERROR: Index has {actual_dim}-dim features, expected 75 or 79. "
                      f"Rendering DISABLED. Rebuild index: GUI → 'Update / Create Index'")
                self.paths = []
                self.features = []
                return

            schema = data.get("schema_version", "unknown")
            if schema not in ("5x5", "5x5_edge"):
                print(f"WARNING: Index schema '{schema}', expected '5x5' or '5x5_edge'.")

            self.settings = {
                "allow_mirror": True,
                "edge_aware": False,
                "freq_penalty": 30.0,
            }
            self._neighbors_cache: dict = {}
            self._neighbors_lock = threading.Lock()
            print(f"Smart Engine Ready. Images: {len(self.paths)}  "
                  f"schema: {schema}  dim: {actual_dim}")
        except FileNotFoundError:
            print("Error: Smart Index not found. Run 'Update / Create Index' in GUI.")
            self.paths = []
            self.features = []

    def _get_neighbors_map(self, _nkey, points, search_radius):
        """Return the cached neighbour adjacency for this render geometry.

        Concurrent preview renders may run two _do_render calls in parallel
        (the generation token only gates result delivery, not execution), so
        the cache-miss path is serialised with double-checked locking to avoid
        racing mutation of self._neighbors_cache. The fast path is a lock-free
        dict read; the tree is built at most once per key under the lock.
        """
        neighbors_map = self._neighbors_cache.get(_nkey)
        if neighbors_map is not None:
            return neighbors_map
        with self._neighbors_lock:
            # Re-check under lock: another thread may have populated it while
            # we waited, so we don't recompute the tree needlessly.
            neighbors_map = self._neighbors_cache.get(_nkey)
            if neighbors_map is None:
                tree = cKDTree(points)
                neighbors_map = tree.query_ball_tree(tree, r=search_radius)
                if len(self._neighbors_cache) > 8:
                    self._neighbors_cache.pop(next(iter(self._neighbors_cache)))
                self._neighbors_cache[_nkey] = neighbors_map
        return neighbors_map

    # ==========================================
    # FEATURE EXTRACTION HELPER
    # ==========================================
    def _compute_sector_feature(self, s_img, edge_aware):
        """Return a 75-dim or 79-dim LAB feature vector for a tile-sized crop."""
        mat = s_img.resize((5, 5), Image.Resampling.BOX)
        arr = np.array(mat) / 255.0
        lab_5x5 = skimage.color.rgb2lab(arr)  # (5, 5, 3)
        lab = lab_5x5.flatten()
        lab[0::3] /= 100.0
        lab[1::3] = (lab[1::3] + 128) / 255.0
        lab[2::3] = (lab[2::3] + 128) / 255.0
        vec = lab.astype(np.float32)
        if edge_aware:
            edge_feats = np.array([
                lab_5x5[0, :, 0].mean() / 100.0,   # top row
                lab_5x5[:, 4, 0].mean() / 100.0,   # right column
                lab_5x5[4, :, 0].mean() / 100.0,   # bottom row
                lab_5x5[:, 0, 0].mean() / 100.0,   # left column
            ], dtype=np.float32) * EDGE_WEIGHT
            vec = np.concatenate([vec, edge_feats])
        return vec

    # ==========================================
    # KITE GRID MATHEMATICS
    # ==========================================
    def _get_kite_poly(self, cx, cy, s, k):
        """Return the 4 vertices of a single kite on a flat-topped hexagonal grid.

        Args:
            cx, cy: Cartesian centre of the parent hexagon.
            s:      Hexagon side length in pixels.
            k:      Kite index within the hexagon (0–5).

        Returns:
            List of four (x, y) tuples: [hex_centre, edge_mid(k-1), vertex(k), edge_mid(k)].
        """
        r3 = math.sqrt(3)
        def P(idx):
            angle = math.radians(idx * 60)
            return (cx + s * math.cos(angle), cy + s * math.sin(angle))

        def M(idx):
            angle = math.radians(idx * 60 + 30)
            return (cx + s * r3/2 * math.cos(angle), cy + s * r3/2 * math.sin(angle))

        return [(cx, cy), M((k-1) % 6), P(k), M(k)]

    def _transform_kite_index(self, base_q, base_r, base_k, offset_q, offset_r, rot, flip):
        """Apply a topological transformation to kite axial coordinates (q, r, k).

        Args:
            base_q, base_r, base_k: Source kite coordinates.
            offset_q, offset_r:     Translation in axial hex space.
            rot:                    Number of 60-degree counter-clockwise rotations.
            flip:                   Whether to mirror along the horizontal axis first.

        Returns:
            Transformed (q, r, k) tuple.
        """
        q, r, k = base_q, base_r, base_k

        if flip:
            q, r = q, -q - r
            k = (6 - k) % 6

        for _ in range(rot):
            q, r = -r, q + r
            k = (k + 1) % 6

        return (q + offset_q, r + offset_r, k)

    # ==========================================
    # STANDARD SHAPES AND MASKS
    # ==========================================
    def _get_shape_mask(self, shape_type, w, h, flipped=False, padding=1.0):
        scale_aa = 4
        W, H = int(w * scale_aa), int(h * scale_aa)
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)
        cx, cy = W/2, H/2

        pad_w = W * (1 - padding) / 2
        pad_h = H * (1 - padding) / 2

        if shape_type == "square" or shape_type == "rectangle_3x1" or shape_type == "brick_wall":
            draw.rectangle((pad_w, pad_h, W-pad_w, H-pad_h), fill=255)
        elif "hexagon" in shape_type and "romb" not in shape_type:
            pts = [(cx, pad_h), (W-pad_w, H*0.25+pad_h/2), (W-pad_w, H*0.75-pad_h/2),
                   (cx, H-pad_h), (pad_w, H*0.75-pad_h/2), (pad_w, H*0.25+pad_h/2)]
            draw.polygon(pts, fill=255)
        elif "romb" in shape_type and "hexagon" not in shape_type:
            pts = [(cx, pad_h), (W-pad_w, cy), (cx, H-pad_h), (pad_w, cy)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_top":
            pts = [(cx, cy), (W - pad_w, H*0.25 + pad_h/2), (cx, 0 + pad_h), (0 + pad_w, H*0.25 + pad_h/2)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_left":
            pts = [(cx, cy), (0 + pad_w, H*0.25 + pad_h/2), (0 + pad_w, H*0.75 - pad_h/2), (cx, H - pad_h)]
            draw.polygon(pts, fill=255)
        elif shape_type == "mask_right":
            pts = [(cx, cy), (cx, H - pad_h), (W - pad_w, H*0.75 - pad_h/2), (W - pad_w, H*0.25 + pad_h/2)]
            draw.polygon(pts, fill=255)
        elif shape_type == "triangle":
            if not flipped: pts = [(cx, pad_h), (W-pad_w, H-pad_h), (pad_w, H-pad_h)]
            else: pts = [(pad_w, pad_h), (W-pad_w, pad_h), (cx, H-pad_h)]
            draw.polygon(pts, fill=255)

        return mask.resize((w, h), Image.Resampling.LANCZOS)

    @staticmethod
    def _load_hires_overlay():
        """Return the set of filenames present in the hi-res overlay dir.

        Built once per render (see _do_render) so the assembly loop never
        touches the filesystem per tile — cheap even with a large overlay,
        and a single iterdir instead of 100k+ stat calls. Reads HIRES_DIR via
        module-global lookup so tests can monkeypatch it. Returns an empty set
        when the dir is absent (overlay becomes a no-op, render bit-identical).
        """
        try:
            return {p.name for p in HIRES_DIR.iterdir() if p.is_file()}
        except (FileNotFoundError, NotADirectoryError):
            return set()

    @staticmethod
    def _resolve_tile_path(path, overlay_names):
        """Redirect a library tile path to its hi-res overlay copy if present.

        The overlay is keyed by filename only (``path.name``), so a tile from
        any library dir is served from ``HIRES_DIR/<name>`` when that name is
        in ``overlay_names`` (the precomputed set from _load_hires_overlay).
        An empty set leaves every path untouched. Accepts str or Path.
        """
        p = Path(path)
        if p.name in overlay_names:
            return HIRES_DIR / p.name
        return p

    def _smart_crop(self, img, target_w, target_h):
        src_w, src_h = img.size
        src_ratio = src_w / src_h; tgt_ratio = target_w / target_h
        if src_ratio > tgt_ratio:
            new_w = int(src_h * tgt_ratio); offset = (src_w - new_w) // 2
            box = (offset, 0, offset + new_w, src_h)
        else:
            new_h = int(src_w / tgt_ratio); offset = (src_h - new_h) // 2
            box = (0, offset, src_w, offset + new_h)
        return img.crop(box).resize((target_w, target_h), Image.Resampling.LANCZOS)

    def _used_tiles_report(self, used_counts):
        """Build the used-tiles list from a per-library-index count array.

        Returns one entry per tile actually placed (count > 0), sorted by
        count descending then path (deterministic, idempotent output). Each
        entry: {"path", "name", "count"}. Names feed the per-source router in
        upgrade_tiles.py (Sprint 3), so basenames must be preserved verbatim.
        """
        entries = []
        for idx, c in enumerate(used_counts):
            c = int(c)
            if c > 0:
                p = self.paths[idx]
                entries.append({"path": str(p), "name": Path(p).name, "count": c})
        entries.sort(key=lambda e: (-e["count"], e["path"]))
        return entries

    def _write_used_tiles(self, output_path, shape_mode):
        """Dump the used-tiles report for the last render next to the mosaic.

        Writes ``<stem>_used_tiles.json`` beside ``output_path`` (stem-based,
        no timestamp -> idempotent overwrite, like the batch CLI naming). Reads
        self.last_used_counts set by _do_render; a no-op if it is missing.
        """
        counts = getattr(self, "last_used_counts", None)
        if counts is None:
            return
        report = self._used_tiles_report(counts)
        out = Path(output_path)
        json_path = out.with_name(f"{out.stem}_used_tiles.json")
        payload = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "engine": "smart",
            "shape_mode": shape_mode,
            "mosaic": out.name,
            "unique_tiles": len(report),
            "total_placements": sum(e["count"] for e in report),
            "tiles": report,
        }
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"Used-tiles report: {json_path.name} "
              f"({len(report)} unique tiles, {payload['total_placements']} placements)")

    def create_mosaic(self, target_path, output_path, resolution_key, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, grout_level=1, save_used_tiles=False, progress_cb=None, cancel_event=None):
        """Public API — resolves resolution_key and delegates to _do_render.

        ``grout_preset`` (None | "thin"/"medium"/"thick") is an independent
        opt-in border pass: when set, hierarchical grout lines are drawn on the
        finished mosaic (see _do_render). Orthogonal to ``border_mode`` (the
        tile-shrink gap), which is left untouched.

        ``save_used_tiles`` (default False) writes ``<stem>_used_tiles.json``
        beside the mosaic — the input for the hi-res upgrade tool
        (``python -m src.tools.upgrade_tiles``). Off by default so routine
        renders don't litter the output directory.
        """
        if not self.paths:
            print("ERROR: Index not loaded.")
            return
        res_map = {"2K": 1920, "4K": 3840, "8K": 7680, "16K": 15360}
        target_long = res_map.get(resolution_key, 3840)
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale_res = target_long / max(img_w, img_h)
        target = target.resize((int(img_w * scale_res), int(img_h * scale_res)), Image.Resampling.LANCZOS)
        result = self._do_render(target, shape_mode, tile_scale, border_mode, blend_strength, tint_strength, grout_preset=grout_preset, grout_level=grout_level, progress_cb=progress_cb, cancel_event=cancel_event)
        save_kwargs = {"quality": 95}
        if str(output_path).lower().endswith((".jpg", ".jpeg")):
            # 4:4:4 chroma (no subsampling): a mosaic is thousands of hard
            # colour edges between tiles; the default 4:2:0 blurs chroma on
            # every seam and grout line. Non-JPEG outputs ignore the key.
            save_kwargs["subsampling"] = 0
        result.save(output_path, **save_kwargs)

        # Report which tiles were used — input for the hi-res upgrade tool.
        if save_used_tiles:
            self._write_used_tiles(output_path, shape_mode)

    def render_preview(self, target_path, short_edge=512, shape_mode="hexagon_romb",
                       tile_scale=1.0, border_mode=False, grout_preset=None,
                       grout_level=1):
        """Return a PIL Image preview at ~short_edge px short side — no file I/O."""
        if not self.paths:
            raise RuntimeError("Index not loaded.")
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale = short_edge / min(img_w, img_h)
        prev_w = max(1, int(img_w * scale))
        prev_h = max(1, int(img_h * scale))
        target = target.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
        return self._do_render(target, shape_mode, tile_scale, border_mode, 0.0, 0.0, grout_preset=grout_preset, grout_level=grout_level)

    def _resolve_matching_modes(self):
        """Resolve edge_aware/allow_mirror, degrading on conflicts (warns on stdout).

        Returns (edge_aware, allow_mirror). Two mutually-exclusive degradations:
          * edge_aware requested but index is 75-dim -> edge_aware off
          * edge_aware AND allow_mirror both on -> allow_mirror off (edge_aware wins)

        The second guard backs up the GUI mutex: allow_mirror reshapes tile
        features as 75-dim (5x5x3), which is incompatible with the 79-dim
        edge-aware features. Without this, _do_render would raise a cryptic
        ValueError on reshape when both modes reach the engine (e.g. via CLI).
        """
        edge_aware = self.settings.get("edge_aware", False)
        allow_mirror = self.settings.get("allow_mirror", False)
        has_edge_features = (self.features.ndim == 2 and self.features.shape[1] == 79)

        if edge_aware and not has_edge_features:
            print("WARNING: Edge-Aware requested but index is 75-dim. "
                  "Rebuild index (Update / Create Index). Falling back to standard matching.")
            edge_aware = False

        if edge_aware and allow_mirror:
            print("WARNING: allow_mirror is incompatible with edge_aware (79-dim "
                  "features). Disabling mirror for this render.")
            allow_mirror = False

        return edge_aware, allow_mirror

    @staticmethod
    def _mean_fill_outside_mask(s_img, mask):
        """Replace pixels outside *mask* with the in-mask mean colour.

        A non-convex tile (kite, spectre) carries a lot of neighbouring content
        in its bounding box; filling the outside with the tile's own mean keeps
        that content from polluting the LAB feature match. Returns *s_img*
        unchanged if the mask is empty.
        """
        arr = np.asarray(s_img, dtype=np.float32)
        m = np.asarray(mask, dtype=np.float32)[:, :, None] / 255.0
        m_sum = float(m.sum())
        if m_sum <= 0.0:
            return s_img
        mean_rgb = (arr * m).sum(axis=(0, 1)) / m_sum
        filled = arr * m + mean_rgb * (1.0 - m)
        return Image.fromarray(np.clip(filled, 0, 255).astype(np.uint8))

    @staticmethod
    def _mask_cell_weights(mask, edge_aware):
        """Per-cell matching weights derived from a tile mask, or None.

        Downsamples *mask* to the 5x5 feature grid with BOX — the same kernel
        `_compute_sector_feature` applies to the image — so each of the 25
        cells gets its mask coverage in [0, 1], repeated x3 for the LAB
        channels. Used by the matching loop to re-score the top-K candidates
        with a weighted Euclidean distance: cells outside the mask are never
        visible in the render, so they should not contribute to the match.

        Weights are normalised to mean 1.0 so the weighted distance keeps the
        magnitude of the unweighted one — otherwise a triangle (~50% coverage)
        would halve its distances and silently double the relative strength of
        the freq_penalty term.

        Returns None when the mask (almost) fully covers the canvas: the
        weighted distance would equal the plain GEMM one, and the caller skips
        the re-scoring entirely, keeping full-mask shapes (square) bit-exact.
        Edge-aware feature dims (the 4 border-strip means) keep weight 1.0 —
        they encode cross-tile continuity, not in-mask content.
        """
        cov = np.asarray(mask.resize((5, 5), Image.Resampling.BOX),
                         dtype=np.float32) / 255.0
        if cov.min() >= 0.999:
            return None
        w = np.repeat(cov.flatten(), 3)  # cell-major, one weight per LAB channel
        total = float(w.sum())
        if total <= 0.0:
            return None  # degenerate mask — fall back to unweighted
        w *= w.size / total
        if edge_aware:
            w = np.concatenate([w, np.ones(4, dtype=np.float32)])
        return w.astype(np.float32)

    def _polygon_sector(self, target, poly, render_padding, aa, edge_aware):
        """Build one non-grid (polygon) sector from a single image-space polygon.

        Shared core of every polygon shape (kites, spectre, and the Sprint 3+
        tilings). `poly` is a list of (x, y) vertices already in image space
        (y down) — any y-flip belongs in the shape generator, not here.

        Steps: shrink toward the polygon centroid by `render_padding`; take the
        bounding box; crop the target to it; `_LazyMask` at supersample `aa`;
        `_mean_fill_outside_mask` so the bbox's neighbouring content does not
        pollute the LAB match; compute the feature.

        Bounding-box strategy is the KITE one (PLAN_SHAPES.md Sprint 2, point 1):
        the paste origin may be negative at the top/left edge, handled by an
        offset repaste (`sb[0] - safe_box[0]`) rather than clamping min to 0.
        This correctly places edge tiles whose polygon spills off-canvas — the
        off-canvas strip stays black and is clipped by the negative-dest
        alpha_composite at assembly time.

        Returns a sector dict {"meta": (0, min_x, min_y, lazy_mask, bw, bh,
        False), "feature": ...} (the caller overwrites the placeholder index 0),
        or None if the sector is degenerate or entirely off-canvas.
        """
        target_w, target_h = target.size
        n = len(poly)
        cx = sum(p[0] for p in poly) / n
        cy = sum(p[1] for p in poly) / n
        padded_poly = [
            (cx + (px - cx) * render_padding, cy + (py - cy) * render_padding)
            for px, py in poly
        ]

        min_x = min(p[0] for p in padded_poly)
        max_x = max(p[0] for p in padded_poly)
        min_y = min(p[1] for p in padded_poly)
        max_y = max(p[1] for p in padded_poly)

        bw, bh = int(max_x - min_x), int(max_y - min_y)
        if bw <= 0 or bh <= 0:
            return None

        safe_box = (int(min_x), int(min_y), int(max_x), int(max_y))
        sb = (max(0, safe_box[0]), max(0, safe_box[1]),
              min(target_w, safe_box[2]), min(target_h, safe_box[3]))
        if sb[2] <= sb[0] or sb[3] <= sb[1]:
            return None

        s_img = target.crop(sb)
        if s_img.size != (bw, bh):
            tmp = Image.new("RGB", (bw, bh), (0, 0, 0))
            tmp.paste(s_img, (sb[0] - safe_box[0], sb[1] - safe_box[1]))
            s_img = tmp

        shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
        lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=aa)
        mask = lazy_mask.render()
        feat_img = self._mean_fill_outside_mask(s_img, mask)

        return {
            "meta": (0, int(min_x), int(min_y), lazy_mask, bw, bh, False),
            "feature": self._compute_sector_feature(feat_img, edge_aware),
            "wmask": self._mask_cell_weights(mask, edge_aware),
        }

    # ==========================================
    # GROUT CELLS  (hierarchical border-pass geometry)
    # ==========================================
    def _grout_cells(self, shape_mode, target_w, target_h, base_s):
        """Build ``(poly, g2, g3)`` cells for the grout pass, in image space
        (y down). Cells reproduce the NOMINAL tile geometry (the same step
        formulas the composite uses) so grout lines land on the tile seams;
        the composite's integer mask-truncation differs by <1 px, well inside
        the grout line width. Registry polygon shapes without an explicit
        branch fall through to the generic case: their SHAPE_MODES generator
        re-yields the exact tile polygons (deterministic for the same
        dimensions, incl. the seeded voronoi), so flat grout lands precisely
        on the seams with no second geometry definition. Returns None only
        for shapes unknown to the registry — the caller then skips the pass.
        """
        if shape_mode == "square":
            return self._grout_cells_square(target_w, target_h, base_s)
        if shape_mode == "triangle":
            return self._grout_cells_triangle(target_w, target_h, base_s)
        if shape_mode == "hexagon":
            return self._grout_cells_hexagon(target_w, target_h, base_s)
        if shape_mode == "kites":
            return self._grout_cells_kites(target_w, target_h, base_s)
        if shape_mode == "poincare":
            return self._grout_cells_poincare(target_w, target_h, base_s)
        if shape_mode == "spectre":
            return self._grout_cells_flat_spectre(target_w, target_h, base_s)
        if shape_mode == "romb":
            return self._grout_cells_flat_romb(target_w, target_h, base_s)
        if shape_mode == "rectangle_3x1":
            th = base_s // 3
            return self._grout_cells_flat_rect(
                target_w, target_h, base_s, th, float(base_s), float(th), 0.0)
        if shape_mode == "brick_wall":
            th = base_s // 2
            return self._grout_cells_flat_rect(
                target_w, target_h, base_s, th, float(base_s), float(th),
                float(base_s // 2))
        if shape_mode == "hexagon_romb":
            return self._grout_cells_flat_hexagon_romb(target_w, target_h, base_s)
        spec = SHAPE_MODES.get(shape_mode)
        if spec is not None and spec.kind == "polygon":
            # Uniform (g2, g3) -> every interior seam is L1, frame closes at
            # L3; _apply_grout then draws these flat (single width).
            return [(list(poly), 0, 0)
                    for poly in spec.generator(self, target_w, target_h, base_s)]
        return None

    def _grout_cells_square(self, target_w, target_h, base_s):
        s = base_s
        cols = int(target_w / s) + 2
        rows = int(target_h / s) + 2
        cells = []
        for r in range(-1, rows):
            for c in range(-1, cols):
                x, y = c * s, r * s
                poly = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
                cells.append((poly, (c // 3, r // 3), (c // 9, r // 9)))
        return cells

    def _grout_cells_triangle(self, target_w, target_h, base_s):
        # Matches the composite's triangle grid exactly (tile_w=base_s,
        # tile_h=int(base_s*0.866), step_x=base_s/2). The vertex lattice and the
        # class-0-corner "owner" grouping are the reviewed proposal geometry.
        w = float(base_s)
        h = float(int(base_s * 0.866))
        cols = int(target_w / (w / 2)) + 2
        rows = int(target_h / h) + 2

        def owner(corners):
            for (a, b) in corners:
                if a % 3 == 0:
                    return (a, b)
            raise AssertionError("triangle grout: no class-0 corner")

        def hex_axial(a, b):
            p = a // 3
            j = (b - ((1 + p) % 2)) // 2
            return (p, j - (p - (p & 1)) // 2)

        cells = []
        for r in range(-1, rows):
            for c in range(-1, cols):
                if (c + r) % 2 == 0:
                    corners = [(c, r + 1), (c + 2, r + 1), (c + 1, r)]
                else:
                    corners = [(c, r), (c + 2, r), (c + 1, r + 1)]
                poly = [(a * w / 2, b * h) for (a, b) in corners]
                own = owner(corners)
                cells.append((poly, own, sub7(*hex_axial(*own))))
        return cells

    def _grout_cells_hexagon(self, target_w, target_h, base_s):
        # Hexes on the composite's offset grid (odd rows shifted +base_s/2).
        # Offset->axial q = c - (r - (r&1))//2 (r_axial = r) so the sub7 flowers
        # are spatially contiguous; see test_grout_engine.
        #
        # th is the FLOAT regular-hexagon height base_s*2/sqrt(3); the composite
        # truncates it to int for the mask, but grout needs th*0.75 == step_y
        # exactly or the diagonal edges of adjacent rows miss each other and
        # classify_edges finds no shared edges (all become frame boundaries ->
        # flat grout with black gaps). The <1 px difference from the composite's
        # int mask is hidden under the line width and the 2% tile overlap.
        hr3 = math.sqrt(3) / 2
        tw = base_s
        th = base_s * 2.0 / math.sqrt(3)
        step_x = float(tw)
        step_y = base_s * hr3
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (base_s / 2 if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x + tw / 2, pos_y),
                    (pos_x + tw,     pos_y + th * 0.25),
                    (pos_x + tw,     pos_y + th * 0.75),
                    (pos_x + tw / 2, pos_y + th),
                    (pos_x,          pos_y + th * 0.75),
                    (pos_x,          pos_y + th * 0.25),
                ]
                q = c - (r - (r & 1)) // 2
                g2 = sub7(q, r)
                cells.append((poly, g2, sub7(*g2)))
        return cells

    def _grout_cells_kites(self, target_w, target_h, base_s):
        # Mirrors _gen_kites (same q,r,k iteration and y-flip) so lines sit on
        # the composited kite edges; L2 = parent hexagon, L3 = its 7-flower.
        s = base_s
        r3 = math.sqrt(3)
        range_q = int(target_w / (1.5 * s)) + 3
        range_r = int(target_h / (r3 * s)) + 3
        cells = []
        for q in range(-range_q, range_q):
            r_mid = -(q // 2)
            for r in range(r_mid - range_r, r_mid + range_r):
                cx = 1.5 * s * q
                cy = r3 * s * (r + q / 2.0)
                if -2 * s < cx < target_w + 2 * s and -2 * s < cy < target_h + 2 * s:
                    g3 = sub7(q, r)
                    for k in range(6):
                        poly = self._get_kite_poly(cx, cy, s, k)
                        cent_x = sum(p[0] for p in poly) / 4
                        cent_y = sum(p[1] for p in poly) / 4
                        if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                            img_poly = [(px, target_h - py) for px, py in poly]
                            cells.append((img_poly, (q, r), g3))
        return cells

    def _grout_cells_poincare(self, target_w, target_h, base_s):
        # Re-yield the step-2 hyperbolic quad mesh (_poincare_cells already emits
        # image-space polys plus its own grouping) as hierarchical grout cells:
        #   L1 = the quad sub-cell (nd^2 per kite),
        #   L2 = the parent khatam kite  -> g2 = (hi, k),
        #   L3 = the 7-kite heptagon     -> g3 = hi.
        # The constructive anti-T-junction snapping (arc splits pinned to the
        # global step-1 grid, every cell emitting all its arc samples as
        # vertices) means adjacent cells hand classify_edges identical seam
        # segments even with differing nd, so shared seams stay at L1/L2 instead
        # of being promoted to frame boundaries (L3). Deterministic, no RNG.
        return [(list(poly), (hi, k), hi)
                for poly, hi, k in _poincare_cells(target_w, target_h, base_s)]

    def _grout_cells_flat_spectre(self, target_w, target_h, base_s):
        # Flat (non-hierarchical) grout: every spectre monotile shares one group
        # id, so classify_edges keeps the interior seams at L1 and closes the
        # frame-boundary edges at L3. generate_spectre_tiling emits nominal
        # image-space points (the same source _gen_spectre composites from), so
        # the grout lines land on the seams. _apply_grout draws all three levels
        # at one uniform width for flat shapes, so the L1/L3 split only decides
        # which segments exist, not their thickness.
        return [(list(spec.points), 0, 0)
                for spec in generate_spectre_tiling(target_w, target_h, base_s)]

    def _grout_cells_flat_romb(self, target_w, target_h, base_s):
        # Mirrors the composite's romb grid (tile_w=base_s, step_x=base_s,
        # step_y=base_s*0.75, odd rows shifted +base_s/2), same -1 start so the
        # edge wedges are covered. tile_h MUST be the FLOAT base_s*1.5: the
        # composite truncates it to int for the mask, but grout needs the exact
        # value so each diamond's side vertices sit exactly step_y (= tile_h/2)
        # below its top -> adjacent rows share edges. With int() the seam splits
        # by <1 px and classify_edges finds no shared edges (all become frame
        # boundaries) -- the same lesson as the hexagon th. Flat: one group id,
        # so interior seams stay L1 and only the frame boundary is L3.
        tile_w = float(base_s)
        tile_h = base_s * 1.5
        step_x = float(base_s)
        step_y = base_s * 0.75
        offset_odd = base_s / 2.0
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (offset_odd if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x + tile_w / 2, pos_y),
                    (pos_x + tile_w,     pos_y + tile_h / 2),
                    (pos_x + tile_w / 2, pos_y + tile_h),
                    (pos_x,              pos_y + tile_h / 2),
                ]
                cells.append((poly, 0, 0))
        return cells

    def _grout_cells_flat_rect(self, target_w, target_h,
                               tile_w, tile_h, step_x, step_y, offset_odd):
        # Shared flat-grout geometry for the rectangular grids (rectangle_3x1,
        # brick_wall), same -1 start as the composite so the edge wedges are
        # covered. Rectangles abut EXACTLY, so unlike romb/hexagon the steps
        # stay at the integer canvas size (tile_h passed already //-truncated);
        # a float step here would open the 1-px gaps the composite comment
        # warns about. brick_wall's half-brick offset makes the horizontal
        # mortar meet vertical edges at T-junctions -- harmless for flat grout:
        # every level draws one width and the collinear horizontal segments of
        # adjacent rows paint the same line (no gap, no visible doubling).
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (offset_odd if r % 2 == 1 else 0.0)
                poly = [
                    (pos_x, pos_y),
                    (pos_x + tile_w, pos_y),
                    (pos_x + tile_w, pos_y + tile_h),
                    (pos_x, pos_y + tile_h),
                ]
                cells.append((poly, 0, 0))
        return cells

    def _grout_cells_flat_hexagon_romb(self, target_w, target_h, base_s):
        # Variant 2 of the hexagon_romb grout: the composite builds each hexagon
        # from three romb sub-masks (mask_top/left/right) -- three separate
        # photos -- so the grout splits every hexagon into its three rhombi (the
        # internal "Y" through the centre), not just the outer hexagon outline.
        # Same hex grid as _grout_cells_hexagon (tw=base_s, step_x=base_s,
        # step_y=base_s*sqrt3/2, odd rows +base_s/2); th MUST be the FLOAT
        # base_s*2/sqrt3 so the outer hexagon edges align with neighbours and
        # the rhombi share edges -- the th lesson again. Flat: one group id, so
        # the three rhombi of a hexagon share the internal spokes at L1 and
        # adjacent hexagons share the outer edges at L1; only the frame is L3.
        hr3 = math.sqrt(3) / 2
        tw = float(base_s)
        th = base_s * 2.0 / math.sqrt(3)
        step_x = float(base_s)
        step_y = base_s * hr3
        cols = int(target_w / step_x) + 2
        rows = int(target_h / step_y) + 2
        cells = []
        for r in range(-1, rows):
            pos_y = r * step_y
            for c in range(-1, cols):
                pos_x = c * step_x + (base_s / 2 if r % 2 == 1 else 0.0)
                C = (pos_x + tw / 2, pos_y + th / 2)          # shared centre
                T = (pos_x + tw / 2, pos_y)                   # top
                UR = (pos_x + tw, pos_y + th * 0.25)          # upper-right
                LR = (pos_x + tw, pos_y + th * 0.75)          # lower-right
                B = (pos_x + tw / 2, pos_y + th)              # bottom
                LL = (pos_x, pos_y + th * 0.75)               # lower-left
                UL = (pos_x, pos_y + th * 0.25)               # upper-left
                cells.append(([C, UR, T, UL], 0, 0))          # top romb
                cells.append(([C, UL, LL, B], 0, 0))          # left romb
                cells.append(([C, B, LR, UR], 0, 0))          # right romb
        return cells

    # Shapes with an approved multi-level grouping get graded widths (thin L1 ->
    # thick L3); every other supported shape draws flat single-width grout.
    _HIERARCHICAL_GROUT = ("square", "triangle", "hexagon", "kites", "poincare")

    def _apply_grout(self, mosaic_rgb, shape_mode, target_w, target_h, base_s,
                     preset, min_level=1):
        """Draw the grout overlay on the finished RGB mosaic.

        Hierarchical shapes (``_HIERARCHICAL_GROUT``) get graded widths from the
        preset (thin L1 -> thick L3). Flat shapes reuse the same classified
        segments but draw every level at one uniform width (the preset's L1),
        including the frame-boundary edges (drawn, not suppressed). A no-op (with
        a note) for shapes still lacking any grouping.

        ``min_level`` picks the smallest structure that gets an outline (kites:
        1 = each kite, 2 = the 6-kite hexagon, 3 = the 7-hexagon flower). Flat
        shapes own a single level, so for them the choice is ignored rather than
        honoured — obeying it would erase their grout entirely and leave a bare
        frame.
        """
        cells = self._grout_cells(shape_mode, target_w, target_h, base_s)
        if cells is None:
            print(f"Grout: '{shape_mode}' has no grouping yet — grout skipped.")
            return
        hierarchical = shape_mode in self._HIERARCHICAL_GROUT
        if hierarchical:
            level_w = scale_widths(preset, base_s, min_level=min_level)
            kind = f"hierarchical, from level {min_level}"
        else:
            w = scale_widths(preset, base_s)[1]
            level_w = {1: w, 2: w, 3: w}
            kind = "flat"
            if min_level > 1:
                print(f"Grout: '{shape_mode}' has no tile grouping — "
                      f"level {min_level} ignored, drawing every seam.")
        print(f"Grout: drawing {kind} borders '{preset}' over {len(cells)} cells...")
        by_level = classify_edges(cells)
        draw_grout(mosaic_rgb, by_level, level_w, color=(0, 0, 0))

    def _do_render(self, target, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, grout_level=1, progress_cb=None, cancel_event=None):
        """Core rendering kernel — accepts a pre-scaled PIL Image, returns PIL Image.

        ``progress_cb``, if given, is called ``progress_cb(done, total)`` after each
        matching chunk during the final assembly loop (the dominant cost), where
        ``total`` is the number of sectors. Used by the GUI to drive a progress bar.

        ``cancel_event`` (``threading.Event``), if given, is polled at loop
        boundaries in both the sector-building and matching passes; when set,
        the render aborts by raising RenderCancelled (no partial output).
        """
        def _check_cancel():
            if cancel_event is not None and cancel_event.is_set():
                raise RenderCancelled("Render cancelled by user.")

        edge_aware, allow_mirror = self._resolve_matching_modes()

        target_w, target_h = target.size
        base_s = int(100 * tile_scale)
        if base_s < 10: base_s = 10
        render_padding = 0.94 if border_mode else 1.02

        final_mosaic = Image.new("RGBA", (target_w, target_h), (0,0,0,255))
        sectors_data = []

        # ==========================================
        # KITE TILING (DELTOIDAL TRIHEXAGONAL, PER-TILE)
        # ==========================================
        if shape_mode == "kites":
            # Each hexagon on the flat-topped grid splits into 6 kites; every
            # kite is its own sector (one photo per kite). The earlier "kite"
            # mode bundled 8 kites into randomly-oriented einstein "hats", which
            # read as chaotic blobs and emphasised the black borders. Per-tile
            # is fully deterministic (no RNG): the (q, r, k) iteration order is a
            # pure function of geometry, so preview and render stay reproducible
            # and the _neighbors_cache entry keyed by _nkey is stable.
            print(f"Mode: Kite tiling (deltoidal, per-tile). Borders: {border_mode}")

            s  = base_s
            r3 = math.sqrt(3)

            range_q = int(target_w / (1.5 * s)) + 3
            range_r = int(target_h / (r3 * s)) + 3

            print("Building kite grid...")
            target_kites = []
            for q in range(-range_q, range_q):
                _check_cancel()
                # centre the r-window on -q/2 (same fix as _gen_kites): the shear
                # term q/2 in cy displaced the scanned band at large |q|, leaving
                # the bottom-right corner without kites (fixed 2026-07-04)
                r_mid = -(q // 2)
                for r in range(r_mid - range_r, r_mid + range_r):
                    cx = 1.5 * s * q
                    cy = r3 * s * (r + q / 2.0)

                    if -2*s < cx < target_w + 2*s and -2*s < cy < target_h + 2*s:
                        for k in range(6):
                            poly   = self._get_kite_poly(cx, cy, s, k)
                            cent_x = sum(p[0] for p in poly) / 4
                            cent_y = sum(p[1] for p in poly) / 4

                            if 0 <= cent_x < target_w and 0 <= cent_y < target_h:
                                target_kites.append((cx, cy, k))

            print(f"Rendering {len(target_kites)} kites...")
            for i_kite, (cx, cy, k) in enumerate(tqdm(target_kites, desc="Sampling kite sectors")):
                if i_kite % 256 == 0:
                    _check_cancel()
                poly = self._get_kite_poly(cx, cy, s, k)
                kite_cx = sum(p[0] for p in poly) / 4
                kite_cy = sum(p[1] for p in poly) / 4

                # Shrink toward the kite's own centroid (not a hat centroid): the
                # black border now outlines every individual kite.
                padded_poly = []
                for px, py in poly:
                    nx = kite_cx + (px - kite_cx) * render_padding
                    ny = kite_cy + (py - kite_cy) * render_padding
                    padded_poly.append((nx, target_h - ny))

                min_x = min(p[0] for p in padded_poly)
                max_x = max(p[0] for p in padded_poly)
                min_y = min(p[1] for p in padded_poly)
                max_y = max(p[1] for p in padded_poly)

                bw, bh = int(max_x - min_x), int(max_y - min_y)
                if bw <= 0 or bh <= 0: continue

                safe_box = (int(min_x), int(min_y), int(max_x), int(max_y))
                sb = (max(0, safe_box[0]), max(0, safe_box[1]), min(target_w, safe_box[2]), min(target_h, safe_box[3]))
                if sb[2] <= sb[0] or sb[3] <= sb[1]: continue

                s_img = target.crop(sb)
                if s_img.size != (bw, bh):
                    tmp = Image.new("RGB", (bw, bh), (0,0,0))
                    tmp.paste(s_img, (sb[0] - safe_box[0], sb[1] - safe_box[1]))
                    s_img = tmp

                shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
                lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=1)
                mask_kite = lazy_mask.render()

                # Replace outside-mask pixels with the kite's mean colour so the
                # bounding box does not leak neighbouring content into the LAB
                # match (same treatment as the spectre mode).
                feat_img = self._mean_fill_outside_mask(s_img, mask_kite)

                # is_hat=False -> standard spatial anti-repetition across all
                # neighbours (no hat grouping to scope it to). Store the lazy
                # descriptor, not the rasterised mask: it is re-rendered
                # identically at composite time (see putalpha).
                sectors_data.append({
                    "meta": (i_kite, int(min_x), int(min_y), lazy_mask, bw, bh, False),
                    "feature": self._compute_sector_feature(feat_img, edge_aware),
                    "wmask": self._mask_cell_weights(mask_kite, edge_aware)
                })

        # ==========================================
        # SPECTRE TILING (CHIRAL APERIODIC MONOTILE)
        # ==========================================
        elif shape_mode == "spectre":
            print(f"Mode: Spectre (chiral aperiodic monotile). Borders: {border_mode}")

            spectres = generate_spectre_tiling(target_w, target_h, base_s)
            print(f"Aperiodic tiling ready: {len(spectres)} spectres")

            scale_aa = 4
            for i_spec, spec in enumerate(tqdm(spectres, desc="Sampling spectre sectors")):
                if i_spec % 256 == 0:
                    _check_cancel()
                spec_cx = sum(p[0] for p in spec.points) / len(spec.points)
                spec_cy = sum(p[1] for p in spec.points) / len(spec.points)
                padded_poly = [
                    (spec_cx + (px - spec_cx) * render_padding,
                     spec_cy + (py - spec_cy) * render_padding)
                    for px, py in spec.points
                ]

                # Clamp the bounding box at the top/left edges so the paste
                # origin stays non-negative (alpha_composite requirement).
                min_x = max(0.0, min(p[0] for p in padded_poly))
                min_y = max(0.0, min(p[1] for p in padded_poly))
                max_x = max(p[0] for p in padded_poly)
                max_y = max(p[1] for p in padded_poly)

                bw, bh = int(max_x - min_x), int(max_y - min_y)
                if bw <= 0 or bh <= 0: continue

                safe_box = (int(min_x), int(min_y),
                            min(target_w, int(max_x)), min(target_h, int(max_y)))
                if safe_box[2] <= safe_box[0] or safe_box[3] <= safe_box[1]: continue

                s_img = target.crop(safe_box)
                if s_img.size != (bw, bh):
                    tmp = Image.new("RGB", (bw, bh), (0,0,0))
                    tmp.paste(s_img, (0, 0))
                    s_img = tmp

                # Anti-aliased polygon mask (supersampled, like _get_shape_mask):
                # store the unscaled polygon; _LazyMask.render() supersamples by
                # scale_aa and downsamples with LANCZOS — identical to the build pass.
                shifted_poly = [(p[0] - min_x, p[1] - min_y) for p in padded_poly]
                lazy_mask = _LazyMask(shifted_poly, bw, bh, aa=scale_aa)
                mask_spec = lazy_mask.render()

                # The spectre is non-convex, so its bounding box contains a
                # lot of neighbouring content; replace outside-mask pixels
                # with the tile's mean colour so they do not pollute the
                # LAB match.
                feat_img = self._mean_fill_outside_mask(s_img, mask_spec)

                # Store the lazy descriptor, not the rasterised mask (re-rendered
                # identically at composite time — see putalpha).
                sectors_data.append({
                    "meta": (i_spec, int(min_x), int(min_y), lazy_mask, bw, bh, False),
                    "feature": self._compute_sector_feature(feat_img, edge_aware),
                    "wmask": self._mask_cell_weights(mask_spec, edge_aware)
                })

        # ==========================================
        # GENERIC POLYGON SHAPES (registry-driven)
        # ==========================================
        # Every polygon shape beyond kites/spectre flows through the shared
        # `_polygon_sector` helper: the SHAPE_MODES generator yields image-space
        # polygons, the helper builds one sector per polygon (crop + LazyMask +
        # mean-fill + feature). kites/spectre keep their own branches above only
        # to preserve their locked golden hashes (spectre's edge bbox strategy
        # differs); migrating them here is a bit-identical cleanup for later.
        elif SHAPE_MODES.get(shape_mode) and SHAPE_MODES[shape_mode].kind == "polygon":
            spec = SHAPE_MODES[shape_mode]
            print(f"Mode: {shape_mode} (polygon, aa={spec.aa}). Borders: {border_mode}")
            polys = list(spec.generator(self, target_w, target_h, base_s))
            print(f"Polygon tiling ready: {len(polys)} cells")
            for i_poly, poly in enumerate(
                    tqdm(polys, desc=f"Sampling {shape_mode} sectors")):
                if i_poly % 256 == 0:
                    _check_cancel()
                sector = self._polygon_sector(
                    target, poly, render_padding, spec.aa, edge_aware)
                if sector is None:
                    continue
                # _polygon_sector emits a placeholder meta index 0; stamp the
                # real sector index (only consulted for is_hat grouping, which
                # is always False for these shapes).
                m = sector["meta"]
                sector["meta"] = (i_poly, m[1], m[2], m[3], m[4], m[5], m[6])
                sectors_data.append(sector)

        # ==========================================
        # STANDARD GRID (HexagonRomb, Square, Triangle, …)
        # ==========================================
        else:
            print(f"Mode: Grid ({shape_mode}). Borders: {border_mode}")
            # Mask canvases (tile_w/tile_h) stay integer. Grid steps are kept
            # as floats ONLY for geometries whose mask overlaps past the step
            # (hexagon, romb) — there the old int() truncation compounded row
            # after row into a ~0.7% vertical squeeze. Shapes that abut
            # exactly (rectangle, brick, triangle rows) must keep the step
            # equal to the integer canvas size or 1-px gaps open up.
            hr3 = math.sqrt(3) / 2
            tile_w, tile_h = base_s, base_s
            step_x, step_y = float(base_s), float(base_s)
            offset_odd_row_x = 0.0

            if shape_mode == "rectangle_3x1": tile_h=base_s//3; step_y=float(tile_h)
            elif shape_mode == "brick_wall": tile_h=base_s//2; step_y=float(tile_h); offset_odd_row_x=base_s//2
            elif "hexagon" in shape_mode or shape_mode == "hexagon_romb":
                tile_w=base_s; tile_h=int(base_s*1.155)
                step_x=float(tile_w); step_y=base_s*hr3; offset_odd_row_x=base_s/2
            elif shape_mode == "triangle": tile_w=base_s; tile_h=int(base_s*0.866); step_x=base_s/2; step_y=float(tile_h)
            elif shape_mode == "romb": tile_w=base_s; tile_h=int(base_s*1.5); step_x=float(tile_w); step_y=base_s*0.75; offset_odd_row_x=base_s/2

            cols = int(target_w / step_x) + 2
            rows = int(target_h / step_y) + 2

            if shape_mode == "hexagon_romb":
                # The composite hexagon is drawn from the three romb masks
                # below; _get_shape_mask has no "hexagon_romb" branch and
                # would silently return a blank mask here.
                mask_norm = mask_flip = None
                mask_left = self._get_shape_mask("mask_left", tile_w, tile_h, padding=render_padding)
                mask_right = self._get_shape_mask("mask_right", tile_w, tile_h, padding=render_padding)
                mask_top = self._get_shape_mask("mask_top", tile_w, tile_h, padding=render_padding)
                # Matching weights per sub-romb mask (order must match `masks`
                # in the scan loop below).
                romb_weights = [self._mask_cell_weights(m, edge_aware)
                                for m in (mask_left, mask_right, mask_top)]
            else:
                mask_norm = self._get_shape_mask(shape_mode, tile_w, tile_h, False, padding=render_padding)
                mask_flip = self._get_shape_mask(shape_mode, tile_w, tile_h, True, padding=render_padding)
                w_norm_mask = self._mask_cell_weights(mask_norm, edge_aware)
                w_flip_mask = self._mask_cell_weights(mask_flip, edge_aware)

            print("Scanning grid...")
            # Start at -1, not 0: offset/half-step geometries (hexagon,
            # hexagon_romb, romb, brick_wall, triangle) leave a triangular or
            # half-tile gap along the top/left edge because odd rows are pushed
            # right by offset_odd_row_x and rows below the first don't cover the
            # canvas top. The phantom -1 row/column fills those wedges; its
            # tiles land at negative px/py and are clipped by the safe-box +
            # safe[2]<=safe[0] guards below (off-canvas tiles, e.g. square's
            # even-row c=-1, collapse to zero width and are skipped). Pillow
            # 11.1 accepts negative dest in alpha_composite, so the partially
            # visible edge tiles composite correctly.
            for r in range(-1, rows):
                _check_cancel()
                for c in range(-1, cols):
                    pos_x = c * step_x
                    pos_y = r * step_y
                    is_flipped = False

                    if shape_mode in ["brick_wall", "hexagon", "hexagon_romb", "romb"]:
                        if r % 2 == 1: pos_x += offset_odd_row_x
                    elif shape_mode == "triangle":
                        if (c+r)%2==1: is_flipped = True

                    if shape_mode == "hexagon_romb":
                        off_d = tile_w // 4
                        sample_offsets = [(-off_d, off_d), (off_d, off_d), (0, -off_d)]
                        masks = [mask_left, mask_right, mask_top]
                        for k in range(3):
                            spx = int(pos_x + tile_w/2 + sample_offsets[k][0] - tile_w/2)
                            spy = int(pos_y + tile_h/2 + sample_offsets[k][1] - tile_h/2)
                            if spx > target_w or spy > target_h: continue
                            safe = (max(0, spx), max(0, spy), min(target_w, spx+tile_w), min(target_h, spy+tile_h))
                            if safe[2]<=safe[0]: continue
                            s_img = target.crop(safe)
                            if s_img.size != (tile_w, tile_h):
                                tmp = Image.new("RGB", (tile_w, tile_h), (0,0,0)); tmp.paste(s_img, (0,0)); s_img = tmp

                            # Each romb mask covers ~1/3 of the tile canvas;
                            # mean-fill the rest so neighbouring rombs don't
                            # pollute the LAB match (same as kites/spectre).
                            feat_img = self._mean_fill_outside_mask(s_img, masks[k])

                            sectors_data.append({
                                "meta": (r, int(pos_x), int(pos_y), masks[k], tile_w, tile_h, False),
                                "feature": self._compute_sector_feature(feat_img, edge_aware),
                                "wmask": romb_weights[k]
                            })
                        continue

                    px, py = int(pos_x), int(pos_y)
                    if px > target_w or py > target_h: continue
                    safe = (max(0, px), max(0, py), min(target_w, px+tile_w), min(target_h, py+tile_h))
                    if safe[2]<=safe[0]: continue
                    s_img = target.crop(safe)
                    if s_img.size != (tile_w, tile_h):
                        tmp = Image.new("RGB", (tile_w, tile_h), (0,0,0)); tmp.paste(s_img, (0,0)); s_img = tmp

                    current_mask = mask_flip if is_flipped else mask_norm
                    # Non-rectangular grid masks (triangle ~50%, hexagon ~25%,
                    # romb ~50% of the canvas outside the mask) used to match
                    # against neighbouring content; mean-fill it away like the
                    # kites/spectre branches do. For square (full-canvas mask,
                    # padding>=1.0) this is numerically a no-op.
                    feat_img = self._mean_fill_outside_mask(s_img, current_mask)
                    sectors_data.append({
                        "meta": (r, px, py, current_mask, tile_w, tile_h, False),
                        "feature": self._compute_sector_feature(feat_img, edge_aware),
                        "wmask": w_flip_mask if is_flipped else w_norm_mask
                    })

        # ==========================================
        # PHOTO-TO-TILE MATCHING (SHARED PASS)
        # ==========================================
        if not sectors_data:
            # Returning None here used to surface as a cryptic AttributeError
            # in create_mosaic (result.save on None).
            raise ValueError(
                f"No tiles generated for {target_w}x{target_h} target with "
                f"shape '{shape_mode}' and tile scale {tile_scale} — the "
                f"target is too small for the chosen tile size.")

        # Select which tile features to use for matching.
        # edge_aware/allow_mirror conflict already resolved by _resolve_matching_modes
        # (GUI enforces the mutex; the engine guard backs it up for CLI/programmatic use).
        tile_features = self.features if edge_aware else self.features[:, :75]

        print(f"Building Spatial Tree for {len(sectors_data)} tiles...")
        points = [(s["meta"][1] + s["meta"][4]/2.0, s["meta"][2] + s["meta"][5]/2.0) for s in sectors_data]
        search_radius = base_s * 1.5
        # border_mode changes render_padding (0.94 vs 1.02), which can shift the
        # sector count of edge tiles for kite/spectre. Without it in the key, a
        # second render of the same geometry with the border toggled reuses a
        # stale neighbors_map of the wrong length -> IndexError.
        _nkey = (base_s, shape_mode, target_w, target_h, border_mode)
        neighbors_map = self._get_neighbors_map(_nkey, points, search_radius)

        print("Matching and generating final mosaic...")
        if tint_strength > 0.0:
            print(f"  Tile Tint active: {int(tint_strength * 100)}% (pixel lerp toward sector colour)")
        if blend_strength > 0.0:
            print(f"  Color Blend will be applied at save: {int(blend_strength * 100)}%")
        if edge_aware:
            print("  Edge-Aware Matching active (79-dim features)")

        tgt_features = np.array([x["feature"] for x in sectors_data])
        # int64: used_counts**2 in the frequency penalty (below) overflows int32
        # once a tile is reused >46340 times (huge render + tiny library), which
        # would wrap negative and invert the penalty.
        used_counts = np.zeros(len(self.paths), dtype=np.int64)
        sector_assignments = -1 * np.ones(len(sectors_data), dtype=np.int32)
        failed_tiles = 0

        # Snapshot the hi-res overlay once (not per tile) so the assembly loop
        # below can redirect any matched tile to its sharp copy without a
        # per-open filesystem stat. Empty when data/tiles_hires is absent.
        hires_names = self._load_hires_overlay()
        if hires_names:
            print(f"  Hi-res overlay active: {len(hires_names)} tiles in {HIRES_DIR.name}/")

        features_norm = tile_features.astype(np.float32, copy=False)
        features_flip = None
        if allow_mirror:
            # tile_features is guaranteed 75-dim here: _resolve_matching_modes
            # disables allow_mirror whenever edge_aware (79-dim) is active.
            reshaped = features_norm.reshape(-1, 5, 5, 3)
            flipped = reshaped[:, :, ::-1, :]
            features_flip = flipped.reshape(-1, 75)

        # Precompute library squared norms once for the GEMM distance (see
        # _euclid_f32). The flip is a column permutation, so its per-tile norm is
        # identical — but recomputing is O(N) and keeps the call site obvious.
        norms_norm = np.einsum("ij,ij->i", features_norm, features_norm)
        norms_flip = (np.einsum("ij,ij->i", features_flip, features_flip)
                      if allow_mirror else None)
        tgt32 = tgt_features.astype(np.float32, copy=False)

        # Adaptive chunk size: cap the float32 distance matrix (or matrices, when
        # mirroring keeps norm+flip resident together) at ~256 MB. The old fixed
        # chunk_size=500 produced a ~1.8 GB float64 matrix (x2 with mirror) — the
        # dominant peak-RAM spike at 16K.
        n_lib = max(features_norm.shape[0], 1)
        n_matrices = 2 if allow_mirror else 1
        rows_budget = (256 * 1024 * 1024) // (n_lib * 4 * n_matrices)
        chunk_size = int(np.clip(rows_budget, 64, 500))

        top_k = min(len(self.paths), 200)

        for i in tqdm(range(0, len(sectors_data), chunk_size)):
            _check_cancel()
            end = min(i + chunk_size, len(sectors_data))
            chunk_tgt = tgt32[i:end]

            dists_norm = _euclid_f32(chunk_tgt, features_norm, norms_norm)
            if allow_mirror:
                dists_flip = _euclid_f32(chunk_tgt, features_flip, norms_flip)

            top_k_norm = np.argpartition(dists_norm, top_k - 1, axis=1)[:, :top_k]
            if allow_mirror:
                top_k_flip = np.argpartition(dists_flip, top_k - 1, axis=1)[:, :top_k]

            for j in range(len(chunk_tgt)):
                global_idx = i + j
                meta = sectors_data[global_idx]["meta"]

                idx_id, px, py, mask, tw, th, is_hat = meta

                # Masked re-scoring: the GEMM top-K above ranks candidates by
                # plain Euclidean distance over the full 5x5 grid; for shaped
                # tiles, re-score those candidates with a weighted distance so
                # cells outside the mask (never visible in the render) stop
                # influencing the choice. wmask is None for full-canvas masks
                # (square) — the plain GEMM distances are used untouched, which
                # keeps those renders bit-exact. O(top_k x dim) per sector.
                wmask = sectors_data[global_idx].get("wmask")
                if wmask is not None:
                    diff = features_norm[top_k_norm[j]] - chunk_tgt[j]
                    dists_w_norm = np.einsum("kd,kd->k", diff * wmask, diff)
                    if allow_mirror:
                        diff = features_flip[top_k_flip[j]] - chunk_tgt[j]
                        dists_w_flip = np.einsum("kd,kd->k", diff * wmask, diff)

                forbidden_indices = set()
                my_neighbors = neighbors_map[global_idx]
                for n_idx in my_neighbors:
                    if n_idx == global_idx: continue
                    if is_hat:
                        if sectors_data[n_idx]["meta"][0] == idx_id:
                            assigned = sector_assignments[n_idx]
                            if assigned != -1: forbidden_indices.add(assigned)
                    else:
                        assigned = sector_assignments[n_idx]
                        if assigned != -1: forbidden_indices.add(assigned)

                candidates = []
                for t, idx in enumerate(top_k_norm[j]):
                    base_d = dists_w_norm[t] if wmask is not None else dists_norm[j, idx]
                    score = base_d + (used_counts[idx]**2 * self.settings["freq_penalty"] * 0.001)
                    if idx in forbidden_indices: score += 1000000.0
                    candidates.append((score, idx, False))

                if allow_mirror:
                    for t, idx in enumerate(top_k_flip[j]):
                        base_d = dists_w_flip[t] if wmask is not None else dists_flip[j, idx]
                        score = base_d + (used_counts[idx]**2 * self.settings["freq_penalty"] * 0.001)
                        if idx in forbidden_indices: score += 1000000.0
                        candidates.append((score, idx, True))

                candidates.sort(key=lambda x: x[0])
                best_score, best_idx, should_mirror = candidates[0]

                used_counts[best_idx] += 1
                sector_assignments[global_idx] = best_idx

                try:
                    tile_path = self._resolve_tile_path(self.paths[best_idx], hires_names)
                    with Image.open(tile_path) as img:
                        img = img.convert("RGBA")
                        if should_mirror: img = ImageOps.mirror(img)

                        img = self._smart_crop(img, tw, th)

                        if tint_strength > 0.0:
                            sector_box = (
                                max(0, px), max(0, py),
                                min(target_w, px + tw), min(target_h, py + th)
                            )
                            if sector_box[2] > sector_box[0] and sector_box[3] > sector_box[1]:
                                sector_crop = target.crop(sector_box)
                                sector_mean = np.array(
                                    sector_crop.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)),
                                    dtype=np.float32)[:3]
                                tile_rgb = img.convert("RGB")
                                tile_arr = np.array(tile_rgb, dtype=np.float32)
                                tile_arr = tile_arr * (1.0 - tint_strength) + sector_mean * tint_strength
                                tile_arr = np.clip(tile_arr, 0, 255).astype(np.uint8)
                                img = Image.fromarray(tile_arr).convert("RGBA")

                        # Grid masks are shared PIL images; kite/spectre store a
                        # _LazyMask re-rasterised here (identical to build time).
                        tile_mask = mask.render() if isinstance(mask, _LazyMask) else mask
                        img.putalpha(tile_mask)
                        final_mosaic.alpha_composite(img, (px, py))
                except Exception:
                    # One bad tile must not abort the render, but silent
                    # holes are debugging hell — count and report below.
                    failed_tiles += 1

            if progress_cb is not None:
                progress_cb(end, len(sectors_data))

        if failed_tiles > 0:
            print(f"WARNING: {failed_tiles} of {len(sectors_data)} tiles "
                  f"failed to load/composite and were skipped (holes show "
                  f"the black background).")

        mosaic_rgb = final_mosaic.convert("RGB")
        if blend_strength > 0.0:
            print(f"Applying Color Blend: {int(blend_strength * 100)}%...")
            original_resized = target.resize(mosaic_rgb.size, Image.Resampling.LANCZOS)
            mosaic_rgb = Image.blend(mosaic_rgb, original_resized, blend_strength)

        # Grout is drawn last so it sits on top of the blend as a hard overlay
        # (a colour blend must not wash the lines out).
        if grout_preset is not None:
            _check_cancel()
            self._apply_grout(mosaic_rgb, shape_mode, target_w, target_h, base_s,
                              grout_preset, min_level=grout_level)
        # Expose which library tiles were placed (indexed like self.paths) so
        # create_mosaic can dump a used-tiles report for the hi-res upgrade
        # tool (Sprint 3). Kept in memory only; render_preview never writes it
        # to disk (it stays a no-I/O path).
        self.last_used_counts = used_counts
        return mosaic_rgb
