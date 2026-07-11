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
classified segments thinnest-first / thickest-last with rounded joints so
thick lines meet without notches — byte-for-byte the render_panel behaviour.

The ``sub7`` flower grouping is the one shared helper: flower centres form the
norm-7 sublattice of the axial hex lattice spanned by A=(2,1), B=(-1,3); a
hex's membership is exact (centre + 6 unit neighbours, no metric rounding).
The sublattice's own coordinates are again an axial hex lattice, so level 3 is
literally ``sub7`` applied to the level-2 coordinates.

Pure Python + PIL. Deterministic (no RNG here).
"""
import zlib

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


def draw_grout(draw, by_level, level_w, color=(0, 0, 0)):
    """Paint classified grout segments onto a ``PIL.ImageDraw`` surface.

    ``by_level`` — output of :func:`classify_edges`. ``level_w`` — ``{level:
    width_px}`` (e.g. from :func:`scale_widths`); a level with width <= 0 is
    skipped, so passing only ``{1: w}`` draws flat (non-hierarchical) grout.
    Levels are drawn thin-first so thicker higher-level lines sit on top;
    rounded joints fill the notches where thick segments meet.
    """
    for level in (1, 2, 3):
        wd = level_w.get(level, 0)
        if wd <= 0:
            continue
        for a, b in by_level[level]:
            draw.line([a, b], fill=color, width=wd)
            if level > 1:
                rr = wd / 2 - 0.5
                for p in (a, b):
                    draw.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr],
                                 fill=color)
