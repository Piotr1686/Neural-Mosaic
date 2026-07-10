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
import json
import threading
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from tqdm import tqdm
from scipy.spatial import cKDTree, Voronoi
import skimage.color

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
GROUT_HIERARCHICAL = ("square", "hexagon", "triangle", "kites")

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


def _lloyd_relax(pts, iters, clip=1.6):
    """Lloyd relaxation: move each generator to its Voronoi-cell centroid.
    Rounds seeds toward even 'pebbles' while the phyllotaxis spiral arms
    survive. Unbounded cells stay put."""
    pts = np.asarray(pts, dtype=np.float64)
    for _ in range(iters):
        vor = Voronoi(pts)
        new = pts.copy()
        for i in range(len(pts)):
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


@dataclass(frozen=True)
class ShapeSpec:
    """Descriptor for one tile shape.

    kind      : "grid"    -> axis-aligned crop + shared mask (grid branch).
                "polygon" -> per-tile polygon via `_polygon_sector`.
    generator : callable(engine, target_w, target_h, base_s) -> iterable[poly],
                each poly a list of (x, y) vertices in image space (y down).
                None for grid shapes.
    aa        : anti-aliasing supersample for the polygon mask (1 = native).
    seeded    : reserved for future variable-cell shapes that need a
                deterministic RNG seed (voronoi/phyllotaxis/poincare, S5).
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

    def create_mosaic(self, target_path, output_path, resolution_key, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, progress_cb=None, cancel_event=None):
        """Public API — resolves resolution_key and delegates to _do_render.

        ``grout_preset`` (None | "cienki"/"sredni"/"gruby") is an independent
        opt-in border pass: when set, hierarchical grout lines are drawn on the
        finished mosaic (see _do_render). Orthogonal to ``border_mode`` (the
        tile-shrink gap), which is left untouched.
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
        result = self._do_render(target, shape_mode, tile_scale, border_mode, blend_strength, tint_strength, grout_preset=grout_preset, progress_cb=progress_cb, cancel_event=cancel_event)
        save_kwargs = {"quality": 95}
        if str(output_path).lower().endswith((".jpg", ".jpeg")):
            # 4:4:4 chroma (no subsampling): a mosaic is thousands of hard
            # colour edges between tiles; the default 4:2:0 blurs chroma on
            # every seam and grout line. Non-JPEG outputs ignore the key.
            save_kwargs["subsampling"] = 0
        result.save(output_path, **save_kwargs)

        # Report which tiles were used — input for the hi-res upgrade tool.
        self._write_used_tiles(output_path, shape_mode)

    def render_preview(self, target_path, short_edge=512, shape_mode="hexagon_romb",
                       tile_scale=1.0, border_mode=False, grout_preset=None):
        """Return a PIL Image preview at ~short_edge px short side — no file I/O."""
        if not self.paths:
            raise RuntimeError("Index not loaded.")
        target = Image.open(target_path).convert("RGB")
        img_w, img_h = target.size
        scale = short_edge / min(img_w, img_h)
        prev_w = max(1, int(img_w * scale))
        prev_h = max(1, int(img_h * scale))
        target = target.resize((prev_w, prev_h), Image.Resampling.LANCZOS)
        return self._do_render(target, shape_mode, tile_scale, border_mode, 0.0, 0.0, grout_preset=grout_preset)

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
        the grout line width. Returns None for shapes without an approved
        grouping — the caller then skips the hierarchical pass.
        """
        if shape_mode == "square":
            return self._grout_cells_square(target_w, target_h, base_s)
        if shape_mode == "triangle":
            return self._grout_cells_triangle(target_w, target_h, base_s)
        if shape_mode == "hexagon":
            return self._grout_cells_hexagon(target_w, target_h, base_s)
        if shape_mode == "kites":
            return self._grout_cells_kites(target_w, target_h, base_s)
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
    _HIERARCHICAL_GROUT = ("square", "triangle", "hexagon", "kites")

    def _apply_grout(self, mosaic_rgb, shape_mode, target_w, target_h, base_s, preset):
        """Draw the grout overlay on the finished RGB mosaic.

        Hierarchical shapes (``_HIERARCHICAL_GROUT``) get graded widths from the
        preset (thin L1 -> thick L3). Flat shapes reuse the same classified
        segments but draw every level at one uniform width (the preset's L1),
        including the frame-boundary edges (drawn, not suppressed). A no-op (with
        a note) for shapes still lacking any grouping.
        """
        cells = self._grout_cells(shape_mode, target_w, target_h, base_s)
        if cells is None:
            print(f"Grout: '{shape_mode}' has no grouping yet — grout skipped.")
            return
        widths = scale_widths(preset, base_s)
        if shape_mode in self._HIERARCHICAL_GROUT:
            level_w = widths
            kind = "hierarchical"
        else:
            w = widths[1]
            level_w = {1: w, 2: w, 3: w}
            kind = "flat"
        print(f"Grout: drawing {kind} borders '{preset}' over {len(cells)} cells...")
        by_level = classify_edges(cells)
        draw_grout(ImageDraw.Draw(mosaic_rgb), by_level, level_w, color=(0, 0, 0))

    def _do_render(self, target, shape_mode, tile_scale, border_mode=False, blend_strength=0.0, tint_strength=0.0, grout_preset=None, progress_cb=None, cancel_event=None):
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
                              grout_preset)
        # Expose which library tiles were placed (indexed like self.paths) so
        # create_mosaic can dump a used-tiles report for the hi-res upgrade
        # tool (Sprint 3). Kept in memory only; render_preview never writes it
        # to disk (it stays a no-I/O path).
        self.last_used_counts = used_counts
        return mosaic_rgb
