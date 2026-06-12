"""
src/spectre_tiling.py
---------------------
Exact chiral aperiodic "spectre" tiling generator.

Implements the nine-metatile substitution system from:

    D. Smith, J. S. Myers, C. S. Kaplan, C. Goodman-Strauss,
    "A chiral aperiodic monotile", arXiv:2305.17743 (2023).

The construction is a faithful Python port of the authors' reference
implementation (Craig S. Kaplan, https://cs.uwaterloo.ca/~csk/spectre/
spectre.js).

The spectre is a 14-sided polygon (Tile(1,1) of the hat family with all
edges of equal length) that tiles the plane only aperiodically and only
WITHOUT reflections — a strictly chiral monotile. Nine metatile types
(Gamma, Delta, Theta, Lambda, Xi, Pi, Sigma, Phi, Psi) substitute into
supertiles of up to eight children; Gamma is the "mystic", a fused pair
of spectres with the second one rotated by 30 degrees. Each substitution
step conjugates the whole system by a reflection, so within any generated
patch every spectre has the same handedness (the defining property of
the chiral tiling).

Affine primitives are shared with the einstein-hat generator
(src/hat_tiling.py).

Public API:
    generate_spectre_tiling(width, height, tile_size) -> list[SpectrePlacement]
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

from .hat_tiling import (
    Affine,
    Point,
    _IDENT,
    _mul,
    _polygon_area,
    _trans_pt,
    _trot,
    _ttrans,
)

logger = logging.getLogger(__name__)

_HR3 = math.sqrt(3.0) / 2.0

# See _BOUNDARY_MARGIN_HATS in hat_tiling.py — same role: the patch
# boundary wiggles around the quad anchor polygon, so containment is
# tested with a safety margin and one guard substitution level.
_BOUNDARY_MARGIN_TILES = 3.0


# ==========================================
# SPECTRE GEOMETRY (spectre.js: buildSpectreBase)
# ==========================================
# 14 vertices, every edge of length 1 (Tile(1,1) straight-edge variant).
SPECTRE_OUTLINE: Tuple[Point, ...] = (
    (0.0, 0.0),
    (1.0, 0.0),
    (1.5, -_HR3),
    (1.5 + _HR3, 0.5 - _HR3),
    (1.5 + _HR3, 1.5 - _HR3),
    (2.5 + _HR3, 1.5 - _HR3),
    (3.0 + _HR3, 1.5),
    (3.0, 2.0),
    (3.0 - _HR3, 1.5),
    (2.5 - _HR3, 1.5 + _HR3),
    (1.5 - _HR3, 1.5 + _HR3),
    (0.5 - _HR3, 1.5 + _HR3),
    (-_HR3, 1.5),
    (0.0, 1.0),
)

# Key anchor points used to assemble supertiles (spectre_keys).
_KEY_INDICES = (3, 5, 7, 11)

_SPECTRE_AREA = _polygon_area(SPECTRE_OUTLINE)
_SPECTRE_BBOX_W = (max(p[0] for p in SPECTRE_OUTLINE)
                   - min(p[0] for p in SPECTRE_OUTLINE))
_SPECTRE_BBOX_H = (max(p[1] for p in SPECTRE_OUTLINE)
                   - min(p[1] for p in SPECTRE_OUTLINE))
_SPECTRE_DIAG = math.hypot(_SPECTRE_BBOX_W, _SPECTRE_BBOX_H)

_TILE_LABELS = ("Gamma", "Delta", "Theta", "Lambda", "Xi",
                "Pi", "Sigma", "Phi", "Psi")


class _Shape:
    """Leaf of the substitution tree: a single spectre."""
    __slots__ = ("pts", "quad", "label")

    def __init__(self, pts, quad, label):
        self.pts = pts
        self.quad = quad
        self.label = label


class _Meta:
    """Inner node: transformed children plus quad anchor points."""
    __slots__ = ("children", "quad")

    def __init__(self):
        self.children: List[Tuple[Affine, "_Geom"]] = []
        self.quad: List[Point] = []

    def add_child(self, geom: "_Geom", t: Affine) -> None:
        self.children.append((t, geom))

    def recentre(self, cx: float, cy: float) -> None:
        """Translate by (-cx, -cy) so the given centre sits at the origin.

        The reference implementation lets supertiles drift away from the
        origin with every substitution; recentring on the true bbox centre
        keeps the patch mass under the target rectangle (the quad centroid
        is NOT a reliable centre — it sits off the patch mass and produced
        corner gaps at large render sizes).
        """
        m = _ttrans(-cx, -cy)
        self.quad = [(p[0] - cx, p[1] - cy) for p in self.quad]
        self.children = [(_mul(m, t), g) for t, g in self.children]


_Geom = Union[_Shape, _Meta]


def _trans_to(p: Point, q: Point) -> Affine:
    return _ttrans(q[0] - p[0], q[1] - p[1])


# ==========================================
# SUBSTITUTION SYSTEM (spectre.js: buildSpectreBase / buildSupertiles)
# ==========================================
def _build_spectre_base() -> Dict[str, _Geom]:
    keys = [SPECTRE_OUTLINE[i] for i in _KEY_INDICES]
    sys: Dict[str, _Geom] = {}

    for lab in _TILE_LABELS[1:]:  # all except Gamma
        sys[lab] = _Shape(SPECTRE_OUTLINE, list(keys), lab)

    # Gamma is the "mystic": two fused spectres, the second rotated 30 deg.
    mystic = _Meta()
    mystic.add_child(_Shape(SPECTRE_OUTLINE, list(keys), "Gamma1"), _IDENT)
    p8 = SPECTRE_OUTLINE[8]
    mystic.add_child(
        _Shape(SPECTRE_OUTLINE, list(keys), "Gamma2"),
        _mul(_ttrans(p8[0], p8[1]), _trot(math.pi / 6.0)))
    mystic.quad = list(keys)
    sys["Gamma"] = mystic
    return sys


# Per-slot placement rules: (rotation increment in degrees, key index of
# the previous slot to attach from, key index of the new slot to attach to).
_T_RULES = ((60, 3, 1), (0, 2, 0), (60, 3, 1), (60, 3, 1),
            (0, 2, 0), (60, 3, 1), (-120, 3, 3))

# Which unit tile goes into each of the 8 slots of every supertile.
_SUPER_RULES: Dict[str, Tuple[str, ...]] = {
    "Gamma":  ("Pi", "Delta", None, "Theta", "Sigma", "Xi", "Phi", "Gamma"),
    "Delta":  ("Xi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Phi", "Gamma"),
    "Theta":  ("Psi", "Delta", "Pi", "Phi", "Sigma", "Pi", "Phi", "Gamma"),
    "Lambda": ("Psi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Phi", "Gamma"),
    "Xi":     ("Psi", "Delta", "Pi", "Phi", "Sigma", "Psi", "Phi", "Gamma"),
    "Pi":     ("Psi", "Delta", "Xi", "Phi", "Sigma", "Psi", "Phi", "Gamma"),
    "Sigma":  ("Xi", "Delta", "Xi", "Phi", "Sigma", "Pi", "Lambda", "Gamma"),
    "Phi":    ("Psi", "Delta", "Psi", "Phi", "Sigma", "Pi", "Phi", "Gamma"),
    "Psi":    ("Psi", "Delta", "Psi", "Phi", "Sigma", "Psi", "Phi", "Gamma"),
}


def _build_supertiles(sys: Dict[str, _Geom]) -> Dict[str, _Geom]:
    """One substitution step: nine unit tiles -> nine supertiles.

    Note the reflection R applied to every slot transform: each
    substitution conjugates the system, which is why a finished patch
    contains spectres of one handedness only.
    """
    quad = sys["Delta"].quad
    refl: Affine = (-1.0, 0.0, 0.0, 0.0, 1.0, 0.0)

    transforms: List[Affine] = [_IDENT]
    total_ang = 0.0
    rot: Affine = _IDENT
    tquad = list(quad)
    for ang, idx_from, idx_to in _T_RULES:
        total_ang += ang
        if ang != 0:
            rot = _trot(math.radians(total_ang))
            tquad = [_trans_pt(rot, q) for q in quad]
        ttt = _trans_to(tquad[idx_to],
                        _trans_pt(transforms[-1], quad[idx_from]))
        transforms.append(_mul(ttt, rot))

    transforms = [_mul(refl, t) for t in transforms]

    super_quad = [
        _trans_pt(transforms[6], quad[2]),
        _trans_pt(transforms[5], quad[1]),
        _trans_pt(transforms[3], quad[2]),
        _trans_pt(transforms[0], quad[1]),
    ]

    ret: Dict[str, _Geom] = {}
    for lab, subs in _SUPER_RULES.items():
        sup = _Meta()
        for idx in range(8):
            if subs[idx] is None:
                continue
            sup.add_child(sys[subs[idx]], transforms[idx])
        sup.quad = list(super_quad)
        ret[lab] = sup

    # All nine supertiles must share one coordinate frame (the next
    # generation glues them via the common super_quad), so they are all
    # recentred by the SAME translation: the bbox centre of the Delta
    # supertile, the tile the generator later collects from. Per-label
    # centres would desynchronise the gluing and tear the tiling apart.
    bbox = _node_bbox(ret["Delta"], {})
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    for sup in ret.values():
        sup.recentre(cx, cy)
    return ret


# ==========================================
# BOUNDING BOXES (exact, memoised bottom-up)
# ==========================================
_BBox = Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y


def _transform_bbox(m: Affine, b: _BBox) -> _BBox:
    corners = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]
    pts = [_trans_pt(m, c) for c in corners]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def _node_bbox(geom: _Geom, memo: Dict[int, _BBox]) -> _BBox:
    """True conservative bbox of a node in its own coordinates.

    Computed bottom-up from actual child geometry, so pruning against it
    needs no fractal-wiggle margin (unlike the hat's ideal outlines).
    """
    cached = memo.get(id(geom))
    if cached is not None:
        return cached
    if isinstance(geom, _Shape):
        bbox = (min(p[0] for p in geom.pts), min(p[1] for p in geom.pts),
                max(p[0] for p in geom.pts), max(p[1] for p in geom.pts))
    else:
        boxes = [_transform_bbox(t, _node_bbox(g, memo))
                 for t, g in geom.children]
        bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    memo[id(geom)] = bbox
    return bbox


# ==========================================
# PUBLIC API
# ==========================================
@dataclass(frozen=True)
class SpectrePlacement:
    """One placed spectre: 14 polygon vertices in pixel coordinates."""
    points: Tuple[Point, ...]
    mirrored: bool  # uniform across a tiling (chirality), kept for parity


def _collect_spectres(geom: _Geom, m: Affine,
                      rect: Tuple[float, float, float, float],
                      memo: Dict[int, _BBox], slack: float,
                      out: List[SpectrePlacement]) -> None:
    bbox = _transform_bbox(m, _node_bbox(geom, memo))
    if (bbox[2] < rect[0] - slack or bbox[0] > rect[2] + slack
            or bbox[3] < rect[1] - slack or bbox[1] > rect[3] + slack):
        return

    if isinstance(geom, _Shape):
        pts = tuple(_trans_pt(m, p) for p in geom.pts)
        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)
        if (max_x > rect[0] and min_x < rect[2]
                and max_y > rect[1] and min_y < rect[3]):
            det = m[0] * m[4] - m[1] * m[3]
            out.append(SpectrePlacement(points=pts, mirrored=det < 0.0))
        return

    for ct, child in geom.children:
        _collect_spectres(child, _mul(m, ct), rect, memo, slack, out)


def generate_spectre_tiling(width: int, height: int, tile_size: float,
                            max_levels: int = 10) -> List[SpectrePlacement]:
    """Generate an exact chiral spectre tiling covering a width x height rect.

    Args:
        width, height: Target rectangle in pixels.
        tile_size:     Desired granularity; each spectre covers an area of
                       roughly tile_size**2 pixels (parity with square
                       tiles and the einstein hat).
        max_levels:    Safety cap on substitution depth.

    Returns:
        List of SpectrePlacement whose polygons jointly cover the
        rectangle (boundary tiles overhang and should be clipped by the
        caller). All placements share one handedness — the tiling is
        strictly chiral. Deterministic for identical arguments.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    tile_size = max(2.0, float(tile_size))
    sc = tile_size / math.sqrt(_SPECTRE_AREA)
    to_screen: Affine = (sc, 0.0, width / 2.0, 0.0, sc, height / 2.0)

    tile_diag_px = _SPECTRE_DIAG * sc
    margin = _BOUNDARY_MARGIN_TILES * tile_diag_px
    corners = ((-margin, -margin), (width + margin, -margin),
               (width + margin, height + margin), (-margin, height + margin))

    sys = _build_spectre_base()
    level = 1
    while level < max_levels:
        # The patch is a roughly hexagonal blob recentred on its true bbox
        # centre; requiring the inflated rectangle to fit inside the bbox
        # shrunk to half extents keeps it conservatively in the interior.
        # One guard substitution then adds clearance of the order of the
        # whole previous-generation patch (same reasoning as hat_tiling).
        bbox = _transform_bbox(to_screen, _node_bbox(sys["Delta"], {}))
        half_w = (bbox[2] - bbox[0]) / 4.0
        half_h = (bbox[3] - bbox[1]) / 4.0
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        if all(abs(c[0] - cx) <= half_w and abs(c[1] - cy) <= half_h
               for c in corners):
            sys = _build_supertiles(sys)
            level += 1
            break
        sys = _build_supertiles(sys)
        level += 1
    else:
        logger.warning(
            "spectre tiling: substitution depth capped at %d levels; "
            "coverage of %dx%d may be incomplete", max_levels, width, height)

    memo: Dict[int, _BBox] = {}
    spectres: List[SpectrePlacement] = []
    _collect_spectres(sys["Delta"], to_screen,
                      (0.0, 0.0, float(width), float(height)),
                      memo, tile_diag_px, spectres)

    mirrored = sum(1 for s in spectres if s.mirrored)
    logger.info(
        "spectre tiling: %dx%d px, tile_size=%.1f -> level=%d, spectres=%d "
        "(mirrored=%d)", width, height, tile_size, level,
        len(spectres), mirrored)
    return spectres
