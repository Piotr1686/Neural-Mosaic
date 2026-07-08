"""Unit tests for SmartEngine._mask_cell_weights (masked top-K re-scoring).

The matching loop re-scores GEMM top-K candidates with a weighted Euclidean
distance whose per-cell weights come from the tile mask (see _do_render).
These tests lock the helper's contract:

* full-canvas mask  -> None (caller skips re-scoring; square stays bit-exact),
* partial mask      -> coverage-proportional weights, mean-normalised to 1.0,
* weight order      -> must match the (5, 5, 3) flatten order of
                       _compute_sector_feature (cell-major, x3 LAB channels),
* edge_aware        -> 4 extra dims appended with weight exactly 1.0,
* degenerate mask   -> None (fall back to unweighted matching).
"""
import numpy as np
from PIL import Image, ImageDraw

from src.engine_smart import SmartEngine

W = SmartEngine._mask_cell_weights


def _full_mask(w=75, h=75):
    return Image.new("L", (w, h), 255)


def _triangle_mask(w=75, h=75):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(w / 2, 0), (w - 1, h - 1), (0, h - 1)], fill=255)
    return m


def test_full_mask_returns_none():
    assert W(_full_mask(), edge_aware=False) is None


def test_empty_mask_returns_none():
    assert W(Image.new("L", (75, 75), 0), edge_aware=False) is None


def test_triangle_weights_shape_and_normalisation():
    w = W(_triangle_mask(), edge_aware=False)
    assert w is not None
    assert w.shape == (75,)
    assert w.dtype == np.float32
    # Mean-normalised: sum equals the dimension count.
    assert abs(float(w.sum()) - 75.0) < 1e-3


def test_triangle_corner_below_center():
    w = W(_triangle_mask(), edge_aware=False)
    cells = w.reshape(5, 5, 3)[:, :, 0]  # per-cell weight (identical x3)
    # Top corners of the bbox lie outside the triangle; bottom-center inside.
    assert cells[0, 0] < cells[4, 2]
    assert cells[0, 4] < cells[4, 2]
    # All three LAB channels of a cell share one weight.
    assert np.array_equal(w.reshape(25, 3)[:, 0], w.reshape(25, 3)[:, 1])


def test_weight_order_matches_feature_flatten_order():
    # Only the top-left 5x5 cell (15x15 px of a 75x75 mask) is white ->
    # after mean-normalisation exactly the first 3 entries are non-zero.
    m = Image.new("L", (75, 75), 0)
    ImageDraw.Draw(m).rectangle((0, 0, 14, 14), fill=255)
    w = W(m, edge_aware=False)
    assert w is not None
    assert np.all(w[:3] > 0)
    assert np.all(w[3:] == 0)


def test_edge_aware_appends_unit_weights():
    w = W(_triangle_mask(), edge_aware=True)
    assert w.shape == (79,)
    assert np.array_equal(w[75:], np.ones(4, dtype=np.float32))
    # The 75 cell weights are normalised on their own, not diluted by the 4.
    assert abs(float(w[:75].sum()) - 75.0) < 1e-3
