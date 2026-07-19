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

# The structures a user can ask to have outlined, lowest first. Only the shapes
# in engine_smart._HIERARCHICAL_GROUT actually HAVE levels 2 and 3; the flat
# ones own a single level and ignore the choice.
LEVELS = (1, 2, 3)
DEFAULT_MIN_LEVEL = 1

# Tile edge (px) the preset widths above are tuned for. ``scale_widths`` keeps
# grout width proportional to tile edge length so the same preset reads the
# same at any tile scale.
REFERENCE_TILE_PX = 55.0


def preset_names():
    """Ordered preset names (single source of truth for GUI/CLI choices)."""
    return list(PRESETS.keys())


# ---------------------------------------------------------------------------
# Colour palette + stroke styles (user verdict 2026-07-19: all 10 proposed
# styles accepted, plus a basic colour choice; "solid" is the classic capsule)
# ---------------------------------------------------------------------------
GROUT_COLORS = {
    "black":   (0, 0, 0),
    "white":   (245, 245, 245),
    "gray":    (128, 128, 128),
    "silver":  (196, 199, 204),
    "cream":   (235, 225, 205),
    "gold":    (198, 161, 54),
    "red":     (170, 45, 40),
    "orange":  (210, 120, 45),
    "green":   (60, 130, 70),
    "blue":    (50, 90, 170),
    "cyan":    (0, 190, 235),
    "magenta": (170, 60, 150),
}
DEFAULT_COLOR = "black"


def color_names():
    """Ordered colour names (single source of truth for GUI/CLI choices)."""
    return list(GROUT_COLORS.keys())


def resolve_color(name):
    if name not in GROUT_COLORS:
        raise ValueError(f"unknown grout color {name!r}; "
                         f"choices: {color_names()}")
    return GROUT_COLORS[name]


def scale_widths(preset, tile_px, reference_tile_px=REFERENCE_TILE_PX,
                 min_level=1):
    """Return ``{level: width_px}`` for ``preset`` scaled to a tile of edge
    ``tile_px``. Widths stay proportional to tile edge length; each is at least
    1 px so a selected level never silently vanishes.

    ``min_level`` — the LOWEST structure that gets an outline; levels below it
    are given width 0, which :func:`draw_grout` skips. Note the direction: to
    outline the 7-hex flowers you keep the HIGH levels, not the low ones. An
    edge is classified as the highest level that separates two groups, so a
    single hexagon's border is level 2 where its neighbour is in the same
    flower and level 3 where it is not — asking for "flowers only" therefore
    means "levels >= 2", never "levels <= 2".

    min_level=1 : every tile outlined (a kite, a square, ...) — the default
    min_level=2 : only the groups (kites: the 6-kite hexagon)
    min_level=3 : only the super-groups (kites: the 7-hexagon flower)
    """
    if preset not in PRESETS:
        raise KeyError(f"unknown grout preset {preset!r}; "
                       f"choices: {preset_names()}")
    factor = float(tile_px) / float(reference_tile_px)
    return {lvl: (max(1, round(w * factor)) if lvl >= min_level else 0)
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


def draw_grout(img, by_level, level_w, color=(0, 0, 0), ss=4, style="solid"):
    """Paint classified grout segments onto a ``PIL.Image``, anti-aliased.

    ``style`` — stroke style name (see :func:`style_names`). ``"solid"``
    (default) is the classic capsule pass below, byte-identical to the
    pre-style implementation; any other name dispatches to the styled
    renderer, which synthesises decorative strokes along the same classified
    segments. ``color`` is the base stroke colour; styles with intrinsic
    accents (bevel shading, neon core, kintsugi highlight, bead rims) derive
    them from it by mixing towards white/black.

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
    if style != "solid":
        if style not in _STYLES:
            raise ValueError(f"unknown grout style {style!r}; "
                             f"choices: {style_names()}")
        _draw_grout_styled(img, by_level, level_w, color, ss, style)
        return
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


# ---------------------------------------------------------------------------
# Styled strokes (2026-07-19). Each style synthesises geometry per classified
# SEGMENT into one or more full-canvas L masks (one per colour layer), using
# the same local-buffer ss-supersample + BOX + paste-with-self machinery as
# the solid pass, then the layers are composited in declaration order.
#
# Pattern phase and jitter come from crc32 of the segment's quantised
# endpoints (never an RNG, never hash()) so a styled render is reproducible
# bit-for-bit across processes and identical for both cells of a seam.
#
# Segments shorter than one pattern period fall back to a thin solid capsule:
# densely polygonised curved seams (truchet arcs) therefore degrade to solid
# lines instead of restarting the pattern every few px. All amplitudes and
# periods scale with the level width, so thin/medium/thick presets restyle
# the pattern coherently.
# ---------------------------------------------------------------------------
def _mix(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def _seg_crc(a, b, salt=0):
    return zlib.crc32(repr((_vkey(a), _vkey(b), salt)).encode("ascii"))


def _seg_frame(a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L == 0:
        return 0.0, (1.0, 0.0), (0.0, 1.0)
    u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    return L, u, (-u[1], u[0])


def _at(a, u, n, t, off):
    return (a[0] + t * u[0] + off * n[0], a[1] + t * u[1] + off * n[1])


def _blit_polyline(mask, pts, wd, ss):
    """Round-capped, round-jointed polyline into ``mask`` (the solid pass's
    local-buffer pattern, generalised from 2 points to N)."""
    if len(pts) < 2 or wd <= 0:
        return
    r = wd / 2.0
    x0 = math.floor(min(p[0] for p in pts) - r) - 1
    y0 = math.floor(min(p[1] for p in pts) - r) - 1
    x1 = math.ceil(max(p[0] for p in pts) + r) + 1
    y1 = math.ceil(max(p[1] for p in pts) + r) + 1
    loc = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    d = ImageDraw.Draw(loc)
    lpts = [((p[0] - x0) * ss, (p[1] - y0) * ss) for p in pts]
    lw = max(1, round(wd * ss))
    d.line(lpts, fill=255, width=lw, joint="curve")
    rr = lw / 2.0
    for p in (lpts[0], lpts[-1]):
        d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=255)
    loc = loc.resize((x1 - x0, y1 - y0), Image.Resampling.BOX)
    mask.paste(loc, (x0, y0), loc)


def _blit_dot(mask, c, r, ss):
    if r <= 0:
        return
    x0, y0 = math.floor(c[0] - r) - 1, math.floor(c[1] - r) - 1
    x1, y1 = math.ceil(c[0] + r) + 1, math.ceil(c[1] + r) + 1
    loc = Image.new("L", ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    d = ImageDraw.Draw(loc)
    lc = ((c[0] - x0) * ss, (c[1] - y0) * ss)
    d.ellipse([lc[0] - r * ss, lc[1] - r * ss, lc[0] + r * ss, lc[1] + r * ss],
              fill=255)
    loc = loc.resize((x1 - x0, y1 - y0), Image.Resampling.BOX)
    mask.paste(loc, (x0, y0), loc)


def _sy_zigzag(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    P = 5.0 * wd
    if L < 2 * P:
        _blit_polyline(m["main"], [a, b], 0.5 * wd, ss)
        return
    amp, pts, side, t = 1.6 * wd, [a], 1, P / 2
    while t < L - P / 4:
        pts.append(_at(a, u, n, t, amp * side))
        side, t = -side, t + P / 2
    pts.append(b)
    _blit_polyline(m["main"], pts, 0.55 * wd, ss)


def _sy_squiggle(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    P = 6.0 * wd
    if L < P:
        _blit_polyline(m["main"], [a, b], 0.5 * wd, ss)
        return
    step = max(0.7 * wd, 1.0)
    pts = [_at(a, u, n, t, 1.5 * wd * math.sin(2 * math.pi * t / P))
           for t in _frange(0.0, L, step)] + [b]
    _blit_polyline(m["main"], pts, 0.55 * wd, ss)


def _sy_double(m, a, b, wd, ss):
    _, u, n = _seg_frame(a, b)
    for off in (-1.1 * wd, 1.1 * wd):
        pa = (a[0] + off * n[0], a[1] + off * n[1])
        pb = (b[0] + off * n[0], b[1] + off * n[1])
        _blit_polyline(m["main"], [pa, pb], 0.45 * wd, ss)


def _sy_stitch(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    dash, gap = 2.2 * wd, 2.2 * wd
    if L < dash + gap:
        mid = L / 2.0
        _blit_polyline(m["main"], [_at(a, u, n, max(0.0, mid - dash / 2), 0),
                                   _at(a, u, n, min(L, mid + dash / 2), 0)],
                       0.6 * wd, ss)
        return
    k, t = 0, gap / 2
    while t + dash <= L:
        tilt = 0.5 * wd if k % 2 == 0 else -0.5 * wd
        _blit_polyline(m["main"], [_at(a, u, n, t, -tilt),
                                   _at(a, u, n, t + dash, tilt)],
                       0.6 * wd, ss)
        k, t = k + 1, t + dash + gap


def _sy_beads(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    step, r = 2.6 * wd, 0.95 * wd
    ts = list(_frange(step / 2, L, step)) if L >= step else [L / 2.0]
    for t in ts:
        c = _at(a, u, n, t, 0)
        _blit_dot(m["rim"], c, r + 0.3 * wd, ss)
        _blit_dot(m["fill"], c, r, ss)


def _sy_rope(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    span = 2.6 * wd
    if L < 2 * span:
        _blit_polyline(m["main"], [a, b], 0.5 * wd, ss)
        return
    k, t = 0, 0.0
    while t + span <= L:
        side = 1.0 if k % 2 == 0 else -1.0
        c = t + span / 2
        pts = [_at(a, u, n, c + (span / 2) * math.cos(ph),
                   side * (span / 2) * math.sin(ph))
               for ph in [i * math.pi / 8 for i in range(9)]]
        _blit_polyline(m["main"], pts, 0.5 * wd, ss)
        k, t = k + 1, t + span


def _sy_bevel(m, a, b, wd, ss):
    _, u, n = _seg_frame(a, b)
    # global light from the top-left: the light stripe sits on whichever side
    # of the seam faces it
    light = n if (n[0] + n[1]) < 0 else (-n[0], -n[1])
    for key, sgn in (("light", 1.0), ("dark", -1.0)):
        off = 0.55 * wd * sgn
        pa = (a[0] + off * light[0], a[1] + off * light[1])
        pb = (b[0] + off * light[0], b[1] + off * light[1])
        _blit_polyline(m[key], [pa, pb], 0.5 * wd, ss)


def _sy_neon(m, a, b, wd, ss):
    for key, f in (("halo1", 3.2), ("halo2", 1.9), ("mid", 1.1), ("core", 0.5)):
        _blit_polyline(m[key], [a, b], f * wd, ss)


def _sy_kintsugi(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    step = 2.5 * wd
    if L < 2 * step:
        _blit_polyline(m["gold"], [a, b], 0.7 * wd, ss)
        return
    pts = [a]
    for i, t in enumerate(_frange(step, L - step / 2, step)):
        off = ((_seg_crc(a, b, i) & 255) / 255.0 - 0.5) * 2.2 * wd
        pts.append(_at(a, u, n, t, off))
    pts.append(b)
    _blit_polyline(m["gold"], pts, 0.85 * wd, ss)
    _blit_polyline(m["hl"], pts, 0.3 * wd, ss)


def _sy_brush(m, a, b, wd, ss):
    L, u, n = _seg_frame(a, b)
    ph = ((_seg_crc(a, b) & 255) / 255.0) * 2 * math.pi
    step = max(0.6 * wd, 1.0)
    for t in _frange(0.0, L, step):
        r = wd * (0.30 + 0.55 * (0.5 + 0.5 * math.sin(t / (7.0 * wd) + ph)))
        _blit_dot(m["main"], _at(a, u, n, t, 0), r, ss)
    _blit_dot(m["main"], b, 0.35 * wd, ss)


def _frange(a, b, step):
    t = a
    while t <= b:
        yield t
        t += step


# style -> (ordered colour layers, per-segment draw fn). A layer is
# (mask_key, colour_fn(base_rgb) -> rgb, alpha).
_STYLES = {
    "zigzag":   ([("main", lambda c: c, 1.0)], _sy_zigzag),
    "squiggle": ([("main", lambda c: c, 1.0)], _sy_squiggle),
    "double":   ([("main", lambda c: c, 1.0)], _sy_double),
    "stitch":   ([("main", lambda c: c, 1.0)], _sy_stitch),
    "beads":    ([("rim", lambda c: _mix(c, (0, 0, 0), 0.55), 1.0),
                  ("fill", lambda c: c, 1.0)], _sy_beads),
    "rope":     ([("main", lambda c: c, 1.0)], _sy_rope),
    "bevel":    ([("light", lambda c: _mix(c, (255, 255, 255), 0.75), 0.55),
                  ("dark", lambda c: _mix(c, (0, 0, 0), 0.80), 0.65)],
                 _sy_bevel),
    "neon":     ([("halo1", lambda c: c, 0.18),
                  ("halo2", lambda c: c, 0.38),
                  ("mid", lambda c: _mix(c, (255, 255, 255), 0.45), 0.70),
                  ("core", lambda c: _mix(c, (255, 255, 255), 0.90), 1.0)],
                 _sy_neon),
    "kintsugi": ([("gold", lambda c: c, 1.0),
                  ("hl", lambda c: _mix(c, (255, 255, 255), 0.55), 0.90)],
                 _sy_kintsugi),
    "brush":    ([("main", lambda c: c, 1.0)], _sy_brush),
}
DEFAULT_STYLE = "solid"


def style_names():
    """Ordered style names, "solid" first (single source of truth)."""
    return ["solid"] + list(_STYLES.keys())


def _draw_grout_styled(img, by_level, level_w, color, ss, style):
    layers, draw_fn = _STYLES[style]
    masks = {key: Image.new("L", img.size, 0) for key, _, _ in layers}
    for level in (1, 2, 3):
        wd = level_w.get(level, 0)
        if wd <= 0:
            continue
        for a, b in by_level[level]:
            draw_fn(masks, a, b, float(wd), ss)
    for key, col_fn, alpha in layers:
        mask = masks[key]
        if alpha < 1.0:
            mask = mask.point(lambda v, al=alpha: round(v * al))
        img.paste(col_fn(color), (0, 0), mask)
