"""
src/grout.py
------------
Hierarchical grout (multi-level tile borders) — engine-agnostic geometry.

Productionised home of the group-id + edge-classification logic first
prototyped in ``src/tools/gen_grout_proposals.py``. User verdict 2026-07-05:
grout thickness must be USER-SELECTABLE, so widths are expressed as presets
(thin / medium / thick) that the caller scales to its own tile size. The
engine's border pass and the proposal tool both import from here so the
geometry has a single definition (the proposal docstring's stated plan:
"after the verdict the same group-id logic moves into the engine").

Data model
==========
A *cell* is ``(poly, g2, g3)``:
  * ``poly`` — list of ``(x, y)`` vertices in image space (y down),
  * ``g2``   — level-2 group id (any hashable),
  * ``g3``   — level-3 group id (any hashable).
Level 1 is always the individual tile.

``classify_edges`` keys every cell edge by its rounded endpoints and assigns
it the HIGHEST level whose group ids differ across it; frame-boundary edges
(shared by only one cell) close the top group. ``draw_grout`` paints the
classified segments as ANTI-ALIASED round-capped capsules (locally
supersampled, composited through an L mask) so diagonal seams stay smooth at
any zoom — see the function docstring for why plain ``ImageDraw.line`` is not
enough.

The ``sub7`` flower grouping is the one shared helper: flower centres form the
norm-7 sublattice of the axial hex lattice spanned by A=(2,1), B=(-1,3); a
hex's membership is exact (centre + 6 unit neighbours, no metric rounding).
The sublattice's own coordinates are again an axial hex lattice, so level 3 is
literally ``sub7`` applied to the level-2 coordinates.

Pure Python + PIL. Deterministic (no RNG here).
"""
import math
import zlib

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Width presets
# ---------------------------------------------------------------------------
# Line width per level. Values are px at the proposal montage's reference scale
# (supersample 2, ~26-tile canvas -> hex edge ~55 px); the engine rescales them
# to its own tile size via ``scale_widths``. Ratios between levels are the
# user-facing "look" and are preserved by the scaling.
PRESETS = {
    "thin":   {1: 2, 2: 5,  3: 10},
    "medium": {1: 3, 2: 8,  3: 16},
    "thick":  {1: 5, 2: 12, 3: 24},
}
DEFAULT_PRESET = "medium"

# Tile edge (px) the preset widths above are tuned for. ``scale_widths`` keeps
# grout width proportional to tile edge length so the same preset reads the
# same at any tile scale.
REFERENCE_TILE_PX = 55.0


def preset_names():
    """Ordered preset names (single source of truth for GUI/CLI choices)."""
    return list(PRESETS.keys())


def scale_widths(preset, tile_px, reference_tile_px=REFERENCE_TILE_PX):
    """Return ``{level: width_px}`` for ``preset`` scaled to a tile of edge
    ``tile_px``. Widths stay proportional to tile edge length; each is at least
    1 px so a selected level never silently vanishes.
    """
    if preset not in PRESETS:
        raise KeyError(f"unknown grout preset {preset!r}; "
                       f"choices: {preset_names()}")
    factor = float(tile_px) / float(reference_tile_px)
    return {lvl: max(1, round(w * factor))
            for lvl, w in PRESETS[preset].items()}


def stable_seed(name):
    """Deterministic 31-bit seed from a string. Replaces ``hash(name)``, which
    is salted per-process (PYTHONHASHSEED) and would make seeded output
    non-reproducible across runs — a determinism invariant for this project.
    """
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


# ---------------------------------------------------------------------------
# sub-7 flower grouping on the axial hex lattice
# ---------------------------------------------------------------------------
_A = (2, 1)
_B = (-1, 3)
_UNIT7 = {(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, -1), (-1, 1)}


def sub7(q, r):
    """Map axial hex ``(q, r)`` to the lattice coords ``(i, j)`` of its
    7-flower. Flower centres are ``i*A + j*B``; every hex is either a centre or
    one of its six unit neighbours, so membership is exact.
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
# edge classification + drawing
# ---------------------------------------------------------------------------
def _vkey(p):
    """Quantise a vertex to 1/4-px so shared edges of adjacent cells collide on
    the same dict key despite float rounding."""
    return (round(p[0] * 4), round(p[1] * 4))


def classify_edges(cells):
    """Classify every cell edge by the highest level whose group ids differ.

    ``cells`` — iterable of ``(poly, g2, g3)``. Returns ``{1: [...], 2: [...],
    3: [...]}`` where each list holds ``(a, b)`` endpoint pairs. An edge shared
    by two cells takes level 2 if their ``g2`` differ, level 3 if their ``g3``
    differ (checked last, so it wins); an edge on the frame boundary (only one
    adjacent cell) is level 3 to close the top group. Cells must be materialised
    as a list because indices key the adjacency map.
    """
    cells = list(cells)
    edges = {}
    for idx, (poly, _, _) in enumerate(cells):
        for a, b in zip(poly, poly[1:] + poly[:1]):
            key = tuple(sorted((_vkey(a), _vkey(b))))
            edges.setdefault(key, []).append((idx, a, b))

    by_level = {1: [], 2: [], 3: []}
    for adj in edges.values():
        idx0, a, b = adj[0]
        if len(adj) == 1:
            level = 3                     # frame boundary: close the top group
        else:
            _, g2a, g3a = cells[idx0]
            _, g2b, g3b = cells[adj[1][0]]
            level = 1
            if g2a != g2b:
                level = 2
            if g3a != g3b:
                level = 3
        by_level[level].append((a, b))
    return by_level


def draw_grout(img, by_level, level_w, color=(0, 0, 0), ss=4):
    """Paint classified grout segments onto a ``PIL.Image``, anti-aliased.

    ``by_level`` — output of :func:`classify_edges`. ``level_w`` — ``{level:
    width_px}`` (e.g. from :func:`scale_widths`); a level with width <= 0 is
    skipped, so passing only ``{1: w}`` draws flat (non-hierarchical) grout.

    Every segment is rendered as a round-capped capsule into a small local
    buffer supersampled ``ss``x, LANCZOS-downscaled and composited into one
    full-resolution L mask; ``color`` is pasted through that mask in a single
    pass (so level draw order cannot matter). This is the `_LazyMask aa=4`
    pattern from the engine and the reason the pass exists: the original
    implementation drew straight onto the canvas with ``ImageDraw.line``,
    which Pillow does NOT anti-alias — every diagonal seam carried a hard
    1-px staircase that read as pixelated grout when zooming a 16K render.
    The defect never showed in the approved proposal montages because
    ``gen_grout_proposals.render_panel`` draws its panels at SS=2 and
    downsizes. Round caps double as the joint filler at segment meetings
    (the old per-endpoint ellipses, now on every level).
    """
    mask = Image.new("L", img.size, 0)
    for level in (1, 2, 3):
        wd = level_w.get(level, 0)
        if wd <= 0:
            continue
        r = wd / 2.0
        for a, b in by_level[level]:
            x0 = math.floor(min(a[0], b[0]) - r) - 1
            y0 = math.floor(min(a[1], b[1]) - r) - 1
            x1 = math.ceil(max(a[0], b[0]) + r) + 1
            y1 = math.ceil(max(a[1], b[1]) + r) + 1
            loc = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
            d = ImageDraw.Draw(loc)
            la = ((a[0] - x0) * ss, (a[1] - y0) * ss)
            lb = ((b[0] - x0) * ss, (b[1] - y0) * ss)
            d.line([la, lb], fill=255, width=round(wd * ss))
            rr = wd * ss / 2.0
            for p in (la, lb):
                d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr],
                          fill=255)
            # BOX, not LANCZOS: at an integer factor BOX is the exact
            # supersampling average — interiors stay a full 255 and edges get
            # their true coverage fraction. LANCZOS ringing reaches the centre
            # of thin (~4 px) L1 lines and leaves them ~247 instead of 255.
            loc = loc.resize((x1 - x0, y1 - y0), Image.Resampling.BOX)
            # paste-with-self ~ screen blend: interiors stay 255, AA edges
            # only ever brighten, so overlapping capsules cannot leave seams
            mask.paste(loc, (x0, y0), loc)
    img.paste(color, (0, 0), mask)
