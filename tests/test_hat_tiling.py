"""Tests for src/hat_tiling.py and the einstein_hat mode of SmartEngine.

All assertions are geometric/numeric; output is ASCII-only (CP1250 console).
"""
import threading

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.hat_tiling import HAT_OUTLINE, HatPlacement, generate_hat_tiling
from src.engine_smart import SmartEngine


def _shoelace(pts):
    acc = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        acc += x1 * y2 - x2 * y1
    return abs(acc) / 2.0


# ---------------------------------------------------------------------------
# Hat geometry
# ---------------------------------------------------------------------------

class TestHatOutline:
    def test_has_13_vertices(self):
        assert len(HAT_OUTLINE) == 13

    def test_positive_area(self):
        assert _shoelace(HAT_OUTLINE) > 0.0


# ---------------------------------------------------------------------------
# Tiling generation
# ---------------------------------------------------------------------------

class TestGenerateHatTiling:
    def test_rejects_non_positive_dimensions(self):
        with pytest.raises(ValueError):
            generate_hat_tiling(0, 100, 50)
        with pytest.raises(ValueError):
            generate_hat_tiling(100, -1, 50)

    def test_returns_hat_placements(self):
        hats = generate_hat_tiling(400, 300, 60)
        assert len(hats) > 0
        assert all(isinstance(h, HatPlacement) for h in hats)
        assert all(len(h.points) == 13 for h in hats)

    def test_full_rectangle_coverage(self):
        """Every pixel of the target rectangle is covered by some hat."""
        w, h = 800, 600
        hats = generate_hat_tiling(w, h, 60)
        acc = np.zeros((h, w), dtype=np.int32)
        for hat in hats:
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).polygon(list(hat.points), fill=1)
            acc += np.asarray(m, dtype=np.int32)
        assert int((acc == 0).sum()) == 0

    def test_overlap_limited_to_raster_boundaries(self):
        """Hats are edge-to-edge: only thin rasterised seams may overlap."""
        w, h = 800, 600
        hats = generate_hat_tiling(w, h, 60)
        acc = np.zeros((h, w), dtype=np.int32)
        for hat in hats:
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).polygon(list(hat.points), fill=1)
            acc += np.asarray(m, dtype=np.int32)
        overlap_fraction = float((acc > 1).sum()) / acc.size
        assert overlap_fraction < 0.05

    def test_hat_area_matches_hat_size(self):
        """Each hat covers ~hat_size**2 px (parity with square tiles)."""
        hat_size = 60
        hats = generate_hat_tiling(500, 400, hat_size)
        areas = [_shoelace(h.points) for h in hats]
        mean_area = sum(areas) / len(areas)
        assert mean_area == pytest.approx(hat_size ** 2, rel=0.01)

    def test_mirrored_anti_hats_present(self):
        """The aperiodic tiling requires reflected hats (ratio about 1:7)."""
        hats = generate_hat_tiling(1000, 800, 50)
        frac = sum(1 for h in hats if h.mirrored) / len(hats)
        assert 0.05 < frac < 0.25

    def test_deterministic(self):
        a = generate_hat_tiling(400, 300, 60)
        b = generate_hat_tiling(400, 300, 60)
        assert a == b

    def test_smaller_hats_mean_more_hats(self):
        few = generate_hat_tiling(600, 400, 80)
        many = generate_hat_tiling(600, 400, 40)
        assert len(many) > len(few) * 2


# ---------------------------------------------------------------------------
# SmartEngine integration (einstein_hat shape mode)
# ---------------------------------------------------------------------------

@pytest.fixture
def mini_engine(tmp_path):
    """SmartEngine with a tiny synthetic in-memory index (no pkl on disk)."""
    engine = SmartEngine(index_path="__nonexistent_test_index__.pkl")
    colors = [(220, 40, 40), (40, 180, 60), (50, 80, 220), (240, 220, 60),
              (240, 240, 240), (20, 20, 20), (160, 60, 200), (60, 200, 200)]
    paths, feats = [], []
    for i, col in enumerate(colors):
        p = tmp_path / f"tile_{i}.png"
        img = Image.new("RGB", (100, 100), col)
        img.save(p)
        paths.append(str(p))
        feats.append(engine._compute_sector_feature(img, edge_aware=False))
    engine.paths = paths
    engine.features = np.stack(feats)
    engine.settings = {"allow_mirror": False, "edge_aware": False,
                       "tile_size": 100, "freq_penalty": 30.0}
    # __init__ skips these on FileNotFoundError; restore them like the
    # fixture in test_smart_engine.py restores settings.
    engine._neighbors_cache = {}
    engine._neighbors_lock = threading.Lock()
    return engine


class TestEinsteinHatRender:
    def test_do_render_einstein_hat(self, mini_engine):
        target = Image.new("RGB", (320, 240))
        px = target.load()
        for y in range(240):
            for x in range(320):
                px[x, y] = (x * 255 // 320, y * 255 // 240, 128)
        result = mini_engine._do_render(target, "einstein_hat", tile_scale=0.5)
        assert result.size == (320, 240)
        arr = np.asarray(result)
        # Mosaic must be fully painted: no residual black background.
        black = np.all(arr < 8, axis=2)
        assert float(black.mean()) < 0.01
