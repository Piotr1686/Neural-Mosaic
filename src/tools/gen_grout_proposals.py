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
is therefore rendered in three width presets (thin / medium / thick); in the
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

from src.grout import PRESETS as _PRESET_WIDTHS
from src.grout import classify_edges, draw_grout, stable_seed, sub7

OUT_DIR = Path("output/grout_proposals")
SIZE = 720
SS = 2                       # supersample factor for crisp grout lines
BG = (16, 16, 20)
GROUT = (0, 0, 0)
# Width presets per level at supersampled scale (final px = half of these).
# Canonical widths + ratios live in src.grout.PRESETS; kept as (name, dict)
# pairs here for the montage's row-per-preset ordering.
PRESETS = [(name, _PRESET_WIDTHS[name]) for name in ("thin", "medium", "thick")]


def vary(rng, base, amount=14):
    return tuple(int(np.clip(c + rng.integers(-amount, amount + 1), 0, 255))
                 for c in base)


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
# (grouping + edge classification + drawing all live in src.grout)
# ---------------------------------------------------------------------------
def render_panel(cells, base_col, seed, level_w):
    rng = np.random.default_rng(seed)
    dim = SIZE * SS
    img = Image.new("RGB", (dim, dim), BG)
    draw = ImageDraw.Draw(img)

    for poly, _, _ in cells:
        draw.polygon(poly, fill=vary(rng, base_col))

    draw_grout(img, classify_edges(cells), level_w, color=GROUT)
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
            img = render_panel(cells, col, seed=stable_seed(name),
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
