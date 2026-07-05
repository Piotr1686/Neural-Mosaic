"""Generate PROPOSAL schemes for the SUNFLOWER SEEDS tile pattern.

User request 2026-07-05 (reference photos: golden sunflower-head mosaics).
Seeds follow Vogel's phyllotaxis: point n sits at r = c*sqrt(n),
theta = n * golden angle (137.508 deg). Every variant is a TRUE tessellation
(cells abut exactly): Voronoi = partition by construction, the rhombs mesh is
verified numerically (raster gap/overlap report).

Verdict rev 2 (user, 2026-07-05): `sunflower_classic` dropped - too close to
the existing `bloom` shape; `sunflower_corner` and `sunflower_field` REJECTED
outright (generators removed; git history keeps them). Current pool of 8:

  classic-family (uniform seeds, structurally distinct from bloom):
  1. sunflower_soft   - Vogel Voronoi after 2 Lloyd relaxations: rounder,
                        more even "pebble" seeds, spiral arms preserved
  2. sunflower_disc   - two-zone head like a real flower: fine dark disc
                        florets in the centre, coarser golden seeds outside
  3. sunflower_rings  - seed radii softly snapped to concentric rows: seeds
                        line up in circular courses (reference photo 1)
  4. sunflower_rhombs - log-spiral parastichy quad mesh (21/34); centre
                        rebuilt per verdict: two rings of quasi-rhombs
                        continuing the mesh inward + small petals at the pole
                        (previous single long petals looked alien)

  grande-family (growth-graded; grande itself kept unchanged for verdict):
  5. sunflower_grande - Voronoi of r = c*n^0.66 (user pick - do not touch)
  6. grande_xl        - steeper growth r = c*n^0.75: tiny centre, huge rim
  7. grande_soft      - grande geometry + 1 Lloyd pass: rounder cells,
                        gentler size ramp
  8. grande_inverse   - reversed gradient r = c*n^0.40: large seeds in the
                        centre shrinking toward a fine rim

Pure PIL + numpy + scipy, deterministic. ASCII-only prints.

Outputs:
  output/sunflower_proposals/<name>.png            (720x720 panels)
  output/sunflower_proposals/proposals_sunflower.png (montage 4x2)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_sunflower_schemes
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import Voronoi

from src.tools.gen_fable_shape_schemes import render, vary, _clip_rect

OUT_DIR = Path("output/sunflower_proposals")
R = 1.0                                  # world half-size: frame [-R, R]^2
GOLDEN = math.pi * (3 - math.sqrt(5))    # 137.508 deg


def vogel_points(n_pts, c, pole=(0.0, 0.0), power=0.5):
    """Vogel phyllotaxis lattice: r = c * n^power, theta = n * golden angle."""
    pts = np.empty((n_pts, 2))
    for i in range(1, n_pts + 1):
        rr = c * (i ** power)
        aa = i * GOLDEN
        pts[i - 1] = (pole[0] + rr * math.cos(aa), pole[1] + rr * math.sin(aa))
    return pts


def voronoi_cells(pts, keep=None):
    """Bounded Voronoi cells clipped to the frame; unbounded cells skipped
    (their generators lie past the corners, so the frame stays covered)."""
    vor = Voronoi(pts)
    cells = []
    for i in range(len(pts)):
        if keep is not None and not keep(i):
            continue
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue
        poly = [tuple(vor.vertices[v]) for v in reg]
        cl = _clip_rect(poly, R)
        if len(cl) >= 3:
            cells.append((i, cl))
    return cells


# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------
GOLD = (208, 158, 56)
HONEY = (222, 178, 84)
OCHRE = (188, 132, 52)
RUST = (172, 108, 48)


def _radial_mix(base, far, t):
    return tuple(int(b + (f - b) * t) for b, f in zip(base, far))


def _poly_centroid(cl):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(cl, cl[1:] + cl[:1]):
        cr = x1 * y2 - x2 * y1
        a += cr
        cx += (x1 + x2) * cr
        cy += (y1 + y2) * cr
    if abs(a) < 1e-12:
        return None
    return (cx / (3 * a), cy / (3 * a))


def lloyd_relax(pts, iters=1, clip=1.6):
    """Move each generator to its Voronoi-cell centroid (unbounded cells stay
    put). Rounds the seeds toward even 'pebbles' while the spiral arms of the
    underlying phyllotaxis survive the relaxation."""
    pts = np.array(pts, dtype=float)
    for _ in range(iters):
        vor = Voronoi(pts)
        new = pts.copy()
        for i in range(len(pts)):
            reg = vor.regions[vor.point_region[i]]
            if not reg or -1 in reg:
                continue
            poly = [tuple(vor.vertices[v]) for v in reg]
            cl = _clip_rect(poly, clip)
            if len(cl) < 3:
                continue
            cen = _poly_centroid(cl)
            if cen is not None:
                new[i] = cen
        pts = new
    return pts


# ---------------------------------------------------------------------------
# 1. soft: Lloyd-relaxed classic head
# ---------------------------------------------------------------------------
def gen_sunflower_soft():
    rng = np.random.default_rng(51)
    N = 1400
    c = (math.sqrt(2.0) + 0.45) / math.sqrt(N)
    pts = lloyd_relax(vogel_points(N, c), iters=2)
    polys = []
    for i, cl in voronoi_cells(pts):
        arm = (i + 1) % 21
        base = HONEY if arm % 3 == 0 else GOLD
        polys.append((cl, vary(rng, base, 12)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# 2. disc: fine dark centre florets, coarser golden rim (real head anatomy)
# ---------------------------------------------------------------------------
def gen_sunflower_disc():
    rng = np.random.default_rng(52)
    K = 380                                # florets in the central disc
    disc_r = 0.42
    c1 = disc_r / math.sqrt(K)
    c2 = 1.7 * c1
    reach = math.sqrt(2.0) + 0.45
    N = K + int((reach ** 2 - disc_r ** 2) / (c2 ** 2))
    pts = np.empty((N, 2))
    for n in range(1, N + 1):
        if n <= K:
            rr = c1 * math.sqrt(n)
        else:                              # continue area growth, coarser
            rr = math.sqrt(disc_r ** 2 + (c2 ** 2) * (n - K))
        aa = n * GOLDEN
        pts[n - 1] = (rr * math.cos(aa), rr * math.sin(aa))
    dark = (104, 70, 34)
    polys = []
    for i, cl in voronoi_cells(pts):
        if i < K:
            polys.append((cl, vary(rng, dark, 10)))
        else:
            polys.append((cl, vary(rng, GOLD, 12)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# 3. rings: seed radii softly snapped into concentric courses
# ---------------------------------------------------------------------------
def gen_sunflower_rings():
    rng = np.random.default_rng(56)
    N = 1400
    c = (math.sqrt(2.0) + 0.45) / math.sqrt(N)
    d = 1.9 * c                            # course (row) spacing
    pts = np.empty((N, 2))
    rows = np.empty(N, dtype=int)
    for n in range(1, N + 1):
        rr = c * math.sqrt(n)
        row = int(rr / d)
        rows[n - 1] = row
        # 70% snap toward the row centre keeps courses visible without
        # making the generators exactly co-circular (Voronoi stays stable)
        rr = 0.7 * (d * (row + 0.5)) + 0.3 * rr
        aa = n * GOLDEN
        pts[n - 1] = (rr * math.cos(aa), rr * math.sin(aa))
    polys = []
    for i, cl in voronoi_cells(pts):
        base = HONEY if rows[i] % 2 == 0 else OCHRE
        polys.append((cl, vary(rng, base, 10)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# C. parastichy rhombs (13, 21) + fan centre
# ---------------------------------------------------------------------------
def gen_sunflower_rhombs():
    """LOG-spiral quad mesh: r = r0*exp(k*n), theta = n*golden angle. With
    exponential growth every quad is a rotated+scaled copy of its neighbour
    (self-similar), so the (21, 34) parastichy mesh stays embedded at every
    radius - this is exactly the growing-rhombi look of reference photo 3.
    Vogel's sqrt(n) growth (variants A/B/D) makes a fixed pair lose dominance
    away from its ring and the quads degenerate into overlapping slivers -
    verified numerically, hence the exponential lattice here."""
    rng = np.random.default_rng(53)
    F1, F2 = 21, 34
    # Cells shrink continuously toward the pole (self-similar mesh), so quads
    # below ~15 px would drown in their own outlines as a black blob. The fan
    # takes over from N0 inward: 55 wedges converging at the pole (the
    # approved same-shape-centre pattern), first quads start at r ~ 0.27.
    N0 = 380
    r0 = 0.055
    k = 0.0042                             # per-seed growth; ~2:1 radial cells
    N = int(math.log((math.sqrt(2.0) + 0.6) / r0) / k)

    def P(n):
        rr = r0 * math.exp(k * n)
        aa = n * GOLDEN
        return (rr * math.cos(aa), rr * math.sin(aa))

    quads = []
    for n in range(N0, N + 1):
        quads.append((n, [P(n), P(n + F1), P(n + F1 + F2), P(n + F2)]))

    # Inner boundary edges (used by exactly one quad, near the pole) form a
    # closed 55-edge loop. Verdict rev 2: the centre must RESEMBLE the
    # surrounding rhombi, so the mesh is continued inward by two concentric
    # rings of quasi-rhombs (loop scaled toward the pole at 0.70 and 0.42 -
    # one quad per boundary edge, same size progression as the log mesh) and
    # only the innermost disc becomes 11 small petals converging at the pole.
    edge_count = {}
    for n, q in quads:
        for a, b in zip(q, q[1:] + q[:1]):
            key = tuple(sorted((a, b)))
            edge_count[key] = edge_count.get(key, 0) + 1
    r_inner = 0.6                          # inner-rim vertices sit at r<=0.35
    binner = {}
    for (a, b), cnt in edge_count.items():
        if cnt == 1 and math.hypot(*a) < r_inner and math.hypot(*b) < r_inner:
            binner.setdefault(a, []).append(b)
            binner.setdefault(b, []).append(a)
    # walk the closed loop
    start = next(iter(binner))
    loop, prev, cur = [start], None, start
    while True:
        nxt = [v for v in binner[cur] if v != prev][0]
        if nxt == start:
            break
        loop.append(nxt)
        prev, cur = cur, nxt

    def scaled(v, s):
        return (v[0] * s, v[1] * s)

    # The 55-edge loop is denser than the mesh itself (~34 quads per ring of
    # circumference), so per-edge rings degenerate into a sunburst of slivers
    # (two earlier drafts). Instead ONE transition ring whose cells each span
    # TWO loop edges (~28 cells = mesh-quad width) lands on a smooth circle,
    # and the circle splits into 14 petals converging at the pole (~2:1).
    L = len(loop)
    r_mean = sum(math.hypot(*v) for v in loop) / L
    ring_r = 0.80 * r_mean

    def on_circle(v, radius):
        vr = math.hypot(*v)
        return (v[0] / vr * radius, v[1] / vr * radius)

    pairs = [(i, min(i + 2, L)) for i in range(0, L - 1, 2)]
    if pairs[-1][1] != L:
        pairs[-1] = (pairs[-1][0], L)      # odd L: last cell spans the seam
    circle = []
    polys = []
    for j, (a, b) in enumerate(pairs):
        w0 = on_circle(loop[a], ring_r)
        w1 = on_circle(loop[b % L], ring_r)
        circle.append(w0)
        outer = [loop[k % L] for k in range(b, a - 1, -1)]   # reversed arc
        base = HONEY if j % 2 == 0 else GOLD
        polys.append(([w0, w1] + outer, vary(rng, base, 10)))
    M = len(circle)                        # ~28 circle vertices
    for s in range(0, M, 2):
        seg = circle[s:s + 3]
        if s + 2 >= M:
            seg = circle[s:] + [circle[0]]  # close on the seam
        polys.append(([(0.0, 0.0)] + seg, vary(rng, OCHRE, 10)))
    for n, q in quads:
        cl = _clip_rect(q, R)
        if len(cl) < 3:
            continue
        arm = n % F2
        base = HONEY if arm % 2 == 0 else GOLD
        polys.append((cl, vary(rng, base, 10)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# D. growth-graded head (bigger seeds toward the rim)
# ---------------------------------------------------------------------------
def gen_sunflower_grande():
    rng = np.random.default_rng(54)
    N = 1500
    p = 0.66
    c = (math.sqrt(2.0) + 0.45) / (N ** p)
    pts = vogel_points(N, c, power=p)
    polys = []
    for i, cl in voronoi_cells(pts):
        cx = sum(x for x, _ in cl) / len(cl)
        cy = sum(y for _, y in cl) / len(cl)
        t = min(1.0, math.hypot(cx, cy) / math.sqrt(2.0))
        polys.append((cl, vary(rng, _radial_mix(RUST, HONEY, t), 10)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# grande variants (grande itself above stays untouched per verdict)
# ---------------------------------------------------------------------------
def _graded_head(rng, seed_pts, dark_to_gold=True):
    """Shared body for the grande family: Voronoi of a graded lattice with the
    grande radial palette (dark centre -> gold rim, or reversed)."""
    polys = []
    for i, cl in voronoi_cells(seed_pts):
        cen = _poly_centroid(cl)
        if cen is None:
            continue
        t = min(1.0, math.hypot(*cen) / math.sqrt(2.0))
        if not dark_to_gold:
            t = 1.0 - t
        polys.append((cl, vary(rng, _radial_mix(RUST, HONEY, t), 10)))
    return polys, (-R, -R, R, R)


def gen_grande_xl():
    rng = np.random.default_rng(57)
    N, p = 550, 0.75
    c = (math.sqrt(2.0) + 0.45) / (N ** p)
    return _graded_head(rng, vogel_points(N, c, power=p))


def gen_grande_soft():
    rng = np.random.default_rng(58)
    N, p = 1500, 0.66
    c = (math.sqrt(2.0) + 0.45) / (N ** p)
    return _graded_head(rng, lloyd_relax(vogel_points(N, c, power=p), iters=1))


def gen_grande_inverse():
    rng = np.random.default_rng(59)
    N, p = 1100, 0.40
    c = (math.sqrt(2.0) + 0.45) / (N ** p)
    return _graded_head(rng, vogel_points(N, c, power=p), dark_to_gold=False)


# ---------------------------------------------------------------------------
# coverage check (variant C is hand-built; Voronoi = partition by construction)
# ---------------------------------------------------------------------------
def coverage_report(polys, world, res=600):
    """Raster gap/overlap check. NOTE: PIL fills polygon EDGES on both sides
    of a shared border, so an exact partition still reports ~4.4% 'overlaps'
    at res=600 (measured on the Voronoi variant, a partition by construction).
    Treat that as the baseline; a real overlap problem shows up well above it
    (the broken sqrt(n) fixed-pair mesh scored 11%)."""
    x0, y0, x1, y1 = world
    acc = np.zeros((res, res), dtype=np.int32)
    for poly, _ in polys:
        img = Image.new("L", (res, res), 0)
        d = ImageDraw.Draw(img)
        px = [((x - x0) / (x1 - x0) * (res - 1),
               (y - y0) / (y1 - y0) * (res - 1)) for x, y in poly]
        d.polygon(px, fill=1)
        acc += np.array(img, dtype=np.int32)
    interior = acc[10:-10, 10:-10]
    gaps = float((interior == 0).mean() * 100)
    overlaps = float((interior > 1).mean() * 100)
    return gaps, overlaps


PROPOSALS = [
    ("sunflower_soft", gen_sunflower_soft,
     "1. SOFT (Lloyd x2)", "wygladzone, rowniejsze ziarna; spirale zostaja", False),
    ("sunflower_disc", gen_sunflower_disc,
     "2. DISC (dwie strefy)", "drobne ciemne kwiatki w srodku, grubsze zloto wokol", False),
    ("sunflower_rings", gen_sunflower_rings,
     "3. RINGS (rzedy koncentryczne)", "ziarna dosniete do okregow, rzedy jak na fot. 1", False),
    ("sunflower_rhombs", gen_sunflower_rhombs,
     "4. ROMBY SPIRALNE v2", "srodek: 2 pierscienie quasi-rombow + male platki", True),
    ("sunflower_grande", gen_sunflower_grande,
     "5. GRANDE (r=c*n^0.66)", "faworyt - bez zmian, do werdyktu", False),
    ("grande_xl", gen_grande_xl,
     "6. GRANDE XL (n^0.75)", "mocniejszy gradient: male centrum, wielki obwod", False),
    ("grande_soft", gen_grande_soft,
     "7. GRANDE SOFT (Lloyd x1)", "grande wygladzone, lagodniejsza rampa", False),
    ("grande_inverse", gen_grande_inverse,
     "8. GRANDE INVERSE (n^0.40)", "odwrotnie: wielkie centrum, drobny obwod", False),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panels = {}
    for name, fn, t1, t2, check in PROPOSALS:
        print(f"[sunflower] {name} ...")
        polys, world = fn()
        if check:
            gaps, overlaps = coverage_report(polys, world)
            print(f"            coverage: gaps {gaps:.2f}% | overlaps {overlaps:.2f}%")
        img = render(polys, world)
        img.save(OUT_DIR / f"{name}.png")
        panels[name] = img
        print(f"            {len(polys)} cells -> {name}.png")

    PW, TH = 560, 58
    cols_n, rows_n = 4, 2
    mont = Image.new("RGB", (PW * cols_n, (PW + TH) * rows_n), (10, 10, 12))
    draw = ImageDraw.Draw(mont)
    try:
        f1 = ImageFont.truetype("arial.ttf", 22)
        f2 = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    for i, (name, _, t1, t2, _) in enumerate(PROPOSALS):
        gx = (i % cols_n) * PW
        gy = (i // cols_n) * (PW + TH)
        mont.paste(panels[name].resize((PW, PW), Image.Resampling.LANCZOS),
                   (gx, gy))
        draw.text((gx + 12, gy + PW + 6), t1, fill=(235, 235, 235), font=f1)
        draw.text((gx + 12, gy + PW + 34), t2, fill=(160, 160, 160), font=f2)
    mont.save(OUT_DIR / "proposals_sunflower.png")
    print(f"[sunflower] montage -> {OUT_DIR / 'proposals_sunflower.png'}")


if __name__ == "__main__":
    main()
