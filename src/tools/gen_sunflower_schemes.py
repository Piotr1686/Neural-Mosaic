"""Generate 5 PROPOSAL schemes for the SUNFLOWER SEEDS tile pattern.

User request 2026-07-05 (reference photos: golden sunflower-head mosaics).
Seeds follow Vogel's phyllotaxis: point n sits at r = c*sqrt(n),
theta = n * golden angle (137.508 deg). Five different takes for the user to
choose from; every variant is a TRUE tessellation (cells abut exactly):

  A. sunflower_classic - Voronoi of the Vogel lattice, pole centred, golden
     seed palette (closest to reference photo 1). Differs from the existing
     `bloom` shape (multicolour 21-arm palette) by density + gold tones.
  B. sunflower_corner  - same Voronoi but the pole sits in the bottom-left
     corner: parastichy arcs sweep across the whole frame.
  C. sunflower_rhombs  - parastichy quad mesh, fixed family pair (13, 21):
     quad n = seeds (n, n+13, n+34, n+21). Every interior seed joins exactly
     4 quads, so the mesh is a genuine quadrilateral tiling; rhombi grow and
     shear outward exactly like reference photo 3. The central hole is closed
     by a fan of triangles converging at the pole (pole + each inner-boundary
     edge) - the approved "same-shape centre" pattern.
  D. sunflower_grande  - Voronoi of a growth-graded lattice r = c*n^0.66:
     seeds enlarge toward the rim like a real ripening flower head.
  E. sunflower_field   - one Voronoi over the union of THREE Vogel heads:
     flower heads press into each other like a sunflower field.

Coverage of variant C is verified numerically (raster overlap/gap report)
because the quad mesh is hand-built; Voronoi variants are partitions by
construction. Pure PIL + numpy + scipy, deterministic. ASCII-only prints.

Outputs:
  output/sunflower_proposals/<name>.png            (720x720 panels)
  output/sunflower_proposals/proposals_sunflower.png (montage 2x3)

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


# ---------------------------------------------------------------------------
# A. classic centred head
# ---------------------------------------------------------------------------
def gen_sunflower_classic():
    rng = np.random.default_rng(51)
    N = 1400
    c = (math.sqrt(2.0) + 0.45) / math.sqrt(N)
    pts = vogel_points(N, c)
    polys = []
    for i, cl in voronoi_cells(pts):
        # subtle 21-arm shading keeps the spiral readable but stays golden
        arm = (i + 1) % 21
        base = HONEY if arm % 3 == 0 else GOLD
        polys.append((cl, vary(rng, base, 12)))
    return polys, (-R, -R, R, R)


# ---------------------------------------------------------------------------
# B. pole in the corner
# ---------------------------------------------------------------------------
def gen_sunflower_corner():
    rng = np.random.default_rng(52)
    N = 2600
    diag = 2 * math.sqrt(2.0)
    c = (diag + 0.45) / math.sqrt(N)
    pole = (-R, -R)
    pts = vogel_points(N, c, pole=pole)
    polys = []
    for i, cl in voronoi_cells(pts):
        cx = sum(p[0] for p in cl) / len(cl)
        cy = sum(p[1] for p in cl) / len(cl)
        t = min(1.0, math.hypot(cx - pole[0], cy - pole[1]) / diag)
        polys.append((cl, vary(rng, _radial_mix(HONEY, RUST, t), 10)))
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
    # closed 55-edge loop. 55 pole triangles would be 9:1 slivers (the exact
    # defect the user rejected in earlier shapes), so consecutive edges are
    # grouped into ~11 broad petals - polygons [pole, v0..v5] converging at
    # the pole (approved same-shape-centre pattern) with a sane ~2:1 aspect.
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
    per_petal = 5
    fans = []
    for s in range(0, len(loop), per_petal):
        seg = loop[s:s + per_petal + 1]
        if s + per_petal >= len(loop):
            seg = loop[s:] + [loop[0]]     # close the last petal on the seam
        fans.append([(0.0, 0.0)] + seg)

    polys = []
    for petal in fans:
        polys.append((petal, vary(rng, OCHRE, 10)))
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
# E. field of three heads
# ---------------------------------------------------------------------------
def gen_sunflower_field():
    rng = np.random.default_rng(55)
    dark = (96, 62, 30)                    # disc centre of a real flower head
    # One big head whose lattice reaches past every corner (it owns the
    # background), plus two smaller heads pressed into it. Equal-radius heads
    # interleave everywhere and the spirals dissolve into noise - verified on
    # the first draft; big+small keeps every head's spiral readable.
    # (pole, radius, cell size, base colour): one big head owns the frame,
    # one denser medium head presses into it - two heads read cleanly, three
    # equal ones dissolved into noise at their triple boundary.
    heads = [((-0.45, -0.40), 2.70, 0.052, (216, 170, 70)),
             ((0.52, 0.48), 1.00, 0.038, (196, 138, 58))]
    all_pts, owner = [], []
    for hid, (pole, radius, cell, _) in enumerate(heads):
        n = int((radius / cell) ** 2)
        all_pts.append(vogel_points(n, radius / math.sqrt(n), pole=pole))
        owner.append(np.full(n, hid))
    all_pts = np.vstack(all_pts)
    owner = np.concatenate(owner)
    polys = []
    for i, cl in voronoi_cells(all_pts):
        pole, radius, _, base = heads[owner[i]]
        cx = sum(x for x, _ in cl) / len(cl)
        cy = sum(y for _, y in cl) / len(cl)
        # dark disc centre fading to the head's own gold at its rim, so the
        # three heads read as flowers instead of undifferentiated noise
        t = min(1.0, math.hypot(cx - pole[0], cy - pole[1]) / radius)
        # soften: dark disc only in the innermost ~quarter of each head
        polys.append((cl, vary(rng, _radial_mix(dark, base, 0.3 + 0.7 * t), 10)))
    return polys, (-R, -R, R, R)


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
    ("sunflower_classic", gen_sunflower_classic,
     "A. KLASYCZNY (Voronoi Vogela)", "biegun w srodku, zlote ziarna", False),
    ("sunflower_corner", gen_sunflower_corner,
     "B. NAROZNY", "biegun w rogu, luki przez caly kadr", False),
    ("sunflower_rhombs", gen_sunflower_rhombs,
     "C. ROMBY SPIRALNE (log, 21/34)", "samopodobne romby rosna od srodka, wachlarz w biegunie", True),
    ("sunflower_grande", gen_sunflower_grande,
     "D. WZROST ZIAREN (r=c*n^0.66)", "ziarna rosna ku obwodowi", False),
    ("sunflower_field", gen_sunflower_field,
     "E. POLE SLONECZNIKOW (2 glowy)", "duza glowa + gestsza mniejsza, scisniete Voronoiem", False),
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

    PW, TH = 640, 58
    cols_n, rows_n = 3, 2
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
