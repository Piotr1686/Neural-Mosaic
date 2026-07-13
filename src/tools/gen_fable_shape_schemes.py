"""Generate schematic previews for the 10 Fable-proposed tile shapes.

Outputs:
  assets/shape_schemes/<mode>.png        (720x720, GUI scheme preview)
  output/kite_schemes/proposals_fable_10_shapes.png  (5x2 montage, numbered 11-20)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_fable_shape_schemes

Pure geometry + PIL; deterministic (seeded RNG only). ASCII-only prints (CP1250).
"""
import cmath
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label as _nd_label
from scipy.spatial import ConvexHull, QhullError

ASSETS_DIR = Path("assets/shape_schemes")
OUT_DIR = Path("output/kite_schemes")
SIZE = 720
SS = 2  # supersampling factor

BG = (16, 16, 20, 255)
OUTLINE = (8, 8, 10, 255)


# ==========================================
# RENDER HELPERS
# ==========================================
def render(polys, world, size=SIZE, bg=BG, outline=OUTLINE, lw=3):
    """Rasterise [(poly, rgb), ...] given in world coords onto a size x size canvas.

    world = (x0, y0, x1, y1) window mapped to the canvas (aspect preserved, fill).
    """
    x0, y0, x1, y1 = world
    W = size * SS
    sx = W / (x1 - x0)
    sy = W / (y1 - y0)
    s = max(sx, sy)  # fill the canvas (crop overflow)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    img = Image.new("RGBA", (W, W), bg)
    draw = ImageDraw.Draw(img)
    for poly, col in polys:
        pts = [((px - cx) * s + W / 2, (py - cy) * s + W / 2) for px, py in poly]
        draw.polygon(pts, fill=tuple(col) + (255,), outline=outline, width=lw)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def vary(rng, base, amount=18):
    """Slight per-tile colour variation around a base RGB."""
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255)) for c in base)


def hsv_rgb(h, s, v):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def c2t(poly):
    """complex list -> (x, y) tuple list"""
    return [(z.real, z.imag) for z in poly]


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


# ==========================================
# 15. CAIRO PENTAGONAL
# ==========================================
def gen_cairo():
    rng = np.random.default_rng(15)
    d = (math.sqrt(7) - 1) / 6  # equilateral parameter
    pal = [(214, 126, 44), (188, 80, 64), (226, 178, 92), (150, 100, 130)]
    polys = []
    N = 9
    for i in range(-1, N + 1):
        for j in range(-1, N + 1):
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
            for k, p in enumerate(pents):
                polys.append((p, vary(rng, pal[k])))
    return polys, (0.5, 0.5, N - 0.5, N - 0.5)


# ==========================================
# 16. FLORET PENTAGONAL (dual snub hex)
# ==========================================
def gen_floret():
    rng = np.random.default_rng(16)
    base = [complex(0, 0), complex(1, 1 / math.sqrt(3)),
            complex(1.5, 0.5 / math.sqrt(3)), complex(1.5, -0.5 / math.sqrt(3)),
            complex(1, -1 / math.sqrt(3))]
    t1 = complex(2.5, math.sqrt(3) / 2)
    t2 = complex(2.0, -math.sqrt(3))
    flower_pal = [(213, 145, 60), (190, 88, 88), (168, 168, 78),
                  (105, 145, 185), (148, 108, 168), (88, 158, 128),
                  (205, 170, 95), (130, 120, 90)]
    polys = []
    for m in range(-6, 7):
        for n in range(-6, 7):
            centre = m * t1 + n * t2
            # one colour per flower (slight variation per petal) so the
            # 6-petal pinwheel structure reads clearly
            base_col = flower_pal[(3 * m + n) % 8]
            for k in range(6):
                rot = cmath.exp(1j * math.pi / 3 * k)
                pts = [centre + v * rot for v in base]
                polys.append((c2t(pts), vary(rng, base_col, 14)))
    R = 5.2
    return polys, (-R, -R, R, R)


# ==========================================
# 19. GOSPER ISLAND (hexflake)
# ==========================================
def _gosper_edge(a, b, depth):
    """Replace segment a->b with the Gosper island generator, recursively."""
    if depth == 0:
        return [a]
    v = b - a
    r = 1 / math.sqrt(7)
    m1 = r * cmath.exp(1j * math.radians(19.1066))
    m2 = r * cmath.exp(1j * math.radians(-40.8934))
    p1 = a + v * m1
    p2 = p1 + v * m2
    pts = []
    pts += _gosper_edge(a, p1, depth - 1)
    pts += _gosper_edge(p1, p2, depth - 1)
    pts += _gosper_edge(p2, b, depth - 1)
    return pts


def gen_gosper():
    rng = np.random.default_rng(19)
    hexv = [cmath.exp(1j * math.radians(30 + 60 * k)) for k in range(6)]
    island = []
    for k in range(6):
        island += _gosper_edge(hexv[k], hexv[(k + 1) % 6], 3)
    t1 = complex(math.sqrt(3), 0)
    t2 = complex(math.sqrt(3) / 2, 1.5)
    pal = [(70, 130, 150), (200, 150, 70), (150, 90, 110),
           (100, 150, 95), (170, 120, 170), (120, 110, 80), (90, 100, 160)]
    polys = []
    for m in range(-5, 6):
        for n in range(-5, 6):
            c = m * t1 + n * t2
            if abs(c) > 6.5:
                continue
            col = vary(rng, pal[(m - 2 * n) % 7], 10)
            polys.append((c2t([c + p for p in island]), col))
    R = 3.6
    return polys, (-R, -R, R, R)


# ==========================================
# 13. PINWHEEL (Conway-Radin)
# ==========================================
def _pin_sub(A, B, C):
    """Subdivide 1:2:sqrt5 right triangle (right angle at A, |AB|=2|AC|) into 5."""
    d = C - B
    F = B + ((A - B).real * d.real + (A - B).imag * d.imag) / abs(d) ** 2 * d
    M1 = (A + F) / 2
    M2 = (F + B) / 2
    M3 = (A + B) / 2
    return [(F, A, C), (M1, M3, A), (M2, B, M3), (F, M2, M1), (M3, M1, M2)]


def gen_pinwheel():
    S = 10.0
    tris = [(complex(0, 0), complex(2 * S, 0), complex(0, S)),
            (complex(2 * S, S), complex(0, S), complex(2 * S, 0))]
    for _ in range(4):
        nxt = []
        for t in tris:
            nxt += _pin_sub(*t)
        tris = nxt
    # sanity: every triangle must stay 1:2:sqrt5
    a, b, c = tris[0]
    legs = sorted([abs(b - a), abs(c - a), abs(c - b)])
    assert abs(legs[1] / legs[0] - 2) < 1e-6 and abs(legs[2] / legs[0] - math.sqrt(5)) < 1e-6
    # rotate the whole patch 13 deg: new orientation classes emerge only at
    # unrenderable depths, so tilt the two dominant families off-axis instead
    rng = np.random.default_rng(13)
    ctr = complex(S, S / 2)
    rot = cmath.exp(1j * math.radians(13))
    polys = []
    for (A, B, C) in tris:
        A, B, C = [(z - ctr) * rot + ctr for z in (A, B, C)]
        ang = math.degrees(cmath.phase(B - A)) % 180
        col = hsv_rgb(ang / 180, 0.52, 0.55 + 0.22 * rng.random())
        polys.append((c2t([A, B, C]), col))
    h = 3.8
    return polys, (S - h, S / 2 - h, S + h, S / 2 + h)


# ==========================================
# 12. AMMANN-BEENKER (multigrid N=4)
# ==========================================
def gen_ammann_beenker():
    rng = np.random.default_rng(12)
    N = 4
    zeta = [cmath.exp(1j * math.pi * k / N) for k in range(N)]
    gamma = [0.13, 0.27, 0.41, 0.19]
    RANGE = 10
    polys = []
    for k in range(N):
        for l in range(k + 1, N):
            for m in range(-RANGE, RANGE + 1):
                for n in range(-RANGE, RANGE + 1):
                    # intersection of line (k,m) and (l,n)
                    ak = zeta[k].conjugate()
                    al = zeta[l].conjugate()
                    det = ak.real * al.imag - ak.imag * al.real
                    if abs(det) < 1e-12:
                        continue
                    bk, bl = m + gamma[k], n + gamma[l]
                    px = (bk * al.imag - bl * ak.imag) / det
                    py = (bk * al.real - bl * ak.real) / det
                    p = complex(px, py)
                    if abs(p) > RANGE:
                        continue
                    K = [0] * N
                    for j in range(N):
                        if j == k or j == l:
                            continue
                        K[j] = math.ceil((p * zeta[j].conjugate()).real - gamma[j])
                    basev = sum(K[j] * zeta[j] for j in range(N) if j not in (k, l))
                    verts = []
                    for a, b in [(0, 0), (1, 0), (1, 1), (0, 1)]:
                        verts.append(basev + (m + a) * zeta[k] + (n + b) * zeta[l])
                    ctr = sum(verts) / 4
                    if abs(ctr) > 7.2:
                        continue
                    if (l - k) % N == 2:
                        col = vary(rng, (72, 88, 110), 10)      # squares
                    else:
                        col = vary(rng, (216, 150, 60) if (l - k) % 2 else (190, 100, 70), 12)
                    polys.append((c2t(verts), col))
    R = 4.6
    return polys, (-R, -R, R, R)


# ==========================================
# 17. POINCARE {7,3}
# ==========================================
def _geo_circle(z1, z2):
    """Circle through z1,z2 orthogonal to the unit circle. None -> straight line."""
    a1, b1, c1 = 2 * z1.real, 2 * z1.imag, abs(z1) ** 2 + 1
    a2, b2, c2 = 2 * z2.real, 2 * z2.imag, abs(z2) ** 2 + 1
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-9:
        return None
    cx = (c1 * b2 - c2 * b1) / det
    cy = (a1 * c2 - a2 * c1) / det
    c = complex(cx, cy)
    return c, math.sqrt(abs(c) ** 2 - 1)


def _reflect(z, circ):
    if circ is None:
        return z  # replaced by line handling below
    c, r = circ
    return c + r * r / (z - c).conjugate()


def _edge_arc(z1, z2, n=10):
    circ = _geo_circle(z1, z2)
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


def gen_poincare():
    """{7,3} in the BAND model - TOTAL redesign (user 2026-07-04b: the disk
    version was impractical, 'remove the circle entirely').

    The Poincare disk maps conformally onto an infinite horizontal strip by
    w = (2/pi) * log((1+z)/(1-z))   (|Im w| < 1),
    so the SAME hyperbolic {7,3} tiling runs left-right forever with no
    circular horizon anywhere. Cell size depends only on the distance from
    the strip's midline (factor ~cos(pi*y/2)); capping the window at
    |y| <= W = 0.80 bounds the smallest cells at ~1/3 of the centre-row
    cells - no singularity, no dust ring, yet the heptagons stay visibly
    hyperbolic (three meet at every vertex, edges gently bowed). The window
    needs disk tiles only up to |z| ~ 0.9, so the reflection BFS stops at a
    LARGE diameter cutoff - orders of magnitude fewer tiles than the disk
    version."""
    p, q = 7, 3
    # hyperbolic circumradius from the characteristic right triangle
    # (angles pi/p at centre, pi/q at vertex): cosh R = cot(pi/p) * cot(pi/q)
    coshR = 1.0 / (math.tan(math.pi / p) * math.tan(math.pi / q))
    r0 = math.tanh(math.acosh(coshR) / 2)
    central = [r0 * cmath.exp(1j * (math.pi / 2 + 2 * math.pi * k / p)) for k in range(p)]

    rng = np.random.default_rng(17)
    seen = set()
    result = []
    queue = deque([(central, 0j, 0)])   # (heptagon, its hyperbolic centre, depth)
    while queue and len(result) < 20000:
        poly, hc, depth = queue.popleft()
        ctr = sum(poly) / p
        key = (round(ctr.real, 4), round(ctr.imag, 4))
        if key in seen:
            continue
        seen.add(key)
        diam = max(abs(a - b) for a in poly[:3] for b in poly[3:6])
        if diam < 0.02:            # window uses |z| <= ~0.9 only: rim dust never needed
            continue
        result.append((poly, hc, depth))
        if depth >= 14:
            continue
        for k in range(p):
            z1, z2 = poly[k], poly[(k + 1) % p]
            circ = _geo_circle(z1, z2)
            if circ is None:
                u = (z2 - z1) / abs(z2 - z1)
                newp = [z1 + ((z - z1) / u).conjugate() * u for z in poly]
                newc = z1 + ((hc - z1) / u).conjugate() * u
            else:
                newp = [_reflect(z, circ) for z in poly]
                newc = _reflect(hc, circ)
            queue.append((newp, newc, depth + 1))

    ring_pal = [(220, 170, 70), (170, 90, 80), (90, 120, 160),
                (120, 160, 110), (150, 110, 160), (200, 130, 90), (100, 140, 150)]
    W = 0.80

    def band(z):
        return (2 / math.pi) * cmath.log((1 + z) / (1 - z))

    # whole heptagons are far too big for mosaic cells (33 in frame): split
    # each into 7 kites [centre, edge-mid k-1, vertex k, edge-mid k] - the
    # same khatam split as the girih decagons. The hyperbolic centre is
    # carried through the reflections; edge mids come from the SAMPLED
    # geodesic arcs, so both neighbouring cells share identical polylines
    # (exact partition). Kites inherit the heptagon's ring colour with a
    # per-kite variation -> 7-petal flowers.
    polys = []
    for poly, hc, depth in result:
        arcs = [_edge_arc(poly[k], poly[(k + 1) % p], 6) for k in range(p)]
        wc = band(hc)
        base = ring_pal[depth % 7]
        for k in range(p):
            half_prev = arcs[(k - 1) % p][3:]
            half_next = arcs[k][:4]
            kite = [wc] + [band(z) for z in half_prev + half_next]
            xs = [v.real for v in kite]
            ys = [v.imag for v in kite]
            if min(xs) > W or max(xs) < -W or min(ys) > W or max(ys) < -W:
                continue
            cl = _clip_rect([(v.real, v.imag) for v in kite], W)
            if len(cl) >= 3:
                polys.append((cl, vary(rng, base, 12)))
    return polys, (-W, -W, W, W)


# ==========================================
# 14. VODERBERG (stylised spiral of bent slivers)
# ==========================================
def gen_voderberg():
    """Rev 2026-07-04b (user): the fixed 30-wedge count made the inner slivers
    collapse toward the cap - impractical centre. Solved like sunburst/bloom:
    every ring now gets its OWN wedge count ~ 2*pi*r_mid/target, so the bent
    slivers keep a near-constant tangential size at every radius. Rev
    2026-07-04b #2 (user): the plain cap disk is gone too - the innermost
    ring starts AT r = 0, so the centre is a ring of bent slivers of the
    SAME shape as the rest, converging vertex-first at the pole (no separate
    'circle'). Ring boundaries are circles, so differing counts across rings
    only create T-junctions on the shared arcs (fine for a mosaic partition -
    same as sierpinski row boundaries)."""
    rng = np.random.default_rng(14)
    bend = 5.0                     # radial edge bow (deg)
    # rings run past the far corner (world R=0.92 -> corner ~1.30) so every
    # angle is covered out to the rectangle edge; first ring starts at the pole
    radii = [0.0, 0.14, 0.30, 0.50, 0.74, 1.02, 1.36, 1.75]
    target = 0.115                 # tangential cell size at ring mid-radius
    pal = [(205, 140, 60), (120, 130, 160), (180, 90, 70), (140, 160, 100)]
    polys = []
    base_off = 0.0
    for m in range(len(radii) - 1):
        rin, rout = radii[m], radii[m + 1]
        nw = max(8, int(round(2 * math.pi * ((rin + rout) / 2) / target)))
        step = 360.0 / nw
        twist = step / 2           # spiral shear per ring (in own step units)

        def radial(theta_deg, nseg=14):
            pts = []
            for i in range(nseg + 1):
                t = i / nseg
                r = rin + (rout - rin) * t
                th = math.radians(theta_deg + twist * t + bend * math.sin(math.pi * t))
                pts.append((r * math.cos(th), r * math.sin(th)))
            return pts

        for k in range(nw):
            th0 = k * step + base_off
            th1 = th0 + step
            e_left = radial(th0)
            e_right = radial(th1)
            arc_out = [(rout * math.cos(math.radians(th0 + twist + (th1 - th0) * i / 6)),
                        rout * math.sin(math.radians(th0 + twist + (th1 - th0) * i / 6)))
                       for i in range(1, 6)]
            arc_in = ([] if rin == 0.0 else
                      [(rin * math.cos(math.radians(th1 - (th1 - th0) * i / 6)),
                        rin * math.sin(math.radians(th1 - (th1 - th0) * i / 6)))
                       for i in range(1, 6)])
            poly = e_left + arc_out + list(reversed(e_right)) + arc_in
            col = vary(rng, pal[(k + 2 * m) % 2 + 2 * (m % 2)], 14)
            polys.append((poly, col))
        base_off += twist          # spiral shear keeps accumulating ring-to-ring
    R = 0.92
    return polys, (-R, -R, R, R)


# ==========================================
# 18. ESCHER-STYLE p1 (deformed hexagon critter)
# ==========================================
def _wavy(a, b, offsets):
    """Polyline a->b with perpendicular offsets (fractions of |ab|)."""
    v = b - a
    n = v * 1j  # left normal
    pts = []
    m = len(offsets) + 1
    for i, off in enumerate(offsets, start=1):
        t = i / m
        pts.append(a + v * t + n * off)
    return pts


def gen_escher():
    rng = np.random.default_rng(18)
    h = [cmath.exp(1j * math.radians(30 + 60 * k)) for k in range(6)]
    t01 = h[0] + h[1]
    t12 = h[1] + h[2]
    t23 = h[2] + h[3]

    # hand-tuned edge deformations (head / legs / tail)
    off0 = [0.05, 0.20, 0.31, 0.29, 0.13, -0.09, -0.05]     # round head + neck dip
    off1 = [0.13, -0.09, 0.17, -0.11, 0.11, -0.05]          # two stubby legs
    off2 = [-0.09, -0.22, -0.15, 0.09, 0.25, 0.13]          # tail swoosh
    f0 = [h[0]] + _wavy(h[0], h[1], off0)
    f1 = [h[1]] + _wavy(h[1], h[2], off1)
    f2 = [h[2]] + _wavy(h[2], h[3], off2)

    # boundary: f0, f1, f2, then their reverses translated to the opposite edges
    boundary = f0 + f1 + f2
    boundary += [z - t01 for z in list(reversed([h[0]] + _wavy(h[0], h[1], off0) + [h[1]]))][:-1]
    boundary += [z - t12 for z in list(reversed([h[1]] + _wavy(h[1], h[2], off1) + [h[2]]))][:-1]
    boundary += [z - t23 for z in list(reversed([h[2]] + _wavy(h[2], h[3], off2) + [h[3]]))][:-1]

    t_a = complex(math.sqrt(3), 0)
    t_b = complex(math.sqrt(3) / 2, 1.5)
    pal = [(205, 140, 60), (110, 130, 160), (160, 90, 80)]
    polys = []
    for m in range(-5, 6):
        for n in range(-5, 6):
            c = m * t_a + n * t_b
            if abs(c) > 6.0:
                continue
            col = vary(rng, pal[(m - n) % 3], 10)
            polys.append((c2t([c + z for z in boundary]), col))
    R = 3.3
    return polys, (-R, -R, R, R)


# ==========================================
# 20. WEAVE (interlaced photo ribbons)
# ==========================================
def gen_weave():
    """Rev 2026-07-13 (wiring): the first version faked the interlacing with
    paint order (crossing squares painted twice) and left the gaps between four
    ribbons as background. That is not a partition — in the engine overlapping
    cells mean two photos fighting for the same pixels and the gaps come out
    black. Rebuilt as the exact partition the engine renders (`_gen_weave`):

      * a ribbon is hidden precisely at its under-crossings, so its VISIBLE
        piece runs from one under-crossing to the next: a w x (2 - w) rectangle
        centred on the over-crossing it covers. Parity (i + j) % 2 picks the
        ribbon on top, so every crossing square belongs to exactly one cell.
      * the (1 - w)^2 square between four ribbons becomes its own 'knot' cell.
    """
    rng = np.random.default_rng(20)
    w = 0.74
    half = w / 2
    arm = 1.0 - half          # cell half-length along the ribbon
    N = 9
    warm = (205, 130, 60)
    cool = (90, 120, 160)
    knot = (105, 100, 110)
    polys = []
    for i in range(-1, N + 1):
        for j in range(-1, N + 1):
            if (i + j) % 2 == 1:   # vertical ribbon on top at this crossing
                polys.append(([(i - half, j - arm), (i + half, j - arm),
                               (i + half, j + arm), (i - half, j + arm)],
                              vary(rng, cool, 26)))
            else:                  # horizontal ribbon on top
                polys.append(([(i - arm, j - half), (i + arm, j - half),
                               (i + arm, j + half), (i - arm, j + half)],
                              vary(rng, warm, 26)))
            polys.append(([(i + half, j + half), (i + 1 - half, j + half),
                           (i + 1 - half, j + 1 - half), (i + half, j + 1 - half)],
                          vary(rng, knot, 20)))
    return polys, (-0.2, -0.2, N - 0.8, N - 0.8)


# ==========================================
# 11. GIRIH (greedy edge-gluing patch)
# ==========================================
def _turtle(angles_int):
    """Unit-edge polygon from interior angles (degrees), ccw."""
    pts = [complex(0, 0)]
    heading = 0.0
    for ang in angles_int[:-1]:
        pts.append(pts[-1] + cmath.exp(1j * math.radians(heading)))
        heading += 180 - ang
    return pts


def _girih_attempt(seed):
    rng = np.random.default_rng(seed)
    tiles = {
        "decagon": _turtle([144] * 10),
        "pentagon": _turtle([108] * 5),
        "hexagon": _turtle([72, 144, 144, 72, 144, 144]),
        "bowtie": _turtle([72, 72, 216, 72, 72, 216]),
        "rhomb": _turtle([72, 108, 72, 108]),
    }
    cols = {
        "decagon": (206, 162, 78), "pentagon": (96, 130, 165),
        "hexagon": (168, 96, 82), "bowtie": (110, 150, 110),
        "rhomb": (150, 110, 150),
    }
    # occupancy raster
    RES = 26  # px per unit
    RAD = 11.0
    W = int(2 * RAD * RES)
    occ = Image.new("L", (W, W), 0)
    occ_draw = ImageDraw.Draw(occ)
    occ_np = np.zeros((W, W), dtype=bool)

    def to_px(z):
        return ((z.real + RAD) * RES, (z.imag + RAD) * RES)

    def shrunk(poly, f=0.90):
        c = sum(poly) / len(poly)
        return [c + (z - c) * f for z in poly]

    def fits(poly):
        pts = [to_px(z) for z in shrunk(poly)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, y0 = int(min(xs)) - 1, int(min(ys)) - 1
        x1, y1 = int(max(xs)) + 2, int(max(ys)) + 2
        if x0 < 0 or y0 < 0 or x1 > W or y1 > W:
            return False
        test = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(test).polygon([(px - x0, py - y0) for px, py in pts], fill=255)
        return not np.any(np.logical_and(occ_np[y0:y1, x0:x1], np.array(test)))

    def commit(poly):
        occ_draw.polygon([to_px(z) for z in shrunk(poly, 0.99)], fill=255)
        occ_np[:] = np.array(occ, dtype=bool)

    placed = []
    open_edges = deque()

    def place(name, poly):
        placed.append((poly, name))
        commit(poly)
        n = len(poly)
        for i in range(n):
            open_edges.append((poly[(i + 1) % n], poly[i]))  # reversed -> outward

    d0 = tiles["decagon"]
    ctr0 = sum(d0) / 10
    place("decagon", [z - ctr0 for z in d0])

    decagon_ctrs = [complex(0, 0)]
    steps = 0
    while open_edges and steps < 15000:
        steps += 1
        B, A = open_edges.popleft()
        mid = (A + B) / 2
        if abs(mid) > RAD - 2.0:
            continue
        # hexagons pack around decagons almost perfectly, so they lead most of
        # the time; occasionally let bowtie/pentagon go first for variety.
        # Decagons get first shot away from existing ones.
        r = rng.random()
        if r < 0.60:
            order = ["hexagon", "bowtie", "pentagon", "rhomb"]
        elif r < 0.82:
            order = ["bowtie", "hexagon", "pentagon", "rhomb"]
        else:
            order = ["pentagon", "hexagon", "bowtie", "rhomb"]
        if all(abs(c - mid) > 3.2 for c in decagon_ctrs):
            order = ["decagon"] + order
        done = False
        for name in order:
            tpl = tiles[name]
            n = len(tpl)
            for j in range(n):
                pj, pj1 = tpl[j], tpl[(j + 1) % n]
                rot = (A - B) / (pj1 - pj)
                cand = [(z - pj) * rot + B for z in tpl]
                if fits(cand):
                    place(name, cand)
                    if name == "decagon":
                        decagon_ctrs.append(sum(cand) / len(cand))
                    done = True
                    break
            if done:
                break

    # coverage: filled fraction of the central window (for best-of-seeds pick)
    box = int((RAD - 6.2) * RES), int((RAD + 6.2) * RES)
    coverage = occ_np[box[0]:box[1], box[0]:box[1]].mean()
    # Rev 2026-07-04b (user): a whole decagon is several times larger than any
    # other cell (impractical, like the pre-fix radial centres). Partition
    # every decagon into 10 congruent kites [centre, mid(k-1), vertex k,
    # mid(k)] - the classic khatam split; each kite is comparable to a
    # pentagon/rhomb cell. Rev 2026-07-04b #2 (user): the kites STAY, but the
    # 2-tone wheel colouring is dropped - one decagon-gold base with the same
    # per-tile vary as every other cell, so the rosettes read as ordinary
    # tiles of the tessellation (coherent with the rest).
    polys = []
    for p_, nm in placed:
        if nm == "decagon":
            c = sum(p_) / len(p_)
            n = len(p_)
            mids = [(p_[i] + p_[(i + 1) % n]) / 2 for i in range(n)]
            for i in range(n):
                kite = [c, mids[(i - 1) % n], p_[i], mids[i]]
                polys.append((c2t(kite), vary(rng, cols["decagon"], 8)))
        else:
            polys.append((c2t(p_), vary(rng, cols[nm], 8)))
    # Hole fill (2026-07-04b, user): greedy growth tops out at ~94-99% - the
    # leftover slivers read as BLACK HOLES in the frame. Label the empty
    # raster components (the outside region touches the border and is
    # skipped), emit each interior hole's convex hull as an extra cell,
    # slightly inflated and painted LAST so any overlap with neighbours is
    # sub-pixel and invisible under the outlines.
    lab, nlab = _nd_label(~occ_np)
    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    for l in range(1, nlab + 1):
        if l in border:
            continue
        ys, xs = np.nonzero(lab == l)
        if len(xs) < 8:
            continue
        pts = np.column_stack([xs, ys]).astype(float)
        try:
            hull = ConvexHull(pts)
        except QhullError:
            continue
        hp = pts[hull.vertices]
        c = hp.mean(axis=0)
        hp = c + (hp - c) * 1.10
        poly = [(x / RES - RAD, y / RES - RAD) for x, y in hp]
        polys.append((poly, vary(rng, (150, 110, 150), 10)))
    return polys, coverage


def gen_girih():
    """Greedy girih growth is seed-sensitive; keep the best-covering attempt.
    Wider seed sweep + stricter early-out since 2026-07-04b: uncovered slivers
    read as black holes in the frame (user report)."""
    best, best_cov = None, -1.0
    for seed in range(11, 47):
        polys, cov = _girih_attempt(seed)
        print(f"      girih seed {seed}: coverage {cov:.3f}, {len(polys)} tiles")
        if cov > best_cov:
            best, best_cov = polys, cov
        if cov > 0.997:
            break
    R = 6.0
    return best, (-R, -R, R, R)


# ==========================================
# MONTAGE
# ==========================================
SHAPES = [
    ("girih", gen_girih, "11. GIRIH (perskie/Alhambra)", "dekagony=rozety 10 latawcow + bowtie/pentagon/hex"),
    ("ammann_beenker", gen_ammann_beenker, "12. AMMANN-BEENKER", "aperiodyczny 8-krotny: kwadraty + romby 45 st."),
    ("pinwheel", gen_pinwheel, "13. PINWHEEL (Conway-Radin)", "trojkaty 1:2:sqrt5, nieskonczenie wiele orientacji"),
    ("voderberg", gen_voderberg, "14. VODERBERG (stylizowany)", "spirala wygietych klinow, srodek=kliny w biegunie"),
    ("cairo", gen_cairo, "15. CAIRO (bruk kairski)", "pieciokaty koszykowe, 4 orientacje"),
    ("floret", gen_floret, "16. FLORET (dual snub hex)", "kwiaty: 6 pieciokatnych platkow, chiralny"),
    ("poincare", gen_poincare, "17. POINCARE {7,3} PAS", "model pasmowy - bez okregu, heptagony 3-w-wierzcholku"),
    ("escher_lizard", gen_escher, "18. ESCHER-STYLE (p1)", "deformacja heksagonu, organiczne stworki"),
    ("gosper", gen_gosper, "19. GOSPER ISLAND", "fraktalne wyspy (hexflake), granica Gospera"),
    ("weave", gen_weave, "20. WEAVE (tkanina)", "wstegi zdjec przeplatane nad/pod"),
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

    # montage 5 x 2, matching the Opus proposals style
    PW, TH = 475, 60
    mont = Image.new("RGB", (PW * 5, (PW + TH) * 2), (10, 10, 12))
    draw = ImageDraw.Draw(mont)
    try:
        f_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 17)
        f_reg = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    except OSError:
        f_bold = f_reg = ImageFont.load_default()

    for idx, (name, fn, t1, t2) in enumerate(SHAPES):
        r, c = divmod(idx, 5)
        x0, y0 = c * PW, r * (PW + TH)
        img = panels[name].resize((PW - 24, PW - 24), Image.Resampling.LANCZOS)
        for txt, font, dy in [(t1, f_bold, 10), (t2, f_reg, 34)]:
            tw = draw.textlength(txt, font=font)
            draw.text((x0 + (PW - tw) / 2, y0 + dy), txt, fill=(235, 235, 235), font=font)
        mont.paste(img.convert("RGB"), (x0 + 12, y0 + TH))

    out = OUT_DIR / "proposals_fable_10_shapes.png"
    mont.save(out)
    print(f"[gen] montage -> {out}")


if __name__ == "__main__":
    main()
