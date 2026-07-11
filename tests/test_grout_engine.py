"""Tests for the SmartEngine hierarchical grout pass (border overlay).

Two concerns:
  * cell generation (``_grout_cells_*``) reproduces the reviewed grouping and,
    for hexagons, that the derived offset->axial conversion yields spatially
    contiguous sub7 flowers (a wrong linear map still groups into 7s, so this
    is verified geometrically, not just by count);
  * the pass is a pure overlay — ``grout_preset=None`` is byte-identical to the
    baseline render, a preset adds black grout, and an unsupported shape is a
    silent no-op.
"""
import math
import threading
from collections import Counter

import numpy as np
from PIL import Image

from src.engine_smart import SmartEngine
from src.grout import classify_edges
from tests.test_golden_shapes import _build_library, _make_target


def _engine():
    return SmartEngine(index_path="__none__.pkl")


def _centroid(poly):
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


# ---------------------------------------------------------------------------
# cell generation / grouping
# ---------------------------------------------------------------------------
def test_square_blocks_partition_3x3_and_9x9():
    cells = _engine()._grout_cells_square(600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    # every level-2 block collects at most 3x3 = 9 tiles; interior blocks full
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 9
    l3 = Counter(g3 for _, _, g3 in cells)
    assert max(l3.values()) == 81           # 9x9 block


def test_hexagon_sub7_flowers_are_spatially_contiguous():
    # THE conversion check: offset->axial q = c - (r-(r&1))//2 must make every
    # sub7 flower a compact 7-hex cluster. A wrong map still yields groups of 7
    # but geometrically scattered, so we assert on inter-member distance.
    base_s = 60
    cells = _engine()._grout_cells_hexagon(600, 600, base_s)
    groups = {}
    for poly, g2, _ in cells:
        groups.setdefault(g2, []).append(_centroid(poly))

    full = [pts for pts in groups.values() if len(pts) == 7]
    assert full, "expected at least one complete 7-flower"
    # a correct flower spans two hex steps (opposite neighbours ~2*base_s apart)
    for pts in full:
        dmax = max(math.hypot(a[0] - b[0], a[1] - b[1])
                   for a in pts for b in pts)
        assert dmax < 2.5 * base_s, f"flower not contiguous: span {dmax:.1f}"


def test_hexagon_level3_is_sub7_of_level2():
    cells = _engine()._grout_cells_hexagon(600, 600, 60)
    # each level-3 group gathers up to 7 level-2 flowers -> up to 49 hexes
    l3 = Counter(g3 for _, _, g3 in cells)
    assert max(l3.values()) <= 49


def test_triangle_owner_groups_are_hexagons_of_six():
    cells = _engine()._grout_cells_triangle(600, 600, 80)
    assert cells and all(len(poly) == 3 for poly, _, _ in cells)
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 6            # 6 triangles meet at a class-0 corner


def test_kites_level2_is_parent_hexagon_of_six():
    cells = _engine()._grout_cells_kites(600, 600, 80)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    l2 = Counter(g2 for _, g2, _ in cells)
    assert max(l2.values()) == 6            # 6 kites per hexagon


def test_unsupported_shapes_return_none():
    e = _engine()
    # only shapes absent from the SHAPE_MODES registry hit the dispatcher's
    # default None path (the caller then skips the pass).
    for shape in ("penrose", "girih"):
        assert e._grout_cells(shape, 400, 300, 100) is None, shape


def test_polygon_registry_shapes_get_flat_cells():
    # Registry polygon shapes without an explicit branch fall through to the
    # generic case: their SHAPE_MODES generator re-yields the tile polygons as
    # flat cells (uniform group ids -> L1 seams, L3 frame).
    e = _engine()
    for shape in ("voronoi", "phyllotaxis", "sunflower_grande", "rhombs_star"):
        cells = e._grout_cells(shape, 400, 300, 100)
        assert cells, shape
        assert all(len(poly) >= 3 for poly, _, _ in cells), shape
        assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}, shape


def test_polygon_grout_cells_match_render_geometry():
    # The grout pass re-runs the same generator with the same dimensions, so
    # the cells must be identical polys to what the render used (seeded
    # voronoi included) — grout lines land exactly on the tile seams.
    from src.engine_smart import SHAPE_MODES
    e = _engine()
    for shape in ("voronoi", "sunflower_grande"):
        gen_polys = [list(p) for p in
                     SHAPE_MODES[shape].generator(e, 400, 300, 100)]
        cells = e._grout_cells(shape, 400, 300, 100)
        assert [poly for poly, _, _ in cells] == gen_polys, shape


def test_spectre_flat_cells_share_one_group():
    # Flat grout: every spectre monotile carries the SAME (g2, g3) so
    # classify_edges leaves interior seams at L1 and only the frame boundary at
    # L3. A per-tile group id here would silently promote every seam to L3.
    cells = _engine()._grout_cells("spectre", 600, 600, 60)
    assert cells, "spectre grout cells missing"
    assert all(len(poly) >= 3 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}


def test_romb_flat_cells_share_one_group():
    cells = _engine()._grout_cells("romb", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}


def test_romb_adjacent_diamonds_share_edges():
    # THE float-th check: with tile_h = FLOAT base_s*1.5 the diamonds tessellate
    # and interior seams are shared -> classify_edges puts them at L1. If tile_h
    # were int()-truncated the seams would split by <1 px, every edge would be a
    # frame boundary (L3) and L1 would be nearly empty. Assert L1 dominates.
    cells = _engine()._grout_cells("romb", 600, 600, 60)
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3]), (
        f"interior seams not shared: L1={len(by_level[1])} L3={len(by_level[3])} "
        f"(tile_h likely truncated to int)")


def test_rectangle_3x1_flat_cells_share_one_group():
    cells = _engine()._grout_cells("rectangle_3x1", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    # clean abutting grid: interior edges shared (L1), only the true frame is L3
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3])


def test_brick_wall_flat_cells_share_one_group():
    # brick_wall's half-brick offset means horizontal mortar meets vertical
    # edges at T-junctions, so those seams are not shared (they land at L3). That
    # is fine for flat grout -- assert only the uniform group id and that the
    # bricks are the right 2:1 shape (tile_h = base_s//2).
    cells = _engine()._grout_cells("brick_wall", 600, 600, 60)
    assert cells and all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    w = cells[0][0][1][0] - cells[0][0][0][0]
    h = cells[0][0][2][1] - cells[0][0][1][1]
    assert w == 60 and h == 30


def test_hexagon_romb_three_rhombi_per_hexagon():
    # Variant 2: each hexagon becomes three rhombi (its three composite photos)
    # that share the centre vertex -> an internal "Y". Cells come in triples
    # whose first vertex is that shared centre.
    cells = _engine()._grout_cells("hexagon_romb", 600, 600, 60)
    assert cells and len(cells) % 3 == 0
    assert all(len(poly) == 4 for poly, _, _ in cells)
    assert {(g2, g3) for _, g2, g3 in cells} == {(0, 0)}
    for k in range(0, len(cells), 3):
        c0 = cells[k][0][0]
        assert cells[k + 1][0][0] == c0 and cells[k + 2][0][0] == c0


def test_hexagon_romb_edges_are_shared():
    # Internal spokes (shared by two rhombi of one hexagon) and outer edges
    # (shared by adjacent hexagons) must land at L1; wrong th would split the
    # outer edges into frame boundaries. Assert L1 dominates.
    cells = _engine()._grout_cells("hexagon_romb", 600, 600, 60)
    by_level = classify_edges(cells)
    assert len(by_level[1]) > len(by_level[3])


# ---------------------------------------------------------------------------
# render integration: overlay semantics
# ---------------------------------------------------------------------------
def _small_engine(tmp_path):
    paths, feats = _build_library(tmp_path)
    e = _engine()
    e.paths = paths
    e.features = feats
    e.settings = {"allow_mirror": False, "edge_aware": False, "freq_penalty": 30.0}
    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    return e


def _preview(e, tmp_path, shape, grout_preset=None):
    tgt = _make_target()
    p = tmp_path / "target.png"
    tgt.save(p)
    return e.render_preview(str(p), short_edge=200, shape_mode=shape,
                            tile_scale=1.0, grout_preset=grout_preset)


def test_grout_none_is_identical_to_baseline(tmp_path):
    e = _small_engine(tmp_path)
    base = _preview(e, tmp_path, "square", grout_preset=None)
    again = _preview(e, tmp_path, "square", grout_preset=None)
    assert np.array_equal(np.asarray(base), np.asarray(again))


def test_grout_preset_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "square", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "square", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_spectre_adds_black_lines(tmp_path):
    # Flat grout on an aperiodic shape: no grouping, but the seams still get a
    # uniform-width overlay, so the grouted render differs from the baseline and
    # gains black pixels.
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "spectre", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "spectre", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_romb_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "romb", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "romb", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_rectangle_3x1_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "rectangle_3x1", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "rectangle_3x1", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_brick_wall_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "brick_wall", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "brick_wall", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_hexagon_romb_adds_black_lines(tmp_path):
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "hexagon_romb", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "hexagon_romb", grout_preset="thick"))
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_flat_voronoi_adds_black_lines(tmp_path):
    # A registry polygon shape (generic grout branch): seams get the flat
    # uniform-width overlay, same semantics as spectre/romb above.
    e = _small_engine(tmp_path)
    base = np.asarray(_preview(e, tmp_path, "voronoi", grout_preset=None))
    grouted = np.asarray(_preview(e, tmp_path, "voronoi", grout_preset="thick"))
    assert base.shape == grouted.shape
    assert not np.array_equal(base, grouted)
    near_black = lambda a: int((a.sum(axis=2) < 30).sum())
    assert near_black(grouted) > near_black(base)


def test_grout_is_noop_for_unsupported_shape():
    # A shape with no grout geometry leaves the mosaic untouched (the None path
    # in _apply_grout). Checked directly on a blank canvas -- no render needed.
    e = _engine()
    img = Image.new("RGB", (200, 150), "white")
    before = np.asarray(img).copy()
    e._apply_grout(img, "penrose", 200, 150, 60, "medium")
    assert np.array_equal(before, np.asarray(img))
