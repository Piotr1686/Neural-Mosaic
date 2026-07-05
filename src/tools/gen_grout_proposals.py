"""Generate PROPOSAL previews for hierarchical (multi-level) grout lines.

User request 2026-07-05: the "black borders" render option could group tiles
with progressively thicker grout lines. Example for kites: level 1 outlines
every single kite, level 2 outlines the flower of 6 kites meeting at a shared
apex, level 3 outlines a cluster of 7 such flowers. Analogous groupings for
the other shapes.

These are VISUAL PROPOSALS for the user's verdict, NOT engine code. After the
verdict the same group-id logic moves into the engine (border pass) and the
scheme swatches get border variants for the GUI preview.

Groupings visualised here (level 1 = every tile, always):
  square    L2 = 3x3 block,            L3 = 9x9 block (3x rule)
  hexagon   L2 = flower of 7 hexes,    L3 = 7 flowers (Gosper-style sub-7)
  triangle  L2 = hexagon of 6 tris,    L3 = 7 such hexagons (sub-7)
  kites     L2 = 6 kites of one hex,   L3 = 7 hex-flowers (sub-7)

The sub-7 grouping is one shared helper: centres of "flowers" form the norm-7
sublattice of the axial hex lattice spanned by A=(2,1), B=(-1,3); membership
of a hex in a flower is exact (centre + 6 unit neighbours). The sublattice's
own coordinates are again an axial hex lattice, so level 3 is literally the
same function applied to level-2 coordinates.

Edge classification: every cell edge is keyed by its rounded endpoints; an
edge drawn at the width of the HIGHEST level whose group ids differ across it
(frame-boundary edges use their cell's highest level).

User verdict 2026-07-05: grout thickness must be USER-SELECTABLE. Each shape
is therefore rendered in three width presets (cienki / sredni / gruby); in the
engine implementation the preset becomes a GUI/CLI parameter (one "Grout
width" control scaling all levels, level ratios kept from the chosen preset).

Pure PIL + numpy, deterministic (seeded RNG only). ASCII-only prints (CP1250).

Outputs:
  output/grout_proposals/<shape>_grout_<preset>.png  (720x720 panels)
  output/grout_proposals/grout_proposals.png         (montage: shapes x presets)

Run:
  C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m src.tools.gen_grout_proposals
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("output/grout_proposals")
SIZE = 720
SS = 2                       # supersample factor for crisp grout lines
BG = (16, 16, 20)
GROUT = (0, 0, 0)
# Width presets per level at supersampled scale (final px = half of these).
PRESETS = [
    ("cienki", {1: 2, 2: 5, 3: 10}),
    ("sredni", {1: 3, 2: 8, 3: 16}),
    ("gruby",  {1: 5, 2: 12, 3: 24}),
]


def vary(rng, base, amount=14):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255))
                 for c in base)


# ---------------------------------------------------------------------------
# sub-7 flower grouping on the axial hex lattice
# ---------------------------------------------------------------------------
_A = (2, 1)
_B = (-1, 3)
_UNIT7 = {(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, -1), (-1, 1)}


def sub7(q, r):
    """Map axial hex (q, r) to the lattice coords (i, j) of its 7-flower.

    Flower centres are i*A + j*B; every hex is either a centre or one of its
    six unit neighbours, so membership is exact (no metric rounding needed).
    """
    # inverse of M = [[2,-1],[1,3]] (det 7): y = (3q + r, -q + 2r) / 7
    yi = (3 * q + r) / 7.0
    yj = (-q + 2 * r) / 7.0
    for di in (0, -1, 1):
        for dj in (0, -1, 1):
            i = round(yi) + di
            j = round(yj) + dj
            cq = i * _A[0] + j * _B[0]
            cr = i * _A[1] + j * _B[1]
            if (q - cq, r - cr) in _UNIT7:
                return (i, j)
    raise AssertionError(f"sub7 failed for ({q},{r})")


# ---------------------------------------------------------------------------
# cell builders: return list of (poly_px, group2_id, group3_id)
# ---------------------------------------------------------------------------
def cells_square():
    n = 27                     # 27x27 tiles -> 9x9 blocks of L2, 3x3 of L3
    t = SIZE * SS / n
    cells = []
    for r in range(n):
        for c in range(n):
            x, y = c * t, r * t
            poly = [(x, y), (x + t, y), (x + t, y + t), (x, y + t)]
            cells.append((poly, (c // 3, r // 3), (c // 9, r // 9)))
    return cells


def _hex_centre(q, r, s):
    return (1.5 * s * q, math.sqrt(3) * s * (r + q / 2.0))


def _hex_poly(cx, cy, s):
    return [(cx + s * math.cos(math.radians(60 * k)),
             cy + s * math.sin(math.radians(60 * k))) for k in range(6)]


def _hex_range(s, w, h):
    """Axial (q, r) whose flat-top hexes can touch the [0,w]x[0,h] canvas."""
    out = []
    range_q = int(w / (1.5 * s)) + 3
    for q in range(-2, range_q):
        r_lo = int(-q / 2.0 - 2)
        r_hi = int(h / (math.sqrt(3) * s) - q / 2.0 + 2)
        for r in range(r_lo, r_hi + 1):
            out.append((q, r))
    return out


def cells_hexagon():
    s = SIZE * SS / 26.0
    cells = []
    for q, r in _hex_range(s, SIZE * SS, SIZE * SS):
        cx, cy = _hex_centre(q, r, s)
        g2 = sub7(q, r)
        g3 = sub7(*g2)
        cells.append((_hex_poly(cx, cy, s), g2, g3))
    return cells


def cells_kites():
    s = SIZE * SS / 16.0
    r3 = math.sqrt(3)
    cells = []
    for q, r in _hex_range(s, SIZE * SS, SIZE * SS):
        cx, cy = _hex_centre(q, r, s)
        g3 = sub7(q, r)
        for k in range(6):
            P = (cx + s * math.cos(math.radians(60 * k)),
                 cy + s * math.sin(math.radians(60 * k)))
            M0 = (cx + s * r3 / 2 * math.cos(math.radians(60 * (k - 1) + 30)),
                  cy + s * r3 / 2 * math.sin(math.radians(60 * (k - 1) + 30)))
            M1 = (cx + s * r3 / 2 * math.cos(math.radians(60 * k + 30)),
                  cy + s * r3 / 2 * math.sin(math.radians(60 * k + 30)))
            poly = [(cx, cy), M0, P, M1]
            cells.append((poly, (q, r), g3))       # L2 = parent hexagon
    return cells


def cells_triangle():
    w = SIZE * SS / 10.0       # triangle side (engine: tile_w = base_s)
    h = w * math.sqrt(3) / 2
    cols = int(SIZE * SS / (w / 2)) + 4
    rows = int(SIZE * SS / h) + 2
    # vertex (a, b) sits at (a*w/2, b*h); triangle corners all have a+b odd.
    # a mod 3 3-colours the corners; the class-0 corner "owns" the triangle,
    # collecting the 6 triangles around it into a hexagon flower (L2).
    hex_centres = {}

    def owner(corners):
        for (a, b) in corners:
            if a % 3 == 0:
                return (a, b)
        raise AssertionError("no class-0 corner")

    cells_raw = []
    for r in range(-1, rows):
        for c in range(-2, cols):
            up = (c + r) % 2 == 0
            if up:
                corners = [(c, r + 1), (c + 2, r + 1), (c + 1, r)]
            else:
                corners = [(c, r), (c + 2, r), (c + 1, r + 1)]
            poly = [(a * w / 2, b * h) for (a, b) in corners]
            cells_raw.append((poly, owner(corners)))
            hex_centres[owner(corners)] = True

    # L3: hexagon owners (a=3p; b parity fixed by p) form an odd-q offset hex
    # lattice in (p, j); convert offset->axial and reuse sub7.
    def hex_axial(a, b):
        p = a // 3
        j = (b - ((1 + p) % 2)) // 2
        # odd-q offset -> axial
        return (p, j - (p - (p & 1)) // 2)

    cells = []
    for poly, own in cells_raw:
        g2 = own
        g3 = sub7(*hex_axial(*own))
        cells.append((poly, g2, g3))
    return cells


# ---------------------------------------------------------------------------
# rendering: fill cells, then draw edges at the level where group ids change
# ---------------------------------------------------------------------------
def _vkey(p):
    return (round(p[0] * 4), round(p[1] * 4))


def render_panel(cells, base_col, seed, level_w):
    rng = np.random.default_rng(seed)
    dim = SIZE * SS
    img = Image.new("RGB", (dim, dim), BG)
    draw = ImageDraw.Draw(img)

    for poly, _, _ in cells:
        draw.polygon(poly, fill=vary(rng, base_col))

    # edge -> list of adjacent cell indices
    edges = {}
    for idx, (poly, _, _) in enumerate(cells):
        for a, b in zip(poly, poly[1:] + poly[:1]):
            key = tuple(sorted((_vkey(a), _vkey(b))))
            edges.setdefault(key, []).append((idx, a, b))

    by_level = {1: [], 2: [], 3: []}
    for key, adj in edges.items():
        idx0, a, b = adj[0]
        if len(adj) == 1:
            level = 3                    # frame boundary: close the top group
        else:
            _, g2a, g3a = cells[idx0]
            _, g2b, g3b = cells[adj[1][0]]
            level = 1
            if g2a != g2b:
                level = 2
            if g3a != g3b:
                level = 3
        by_level[level].append((a, b))

    for level in (1, 2, 3):
        wd = level_w[level]
        for a, b in by_level[level]:
            draw.line([a, b], fill=GROUT, width=wd)
            # round joints so thick grout lines meet without notches
            if level > 1:
                rr = wd / 2 - 0.5
                for p in (a, b):
                    draw.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr],
                                 fill=GROUT)

    return img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


PANELS = [
    ("square", cells_square, (168, 138, 100),
     "L1 kafel | L2 blok 3x3 | L3 blok 9x9"),
    ("hexagon", cells_hexagon, (110, 140, 168),
     "L1 hex | L2 kwiat 7 hexow | L3 7 kwiatow"),
    ("triangle", cells_triangle, (128, 160, 112),
     "L1 trojkat | L2 hex z 6 trojkatow | L3 7 hexow"),
    ("kites", cells_kites, (176, 122, 122),
     "L1 latawiec | L2 kwiat 6 latawcow | L3 7 kwiatow"),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panels = {}
    for name, fn, col, desc in PANELS:
        print(f"[grout] {name} ...")
        cells = fn()
        for preset, level_w in PRESETS:
            img = render_panel(cells, col, seed=hash(name) % 2**31,
                               level_w=level_w)
            img.save(OUT_DIR / f"{name}_grout_{preset}.png")
            panels[(name, preset)] = img
        print(f"        {len(cells)} cells x {len(PRESETS)} presets")

    # montage: one row per shape, one column per width preset
    PW, TH = 475, 56
    cols_n, rows_n = len(PRESETS), len(PANELS)
    mont = Image.new("RGB", (PW * cols_n, (PW + TH) * rows_n), (10, 10, 12))
    draw = ImageDraw.Draw(mont)
    try:
        f1 = ImageFont.truetype("arial.ttf", 20)
        f2 = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    for row, (name, _, _, desc) in enumerate(PANELS):
        for col_i, (preset, _) in enumerate(PRESETS):
            gx, gy = col_i * PW, row * (PW + TH)
            mont.paste(panels[(name, preset)].resize(
                (PW, PW), Image.Resampling.LANCZOS), (gx, gy))
            draw.text((gx + 12, gy + PW + 4),
                      f"{name.upper()} - {preset}",
                      fill=(235, 235, 235), font=f1)
            if col_i == 0:
                draw.text((gx + 12, gy + PW + 30), desc,
                          fill=(160, 160, 160), font=f2)
    mont.save(OUT_DIR / "grout_proposals.png")
    print(f"[grout] montage -> {OUT_DIR / 'grout_proposals.png'}")


if __name__ == "__main__":
    main()
