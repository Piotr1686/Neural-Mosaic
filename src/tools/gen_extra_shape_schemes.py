"""Generate schematic previews for the additional tile-shape proposals (21-36).

PROPOSAL previews (720x720 GUI swatches), NOT engine implementations. Pure
geometry + PIL + scipy (Voronoi), deterministic (seeded RNG only). ASCII-only
prints (CP1250 terminal).

HARD REQUIREMENT (user, 2026-07-03): every shape must be a TRUE tessellation -
edge-to-edge, no overlaps, no gaps, fills the whole rectangle, self-repeating.
Rev 2026-07-04 (user corrections): the background-grid crutch is gone from all
kept shapes; every cell is part of the tessellation itself:
  - bloom          -> Voronoi diagram of a sunflower phyllotaxis (golden angle)
  - dragon         -> twindragon rep-tile partition (base 1+i digit squares)
  - gereh          -> 4.8.8 partition into quads only (star split into 8 kites)
  - koch_snowflake -> two-size Koch snowflake tessellation (ratio 1/sqrt(3))
  - sierpinski     -> brick-staggered rows, holes = photo cells by level
  - nautilus       -> log-spiral rings, pole OUTSIDE the frame (no singularity);
                      replaces the radial family (mandala / vortex / shatter
                      REMOVED as near-duplicates, 2026-07-04)
  - rosette        -> REVIVED as the 12-fold Islamic rosette the user linked
                      (Shrine of Moulay Idriss II, Fez): 3.12.12 partition
  - scales         -> NEW (user link): fish-scale shield cells, checkerboard
                      circle lattice
  - pebbles        -> NEW (user image): variable-density Voronoi pebble mosaic
  - penrose_p2     -> replaces hirotaka (last ETAP-A placeholder, resolved
                      2026-07-04): true Penrose P2 kites & darts by Robinson
                      deflation - distinct from the engine's `penrose` (P3
                      rhombs from the pentagrid). kepler_ty REMOVED 2026-07-16:
                      same (N, zeta, gamma) as `penrose` => same tiling; only
                      its palette differed, and colour vanishes under photos.

ETAP A fully resolved - no shape uses a background grid any more.

Rev 2026-07-04b #2 (user verdicts after the montage review):
  - sierpinski_b / sierpinski_c REJECTED and removed -> sierpinski_d
    (checkerboard carriers: every 2nd triangle in a row, +1 shift per row)
  - sierpinski_carpet: solids recurse 1 level deeper than holes (smallest
    hole always 3x the background cell)
  - rosette_fractal / voderberg / girih: radial centres rebuilt from cells
    of the SAME shape as the rest of each tessellation (no separate cap)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_extra_shape_schemes
"""
import cmath
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import Voronoi

from src.tools.gen_fable_shape_schemes import (
    ASSETS_DIR, render, vary, hsv_rgb, c2t, _clip_rect,
)

OUT_DIR = Path("output/kite_schemes")


# ==========================================
# SHARED HELPERS
# ==========================================
def _reg_poly(centre, r, n, phase=0.0):
    return [centre + r * cmath.exp(1j * (phase + 2 * math.pi * k / n)) for k in range(n)]


# ==========================================
# 21. SIERPINSKI TRIANGLE  [natywne wypelnienie, cegielki]
# ==========================================
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
    """Sierpinski triangles tiling the plane (up + down interlock), depth 3,
    with ODD ROWS SHIFTED by half a period (brick stagger) so the big level-3
    holes spread evenly instead of lining up in columns. T-junctions on the
    horizontal row boundaries are fine for a mosaic partition (no gaps).

    Photo-mapping plan: every triangle is one photo cell -
      level 0 (solid leaves, side S/8)  -> smallest photos, dense texture;
      level 1..3 holes (side S/4..S/2)  -> progressively LARGER single photos,
    so the fractal reads through photo scale, not through empty space."""
    rng = np.random.default_rng(211)
    R = 1.0
    S = 0.95
    H = S * math.sqrt(3) / 2
    depth = 3
    pal_solid = [(224, 170, 92), (214, 148, 70)]
    pal_hole = [(44, 48, 62), (58, 50, 66), (48, 62, 58), (66, 54, 56)]
    polys = []
    rows = int(2 * R / H) + 3
    cols = int(2 * R / S) + 3
    for r in range(-1, rows):
        y0 = -R + r * H
        xoff = (S / 2) if (r % 2) else 0.0     # brick stagger per row
        for c in range(-2, cols):
            x0 = -R + c * S + xoff
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


def _sierp4(A, B, C, depth, cells):
    """Uniform treatment for NON-carrier triangles: split into 4 half-size
    sub-triangles (the central one included, in its inverted orientation) and
    run a depth-`depth` gasket in each. Keeps the fractal texture but caps the
    largest hole at half the carrier hole size - so the big holes live ONLY on
    carrier triangles."""
    ab, bc, ca = (A + B) / 2, (B + C) / 2, (C + A) / 2
    for tri in ((A, ab, ca), (ab, B, bc), (ca, bc, C), (ab, bc, ca)):
        _sierpinski_cells(tri[0], tri[1], tri[2], depth, cells)


def _gen_sierpinski_variant(seed, carrier):
    """Shared frame for the interleaved-hole Sierpinski variants (user request
    2026-07-04: the LARGEST holes must be evenly distributed instead of
    clustering). Unlike the base `sierpinski` the triangle grid is NOT
    row-staggered here - aligned rows are what lets the carrier pattern offset
    the big holes row to row (with the stagger, per-row carrier picks land in
    the same columns again: the variant-C failure). `carrier(r, t)` decides
    from the row index r and the SEQUENTIAL position t within the row
    (counting BOTH up and down triangles) which triangles get the full
    depth-3 gasket (big central hole); the rest get the capped `_sierp4`
    treatment."""
    rng = np.random.default_rng(seed)
    R = 1.0
    S = 0.95
    H = S * math.sqrt(3) / 2
    pal_solid = [(224, 170, 92), (214, 148, 70)]
    pal_hole = [(44, 48, 62), (58, 50, 66), (48, 62, 58), (66, 54, 56)]
    polys = []
    rows = int(2 * R / H) + 3
    cols = int(2 * R / S) + 3
    for r in range(-1, rows):
        y0 = -R + r * H
        for c in range(-2, cols):
            x0 = -R + c * S
            BL, BR, TOP = complex(x0, y0), complex(x0 + S, y0), complex(x0 + S / 2, y0 + H)
            TL, TR, BOT = complex(x0 + S / 2, y0 + H), complex(x0 + 1.5 * S, y0 + H), complex(x0 + S, y0)
            for tri, t, par in [((BL, BR, TOP), 2 * c, (r + c) % 2),
                                ((TL, TR, BOT), 2 * c + 1, (r + c + 1) % 2)]:
                cells = []
                if carrier(r, t):
                    _sierpinski_cells(tri[0], tri[1], tri[2], 3, cells)
                else:
                    _sierp4(tri[0], tri[1], tri[2], 2, cells)
                for poly, tag in cells:
                    if tag == 0:
                        col = vary(rng, pal_solid[par], 10)
                    else:
                        col = vary(rng, pal_hole[tag % len(pal_hole)], 8)
                    polys.append((c2t(poly), col))
    return polys, (-R, -R, R, R)


def gen_sierpinski_d():
    """Variant D - CHECKERBOARD (user verdict 2026-07-04b; variants B 'up
    only' and C 'row interleave' REJECTED and removed): carriers alternate
    with filled triangles every second triangle SEQUENTIALLY within each row
    (regardless of up/down orientation), and the pattern shifts by ONE
    TRIANGLE on every next row - carrier = (t + r) % 2. On the non-staggered
    grid this offsets the big holes by half a period row to row (and flips
    their orientation), so they weave an even checkerboard instead of
    stacking into columns."""
    return _gen_sierpinski_variant(214, lambda r, t: (t + r) % 2 == 0)


# ==========================================
# 40. SIERPINSKI CARPET  [natywne wypelnienie]
# ==========================================
def _carpet_cells(x, y, s, depth, cells):
    """Classic Sierpinski carpet recursion: the 8 ring sub-squares recurse,
    the centre sub-square is a 'hole' cell tagged with its level - EXCEPT at
    depth 1 (rev 2026-07-04b, user): a level-1 hole has the SAME size as the
    solid background cells, so it becomes indistinguishable once photos
    replace the colours. The depth-1 centre square is emitted as a plain
    solid cell instead, which makes the smallest real hole (level 2) always
    3x the background cell. Every square (solid AND hole) is a cell - no
    actual gaps; the fractal reads through the level-based colouring (holes =
    progressively larger photos, same plan as the Sierpinski triangle)."""
    if depth == 0:
        cells.append(((x, y, s), 0))
        return
    t = s / 3
    for a in range(3):
        for b in range(3):
            if a == 1 and b == 1:
                cells.append(((x + t, y + t, t), depth if depth >= 2 else 0))
            else:
                _carpet_cells(x + a * t, y + b * t, t, depth - 1, cells)


def gen_sierpinski_carpet():
    """Sierpinski carpet (user request 2026-07-04): one carpet spans the
    whole square frame - a true partition into axis-aligned squares. Rev
    2026-07-04b (user): solids recurse one level DEEPER than the holes
    (depth 4, holes only from level 2 up), so the background texture is a
    uniform 1/81 grid and the smallest hole (1/27) stays 3x bigger than any
    background cell - distinguishable after photo substitution. The carpet
    is a rep-tile, so the frame itself repeats seamlessly."""
    rng = np.random.default_rng(40)
    cells = []
    _carpet_cells(-1.0, -1.0, 2.0, 4, cells)
    unit = 2.0 / 81.0
    pal_solid = [(224, 170, 92), (214, 148, 70)]
    pal_hole = [(44, 48, 62), (58, 50, 66), (48, 62, 58)]
    polys = []
    for (x, y, s), tag in cells:
        rect = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
        if tag == 0:
            par = (int(round((x + 1) / unit)) + int(round((y + 1) / unit))) % 2
            col = vary(rng, pal_solid[par], 10)
        else:
            col = vary(rng, pal_hole[tag % len(pal_hole)], 8)
        polys.append((rect, col))
    return polys, (-1.0, -1.0, 1.0, 1.0)


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
# 23. GEREH ON A TESSELLATION  [natywne wypelnienie]
# ==========================================
def gen_gereh():
    """Gereh as a true PARTITION of quads only (rev 2026-07-04: the previous
    version kept the whole 8-point star as ONE spiky cell - impractical to fill
    with a photo). Octagon+square 4.8.8 tiling; each octagon splits into
    8 central kites (they compose the khatam star via colour) + 8 outer kites
    over the vertices. Every cell is a compact quadrilateral."""
    rng = np.random.default_rng(23)
    p = 1 + math.sqrt(2)
    Roct = 1.0 / (2 * math.sin(math.pi / 8))     # octagon circumradius (edge 1)
    apoth = 1.0 / (2 * math.tan(math.pi / 8))    # octagon apothem
    r_in = apoth * 0.60                          # fatter star core than rev 1 (0.42)
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
            # star = 8 kite cells around the centre (photo-friendly quads that
            # still READ as one 8-point star through the shared colour)
            for k in range(8):
                kite_c = [c, inner[(k - 1) % 8], Mid[k], inner[k]]
                polys.append((c2t(kite_c), vary(rng, pal_star, 9)))
            for k in range(8):
                kite = [Mid[k], V[(k + 1) % 8], Mid[(k + 1) % 8], inner[k]]
                polys.append((c2t(kite), vary(rng, pal_kite, 10)))
            cs = complex((i + 0.5) * p, (j + 0.5) * p)
            polys.append((c2t(_reg_poly(cs, math.sqrt(2) / 2, 4, math.pi / 4)),
                          vary(rng, pal_sq, 10)))
    Rw = 2.35 * p
    return polys, (-Rw, -Rw, Rw, Rw)


# ==========================================
# 24. TWINDRAGON (rep-tile partition)  [natywne wypelnienie]
# ==========================================
def _twindragon_boundary(order):
    """Boundary polygon of the order-n twindragon: the 2^n unit squares at
    Gaussian integers sum(d_k (1+i)^k), d_k in {0,1}. Interior edges cancel in
    opposite pairs; the survivors are chained into one loop (at pinch vertices
    the sharpest LEFT turn keeps the interior consistently on the left)."""
    b = 1 + 1j
    cells = {0j}
    for k in range(order):
        step = b ** k
        cells |= {z + step for z in cells}

    edges = set()
    for z in cells:
        x, y = int(round(z.real)), int(round(z.imag))
        corner = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
        for i in range(4):
            e = (corner[i], corner[(i + 1) % 4])
            back = (e[1], e[0])
            if back in edges:
                edges.remove(back)
            else:
                edges.add(e)

    nxt = {}
    for a, bb in edges:
        nxt.setdefault(a, []).append(bb)
    start = min(nxt)
    loop = [start]
    cur = start
    prev_dir = (0, -1)
    while True:
        cands = nxt[cur]
        if len(cands) == 1:
            chosen = cands[0]
        else:
            def turn(nb):
                d = (nb[0] - cur[0], nb[1] - cur[1])
                a0 = math.atan2(prev_dir[1], prev_dir[0])
                a1 = math.atan2(d[1], d[0])
                t = (a1 - a0) % (2 * math.pi)
                return t if t > 1e-9 else 2 * math.pi
            chosen = min(cands, key=turn)      # sharpest left turn first
        cands.remove(chosen)
        prev_dir = (chosen[0] - cur[0], chosen[1] - cur[1])
        if chosen == start:
            break
        loop.append(chosen)
        cur = chosen
    return loop


def gen_dragon():
    """Back to the linked source (Heighway dragon, 'O smokach'): the TWINDRAGON
    is a rep-tile, so congruent dragon-shaped tiles fill the plane exactly -
    no overlaps, no gaps, no background. Lattice: (1+i)^n * Z[i]. Each fractal
    'dragon' is one photo cell with the classic jagged coastline."""
    rng = np.random.default_rng(24)
    order = 8
    loop = _twindragon_boundary(order)
    lam = (1 + 1j) ** order
    v1, v2 = lam, lam * 1j
    ctr0 = complex(sum(x for x, _ in loop) / len(loop),
                   sum(y for _, y in loop) / len(loop))
    pal = [(205, 135, 62), (96, 128, 168), (176, 92, 84),
           (150, 160, 96), (148, 110, 162), (206, 168, 88)]
    Rw = 17.0
    polys = []
    for a in range(-4, 5):
        for bb in range(-4, 5):
            off = a * v1 + bb * v2
            c = ctr0 + off
            if abs(c.real - ctr0.real) > 2.6 * Rw or abs(c.imag - ctr0.imag) > 2.6 * Rw:
                continue
            col = vary(rng, pal[(a - 2 * bb) % len(pal)], 10)
            polys.append(([(x + off.real, y + off.imag) for x, y in loop], col))
    return polys, (ctr0.real - Rw, ctr0.imag - Rw, ctr0.real + Rw, ctr0.imag + Rw)


# ==========================================
# 25. KOCH SNOWFLAKE (two-size tessellation)  [natywne wypelnienie]
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
    """The classic TWO-SIZE Koch snowflake tessellation: big flakes on a
    triangular lattice (spacing = 2R, touching at their 6 radius-R points) and
    small flakes (scale 1/sqrt(3), rotated 30 deg) in the two lattice holes.
    Area check: cell sqrt(3)/2*(2R)^2 = big (2sqrt(3)/5)*3R^2*... = big + 2
    small EXACTLY, so flakes join edge-to-edge on every side - no background.
    (Finite Koch depth is a polygonal approximation of the limit fractal;
    hairline seams below outline width.)"""
    rng = np.random.default_rng(25)
    R = 1.0
    Rb = 0.42                        # big flake: centre -> vertex radius
    spacing = 2 * Rb
    t1 = complex(spacing, 0)
    t2 = complex(spacing / 2, spacing * math.sqrt(3) / 2)
    Rs = Rb / math.sqrt(3)           # small flake radius
    depth = 3
    pal_big = [(210, 150, 60), (170, 95, 90), (120, 160, 110), (150, 110, 160)]
    pal_small = [(90, 120, 160), (120, 120, 85)]
    polys = []
    for m in range(-4, 5):
        for n in range(-4, 5):
            c = m * t1 + n * t2
            if abs(c) > 2.4:
                continue
            polys.append((c2t(_snowflake(c, Rb, depth, phase=0.0)),
                          vary(rng, pal_big[(m - n) % len(pal_big)], 10)))
            for hi, hc in enumerate((c + (t1 + t2) / 3, c + 2 * (t1 + t2) / 3)):
                polys.append((c2t(_snowflake(hc, Rs, depth, phase=math.pi / 6)),
                              vary(rng, pal_small[hi], 10)))
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
# 27. PENROSE P2 (kites & darts via P3 + Robinson A/B relations)
# ==========================================
def _p3_half_deflate(tris):
    """One P3 (rhombus) Robinson-triangle deflation step (Preshing scheme).
    (colour, A, B, C): 0 = half-THIN rhomb (acute 36-72-72, apex A, legs
    AB=AC=L, base BC=L/phi), 1 = half-FAT rhomb (gnomon 36-36-108, apex A,
    legs AB=AC=L, base BC=L*phi). NOTE: direct P2 half-tile substitutions
    derived by hand kept producing T-junctions (2 failed attempts, 2026-07-04:
    edge split points misalign across parent boundaries unless the axis/outer
    role of every child leg is exactly right). The P3 route below is fully
    validated instead."""
    phi = (1 + math.sqrt(5)) / 2
    out = []
    for colour, A, B, C in tris:
        if colour == 0:
            P = A + (B - A) / phi
            out += [(0, C, P, B), (1, P, C, A)]
        else:
            Q = B + (A - B) / phi
            R_ = B + (C - B) / phi
            out += [(1, R_, C, A), (1, Q, R_, B), (0, R_, Q, A)]
    return out


def gen_penrose_p2():
    """TRUE Penrose P2 (kites & darts) - replaces the hirotaka pentaflake
    placeholder (pentaflake does NOT tile; last ETAP-A slot, resolved
    2026-07-04). Deliberately DISTINCT from the engine's `penrose` (P3 rhombs
    from the pentagrid): cells here are full KITES and DARTS.

    Construction (P2 and P3 are mutually locally derivable via Robinson
    A/B-tiles, BS = AL and BL = AL + AS): deflate the P3 'sun' 6x, then
    convert B-tiles to A-tiles - every half-thin IS a half-kite (AL); every
    half-fat splits at U (|BU| = leg) into half-kite + half-dart (AS). The
    cut direction is the one consistent with P2 matching rules: it leaves
    0 unmatched interior halves (the mirror cut |CU|=leg leaves 410).
    Halves then merge into whole tiles by mirror-twin matching: same kind +
    shared leg + common apex point => twins (congruent isoceles halves on
    opposite sides of the shared edge); degree-1-first order resolves the
    ambiguous even cycles at sun/star vertices. Exact edge-to-edge partition:
    no gaps, no overlaps, no background.

    Colouring for the 5-fold motifs: darts dark (5 dart tips meeting = dark
    5-point STAR), kites warm by axis orientation mod 5 (SUNS/rosettes read
    as 5-tone pinwheels)."""
    rng = np.random.default_rng(27)
    R = 1.0
    Rd = 2.2                    # sun radius: decagon inradius 2.09 > sqrt(2)
    depth = 6
    phi = (1 + math.sqrt(5)) / 2
    tris = []
    for i in range(10):
        B = cmath.rect(Rd, (2 * i - 1) * math.pi / 10)
        C = cmath.rect(Rd, (2 * i + 1) * math.pi / 10)
        if i % 2 == 0:
            B, C = C, B         # mirror alternate halves -> consistent pairs
        tris.append((0, 0j, B, C))
    for _ in range(depth):
        tris = _p3_half_deflate(tris)

    a_tiles = []                # (kind, apex, v1, v2); 0 = AL half-kite, 1 = AS half-dart
    for colour, A, B, C in tris:
        if colour == 0:
            a_tiles.append((0, A, B, C))
        else:
            U = B + (C - B) / phi
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
        i = next(iter(alive))   # only sun/star cycles remain: any choice valid
        commit(i, next(iter(alive[i])))

    pal_kite = [(214, 158, 62), (198, 122, 64), (222, 180, 96),
                (182, 96, 70), (206, 142, 84)]
    pal_dart = [(58, 76, 108), (70, 68, 98)]
    polys = []
    for i, j in pairs:
        kind, A, B, C = a_tiles[i]
        pts_j = {rp(a_tiles[j][1]), rp(a_tiles[j][2]), rp(a_tiles[j][3])}
        X = B if rp(B) in pts_j else C          # shared leg = tile axis
        t1 = C if X is B else B
        t2 = next(v for v in a_tiles[j][2:] if rp(v) not in (rp(A), rp(X)))
        ctr = (A + X) / 2
        if abs(ctr.real) > R + 0.2 or abs(ctr.imag) > R + 0.2:
            continue
        ang = cmath.phase(X - A) % (2 * math.pi)
        bucket = int(ang / (2 * math.pi) * 10 + 0.5) % 5   # fold opposite axes
        if kind == 0:
            col = vary(rng, pal_kite[bucket], 9)
        else:
            col = vary(rng, pal_dart[bucket % 2], 8)
        polys.append((c2t([A, t1, X, t2]), col))
    return polys, (-R, -R, R, R)


# ==========================================
# 28. ROSETTE (12-fold Islamic, Fez)  [natywne wypelnienie]
# ==========================================
def gen_rosette():
    """12-fold Islamic rosette per the user's reference (zellij of the Shrine
    of Moulay Idriss II, Fez; researchgate fig. 286876414): 12-pointed-star
    rosettes on the 3.12.12 lattice (dodecagons edge-to-edge + equilateral
    triangles). Each dodecagon partitions into 12 core kites (the gold star),
    12 white petal quads reaching the dodecagon vertices and 12 edge triangles;
    the interstitial 3.12.12 triangles are photo cells too. True partition -
    every cell a compact quad/triangle, no gaps, no overlaps."""
    rng = np.random.default_rng(28)
    R12 = 1.0
    ap = R12 * math.cos(math.pi / 12)
    D = 2 * ap                                  # neighbour distance (shared edge)
    t1 = complex(D, 0)
    t2 = complex(D / 2, D * math.sqrt(3) / 2)
    r0, r1 = 0.26 * R12, 0.52 * R12             # star inner notch / point radii
    pal_core = (214, 170, 82)
    pal_petal = (224, 216, 196)
    pal_edge = (96, 130, 165)
    pal_gap = (150, 92, 88)
    centres = [m * t1 + n * t2 for m in range(-3, 4) for n in range(-3, 4)]
    Rw = 2.55
    polys = []

    def u(ang):
        return cmath.exp(1j * ang)

    for c in centres:
        # BOX filter, not radial: a radial cut drops corner rosettes whose
        # dodecagons still poke into the frame (black wedges, fixed 2026-07-04)
        if abs(c.real) > Rw + 1.15 * R12 or abs(c.imag) > Rw + 1.15 * R12:
            continue
        s = [c + r1 * u(math.pi / 6 * k) for k in range(12)]                  # star points
        i_ = [c + r0 * u(math.pi / 6 * k + math.pi / 12) for k in range(12)]  # inner notches
        t = [c + R12 * u(math.pi / 6 * k + math.pi / 12) for k in range(12)]  # dodecagon verts
        for k in range(12):
            polys.append((c2t([c, i_[(k - 1) % 12], s[k], i_[k]]), vary(rng, pal_core, 8)))
            polys.append((c2t([i_[k], s[k], t[k], s[(k + 1) % 12]]), vary(rng, pal_petal, 9)))
            polys.append((c2t([s[k], t[(k - 1) % 12], t[k]]), vary(rng, pal_edge, 10)))
    # the two 3.12.12 interstitial triangles per lattice cell: vertices are the
    # two dodecagon vertices closest to the hole, from each of the 3
    # surrounding dodecagons (they coincide pairwise -> 3 unique points).
    # SEPARATE pass over ALL centres: a hole inside the frame can belong to a
    # base centre whose rosette is outside the draw filter (black-gap bug,
    # fixed 2026-07-04); dedup because each hole is reachable from 3 centres.
    seen_holes = set()
    for c in centres:
        for h in (c + (t1 + t2) / 3, c + 2 * (t1 + t2) / 3):
            hkey = (round(h.real, 4), round(h.imag, 4))
            if hkey in seen_holes:
                continue
            seen_holes.add(hkey)
            if abs(h.real) > Rw + 0.6 or abs(h.imag) > Rw + 0.6:
                continue
            near = sorted(centres, key=lambda cc: abs(cc - h))[:3]
            if abs(near[2] - h) > 0.8 * D:
                continue                        # lattice border: incomplete hole
            uniq = {}
            for cc in near:
                verts = [cc + R12 * u(math.pi / 6 * k + math.pi / 12) for k in range(12)]
                verts.sort(key=lambda v: abs(v - h))
                for v in verts[:2]:
                    uniq[(round(v.real, 6), round(v.imag, 6))] = v
            tri = sorted(uniq.values(), key=lambda v: cmath.phase(v - h))
            if len(tri) == 3:
                polys.append((c2t(tri), vary(rng, pal_gap, 10)))
    return polys, (-Rw, -Rw, Rw, Rw)


# ==========================================
# 30. NAUTILUS (pole outside the frame)  [natywne wypelnienie]
# ==========================================
def gen_nautilus():
    """Log-spiral chambered growth WITHOUT a central singularity (rev
    2026-07-04: replaces the whole radial family - rosette/mandala/vortex/
    shatter were near-duplicates of this). The spiral pole sits OUTSIDE the
    frame beyond the bottom-left corner, so the visible field is sweeping arc
    cells that grow across the canvas. Geometric radii + a constant sector
    count give near-square cells at every scale (log-polar); every cell is
    clipped to the rectangle - true partition, no overlaps, no gaps."""
    rng = np.random.default_rng(30)
    R = 1.0
    pole = complex(-1.55, -1.30)
    g = 1.16                                   # ring growth ratio
    r = abs(complex(-1, -1) - pole) * 0.55     # first ring well inside the near corner
    radii = [r]
    far = abs(complex(1, 1) - pole) + 0.15
    while radii[-1] < far:
        radii.append(radii[-1] * g)
    nsec = 40
    swirl = 0.42
    pal = [(214, 140, 66), (110, 138, 170), (176, 92, 88), (150, 166, 96), (150, 110, 162)]
    polys = []
    # cap disk under the first ring (covers the near corner if it pokes in)
    disk = [(pole.real + radii[0] * math.cos(2 * math.pi * t / 40),
             pole.imag + radii[0] * math.sin(2 * math.pi * t / 40)) for t in range(40)]
    cl = _clip_rect(disk, R)
    if len(cl) >= 3:
        polys.append((cl, vary(rng, pal[0], 8)))
    for ri in range(len(radii) - 1):
        r0, r1 = radii[ri], radii[ri + 1]
        base = ri * swirl + (math.pi / nsec) * (ri % 2)   # half-sector brick offset
        for k in range(nsec):
            a0 = base + 2 * math.pi * k / nsec
            a1 = base + 2 * math.pi * (k + 1) / nsec
            pts = []
            nseg = 5
            for sg in range(nseg + 1):
                aa = a0 + (a1 - a0) * sg / nseg
                pts.append((pole.real + r1 * math.cos(aa), pole.imag + r1 * math.sin(aa)))
            for sg in range(nseg + 1):
                aa = a1 + (a0 - a1) * sg / nseg
                pts.append((pole.real + r0 * math.cos(aa), pole.imag + r0 * math.sin(aa)))
            cl = _clip_rect(pts, R)
            if len(cl) < 3:
                continue
            col = pal[(ri + (k % 3)) % len(pal)]
            polys.append((cl, vary(rng, col, 10)))
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
# 35. BLOOM (Voronoi phyllotaxis)  [natywne wypelnienie]
# ==========================================
def gen_bloom():
    """Sunflower bloom as a TRUE tessellation (rev 2026-07-04: no background,
    no overlapping rosettes): Voronoi diagram of golden-angle phyllotaxis seeds.
    r = c*sqrt(i) keeps seed density uniform, so the Voronoi cells are
    near-equal-area everywhere while spiralling like a sunflower head. Seeds
    extend past the corners; every bounded cell is clipped to the rectangle -
    the cells join exactly (Voronoi partition) and fill the whole frame.
    Colour follows i mod 21 (Fibonacci parastichy), so the 21 spiral arms of
    the real sunflower show up in the mosaic."""
    rng = np.random.default_rng(35)
    R = 1.0
    diag = math.sqrt(2.0)
    golden = math.pi * (3 - math.sqrt(5))
    N = 520
    c = (diag + 0.45) / math.sqrt(N)
    pts = []
    for i in range(1, N + 1):
        rr = c * math.sqrt(i)
        aa = i * golden
        pts.append((rr * math.cos(aa), rr * math.sin(aa)))
    vor = Voronoi(np.array(pts))
    pal = [(214, 138, 64), (180, 90, 84), (110, 138, 170), (150, 166, 96),
           (150, 110, 162), (96, 160, 140), (206, 168, 88)]
    polys = []
    for i in range(N):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue                       # unbounded outer cells: outside frame
        poly = [tuple(vor.vertices[v]) for v in reg]
        cl = _clip_rect(poly, R)
        if len(cl) < 3:
            continue
        arm = (i + 1) % 21                 # parastichy arm id
        polys.append((cl, vary(rng, pal[arm % len(pal)], 10)))
    return polys, (-R, -R, R, R)


# ==========================================
# 37. SCALES (fish scales)  [natywne wypelnienie]
# ==========================================
def gen_scales():
    """Fish-scale (imbricated scallop) tiling per the user's reference: circles
    of radius r on the checkerboard lattice (dx=2r, dy=r, half-period row
    offset) cover the plane exactly (covering radius = r); each scale = its
    disk minus the two disks of the row below. The circle intersections land
    exactly on the bottom point and the side points of each circle, so every
    cell is the classic shield: a semicircular dome + two concave arcs meeting
    in a bottom tip. True partition - no overlaps, no gaps."""
    rng = np.random.default_rng(37)
    R = 1.0
    rs = 0.17
    nseg = 16
    tpl = []
    for t_ in range(2 * nseg + 1):                      # dome: 180 -> 0 deg
        a = math.pi - math.pi * t_ / (2 * nseg)
        tpl.append((rs * math.cos(a), rs * math.sin(a)))
    for t_ in range(1, nseg + 1):                       # right bite: 90 -> 180 on (rs,-rs)
        a = math.pi / 2 + math.pi / 2 * t_ / nseg
        tpl.append((rs + rs * math.cos(a), -rs + rs * math.sin(a)))
    for t_ in range(1, nseg):                           # left bite: 0 -> 90 on (-rs,-rs)
        a = math.pi / 2 * t_ / nseg
        tpl.append((-rs + rs * math.cos(a), -rs + rs * math.sin(a)))
    pal = [(64, 138, 148), (84, 158, 158), (104, 174, 164), (72, 122, 142)]
    polys = []
    nj = int(math.ceil(2 * R / rs)) + 2
    ni = int(math.ceil(2 * R / (2 * rs))) + 2
    for j in range(-nj // 2, nj):
        y = j * rs - R + rs / 2
        xoff = rs if (j % 2) else 0.0
        for i in range(-ni // 2, ni):
            x = i * 2 * rs + xoff - R
            cell = [(px + x, py + y) for px, py in tpl]
            cl = _clip_rect(cell, R)
            if len(cl) < 3:
                continue
            polys.append((cl, vary(rng, pal[(j % 4)], 12)))
    return polys, (-R, -R, R, R)


# ==========================================
# 38. PEBBLES (variable-density Voronoi)  [natywne wypelnienie]
# ==========================================
def gen_pebbles():
    """Organic pebble mosaic per the user's reference image: a Voronoi
    partition whose seed density varies smoothly across the canvas (sum of
    random Gaussian blobs, rejection sampling), so clusters of small cells sit
    next to patches of big ones. Exact Voronoi partition clipped to the frame -
    no overlaps, no gaps. Distinct from the planned uniform `voronoi` (#15):
    the multi-scale density IS the motif here."""
    rng = np.random.default_rng(38)
    R = 1.0
    blobs = [(complex(rng.uniform(-1, 1), rng.uniform(-1, 1)),
              rng.uniform(0.22, 0.5), rng.uniform(2.5, 8.0)) for _ in range(6)]
    dmax = 1.0 + sum(w for _, _, w in blobs)

    def dens(x, y):
        d = 1.0
        for c, s, w in blobs:
            dd = abs(complex(x, y) - c)
            d += w * math.exp(-(dd * dd) / (2 * s * s))
        return d

    M = 1.4
    pts = []
    while len(pts) < 720:
        x = rng.uniform(-M, M)
        y = rng.uniform(-M, M)
        if rng.uniform(0, dmax) < dens(x, y):
            pts.append((x, y))
    vor = Voronoi(np.array(pts))
    pal = [(196, 178, 150), (176, 160, 138), (188, 166, 128),
           (162, 152, 140), (204, 188, 162), (170, 148, 118)]
    polys = []
    for i in range(len(pts)):
        reg = vor.regions[vor.point_region[i]]
        if not reg or -1 in reg:
            continue
        poly = [tuple(vor.vertices[v]) for v in reg]
        cl = _clip_rect(poly, R)
        if len(cl) < 3:
            continue
        polys.append((cl, vary(rng, pal[i % len(pal)], 12)))
    return polys, (-R, -R, R, R)


# ==========================================
# 39. ROSETTE FRACTAL (spiral aloe)  [natywne wypelnienie]
# ==========================================
def gen_rosette_fractal():
    """Spiral aloe (Aloe polyphylla) per the user's photo: a triangulated
    annulus strip in LOG-POLAR space, alternating leaf triangles (tips
    outward) with dark filler (the shadows between aloe leaves); per-ring
    phase shift lines the shared edges into logarithmic spiral arms.

    Rev 2026-07-04b (user): the constant sector count made leaves shrink to
    NOTHING at the pole - impractical centre. Solved like sunburst/bloom
    (cells ~constant size at every radius): the sector count DOUBLES every m
    rings and the ring ratio is g = 2^(1/m), so tangential cell size resets
    each doubling instead of vanishing inward. Rev 2026-07-04b #2 (user): the
    plain N0-gon cap is gone too - the pole is a fan of N0 leaf/gap triangles
    of the SAME shape as the rings, converging tip-first at the centre (no
    separate 'circle'). A doubling strip fans each coarse sector
    into 3 triangles; every edge is still sampled identically by both cells
    (true partition, T-junction-free within strips)."""
    rng = np.random.default_rng(39)
    R = 1.0
    N0 = 12                              # sectors of the innermost ring
    m = 3                                # rings per sector doubling
    g = 2 ** (1 / m)                     # ring growth: doubles radius per m rings
    r0 = 0.14
    delta = 0.62                         # spiral twist, in own-sector units
    diag = math.sqrt(2.0)
    pal_leaf = [(96, 140, 76), (78, 124, 66), (112, 152, 86), (88, 132, 70)]
    pal_gap = [(52, 72, 46), (60, 66, 44)]
    radii = [r0]
    while radii[-1] < diag + 0.1:
        radii.append(radii[-1] * g)
    Ns = [N0 * (2 ** (i // m)) for i in range(len(radii))]
    offs = [0.0]
    for i in range(1, len(radii)):
        offs.append(offs[-1] + delta * 2 * math.pi / Ns[i])

    def vang(i, k):
        return offs[i] + 2 * math.pi * k / Ns[i]

    def edge(i0, k0, i1, k1, nseg=5):
        """Polyline between vertex k0 of ring i0 and vertex k1 of ring i1
        (each k in its OWN ring's sector units), straight in (log r, theta)
        space. Both cells sharing an edge sample it identically (exact
        seams). Returns nseg points, endpoint excluded."""
        u0, u1 = math.log(radii[i0]), math.log(radii[i1])
        a0, a1 = vang(i0, k0), vang(i1, k1)
        pts = []
        for t in range(nseg):
            f = t / nseg
            u = u0 + (u1 - u0) * f
            a = a0 + (a1 - a0) * f
            pts.append((math.exp(u) * math.cos(a), math.exp(u) * math.sin(a)))
        return pts

    def emit(loop, col):
        pts = _clip_rect(loop, R)
        if len(pts) >= 3:
            polys.append((pts, col))

    polys = []
    # centre fan: N0 triangles converging tip-first at the pole; the outer
    # edge reuses edge(), so the fan meets ring 0 with identical sampling
    # (exact seams). Leaf/gap alternation continues the ring motif inward.
    for k in range(N0):
        a1 = vang(0, k + 1)
        fan = ([(0.0, 0.0)] + edge(0, k, 0, k + 1)
               + [(radii[0] * math.cos(a1), radii[0] * math.sin(a1))])
        if k % 2 == 0:
            col = vary(rng, pal_leaf[(k // 2) % len(pal_leaf)], 10)
        else:
            col = vary(rng, pal_gap[(k // 2) % 2], 8)
        emit(fan, col)
    for i in range(len(radii) - 1):
        Ni, Nj = Ns[i], Ns[i + 1]
        if Nj == Ni:
            # plain strip: leaf (tip outward) + gap (tip inward) per sector
            for k in range(Ni):
                emit(edge(i, k, i, k + 1) + edge(i, k + 1, i + 1, k)
                     + edge(i + 1, k, i, k),
                     vary(rng, pal_leaf[(i + k) % len(pal_leaf)], 10))
                emit(edge(i, k + 1, i + 1, k + 1) + edge(i + 1, k + 1, i + 1, k)
                     + edge(i + 1, k, i, k + 1),
                     vary(rng, pal_gap[(i + k) % 2], 8))
        else:
            # doubling strip: coarse sector k fans into 3 triangles against
            # fine vertices 2k, 2k+1, 2k+2 (leaf points outward in the middle)
            for k in range(Ni):
                emit(edge(i, k, i + 1, 2 * k + 1) + edge(i + 1, 2 * k + 1, i + 1, 2 * k)
                     + edge(i + 1, 2 * k, i, k),
                     vary(rng, pal_gap[(i + k) % 2], 8))
                emit(edge(i, k, i, k + 1) + edge(i, k + 1, i + 1, 2 * k + 1)
                     + edge(i + 1, 2 * k + 1, i, k),
                     vary(rng, pal_leaf[(i + k) % len(pal_leaf)], 10))
                emit(edge(i, k + 1, i + 1, 2 * k + 2) + edge(i + 1, 2 * k + 2, i + 1, 2 * k + 1)
                     + edge(i + 1, 2 * k + 1, i, k + 1),
                     vary(rng, pal_gap[(i + k + 1) % 2], 8))
    return polys, (-R, -R, R, R)


# ==========================================
# MONTAGE
# ==========================================
SHAPES = [
    ("sierpinski", gen_sierpinski, "21. TROJKAT SIERPINSKIEGO", "[B] cegielkowy rozklad dziur, kazdy trojkat=foto"),
    ("sierpinski_d", gen_sierpinski_d, "21d. SIERPINSKI SZACHOWNICA", "[B] dziury co drugi trojkat w rzedzie, +1 co rzad"),
    ("gereh", gen_gereh, "23. GEREH (partycja)", "[B] same czworokaty: 8 rombow gwiazdy + latawce"),
    ("dragon", gen_dragon, "24. TWINDRAGON (reptile)", "[B] smoki kafelkuja plaszczyzne, zero nakladania"),
    ("koch_snowflake", gen_koch_snowflake, "25. PLATEK KOCHA (2 rozmiary)", "[B] duze+male platki brzeg-w-brzeg"),
    ("koch_island", gen_koch_island, "26. WYSPA KOCHA (Minkowski)", "[B] reptile, kafelkuje"),
    ("penrose_p2", gen_penrose_p2, "27. PENROSE P2 (latawce+strzalki)", "[B] deflacja Robinsona, gwiazdy/slonca 5-krotne"),
    ("rosette", gen_rosette, "28. ROZETA 12-krotna (Fez)", "[B] zellij Moulay Idriss II, siatka 3.12.12"),
    ("nautilus", gen_nautilus, "30. NAUTILUS", "[B] log-spirala, biegun poza kadrem (bez srodka)"),
    ("moire", gen_moire, "32. MOIRE (wlasny)", "[B] geom. siatka zwichrowana"),
    ("braid", gen_braid, "33. BRAID (wlasny)", "[B] basketweave, plaski przeplot"),
    ("bloom", gen_bloom, "35. BLOOM (slonecznik)", "[B] Voronoi phyllotaxis, 21 ramion"),
    ("stagger_tri", gen_stagger_tri, "36. TROJKATY PRZESUNIETE", "[B] przesuniete warstwy (b. sierpinski)"),
    ("scales", gen_scales, "37. LUSKI (scales)", "[B] rybie luski: kopula + 2 luki, partycja"),
    ("pebbles", gen_pebbles, "38. PEBBLES (kamyki)", "[B] Voronoi o zmiennej gestosci ziaren"),
    ("rosette_fractal", gen_rosette_fractal, "39. ROZETA SPIRALNA (aloes)", "[B] liscie x2 co 3 pierscienie, srodek=wachlarz lisci"),
    ("sierpinski_carpet", gen_sierpinski_carpet, "40. DYWAN SIERPINSKIEGO", "[B] tlo 1/81, najmniejsza dziura 3x wieksza od tla"),
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
    cols_n = 4
    rows_n = (len(SHAPES) + cols_n - 1) // cols_n
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
