"""
src/hat_tiling.py
-----------------
Exact aperiodic "einstein hat" tiling generator.

Implements the H/T/P/F metatile substitution system from:

    D. Smith, J. S. Myers, C. S. Kaplan, C. Goodman-Strauss,
    "An aperiodic monotile", arXiv:2303.10798 (2023).

The construction is a faithful Python port of Craig S. Kaplan's reference
implementation "hatviz" (https://github.com/isohedral/hatviz, hat.js /
geometry.js), written by a co-author of the paper.

The hat is a 13-vertex polykite: the union of 8 kites of the [3.4.6.4]
Laves tiling (each kite is one sixth of a regular hexagon). Hats can never
be laid out on a regular grid, so instead of a row/column scan the plane
is covered by recursive substitution: four metatile types (H, T, P, F)
are assembled into a 29-child patch, from which the next-generation
supertiles are extracted. Iterating this process grows an exact aperiodic
patch exponentially. Walking the resulting transform tree yields the
precise affine placement of every hat, including the reflected
"anti-hats" required by the tiling (recognised by a negative determinant).

Public API:
    generate_hat_tiling(width, height, hat_size) -> list[HatPlacement]
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple, Union

logger = logging.getLogger(__name__)

Point = Tuple[float, float]
Affine = Tuple[float, float, float, float, float, float]  # row-major 2x3

_HR3 = math.sqrt(3.0) / 2.0
_IDENT: Affine = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)

# Supertile boundaries are ideal polygons; the actual hat-covered region
# wiggles around them by a bounded number of hat diameters. This safety
# margin (in hat bounding-box diagonals) guarantees full rectangle
# coverage and conservative pruning while walking the transform tree.
_BOUNDARY_MARGIN_HATS = 3.0


# ==========================================
# AFFINE GEOMETRY PRIMITIVES (geometry.js port)
# ==========================================
def _hex_pt(x: float, y: float) -> Point:
    """Map hexagonal lattice coordinates to Cartesian."""
    return (x + 0.5 * y, _HR3 * y)


def _mul(a: Affine, b: Affine) -> Affine:
    """Compose two affine transforms (a applied after b)."""
    return (a[0] * b[0] + a[1] * b[3],
            a[0] * b[1] + a[1] * b[4],
            a[0] * b[2] + a[1] * b[5] + a[2],
            a[3] * b[0] + a[4] * b[3],
            a[3] * b[1] + a[4] * b[4],
            a[3] * b[2] + a[4] * b[5] + a[5])


def _inv(t: Affine) -> Affine:
    det = t[0] * t[4] - t[1] * t[3]
    return (t[4] / det, -t[1] / det, (t[1] * t[5] - t[2] * t[4]) / det,
            -t[3] / det, t[0] / det, (t[2] * t[3] - t[0] * t[5]) / det)


def _trans_pt(m: Affine, p: Point) -> Point:
    return (m[0] * p[0] + m[1] * p[1] + m[2],
            m[3] * p[0] + m[4] * p[1] + m[5])


def _padd(p: Point, q: Point) -> Point:
    return (p[0] + q[0], p[1] + q[1])


def _psub(p: Point, q: Point) -> Point:
    return (p[0] - q[0], p[1] - q[1])


def _trot(ang: float) -> Affine:
    c, s = math.cos(ang), math.sin(ang)
    return (c, -s, 0.0, s, c, 0.0)


def _ttrans(tx: float, ty: float) -> Affine:
    return (1.0, 0.0, tx, 0.0, 1.0, ty)


def _rot_about(p: Point, ang: float) -> Affine:
    return _mul(_ttrans(p[0], p[1]), _mul(_trot(ang), _ttrans(-p[0], -p[1])))


def _match_seg(p: Point, q: Point) -> Affine:
    """Affine transform mapping the unit segment (0,0)->(1,0) onto p->q."""
    return (q[0] - p[0], p[1] - q[1], p[0],
            q[1] - p[1], q[0] - p[0], p[1])


def _match_two(p1: Point, q1: Point, p2: Point, q2: Point) -> Affine:
    """Affine transform mapping segment p1->q1 onto segment p2->q2."""
    return _mul(_match_seg(p2, q2), _inv(_match_seg(p1, q1)))


def _intersect(p1: Point, q1: Point, p2: Point, q2: Point) -> Point:
    """Intersection of the lines through segments p1->q1 and p2->q2."""
    d = ((q2[1] - p2[1]) * (q1[0] - p1[0])
         - (q2[0] - p2[0]) * (q1[1] - p1[1]))
    ua = ((q2[0] - p2[0]) * (p1[1] - p2[1])
          - (q2[1] - p2[1]) * (p1[0] - p2[0])) / d
    return (p1[0] + ua * (q1[0] - p1[0]), p1[1] + ua * (q1[1] - p1[1]))


def _polygon_area(pts: Sequence[Point]) -> float:
    """Absolute polygon area via the shoelace formula."""
    acc = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        acc += x1 * y2 - x2 * y1
    return abs(acc) / 2.0


def _point_in_polygon(p: Point, poly: Sequence[Point]) -> bool:
    """Even-odd ray-casting point-in-polygon test."""
    x, y = p
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


# ==========================================
# HAT GEOMETRY
# ==========================================
# The hat outline on the hexagonal lattice (hat.js / geometry.js).
HAT_OUTLINE: Tuple[Point, ...] = tuple(_hex_pt(x, y) for x, y in (
    (0, 0), (-1, -1), (0, -2), (2, -2),
    (2, -1), (4, -2), (5, -1), (4, 0),
    (3, 0), (2, 2), (0, 3), (0, 2),
    (-1, 2),
))

_HAT_AREA_UNIT = _polygon_area(HAT_OUTLINE)
_HAT_BBOX_W = (max(p[0] for p in HAT_OUTLINE)
               - min(p[0] for p in HAT_OUTLINE))
_HAT_BBOX_H = (max(p[1] for p in HAT_OUTLINE)
               - min(p[1] for p in HAT_OUTLINE))
_HAT_DIAG_UNIT = math.hypot(_HAT_BBOX_W, _HAT_BBOX_H)


class _HatTile:
    """Leaf of the substitution tree: a single hat."""
    __slots__ = ("label",)

    def __init__(self, label: str):
        self.label = label


class _MetaTile:
    """Inner node: an outline polygon plus transformed children."""
    __slots__ = ("shape", "children")

    def __init__(self, shape: Sequence[Point]):
        self.shape: List[Point] = list(shape)
        self.children: List[Tuple[Affine, "_Geom"]] = []

    def add_child(self, t: Affine, geom: "_Geom") -> None:
        self.children.append((t, geom))

    def eval_child(self, n: int, i: int) -> Point:
        t, geom = self.children[n]
        return _trans_pt(t, geom.shape[i])

    def recentre(self) -> None:
        cx = sum(p[0] for p in self.shape) / len(self.shape)
        cy = sum(p[1] for p in self.shape) / len(self.shape)
        self.shape = [(p[0] - cx, p[1] - cy) for p in self.shape]
        m = _ttrans(-cx, -cy)
        self.children = [(_mul(m, t), geom) for t, geom in self.children]


_Geom = Union[_HatTile, _MetaTile]

_H_HAT = _HatTile("H")
_H1_HAT = _HatTile("H1")  # the reflected anti-hat
_T_HAT = _HatTile("T")
_P_HAT = _HatTile("P")
_F_HAT = _HatTile("F")


# ==========================================
# LEVEL-1 METATILES (hat.js: H_init / T_init / P_init / F_init)
# ==========================================
def _initial_metatiles() -> List[_MetaTile]:
    h_outline = [(0.0, 0.0), (4.0, 0.0), (4.5, _HR3),
                 (2.5, 5 * _HR3), (1.5, 5 * _HR3), (-0.5, _HR3)]
    h = _MetaTile(h_outline)
    h.add_child(_match_two(HAT_OUTLINE[5], HAT_OUTLINE[7],
                           h_outline[5], h_outline[0]), _H_HAT)
    h.add_child(_match_two(HAT_OUTLINE[9], HAT_OUTLINE[11],
                           h_outline[1], h_outline[2]), _H_HAT)
    h.add_child(_match_two(HAT_OUTLINE[5], HAT_OUTLINE[7],
                           h_outline[3], h_outline[4]), _H_HAT)
    h.add_child(_mul(_ttrans(2.5, _HR3),
                     _mul((-0.5, -_HR3, 0.0, _HR3, -0.5, 0.0),
                          (0.5, 0.0, 0.0, 0.0, -0.5, 0.0))), _H1_HAT)

    t_outline = [(0.0, 0.0), (3.0, 0.0), (1.5, 3 * _HR3)]
    t = _MetaTile(t_outline)
    t.add_child((0.5, 0.0, 0.5, 0.0, 0.5, _HR3), _T_HAT)

    p_outline = [(0.0, 0.0), (4.0, 0.0), (3.0, 2 * _HR3), (-1.0, 2 * _HR3)]
    p = _MetaTile(p_outline)
    p.add_child((0.5, 0.0, 1.5, 0.0, 0.5, _HR3), _P_HAT)
    p.add_child(_mul(_ttrans(0.0, 2 * _HR3),
                     _mul((0.5, _HR3, 0.0, -_HR3, 0.5, 0.0),
                          (0.5, 0.0, 0.0, 0.0, 0.5, 0.0))), _P_HAT)

    f_outline = [(0.0, 0.0), (3.0, 0.0), (3.5, _HR3),
                 (3.0, 2 * _HR3), (-1.0, 2 * _HR3)]
    f = _MetaTile(f_outline)
    f.add_child((0.5, 0.0, 1.5, 0.0, 0.5, _HR3), _F_HAT)
    f.add_child(_mul(_ttrans(0.0, 2 * _HR3),
                     _mul((0.5, _HR3, 0.0, -_HR3, 0.5, 0.0),
                          (0.5, 0.0, 0.0, 0.0, 0.5, 0.0))), _F_HAT)

    return [h, t, p, f]


# Hats are placed inside metatiles at a fixed linear scale relative to
# lattice units (0.5 in the reference construction); derived here from the
# determinant of the first H child so the pixel sizing stays correct even
# if the upstream geometry ever changes.
def _hat_placement_scale() -> float:
    t = _initial_metatiles()[0].children[0][0]
    return math.sqrt(abs(t[0] * t[4] - t[1] * t[3]))


_HAT_PLACEMENT_SCALE = _hat_placement_scale()


# ==========================================
# SUBSTITUTION (hat.js: constructPatch / constructMetatiles)
# ==========================================
# Each rule appends one child to the patch:
#   (label,)                    -> place at identity
#   (n, i, label, j)            -> glue edge j of the new tile to edge i
#                                  of existing child n
#   (np, ip, nq, iq, label, j)  -> glue edge j across two existing children
_PATCH_RULES: Tuple[tuple, ...] = (
    ("H",),
    (0, 0, "P", 2), (1, 0, "H", 2), (2, 0, "P", 2), (3, 0, "H", 2),
    (4, 4, "P", 2), (0, 4, "F", 3), (2, 4, "F", 3),
    (4, 1, 3, 2, "F", 0),
    (8, 3, "H", 0), (9, 2, "P", 0), (10, 2, "H", 0), (11, 4, "P", 2),
    (12, 0, "H", 2), (13, 0, "F", 3), (14, 2, "F", 1), (15, 3, "H", 4),
    (8, 2, "F", 1), (17, 3, "H", 0), (18, 2, "P", 0), (19, 2, "H", 2),
    (20, 4, "F", 3), (20, 0, "P", 2), (22, 0, "H", 2), (23, 4, "F", 3),
    (23, 0, "F", 3), (16, 0, "P", 2),
    (9, 4, 0, 2, "T", 2),
    (4, 0, "F", 3),
)


def _construct_patch(h: _MetaTile, t: _MetaTile,
                     p: _MetaTile, f: _MetaTile) -> _MetaTile:
    """Assemble the 29-child patch of current-generation metatiles."""
    ret = _MetaTile([])
    shapes: Dict[str, _MetaTile] = {"H": h, "T": t, "P": p, "F": f}

    for rule in _PATCH_RULES:
        if len(rule) == 1:
            ret.add_child(_IDENT, shapes[rule[0]])
        elif len(rule) == 4:
            n, i, label, j = rule
            ct, cg = ret.children[n]
            poly = cg.shape
            p2 = _trans_pt(ct, poly[(i + 1) % len(poly)])
            q2 = _trans_pt(ct, poly[i])
            npoly = shapes[label].shape
            ret.add_child(
                _match_two(npoly[j], npoly[(j + 1) % len(npoly)], p2, q2),
                shapes[label])
        else:
            n_p, i_p, n_q, i_q, label, j = rule
            tp, gp = ret.children[n_p]
            tq, gq = ret.children[n_q]
            p2 = _trans_pt(tq, gq.shape[i_q])
            q2 = _trans_pt(tp, gp.shape[i_p])
            npoly = shapes[label].shape
            ret.add_child(
                _match_two(npoly[j], npoly[(j + 1) % len(npoly)], p2, q2),
                shapes[label])

    return ret


def _construct_metatiles(patch: _MetaTile) -> List[_MetaTile]:
    """Extract next-generation H, T, P, F supertiles from the patch."""
    bps1 = patch.eval_child(8, 2)
    bps2 = patch.eval_child(21, 2)
    rbps = _trans_pt(_rot_about(bps1, -2.0 * math.pi / 3.0), bps2)

    p72 = patch.eval_child(7, 2)
    p252 = patch.eval_child(25, 2)
    p62 = patch.eval_child(6, 2)

    llc = _intersect(bps1, rbps, p62, p72)
    w = _psub(p62, llc)

    new_h_outline = [llc, bps1]
    w = _trans_pt(_trot(-math.pi / 3.0), w)
    new_h_outline.append(_padd(new_h_outline[1], w))
    new_h_outline.append(patch.eval_child(14, 2))
    w = _trans_pt(_trot(-math.pi / 3.0), w)
    new_h_outline.append(_psub(new_h_outline[3], w))
    new_h_outline.append(p62)

    new_h = _MetaTile(new_h_outline)
    for ch in (0, 9, 16, 27, 26, 6, 1, 8, 10, 15):
        new_h.add_child(*patch.children[ch])

    new_p_outline = [p72, _padd(p72, _psub(bps1, llc)), bps1, llc]
    new_p = _MetaTile(new_p_outline)
    for ch in (7, 2, 3, 4, 28):
        new_p.add_child(*patch.children[ch])

    new_f_outline = [bps2, patch.eval_child(24, 2), patch.eval_child(25, 0),
                     p252, _padd(p252, _psub(llc, bps1))]
    new_f = _MetaTile(new_f_outline)
    for ch in (21, 20, 22, 23, 24, 25):
        new_f.add_child(*patch.children[ch])

    aaa = new_h_outline[2]
    bbb = _padd(new_h_outline[1], _psub(new_h_outline[4], new_h_outline[5]))
    ccc = _trans_pt(_rot_about(bbb, -math.pi / 3.0), aaa)
    new_t = _MetaTile([bbb, ccc, aaa])
    new_t.add_child(*patch.children[11])

    for meta in (new_h, new_p, new_f, new_t):
        meta.recentre()

    return [new_h, new_t, new_p, new_f]


# ==========================================
# PUBLIC API
# ==========================================
@dataclass(frozen=True)
class HatPlacement:
    """One placed hat: 13 polygon vertices in pixel coordinates."""
    points: Tuple[Point, ...]
    mirrored: bool  # True for the reflected "anti-hat"


def _collect_hats(geom: _Geom, m: Affine, rect: Tuple[float, float, float, float],
                  margin: float, out: List[HatPlacement]) -> None:
    """Walk the transform tree, pruning subtrees away from the rectangle."""
    if isinstance(geom, _HatTile):
        pts = tuple(_trans_pt(m, p) for p in HAT_OUTLINE)
        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)
        if (max_x > rect[0] and min_x < rect[2]
                and max_y > rect[1] and min_y < rect[3]):
            det = m[0] * m[4] - m[1] * m[3]
            out.append(HatPlacement(points=pts, mirrored=det < 0.0))
        return

    if geom.shape:
        pts_o = [_trans_pt(m, p) for p in geom.shape]
        min_x = min(p[0] for p in pts_o)
        max_x = max(p[0] for p in pts_o)
        min_y = min(p[1] for p in pts_o)
        max_y = max(p[1] for p in pts_o)
        # A metatile's hats can protrude past its ideal outline by a wiggle
        # proportional to the metatile's own size (the true boundary is
        # fractal-like), so the pruning pad must scale with the node, with
        # a fixed hat-sized slack for the lowest levels.
        pad = 0.5 * math.hypot(max_x - min_x, max_y - min_y) + margin
        if (max_x < rect[0] - pad or min_x > rect[2] + pad
                or max_y < rect[1] - pad or min_y > rect[3] + pad):
            return

    for ct, child in geom.children:
        _collect_hats(child, _mul(m, ct), rect, margin, out)


def generate_hat_tiling(width: int, height: int, hat_size: float,
                        max_levels: int = 12) -> List[HatPlacement]:
    """Generate an exact aperiodic hat tiling covering a width x height rect.

    Args:
        width, height: Target rectangle in pixels.
        hat_size:      Desired tile granularity; each hat covers an area of
                       roughly hat_size**2 pixels (comparable to a square
                       tile of side hat_size).
        max_levels:    Safety cap on substitution depth.

    Returns:
        List of HatPlacement whose polygons jointly cover the rectangle
        (boundary hats extend past the edges and should be clipped by the
        caller). Deterministic for identical arguments.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    hat_size = max(2.0, float(hat_size))
    # Pixels per lattice unit; hats are placed at _HAT_PLACEMENT_SCALE
    # relative to lattice units, hence the compensation factor.
    sc = hat_size / (math.sqrt(_HAT_AREA_UNIT) * _HAT_PLACEMENT_SCALE)
    to_screen: Affine = (sc, 0.0, width / 2.0, 0.0, sc, height / 2.0)

    hat_diag_px = _HAT_DIAG_UNIT * _HAT_PLACEMENT_SCALE * sc
    margin = _BOUNDARY_MARGIN_HATS * hat_diag_px
    corners = ((-margin, -margin), (width + margin, -margin),
               (width + margin, height + margin), (-margin, height + margin))

    tiles = _initial_metatiles()
    level = 1
    while level < max_levels:
        h_outline_px = [_trans_pt(to_screen, p) for p in tiles[0].shape]
        if all(_point_in_polygon(c, h_outline_px) for c in corners):
            # The outline is only the ideal supertile boundary; the actual
            # hat-covered region recedes from it by a wiggle that grows with
            # the substitution level (the boundary is fractal-like), so a
            # fixed margin is not sufficient on its own. One extra guard
            # level puts the rectangle deep in the supertile interior with
            # clearance of the order of the whole previous-generation
            # supertile. Collection below is bbox-pruned, so the extra
            # level adds no meaningful cost.
            tiles = _construct_metatiles(_construct_patch(*tiles))
            level += 1
            break
        tiles = _construct_metatiles(_construct_patch(*tiles))
        level += 1
    else:
        logger.warning(
            "hat tiling: substitution depth capped at %d levels; "
            "coverage of %dx%d may be incomplete", max_levels, width, height)

    hats: List[HatPlacement] = []
    _collect_hats(tiles[0], to_screen,
                  (0.0, 0.0, float(width), float(height)), margin, hats)

    mirrored = sum(1 for h in hats if h.mirrored)
    logger.info(
        "hat tiling: %dx%d px, hat_size=%.1f -> level=%d, hats=%d "
        "(mirrored=%d)", width, height, hat_size, level, len(hats), mirrored)
    return hats
