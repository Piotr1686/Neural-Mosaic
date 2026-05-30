"""Tests for src/engine_smart.py — _smart_crop and _get_shape_mask."""
import numpy as np
import pytest
from PIL import Image

from src.engine_smart import SmartEngine


@pytest.fixture
def engine():
    """Minimal SmartEngine without an index file.

    SmartEngine.__init__ silently catches FileNotFoundError but does not
    set self.settings in that branch — we add it manually so helper
    methods are testable without a real index on disk.
    """
    e = SmartEngine(index_path="__nonexistent_test_index__.pkl")
    e.settings = {"allow_mirror": True, "tile_size": 100, "freq_penalty": 30.0}
    return e


# ---------------------------------------------------------------------------
# _smart_crop
# ---------------------------------------------------------------------------

class TestSmartCrop:
    def test_output_dimensions_match_target(self, engine):
        img = Image.new("RGB", (300, 200))
        result = engine._smart_crop(img, 80, 60)
        assert result.size == (80, 60)

    def test_landscape_source_to_square_target(self, engine):
        img = Image.new("RGB", (400, 100))
        result = engine._smart_crop(img, 100, 100)
        assert result.size == (100, 100)

    def test_portrait_source_to_square_target(self, engine):
        img = Image.new("RGB", (100, 400))
        result = engine._smart_crop(img, 100, 100)
        assert result.size == (100, 100)

    def test_square_source_to_landscape_target(self, engine):
        img = Image.new("RGB", (200, 200))
        result = engine._smart_crop(img, 200, 100)
        assert result.size == (200, 100)

    def test_same_ratio_preserves_content(self, engine):
        """Crop with identical aspect ratio should not distort the image."""
        img = Image.new("RGB", (200, 100), (255, 0, 0))
        result = engine._smart_crop(img, 100, 50)
        assert result.size == (100, 50)

    def test_preserves_image_mode_rgb(self, engine):
        img = Image.new("RGB", (200, 100))
        assert engine._smart_crop(img, 50, 50).mode == "RGB"

    def test_preserves_image_mode_rgba(self, engine):
        img = Image.new("RGBA", (200, 100))
        assert engine._smart_crop(img, 50, 50).mode == "RGBA"

    def test_center_crop_keeps_center_color(self, engine):
        """Solid-color image: crop result should have the same color."""
        img = Image.new("RGB", (300, 100), (0, 128, 255))
        result = engine._smart_crop(img, 60, 60)
        pixel = result.getpixel((30, 30))
        assert pixel == (0, 128, 255)


# ---------------------------------------------------------------------------
# _get_shape_mask
# ---------------------------------------------------------------------------

class TestGetShapeMask:
    @pytest.mark.parametrize("shape", ["square", "rectangle_3x1", "brick_wall"])
    def test_rectangular_output_size(self, engine, shape):
        mask = engine._get_shape_mask(shape, 100, 80)
        assert mask.size == (100, 80)
        assert mask.mode == "L"

    @pytest.mark.parametrize("shape", ["square", "rectangle_3x1", "brick_wall"])
    def test_rectangular_mask_is_fully_filled(self, engine, shape):
        """Rectangular shapes with default padding should be nearly all white."""
        mask = engine._get_shape_mask(shape, 100, 100)
        arr = np.array(mask)
        assert arr.max() == 255
        assert arr.mean() > 200

    def test_hexagon_output_size(self, engine):
        mask = engine._get_shape_mask("hexagon", 100, 120)
        assert mask.size == (100, 120)
        assert mask.mode == "L"

    def test_hexagon_corners_are_transparent(self, engine):
        """Hexagon cuts off the four corners — they must be black."""
        mask = engine._get_shape_mask("hexagon", 120, 120)
        arr = np.array(mask)
        assert arr[0, 0] == 0,   "top-left corner should be black"
        assert arr[0, -1] == 0,  "top-right corner should be black"
        assert arr[-1, 0] == 0,  "bottom-left corner should be black"
        assert arr[-1, -1] == 0, "bottom-right corner should be black"

    def test_hexagon_center_is_filled(self, engine):
        mask = engine._get_shape_mask("hexagon", 120, 120)
        arr = np.array(mask)
        cx, cy = arr.shape[1] // 2, arr.shape[0] // 2
        assert arr[cy, cx] == 255, "center of hexagon mask must be white"

    def test_triangle_output_size(self, engine):
        mask = engine._get_shape_mask("triangle", 100, 87)
        assert mask.size == (100, 87)

    def test_triangle_has_transparent_areas(self, engine):
        mask = engine._get_shape_mask("triangle", 100, 100)
        arr = np.array(mask)
        assert arr.min() == 0,   "triangle corners should be transparent"
        assert arr.max() == 255, "triangle body should be filled"

    def test_flipped_triangle_differs_from_normal(self, engine):
        norm = np.array(engine._get_shape_mask("triangle", 100, 87, flipped=False))
        flip = np.array(engine._get_shape_mask("triangle", 100, 87, flipped=True))
        assert not np.array_equal(norm, flip), "flipped triangle must differ from normal"

    def test_romb_has_transparent_corners(self, engine):
        mask = engine._get_shape_mask("romb", 100, 100)
        arr = np.array(mask)
        assert arr[0, 0] == 0
        assert arr[0, -1] == 0
        assert arr[-1, 0] == 0
        assert arr[-1, -1] == 0

    def test_padding_reduces_filled_area(self, engine):
        full = np.array(engine._get_shape_mask("square", 100, 100, padding=1.0))
        small = np.array(engine._get_shape_mask("square", 100, 100, padding=0.5))
        assert small.sum() < full.sum(), "smaller padding should reduce filled area"

    @pytest.mark.parametrize("shape", ["mask_top", "mask_left", "mask_right"])
    def test_hexagon_romb_submasks_have_correct_size(self, engine, shape):
        mask = engine._get_shape_mask(shape, 100, 100)
        assert mask.size == (100, 100)
        assert mask.mode == "L"
        arr = np.array(mask)
        assert arr.max() == 255
        assert arr.min() == 0


# ---------------------------------------------------------------------------
# _get_kite_poly / _transform_kite_index (kite geometry math)
# ---------------------------------------------------------------------------

class TestKiteMath:
    def test_kite_poly_returns_four_points(self, engine):
        poly = engine._get_kite_poly(0, 0, 50, 0)
        assert len(poly) == 4

    def test_kite_poly_center_is_first_point(self, engine):
        cx, cy, s = 100, 200, 50
        poly = engine._get_kite_poly(cx, cy, s, 2)
        assert poly[0] == (cx, cy)

    def test_transform_kite_zero_rotation_zero_flip(self, engine):
        """Identity transform: offset only."""
        result = engine._transform_kite_index(1, 2, 3, 10, 20, rot=0, flip=False)
        assert result == (11, 22, 3)

    def test_transform_kite_k_stays_in_range(self, engine):
        for rot in range(6):
            for flip in [True, False]:
                _, _, k = engine._transform_kite_index(0, 0, 0, 0, 0, rot=rot, flip=flip)
                assert 0 <= k < 6, f"k={k} out of range for rot={rot}, flip={flip}"


# ---------------------------------------------------------------------------
# _resolve_matching_modes (edge_aware / allow_mirror conflict guard)
# ---------------------------------------------------------------------------

class TestResolveMatchingModes:
    """edge_aware (79-dim) and allow_mirror (75-dim reshape) are mutually
    exclusive. The engine guard backs up the GUI mutex so a CLI/programmatic
    caller cannot reach the cryptic reshape ValueError."""

    def test_edge_aware_wins_over_mirror(self, engine):
        """Both modes on with a 79-dim index: edge_aware kept, mirror dropped."""
        engine.features = np.zeros((4, 79))
        engine.settings = {"edge_aware": True, "allow_mirror": True}
        assert engine._resolve_matching_modes() == (True, False)

    def test_edge_aware_fallback_when_index_75dim(self, engine):
        """edge_aware requested but index is 75-dim: falls back to standard."""
        engine.features = np.zeros((4, 75))
        engine.settings = {"edge_aware": True, "allow_mirror": False}
        assert engine._resolve_matching_modes() == (False, False)

    def test_mirror_kept_without_edge_aware(self, engine):
        """No edge_aware: allow_mirror survives on a 75-dim index."""
        engine.features = np.zeros((4, 75))
        engine.settings = {"edge_aware": False, "allow_mirror": True}
        assert engine._resolve_matching_modes() == (False, True)

    def test_plain_mode(self, engine):
        """Neither mode requested: both off."""
        engine.features = np.zeros((4, 75))
        engine.settings = {"edge_aware": False, "allow_mirror": False}
        assert engine._resolve_matching_modes() == (False, False)


# ---------------------------------------------------------------------------
# _get_neighbors_map (concurrency-safe cache)
# ---------------------------------------------------------------------------

class TestNeighborsMapCache:
    """The neighbour adjacency cache is mutated from preview render threads.
    The generation token (commit 2a18ec8) gates result delivery but does NOT
    serialise execution, so two _do_render calls can hit the cache-miss path
    concurrently. _get_neighbors_map guards the dict with double-checked
    locking; these tests pin that behaviour without a real index on disk."""

    def _prime(self, engine):
        import threading
        engine._neighbors_cache = {}
        engine._neighbors_lock = threading.Lock()

    def test_miss_computes_and_stores(self, engine):
        self._prime(engine)
        key = (10, "square", 100, 100)
        result = engine._get_neighbors_map(key, [(0, 0), (1, 1)], 5.0)
        assert engine._neighbors_cache[key] is result

    def test_hit_returns_cached_without_recompute(self, engine, monkeypatch):
        """Fast path must not touch cKDTree when the key is already cached."""
        self._prime(engine)
        key = (10, "square", 100, 100)
        sentinel = object()
        engine._neighbors_cache[key] = sentinel

        def _boom(*a, **k):  # pragma: no cover - must never run
            raise AssertionError("cKDTree built on a cache hit")

        monkeypatch.setattr("src.engine_smart.cKDTree", _boom)
        assert engine._get_neighbors_map(key, [(0, 0)], 5.0) is sentinel

    def test_eviction_caps_cache_at_eight(self, engine):
        self._prime(engine)
        for i in range(10):
            engine._get_neighbors_map((i, "square", 100, 100), [(0, 0)], 5.0)
        assert len(engine._neighbors_cache) <= 9

    def test_concurrent_miss_builds_tree_once(self, engine, monkeypatch):
        """Two threads racing the same key must build cKDTree exactly once."""
        import threading
        self._prime(engine)
        key = (10, "square", 100, 100)
        calls = []
        start = threading.Barrier(2)

        class _FakeTree:
            def __init__(self, points):
                calls.append(1)

            def query_ball_tree(self, other, r):
                return [[0]]

        monkeypatch.setattr("src.engine_smart.cKDTree", _FakeTree)

        results = {}

        def worker(name):
            start.wait()
            results[name] = engine._get_neighbors_map(key, [(0, 0)], 5.0)

        t1 = threading.Thread(target=worker, args=("a",))
        t2 = threading.Thread(target=worker, args=("b",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(calls) == 1
        assert results["a"] is results["b"]
