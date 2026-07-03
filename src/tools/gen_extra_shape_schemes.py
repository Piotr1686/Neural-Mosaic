"""Generate schematic previews for 15 additional tile-shape proposals (21-35).

9 user-requested named shapes + 6 original inventions. These are PROPOSAL
previews (720x720 GUI swatches), NOT engine implementations. Pure geometry +
PIL, deterministic (seeded RNG only). ASCII-only prints (CP1250 terminal).

HARD REQUIREMENT (user, 2026-07-03): every shape must be self-repeating and
FILL THE WHOLE RECTANGLE - no empty corners, no holes, every cell = one photo.
Radial motifs (mandala, rosette, nautilus, vortex, bloom, shatter) and fractals
with holes (sierpinski, koch_snowflake, hirotaka) therefore repeat on a lattice
over a full-canvas background grid (`_bg_grid`) that fills any residual gap.
The four natively plane-filling schemes (gereh, koch_island, moire, braid) tile
directly.

Three names were geometrically ambiguous; labelled interpretations:
  - hirotaka   -> pentaflake / pentagonal IFS (source shows it graphically only,
                  with NO definition - czasopismomatematyka.pl 'O smokach' cz.2)
  - kepler_ty  -> stylised 5-fold Harmonices Mundi cluster (pentagon+star+decagon)
  - gereh      -> girih strapwork ON a tessellation (octagon+square 4.8.8 with
                  8-point khatam stars), per czasopismomatematyka.pl 'gereh cz.4'

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_extra_shape_schemes
"""
import cmath
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.tools.gen_fable_shape_schemes import (
    ASSETS_DIR, SIZE, BG, OUTLINE, render, vary, hsv_rgb, c2t,
)

OUT_DIR = Path("output/kite_schemes")

# muted mixed palette for the fill-grid so gaps read as photo cells, not one colour
BG_PAL = [(120, 96, 72), (86, 104, 120), (128, 116, 84), (100, 112, 96),
          (116, 92, 100), (92, 106, 112)]


# ==========================================
# SHARED HELPERS
# ==========================================
def _reg_poly(centre, r, n, phase=0.0):
    return [centre + r * cmath.exp(1j * (phase + 2 * math.pi * k / n)) for k in range(n)]


def _star_poly(centre, r_out, r_in, n, phase=0.0):
    pts = []
    for k in range(n):
        pts.append(centre + r_out * cmath.exp(1j * (phase + 2 * math.pi * k / n)))
        pts.append(centre + r_in * cmath.exp(1j * (phase + 2 * math.pi * (k + 0.5) / n)))
    return pts


def _annular_sector(r0, r1, a0, a1, nseg=6):
    pts = []
    for i in range(nseg + 1):
        a = a0 + (a1 - a0) * i / nseg
        pts.append(r1 * cmath.exp(1j * a))
    for i in range(nseg + 1):
        a = a1 + (a0 - a1) * i / nseg
        pts.append(r0 * cmath.exp(1j * a))
    return pts


def _clip_rect(poly, R):
    """Sutherland-Hodgman clip of a polygon (list of (x,y)) to the square
    [-R, R]^2. Returns clipped vertex list (possibly empty)."""
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

    def ix(a, b, t):        # intersection with vertical x = t
        (ax, ay), (bx, by) = a, b
        f = (t - ax) / (bx - ax)
        return (t, ay + f * (by - ay))

    def iy(a, b, t):        # intersection with horizontal y = t
        (ax, ay), (bx, by) = a, b
        f = (t - ay) / (by - ay)
        return (ax + f * (bx - ax), t)

    pts = poly
    pts = clip(pts, lambda p: p[0] >= -R, lambda a, b: ix(a, b, -R))
    if not pts:
        return pts
    pts = clip(pts, lambda p: p[0] <= R, lambda a, b: ix(a, b, R))
    if not pts:
        return pts
    pts = clip(pts, lambda p: p[1] >= -R, lambda a, b: iy(a, b, -R))
    if not pts:
        return pts
    pts = clip(pts, lambda p: p[1] <= R, lambda a, b: iy(a, b, R))
    return pts


def _radial_clip_cells(R, rings, pal, seed, swirl=0.0, nseg=6, coloff=0):
    """Radial tessellation clipped to the rectangle. rings = [(r0, r1, n), ...];
    each ring is split into n circular-arc sectors (optionally sheared by
    `swirl` radians per ring for a spiral), then every cell is clipped to
    [-R, R]^2. Rings extend past the corners so the square is fully covered.
    Result is a true partition: no overlaps, no gaps."""
    rng = np.random.default_rng(seed)

    def sector(r0, r1, a0, a1):
        pts = []
        for s in range(nseg + 1):
            a = a0 + (a1 - a0) * s / nseg
            pts.append((r1 * math.cos(a), r1 * math.sin(a)))
        for s in range(nseg + 1):
            a = a1 + (a0 - a1) * s / nseg
            pts.append((r0 * math.cos(a), r0 * math.sin(a)))
        return pts

    polys = []
    for ri, (r0, r1, n) in enumerate(rings):
        if n <= 1:
            disk = [(r1 * math.cos(2 * math.pi * t / 40), r1 * math.sin(2 * math.pi * t / 40))
                    for t in range(40)]
            cl = _clip_rect(disk, R)
            if len(cl) >= 3:
                polys.append((cl, vary(rng, pal[coloff % len(pal)], 8)))
            continue
        # stagger every other ring by half a sector (brick offset) so the radial
        # edges never line up into a continuous seam from centre to edge
        off = (math.pi / n) if (ri % 2 == 1) else 0.0
        base = ri * swirl + off
        for k in range(n):
            a0 = base + 2 * math.pi * k / n
            a1 = base + 2 * math.pi * (k + 1) / n
            cl = _clip_rect(sector(r0, r1, a0, a1), R)
            if len(cl) < 3:
                continue
            col = pal[(coloff + ri + (k % 2) + (1 if k % 3 == 0 else 0)) % len(pal)]
            polys.append((cl, vary(rng, col, 9)))
    return polys


def _bg_grid(R, cell, seed, pal=BG_PAL):
    """Full-canvas square-cell grid covering [-R, R]^2 so no corner is ever
    black. Drawn FIRST; motifs paint on top."""
    rng = np.random.default_rng(seed)
    polys = []
    n = int(math.ceil(2 * R / cell)) + 1
    for a in range(n):
        for b in range(n):
            x = -R + a * cell
            y = -R + b * cell
            rect = [(x, y), (x + cell, y), (x + cell, y + cell), (x, y + cell)]
            polys.append((rect, vary(rng, pal[(a + b) % len(pal)], 16)))
    return polys


def _lattice(R, spacing, hexoffset=False):
    """Centres of a square (or row-offset) lattice covering a bit past [-R, R]."""
    n = int(math.ceil(2 * R / spacing)) + 2
    start = -spacing * (n // 2)
    cs = []
    for b in range(n):
        off = spacing / 2 if (hexoffset and b % 2) else 0.0
        for a in range(n):
            cs.append(complex(start + a * spacing + off, start + b * spacing))
    return cs


# ==========================================
# 21. SIERPINSKI TRIANGLE  [wypelnia: siatka gaskets + tlo]
# ==========================================
def _sierp_tris(a, b, c, d, out):
    if d == 0:
        out.append((a, b, c))
        return
    ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
    _sierp_tris(a, ab, ca, d - 1, out)
    _sierp_tris(ab, b, bc, d - 1, out)
    _sierp_tris(ca, bc, c, d - 1, out)


def _sierp_unit(c, R, up, rng, pal):
    ph = math.pi / 2 if up else -math.pi / 2
    A = c + R * cmath.exp(1j * ph)
    B = c + R * cmath.exp(1j * (ph + 2 * math.pi / 3))
    C = c + R * cmath.exp(1j * (ph + 4 * math.pi / 3))
    tris = []
    _sierp_tris(A, B, C, 4, tris)
    return [(c2t([a, b, cc]), vary(rng, pal[i % len(pal)], 12))
            for i, (a, b, cc) in enumerate(tris)]


def _sierpinski_cells(A, B, C, depth, cells):
    """Classic Sierpinski recursion: the 3 corner sub-triangles recurse; the
    central inverted sub-triangle is a 'hole' cell tagged with its level. Every
    triangle (gasket AND hole) is a cell, so there are no actual gaps - the
    nested-triangle look comes from colouring holes dark by level."""
    if depth == 0:
        cells.append(([A, B, C], 0))
        return
    ab, bc, ca = (A + B) / 2, (B + C) / 2, (C + A) / 2
    _sierpinski_cells(A, ab, ca, depth - 1, cells)
    _sierpinski_cells(ab, B, bc, depth - 1, cells)
    _sierpinski_cells(ca, bc, C, depth - 1, cells)
    cells.append(([ab, bc, ca], depth))     # central hole at this level


def gen_sierpinski():
    """The real Sierpinski triangle: a big triangle recursively subdivided with
    nested dark holes, replicated in every direction by tiling up- AND down-
    pointing Sierpinski triangles (which interlock to fill the plane)."""
    rng = np.random.default_rng(211)
    R = 1.0
    S = 0.66
    H = S * math.sqrt(3) / 2
    depth = 4
    pal_solid = [(224, 170, 92), (214, 148, 70)]
    pal_hole = [(44, 48, 62), (58, 50, 66), (48, 62, 58), (66, 54, 56)]
    polys = []
    rows = int(2 * R / H) + 3
    cols = int(2 * R / S) + 3
    for r in range(-1, rows):
        y0 = -R + r * H
        for c in range(-1, cols):
            x0 = -R + c * S
            BL, BR, TOP = complex(x0, y0), complex(x0 + S, y0), complex(x0 + S / 2, y0 + H)
            TL, TR, BOT = complex(x0 + S / 2, y0 + H), complex(x0 + 1.5 * S, y0 + H), complex(x0 + S, y0)
            for tri, par in [((BL, BR, TOP), (r + c) % 2), ((TL, TR, BOT), (r + c + 1) % 2)]:
                cells = []
                _sierpinski_cells(tri[0], tri[1], tri[2], depth, cells)
                for poly, tag in cells:
                    if tag == 0:
                        col = vary(rng, pal_solid[par], 10)
                    else:
                        col = vary(rng, pal_hole[tag % len(pal_hole)], 8)
                    polys.append((c2t(poly), col))
    return polys, (-R, -R, R, R)


def gen_stagger_tri():
    """Staggered triangle grid (kept from the first 'sierpinski' attempt, renamed):
    up/down triangles whose colour bands shift row-to-row, giving an interlocked
    look distinct from the plain `triangle` mode. A true edge-to-edge tiling."""
    rng = np.random.default_rng(21)
    R = 1.0
    s = 0.16
    h = s * math.sqrt(3) / 2
    pal_on = [(214, 150, 62), (186, 92, 72)]
    pal_off = [(70, 84, 98), (92, 96, 78), (120, 110, 150)]
    polys = []
    rows = int(2 * R / h) + 3
    cols = int(2 * R / s) + 3
    for r in range(-1, rows):
        y0 = -R + r * h
        rj = r + 1
        for cq in range(-1, cols):
            cx = -R + cq * s
            ci = cq + 1
            bl, br, tp = (cx, y0), (cx + s, y0), (cx + s / 2, y0 + h)
            tr = (cx + 3 * s / 2, y0 + h)
            on = (ci & rj) == 0
            polys.append(([bl, br, tp], vary(rng, pal_on[rj % 2] if on else pal_off[(ci + rj) % 3], 10)))
            polys.append(([br, tp, tr], vary(rng, pal_off[(ci + rj + 1) % 3], 10)))
    return polys, (-R, -R, R, R)


# ==========================================
# 22. KEPLER 'Ty' (stylised, lattice)  [wypelnia: klaster na siatce + tlo]
# ==========================================
def _kepler_unit(centre, R, rng):
    """Decagon with a regular pentagon edge-glued to every edge (they meet with
    NO gap: 144 + 108 + 108 = 360 at each decagon vertex), plus pentagrams in the
    5 outer notches - the Harmonices Mundi decagon/pentagon/pentagram motif."""
    pal_dec = (206, 162, 78)
    pal_pen = (96, 130, 165)
    pal_star = (176, 92, 84)
    edge = R * 0.42
    Rd = edge / (2 * math.sin(math.pi / 10))
    ap = edge / (2 * math.tan(math.pi / 5))
    Rp = edge / (2 * math.sin(math.pi / 5))
    dec = _reg_poly(centre, Rd, 10, math.pi / 10)
    out = [(c2t(dec), vary(rng, pal_dec, 8))]
    for k in range(10):
        a, b = dec[k], dec[(k + 1) % 10]
        mid = (a + b) / 2
        outw = (mid - centre) / abs(mid - centre)
        pcen = mid + ap * outw
        ph = cmath.phase(a - pcen)
        pent = [pcen + Rp * cmath.exp(1j * (ph + 2 * math.pi * m / 5)) for m in range(5)]
        out.append((c2t(pent), vary(rng, pal_pen, 12)))
    # pentagrams in 5 alternate outer notches (toward every other decagon vertex)
    for k in range(1, 10, 2):
        vdir = (dec[k] - centre) / abs(dec[k] - centre)
        scen = centre + (Rd + 1.9 * ap) * vdir
        out.append((c2t(_star_poly(scen, Rp * 0.85, Rp * 0.34, 5, cmath.phase(vdir))),
                    vary(rng, pal_star, 10)))
    return out


def gen_kepler_ty():
    rng = np.random.default_rng(22)
    R = 1.0
    polys = _bg_grid(R, 0.15, 220)
    for c in _lattice(R, 0.80, hexoffset=True):
        polys += _kepler_unit(c, 0.44, rng)
    return polys, (-R, -R, R, R)


# ==========================================
# 23. GEREH ON A TESSELLATION  [natywne wypelnienie]
# ==========================================
def gen_gereh():
    """Gereh as a true PARTITION: octagon+square 4.8.8 tiling where each octagon
    is split into an 8-point khatam star cell + 8 kite cells (star tip -> edge
    midpoint, kites over the vertices). Nothing overlaps; every cell is a photo."""
    rng = np.random.default_rng(23)
    p = 1 + math.sqrt(2)
    Roct = 1.0 / (2 * math.sin(math.pi / 8))     # octagon circumradius (edge 1)
    r_in = (1.0 / (2 * math.tan(math.pi / 8))) * 0.42
    pal_star = (214, 170, 82)
    pal_kite = (66, 86, 116)
    pal_sq = (176, 92, 84)
    polys = []
    N = 3
    for i in range(-N, N + 1):
        for j in range(-N, N + 1):
            c = complex(i * p, j * p)
            V = [c + Roct * cmath.exp(1j * (math.pi / 8 + math.pi / 4 * k)) for k in range(8)]
            Mid = [(V[k] + V[(k + 1) % 8]) / 2 for k in range(8)]          # star tips
            inner = [c + r_in * cmath.exp(1j * (math.pi / 8 + math.pi / 4 * (k + 1)))
                     for k in range(8)]
            star = []
            for k in range(8):
                star += [Mid[k], inner[k]]
            polys.append((c2t(star), vary(rng, pal_star, 8)))
            for k in range(8):
                kite = [Mid[k], V[(k + 1) % 8], Mid[(k + 1) % 8], inner[k]]
                polys.append((c2t(kite), vary(rng, pal_kite, 10)))
            cs = complex((i + 0.5) * p, (j + 0.5) * p)
            polys.append((c2t(_reg_poly(cs, math.sqrt(2) / 2, 4, math.pi / 4)),
                          vary(rng, pal_sq, 10)))
    Rw = 2.35 * p
    return polys, (-Rw, -Rw, Rw, Rw)


# ==========================================
# 24. HEIGHWAY DRAGON (twindragons on a lattice)  [wypelnia: siatka smokow + tlo]
# ==========================================
def _dragon_turns(order):
    seq = [1]
    for _ in range(order - 1):
        seq = seq + [1] + [-x for x in reversed(seq)]
    return seq


def _dragon_pts(order, origin, phase, scale):
    seq = _dragon_turns(order)
    z = origin
    head = phase
    pts = [z]
    z = z + scale * cmath.exp(1j * head)
    pts.append(z)
    for t in seq:
        head += t * math.pi / 2
        z = z + scale * cmath.exp(1j * head)
        pts.append(z)
    return pts


def _dragon_unit(centre, scale, order, rng):
    width = 0.34 * scale
    out = []

    def ribbon(pts, base):
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = b - a
            nrm = (d / abs(d)) * 1j * width if abs(d) > 1e-9 else 0
            t = i / (len(pts) - 1)
            col = tuple(int(np.clip(cc * (0.7 + 0.5 * t), 0, 255)) for cc in base)
            out.append((c2t([a + nrm, b + nrm, b - nrm, a - nrm]), vary(rng, col, 8)))

    p0 = _dragon_pts(order, centre, 0.0, scale)
    ribbon(p0, (210, 140, 60))
    ribbon(_dragon_pts(order, p0[-1], math.pi, scale), (90, 130, 170))
    return out


def gen_dragon():
    # ETAP A placeholder: still ribbons on a bg grid (NOT yet a true reptile
    # partition). Order kept low so main()'s montage does not choke on ~16k
    # polys/tile; the real twindragon-reptile rework is stage A.
    rng = np.random.default_rng(24)
    R = 1.0
    polys = _bg_grid(R, 0.14, 240)
    order = 6
    for c in _lattice(R, 1.0):
        polys += _dragon_unit(c, 0.11, order, rng)
    return polys, (-R, -R, R, R)


# ==========================================
# 25. KOCH SNOWFLAKE (hex lattice + gap fill)  [wypelnia: siatka platkow + tlo]
# ==========================================
def _koch_edge(a, b, d):
    if d == 0:
        return [a]
    v = b - a
    p1 = a + v / 3
    p2 = a + 2 * v / 3
    peak = p1 + (p2 - p1) * cmath.exp(-1j * math.pi / 3)
    return (_koch_edge(a, p1, d - 1) + _koch_edge(p1, peak, d - 1)
            + _koch_edge(peak, p2, d - 1) + _koch_edge(p2, b, d - 1))


def _snowflake(centre, r, d, phase=0.0):
    v = [centre + r * cmath.exp(1j * (phase + 2 * math.pi * k / 3)) for k in range(3)]
    pts = []
    for k in range(3):
        pts += _koch_edge(v[k], v[(k + 1) % 3], d)
    return pts


def gen_koch_snowflake():
    rng = np.random.default_rng(25)
    R = 1.0
    polys = _bg_grid(R, 0.11, 250)
    pal = [(210, 150, 60), (90, 120, 160), (170, 95, 90), (120, 160, 110),
           (150, 110, 160), (120, 120, 85)]
    t1 = complex(0.62, 0)
    t2 = complex(0.31, 0.62 * math.sqrt(3) / 2 * 2)
    for m in range(-4, 5):
        for n in range(-4, 5):
            c = m * t1 + n * t2
            if abs(c) > 1.5:
                continue
            phase = math.pi / 3 if (m + n) % 2 else 0.0
            col = vary(rng, pal[(m - 2 * n) % 6], 10)
            polys.append((c2t(_snowflake(c, 0.24, 3, phase)), col))
    return polys, (-R, -R, R, R)


# ==========================================
# 26. QUADRATIC KOCH ISLAND (Minkowski reptile)  [natywne wypelnienie]
# ==========================================
def _turtle_string(axiom, rule, angle_deg, depth):
    s = axiom
    for _ in range(depth):
        s = "".join(rule.get(ch, ch) for ch in s)
    z = 0j
    head = 0.0
    pts = [z]
    a = math.radians(angle_deg)
    for ch in s:
        if ch == "F":
            z += cmath.exp(1j * head)
            pts.append(z)
        elif ch == "+":
            head += a
        elif ch == "-":
            head -= a
    return pts


def gen_koch_island():
    rng = np.random.default_rng(26)
    depth = 2
    rule = {"F": "F+F-F-FF+F+F-F"}
    island = _turtle_string("F+F+F+F", rule, 90, depth)
    # true lattice vector: the generator nets 4 units per input segment, so a
    # unit-side square island tiles on a square lattice of side 4**depth. Using
    # the bounding box (coastline overshoot) instead leaves diagonal gaps.
    period = 4 ** depth
    pal = [(70, 130, 150), (200, 150, 70), (150, 90, 110), (110, 155, 100)]
    polys = []
    for i in range(-1, 4):
        for j in range(-1, 4):
            off = complex(i * period, j * period)
            col = vary(rng, pal[(i + 2 * j) % 4], 12)
            polys.append((c2t([z + off for z in island]), col))
    lo, hi = 0.15 * period, 2.15 * period
    return polys, (lo, lo, hi, hi)


# ==========================================
# 27. HIROTAKA (pentaflake IFS on a lattice)  [wypelnia: siatka pentaflake + tlo]
# ==========================================
def _pentaflake_unit(centre, R, phase, rng, pal):
    phi = (1 + math.sqrt(5)) / 2
    ratio = 1 / (1 + phi)
    leaves = []

    def rec(c, r, ph, depth):
        if depth == 0:
            leaves.append((c, r, ph))
            return
        cr = r * ratio
        rec(c, cr, ph, depth - 1)
        for k in range(5):
            ang = ph + 2 * math.pi * k / 5
            rec(c + (r - cr) * cmath.exp(1j * ang), cr, ph, depth - 1)

    rec(centre, R, phase, 3)
    out = []
    for (cc, r, ph) in leaves:
        tag = int(abs(cc - centre) * 6) % len(pal)
        out.append((c2t(_reg_poly(cc, r, 5, ph)), vary(rng, pal[tag], 10)))
    return out


def gen_hirotaka():
    rng = np.random.default_rng(27)
    R = 1.0
    polys = _bg_grid(R, 0.135, 270)
    pal = [(213, 150, 62), (120, 140, 170), (176, 92, 84), (120, 160, 110), (150, 112, 162)]
    for c in _lattice(R, 0.72, hexoffset=True):
        polys += _pentaflake_unit(c, 0.34, math.pi / 2, rng, pal)
    return polys, (-R, -R, R, R)


# ==========================================
# 28. ROSETTE (lattice of rosettes)  [wypelnia: siatka rozet + tlo]
# ==========================================
def gen_rosette():
    """Concentric CIRCULAR geometric rosette as a true edge-to-edge tessellation:
    real circular rings x angular sectors, expanded outward past the corners and
    then CLIPPED to the rectangle (user's insight). Centre stays perfectly round;
    edges/corners are clipped arcs. No overlaps, no gaps - each cell one photo."""
    R = 1.0
    diag = R * math.sqrt(2)
    pal = [(214, 130, 70), (188, 84, 96), (110, 140, 175), (150, 168, 96),
           (150, 108, 170), (96, 160, 140), (210, 168, 84)]
    # true circular ring radii; the last exceeds the corner distance (~1.414)
    rr = [0.0, 0.13, 0.28, 0.45, 0.63, 0.82, 1.02, 1.22, diag + 0.05]
    ang_counts = [1, 12, 12, 24, 24, 36, 48, 48]     # one per ring gap
    rings = [(rr[k], rr[k + 1], ang_counts[k]) for k in range(len(ang_counts))]
    return _radial_clip_cells(R, rings, pal, 28), (-R, -R, R, R)


# ==========================================
# 29. MANDALA (lattice of mandalas)  [wypelnia: siatka mandali + tlo]
# ==========================================
def gen_mandala():
    """Concentric circular mandala, rings expanded past the corners and clipped
    to the rectangle (true partition). Finer angular subdivision than rosette."""
    R = 1.0
    diag = R * math.sqrt(2)
    pal = [(214, 150, 62), (176, 92, 84), (110, 140, 172), (150, 168, 96),
           (150, 110, 162), (96, 160, 140)]
    rr = [0.0, 0.10, 0.20, 0.32, 0.46, 0.62, 0.80, 1.02, diag + 0.05]
    counts = [1, 8, 8, 16, 24, 24, 36, 48]
    rings = [(rr[k], rr[k + 1], counts[k]) for k in range(len(counts))]
    return _radial_clip_cells(R, rings, pal, 29), (-R, -R, R, R)


# ==========================================
# 30. NAUTILUS (lattice of shells)  [wypelnia: siatka muszli + tlo]
# ==========================================
def gen_nautilus():
    """Log-spaced (geometric) rings with a slight swirl, clipped to the rectangle
    - chambered-shell growth as a true radial partition (no overlaps/gaps)."""
    R = 1.0
    diag = R * math.sqrt(2)
    pal = [(214, 140, 66), (180, 92, 84), (110, 138, 170), (150, 165, 96)]
    rr = [0.0]
    r = 0.07
    while r < diag + 0.1:
        rr.append(r)
        r *= 1.5
    rr.append(diag + 0.1)
    counts = [1] + [24] * (len(rr) - 2)
    rings = [(rr[k], rr[k + 1], counts[k]) for k in range(len(counts))]
    return _radial_clip_cells(R, rings, pal, 30, swirl=0.28), (-R, -R, R, R)


# ==========================================
# 31. SHATTER (full-plane radial fracture)  [natywne wypelnienie]
# ==========================================
def gen_shatter():
    """Radial impact fracture from an off-centre point. Outer radius exceeds the
    far corner distance, so the wedges cover the whole canvas - fills natively."""
    rng = np.random.default_rng(31)
    R = 1.0
    centre = complex(-0.15, 0.1)
    n_cracks = 15
    angs = sorted((2 * math.pi * k / n_cracks + rng.uniform(-0.11, 0.11)) for k in range(n_cracks))
    rings = [0.0, 0.28, 0.6, 0.95, 1.35, 1.85, 2.5]   # past the far corner
    pal = [(200, 130, 66), (120, 135, 165), (172, 92, 88), (150, 160, 96)]
    polys = []
    for i in range(len(angs)):
        a0 = angs[i]
        a1 = angs[(i + 1) % n_cracks] + (2 * math.pi if i + 1 == n_cracks else 0)
        jag = rng.uniform(-0.05, 0.05)
        for ri in range(len(rings) - 1):
            r0 = rings[ri] * (1 + jag)
            r1 = rings[ri + 1] * (1 + jag)
            p0 = centre + r0 * cmath.exp(1j * a0)
            p1 = centre + r1 * cmath.exp(1j * a0)
            p2 = centre + r1 * cmath.exp(1j * a1)
            p3 = centre + r0 * cmath.exp(1j * a1)
            shade = 0.62 + 0.09 * ri
            base = pal[(i + ri) % len(pal)]
            col = tuple(int(np.clip(cc * shade, 0, 255)) for cc in base)
            polys.append((c2t([p0, p1, p2, p3]), vary(rng, col, 10)))
    return polys, (-R, -R, R, R)


# ==========================================
# 32. MOIRE (interference grid)  [natywne wypelnienie]
# ==========================================
def gen_moire():
    """GEOMETRIC moire: a grid whose vertices are displaced by a two-grating
    interference field. Cells stay gap-free (shared vertices) but genuinely warp
    in shape/size with the beat - so unlike the trivial version this differs
    from `square` even after photos are substituted."""
    rng = np.random.default_rng(32)
    N = 30
    theta = math.radians(11)
    ct, st = math.cos(theta), math.sin(theta)
    A = 0.42          # < 0.5 so vertices never cross (no inverted cells)
    freq = 0.7

    def vpos(i, j):
        x, y = i - N / 2, j - N / 2
        xr = x * ct - y * st
        yr = x * st + y * ct
        dx = A * math.sin(freq * x) * math.cos(freq * xr)
        dy = A * math.cos(freq * y) * math.sin(freq * yr)
        return (i + dx, j + dy)

    V = {(i, j): vpos(i, j) for i in range(N + 1) for j in range(N + 1)}

    def area(q):
        s = 0.0
        for k in range(4):
            x0, y0 = q[k]
            x1, y1 = q[(k + 1) % 4]
            s += x0 * y1 - x1 * y0
        return abs(s) / 2

    polys = []
    for i in range(N):
        for j in range(N):
            quad = [V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]]
            v = max(0.0, min(1.0, (area(quad) - 0.55) / 0.9))  # beat visible in swatch
            col = hsv_rgb(0.58 - 0.42 * v, 0.5, 0.4 + 0.42 * v)
            polys.append((quad, vary(rng, col, 6)))
    return polys, (3, 3, N - 3, N - 3)


# ==========================================
# 33. BRAID (interwoven wave ribbons)  [natywne wypelnienie]
# ==========================================
def gen_braid():
    """Basketweave: a FLAT interlace (no over/under, so no overlap) - 2x1 bricks
    laid in alternating horizontal/vertical pairs on a checkerboard of 2x2
    blocks. A true edge-to-edge tiling that reads as woven."""
    rng = np.random.default_rng(33)
    warm = (210, 135, 62)
    cool = (96, 128, 168)
    B = 6
    polys = []
    for I in range(-1, B + 1):
        for J in range(-1, B + 1):
            x, y = 2 * I, 2 * J
            if (I + J) % 2 == 0:
                polys.append(([(x, y), (x + 2, y), (x + 2, y + 1), (x, y + 1)], vary(rng, warm, 16)))
                polys.append(([(x, y + 1), (x + 2, y + 1), (x + 2, y + 2), (x, y + 2)], vary(rng, warm, 16)))
            else:
                polys.append(([(x, y), (x + 1, y), (x + 1, y + 2), (x, y + 2)], vary(rng, cool, 16)))
                polys.append(([(x + 1, y), (x + 2, y), (x + 2, y + 2), (x + 1, y + 2)], vary(rng, cool, 16)))
    return polys, (1, 1, 2 * B - 1, 2 * B - 1)


# ==========================================
# 34. VORTEX (lattice of swirls)  [wypelnia: siatka wirow + tlo]
# ==========================================
def gen_vortex():
    """Radial rings with a strong per-ring swirl so the shared radial edges spiral
    into arms, clipped to the rectangle. A true partition (no overlaps/gaps)."""
    R = 1.0
    diag = R * math.sqrt(2)
    pal = [(214, 140, 66), (110, 138, 172), (176, 92, 88), (150, 166, 96), (150, 110, 164)]
    rr = [0.0, 0.14, 0.28, 0.44, 0.62, 0.82, 1.04, 1.28, diag + 0.05]
    counts = [1] + [10] * (len(rr) - 2)
    rings = [(rr[k], rr[k + 1], counts[k]) for k in range(len(counts))]
    return _radial_clip_cells(R, rings, pal, 34, swirl=0.42), (-R, -R, R, R)


# ==========================================
# 35. BLOOM (lattice of phyllotaxis rosettes)  [wypelnia: siatka kwiatow + tlo]
# ==========================================
def _bloom_unit(centre, R, rng, pal):
    golden = math.pi * (3 - math.sqrt(5))
    out = []
    N = 90
    for i in range(1, N):
        r = R * math.sqrt(i / N)
        a = i * golden
        c = centre + r * cmath.exp(1j * a)
        size = (0.05 + 0.09 * (i / N)) * R
        u = cmath.exp(1j * a)
        v = u * 1j
        rh = [c + size * 1.4 * u, c + size * v, c - size * 1.4 * u, c - size * v]
        out.append((c2t(rh), vary(rng, pal[i % len(pal)], 14)))
    return out


def gen_bloom():
    rng = np.random.default_rng(35)
    R = 1.0
    polys = _bg_grid(R, 0.13, 350)
    pal = [(214, 138, 64), (180, 90, 84), (110, 138, 170), (150, 166, 96),
           (150, 110, 162), (96, 160, 140)]
    for c in _lattice(R, 0.62):
        polys += _bloom_unit(c, 0.34, rng, pal)
    return polys, (-R, -R, R, R)


# ==========================================
# MONTAGE
# ==========================================
SHAPES = [
    ("sierpinski", gen_sierpinski, "21. TROJKAT SIERPINSKIEGO", "[B] rekurencyjny, kafelkowany"),
    ("kepler_ty", gen_kepler_ty, "22. TESELACJA 'Ty' KEPLERA", "[ETAP A] 5-krotny, do teselacji"),
    ("gereh", gen_gereh, "23. GEREH (partycja)", "[B] osmiokat=gwiazda+8 latawcow"),
    ("dragon", gen_dragon, "24. SMOK HARTERA-HEIGHWAYA", "[ETAP A] twindragon reptile"),
    ("koch_snowflake", gen_koch_snowflake, "25. PLATEK KOCHA", "[ETAP A] 2-rozmiarowy kafel"),
    ("koch_island", gen_koch_island, "26. WYSPA KOCHA (Minkowski)", "[B] reptile, kafelkuje"),
    ("hirotaka", gen_hirotaka, "27. FRAKTAL HIROTAKI (?)", "[ETAP A] -> Penrose"),
    ("rosette", gen_rosette, "28. ROZETA (kolowa)", "[B] pierscienie kolowe, przyciete"),
    ("mandala", gen_mandala, "29. MANDALA", "[B] koncentryczna, przycieta"),
    ("nautilus", gen_nautilus, "30. NAUTILUS (wlasny)", "[B] log-pierscienie ze skretem"),
    ("shatter", gen_shatter, "31. SHATTER (wlasny)", "[B] pekniecie, promien poza rogi"),
    ("moire", gen_moire, "32. MOIRE (wlasny)", "[B] geom. siatka zwichrowana"),
    ("braid", gen_braid, "33. BRAID (wlasny)", "[B] basketweave, plaski przeplot"),
    ("vortex", gen_vortex, "34. VORTEX (wlasny)", "[B] wir: pierscienie ze skretem"),
    ("bloom", gen_bloom, "35. BLOOM (wlasny)", "[ETAP A] Voronoi phyllotaxis"),
    ("stagger_tri", gen_stagger_tri, "36. TROJKATY PRZESUNIETE", "[B] przesuniete warstwy (b. sierpinski)"),
]


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    panels = {}
    for name, fn, t1, t2 in SHAPES:
        print(f"[gen] {name} ...")
        polys, world = fn()
        img = render(polys, world)
        img.save(ASSETS_DIR / f"{name}.png")
        panels[name] = img
        print(f"      {len(polys)} tiles -> assets/shape_schemes/{name}.png")

    PW, TH = 475, 60
    cols_n, rows_n = 5, 3
    mont = Image.new("RGB", (PW * cols_n, (PW + TH) * rows_n), (10, 10, 12))
    draw = ImageDraw.Draw(mont)
    try:
        f_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 16)
        f_reg = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
    except OSError:
        f_bold = f_reg = ImageFont.load_default()

    for idx, (name, fn, t1, t2) in enumerate(SHAPES):
        r, c = divmod(idx, cols_n)
        x0, y0 = c * PW, r * (PW + TH)
        img = panels[name].resize((PW - 24, PW - 24), Image.Resampling.LANCZOS)
        for txt, font, dy in [(t1, f_bold, 10), (t2, f_reg, 34)]:
            tw = draw.textlength(txt, font=font)
            draw.text((x0 + (PW - tw) / 2, y0 + dy), txt, fill=(235, 235, 235), font=font)
        mont.paste(img.convert("RGB"), (x0 + 12, y0 + TH))

    out = OUT_DIR / "proposals_extra_15_shapes.png"
    mont.save(out)
    print(f"[gen] montage -> {out}")


if __name__ == "__main__":
    main()
