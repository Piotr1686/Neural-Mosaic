"""Proposal schematics: 5 jigsaw-puzzle shape candidates (2026-07-18).

PROPOZYCJE, nie wdrozenia. PNG trafiaja do assets/proposals/, celowo NIE do
assets/shape_schemes/ - audyt "rejestr vs PNG" liczy shape_schemes i kazdy
niewdrozony PNG bylby tam sierota. Po akceptacji ksztalt dostaje pelny cykl:
generator w silniku, goldeny x2, pokrycie x5, schemat regenerowany Z SILNIKA.

Wspolna konstrukcja (silnikowo-legalna, prawdziwa partycja):
  * Wypustka/wciecie (tab) jest wlasnoscia KRAWEDZI, nie komorki: polilinia
    tabu liczona RAZ per krawedz (klucz = posortowane, zaokraglone koncowki)
    i uzywana przez OBIE komorki (druga w odwrotnym kierunku). Zero
    T-junctions i zero dziur/nakladek z konstrukcji - tab dodaje jednej
    komorce dokladnie to, co zabiera sasiadowi (srednie pole bez zmian).
  * Kierunek + jitter tabu z crc32 klucza krawedzi (BEZ RNG) - stabilne
    miedzy procesami i rozdzielczosciami (lekcja girih/truchet: ten sam
    wzor, tylko wiecej).
  * Tab skaluje sie z dlugoscia krawedzi. W silniku luki tabow MUSZA byc
    probkowane przez _arc_pitch (promien tabu ~ base_s, staly w px przy
    kazdej rozdzielczosci - pulapka scales/truchet_hex).
  * Geometria tabu: 3 luki kolowe (szyjka-lewa, glowka >180 stopni z
    podcieciem, szyjka-prawa) o wspolnych punktach z przeciec okregow.

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_puzzle_proposals
"""
import colorsys
import logging
import math
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import Voronoi

from src.engine_smart import _gen_penrose

log = logging.getLogger(__name__)

SIZE = 720
SS = 2
BG = (20, 20, 24)
OUTLINE = (16, 16, 20)


# --------------------------------------------------------------------------
# tab geometry (unit edge (0,0)->(1,0), bump towards +y, then sign-flipped)
# --------------------------------------------------------------------------
def _crc_units(key):
    h = zlib.crc32(repr(key).encode("ascii"))
    sign = (h & 1) * 2 - 1
    u1 = ((h >> 1) & 255) / 255.0
    u2 = ((h >> 9) & 255) / 255.0
    return sign, u1, u2


def _circle_isect(c1, r1, c2, r2):
    (x1, y1), (x2, y2) = c1, c2
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(r1 * r1 - a * a, 0.0))
    mx, my = x1 + a * dx / d, y1 + a * dy / d
    ux, uy = -dy / d, dx / d
    return (mx + h * ux, my + h * uy), (mx - h * ux, my - h * uy)


def _arc_cw(c, rad, a0, a1, step=math.radians(9)):
    """Sample the clockwise arc (decreasing angle) from a0 to a1."""
    while a1 >= a0:
        a1 -= 2 * math.pi
    n = max(2, int((a0 - a1) / step))
    return [(c[0] + rad * math.cos(a0 + (a1 - a0) * k / n),
             c[1] + rad * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


def _bez(p0, p1, p2, p3, n=12):
    out = []
    for k in range(n + 1):
        t = k / n
        s = 1 - t
        out.append((s**3 * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t**3 * p3[0],
                    s**3 * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t**3 * p3[1]))
    return out


def _unit_tab_diecut(u1, u2):
    """Die-cut profile matched to the user's reference photos (2026-07-19):
    big round head (~26% of the edge), narrow neck, S-curved shoulders that
    dip slightly into the neighbour before flaring into the head - the
    classic cardboard-puzzle silhouette. Head = one circular arc entered at
    225 deg and left at -45 deg (clockwise over the top), so the undercut is
    strong; shoulders are cubics whose end handles are aligned with the
    circle tangents (smooth join, no visible kink)."""
    cx = 0.5 + (u1 - 0.5) * 0.10
    sc = 0.90 + 0.20 * u2
    R, H = 0.13 * sc, 0.16 * sc
    C = (cx, H)
    thL, thR = math.radians(225), math.radians(-45)
    PL = (C[0] + R * math.cos(thL), C[1] + R * math.sin(thL))
    PR = (C[0] + R * math.cos(thR), C[1] + R * math.sin(thR))
    # clockwise travel tangent at angle th is (sin th, -cos th)
    tL = (math.sin(thL), -math.cos(thL))
    tR = (math.sin(thR), -math.cos(thR))
    # Shoulders leave the corners EXACTLY along the baseline and all their
    # Bezier control points keep y >= 0 (convex-hull property: the curve can
    # never cross the baseline). A first version pulled the shoulders into a
    # negative dip like a real die-cut, but the dip started at the corner and
    # neighbouring edge polylines crossed there: 295 hole px in the coverage
    # raster (the pool gate demands 0). The flared neck + 270-degree head
    # carry the reference look on their own.
    shoulder_l = _bez((0.10, 0.0), (0.28, 0.0),
                      (PL[0] - 0.05 * tL[0], PL[1] - 0.05 * tL[1]), PL)
    shoulder_r = _bez(PR, (PR[0] + 0.05 * tR[0], PR[1] + 0.05 * tR[1]),
                      (0.72, 0.0), (0.90, 0.0))
    pts = [(0.0, 0.0)] + shoulder_l
    pts += _arc_cw(C, R, thL, thR)
    pts += shoulder_r + [(1.0, 0.0)]
    return pts


def _unit_tab(u1, u2):
    """Full edge polyline (0,0)..(1,0) with a jigsaw tab bumping to +y."""
    cx = 0.5 + (u1 - 0.5) * 0.10          # tab centre wanders a little
    sc = 0.90 + 0.20 * u2                 # tab size varies a little
    R, H = 0.14 * sc, 0.15 * sc           # head circle
    r, D, hy = 0.06 * sc, 0.13 * sc, 0.02 * sc   # neck circles
    C = (cx, H)
    NL, NR = (cx - D, hy), (cx + D, hy)
    jl = max(_circle_isect(C, R, NL, r), key=lambda p: p[1])
    jr = max(_circle_isect(C, R, NR, r), key=lambda p: p[1])
    bx = math.sqrt(r * r - hy * hy)
    pl, pr = (NL[0] - bx, 0.0), (NR[0] + bx, 0.0)
    ang = lambda c, p: math.atan2(p[1] - c[1], p[0] - c[0])
    pts = [(0.0, 0.0), pl]
    pts += _arc_cw(NL, r, ang(NL, pl), ang(NL, jl))
    pts += _arc_cw(C, R, ang(C, jl), ang(C, jr))
    pts += _arc_cw(NR, r, ang(NR, jr), ang(NR, pr))
    pts += [pr, (1.0, 0.0)]
    return pts


# --------------------------------------------------------------------------
# per-edge assembly: one polyline per edge, shared by both cells
# --------------------------------------------------------------------------
def _rkey(p):
    return (round(p[0], 2), round(p[1], 2))


def _edge_key(a, b):
    ka, kb = _rkey(a), _rkey(b)
    return (ka, kb) if ka <= kb else (kb, ka)


def _on_frame(a, b, size, eps=0.6):
    if abs(a[0]) < eps and abs(b[0]) < eps:
        return True
    if abs(a[0] - size) < eps and abs(b[0] - size) < eps:
        return True
    if abs(a[1]) < eps and abs(b[1]) < eps:
        return True
    if abs(a[1] - size) < eps and abs(b[1] - size) < eps:
        return True
    return False


def _tab_edge(A, B, key, profile):
    sign, u1, u2 = _crc_units(key)
    L = math.hypot(B[0] - A[0], B[1] - A[1])
    ux, uy = (B[0] - A[0]) / L, (B[1] - A[1]) / L
    nx, ny = -uy, ux
    return [(A[0] + t * L * ux + sign * y * L * nx,
             A[1] + t * L * uy + sign * y * L * ny)
            for t, y in profile(u1, u2)]


def _assemble(polys, size, lmin, frame_rule=True, profile=None):
    """Turn plain polygons into puzzle cells with per-edge shared tabs."""
    plines = {}
    for poly in polys:
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            k = _edge_key(a, b)
            if k in plines:
                continue
            A, B = (a, b) if _rkey(a) == k[0] else (b, a)
            L = math.hypot(B[0] - A[0], B[1] - A[1])
            if L < lmin or (frame_rule and _on_frame(A, B, size)):
                plines[k] = [A, B]
            else:
                plines[k] = _tab_edge(A, B, k, profile or _unit_tab)
    cells = []
    for poly in polys:
        out = []
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            k = _edge_key(a, b)
            pts = plines[k]
            out += pts[:-1] if _rkey(a) == k[0] else pts[::-1][:-1]
        cells.append(out)
    return cells


# --------------------------------------------------------------------------
# base tessellations for the five panels
# --------------------------------------------------------------------------
def _grid_polys(n=6):
    s = SIZE / n
    return [[(i * s, j * s), ((i + 1) * s, j * s),
             ((i + 1) * s, (j + 1) * s), (i * s, (j + 1) * s)]
            for i in range(n) for j in range(n)]


def _wavy_polys(n=6):
    s = SIZE / n
    amp = 0.22 * s

    def v(i, j):
        dx = 0.0 if i in (0, n) else amp * math.sin(0.85 * j + 0.40 * i)
        dy = 0.0 if j in (0, n) else amp * math.sin(0.85 * i + 1.70 + 0.30 * j)
        return (i * s + dx, j * s + dy)

    V = {(i, j): v(i, j) for i in range(n + 1) for j in range(n + 1)}
    return [[V[(i, j)], V[(i + 1, j)], V[(i + 1, j + 1)], V[(i, j + 1)]]
            for i in range(n) for j in range(n)]


def _hex_polys(rr=66.0):
    polys = []
    w, h = 1.5 * rr, math.sqrt(3.0) * rr
    for col in range(-1, int(SIZE / w) + 2):
        for row in range(-1, int(SIZE / h) + 2):
            cxp = col * w
            cyp = row * h + (h / 2 if col % 2 else 0.0)
            polys.append([(cxp + rr * math.cos(math.radians(60 * k)),
                           cyp + rr * math.sin(math.radians(60 * k)))
                          for k in range(6)])
    return polys


def _organic_polys(n_seeds=110, seed=7):
    rng = np.random.default_rng(seed)
    pts = rng.uniform(-0.30 * SIZE, 1.30 * SIZE, size=(n_seeds, 2))
    vor = Voronoi(pts)
    polys = []
    for reg_i in vor.point_region:
        reg = vor.regions[reg_i]
        if not reg or -1 in reg:
            continue
        poly = [tuple(vor.vertices[v]) for v in reg]
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        if max(xs) < 0 or min(xs) > SIZE or max(ys) < 0 or min(ys) > SIZE:
            continue
        polys.append(poly)
    return polys


def _penrose_polys(base_s=85):
    return [[tuple(p) for p in poly]
            for poly in _gen_penrose(None, SIZE, SIZE, base_s)]


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------
def _draw_panel(cells, h0, h1):
    img = Image.new("RGB", (SIZE * SS, SIZE * SS), BG)
    dr = ImageDraw.Draw(img)
    for idx, poly in enumerate(cells):
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        t = ((cx / SIZE) * 0.6 + (cy / SIZE) * 0.4) % 1.0
        hue = h0 + (h1 - h0) * t
        val = 0.55 + 0.35 * ((idx * 7) % 5) / 4.0
        r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.55, val)
        dr.polygon([(x * SS, y * SS) for x, y in poly],
                   fill=(int(r * 255), int(g * 255), int(b * 255)),
                   outline=OUTLINE)
    return img.resize((SIZE, SIZE), Image.BOX)


def _montage(panels, path, cols=2, cell=500, pad=14, label_h=30):
    rows = (len(panels) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + label_h) + (rows + 1) * pad
    m = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(m)
    font = ImageFont.load_default()
    for i, (name, img) in enumerate(panels):
        c, r = i % cols, i // cols
        x = pad + c * (cell + pad)
        y = pad + r * (cell + label_h + pad)
        m.paste(img.resize((cell, cell), Image.LANCZOS), (x, y))
        dr.text((x + 6, y + cell + 8), name, fill=(225, 225, 225), font=font)
    m.save(path)


PANELS = [
    # (name, builder, lmin, frame_rule, hues, profile)
    ("puzzle_classic", _grid_polys, 50, True, (0.03, 0.10), None),
    ("puzzle_ribbon", _wavy_polys, 50, True, (0.55, 0.62), None),
    ("puzzle_hex", _hex_polys, 50, False, (0.30, 0.38), None),
    ("puzzle_organic", _organic_polys, 42, False, (0.08, 0.16), None),
    ("puzzle_penrose", _penrose_polys, 30, False, (0.75, 0.83), None),
    # 2026-07-19: die-cut profile matched to the user's reference photos;
    # shown on the classic grid, but the profile drops into ribbon/hex too
    # (the tab is a per-edge function - the lattice does not care).
    ("puzzle_diecut", _grid_polys, 50, True, (0.98, 1.06), _unit_tab_diecut),
]


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_dir = Path(__file__).resolve().parents[2] / "assets" / "proposals"
    out_dir.mkdir(parents=True, exist_ok=True)
    panels = []
    for name, builder, lmin, frame_rule, (h0, h1), profile in PANELS:
        polys = [[tuple(p) for p in poly] for poly in builder()]
        cells = _assemble(polys, SIZE, lmin, frame_rule, profile)
        img = _draw_panel(cells, h0, h1)
        img.save(out_dir / f"{name}.png")
        panels.append((name, img))
        log.info("Saved: %s  (%d cells)", out_dir / f"{name}.png", len(cells))
    _montage(panels, out_dir / "montage_puzzle.png")
    log.info("Saved: %s", out_dir / "montage_puzzle.png")


if __name__ == "__main__":
    main()
