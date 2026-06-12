"""Tests for src/spectre_tiling.py and the spectre mode of SmartEngine.

All assertions are geometric/numeric; output is ASCII-only (CP1250 console).
"""
import threading

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.spectre_tiling import (
    SPECTRE_OUTLINE,
    SpectrePlacement,
    generate_spectre_tiling,
)
from src.engine_smart import SmartEngine


def _shoelace(pts):
    acc = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        acc += x1 * y2 - x2 * y1
    return abs(acc) / 2.0


# ---------------------------------------------------------------------------
# Spectre geometry
# ---------------------------------------------------------------------------

class TestSpectreOutline:
    def test_has_14_vertices(self):
        assert len(SPECTRE_OUTLINE) == 14

    def test_all_edges_unit_length(self):
        """Tile(1,1): every edge of the spectre has the same length."""
        n = len(SPECTRE_OUTLINE)
        for i in range(n):
            x1, y1 = SPECTRE_OUTLINE[i]
            x2, y2 = SPECTRE_OUTLINE[(i + 1) % n]
            assert ((x2 - x1) ** 2 + (y2 - y1) ** 2) == pytest.approx(1.0)

    def test_positive_area(self):
        assert _shoelace(SPECTRE_OUTLINE) > 0.0


# ---------------------------------------------------------------------------
# Tiling generation
# ---------------------------------------------------------------------------

class TestGenerateSpectreTiling:
    def test_rejects_non_positive_dimensions(self):
        with pytest.raises(ValueError):
            generate_spectre_tiling(0, 100, 50)
        with pytest.raises(ValueError):
            generate_spectre_tiling(100, -1, 50)

    def test_returns_spectre_placements(self):
        tiles = generate_spectre_tiling(400, 300, 60)
        assert len(tiles) > 0
        assert all(isinstance(t, SpectrePlacement) for t in tiles)
        assert all(len(t.points) == 14 for t in tiles)

    def test_full_rectangle_coverage(self):
        """Every pixel of the target rectangle is covered by some spectre."""
        w, h = 800, 600
        tiles = generate_spectre_tiling(w, h, 60)
        acc = np.zeros((h, w), dtype=np.int32)
        for t in tiles:
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).polygon(list(t.points), fill=1)
            acc += np.asarray(m, dtype=np.int32)
        assert int((acc == 0).sum()) == 0

    def test_overlap_limited_to_raster_boundaries(self):
        """Spectres are edge-to-edge: only thin rasterised seams overlap."""
        w, h = 800, 600
        tiles = generate_spectre_tiling(w, h, 60)
        acc = np.zeros((h, w), dtype=np.int32)
        for t in tiles:
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).polygon(list(t.points), fill=1)
            acc += np.asarray(m, dtype=np.int32)
        overlap_fraction = float((acc > 1).sum()) / acc.size
        assert overlap_fraction < 0.05

    def test_full_coverage_at_8k_dimensions(self):
        """Regression guard mirroring the einstein-hat 8K coverage test."""
        w, h, k = 7680, 5760, 4  # rasterised at 1/4 scale
        tiles = generate_spectre_tiling(w, h, 100)
        acc = Image.new("L", (w // k, h // k), 0)
        draw = ImageDraw.Draw(acc)
        for t in tiles:
            draw.polygon([(x / k, y / k) for x, y in t.points], fill=255)
        assert int((np.asarray(acc) == 0).sum()) == 0

    def test_tile_area_matches_tile_size(self):
        """Each spectre covers ~tile_size**2 px (parity with square tiles)."""
        tile_size = 60
        tiles = generate_spectre_tiling(500, 400, tile_size)
        areas = [_shoelace(t.points) for t in tiles]
        mean_area = sum(areas) / len(areas)
        assert mean_area == pytest.approx(tile_size ** 2, rel=0.01)

    def test_strictly_chiral(self):
        """The defining spectre property: one handedness per tiling."""
        for size in (40, 60, 100):
            tiles = generate_spectre_tiling(900, 700, size)
            assert len(set(t.mirrored for t in tiles)) == 1

    def test_deterministic(self):
        a = generate_spectre_tiling(400, 300, 60)
        b = generate_spectre_tiling(400, 300, 60)
        assert a == b

    def test_smaller_tiles_mean_more_tiles(self):
        few = generate_spectre_tiling(600, 400, 80)
        many = generate_spectre_tiling(600, 400, 40)
        assert len(many) > len(few) * 2


# ---------------------------------------------------------------------------
# SmartEngine integration (spectre shape mode)
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


class TestSpectreRender:
    def test_do_render_spectre(self, mini_engine):
        target = Image.new("RGB", (320, 240))
        px = target.load()
        for y in range(240):
            for x in range(320):
                px[x, y] = (x * 255 // 320, y * 255 // 240, 128)
        result = mini_engine._do_render(target, "spectre", tile_scale=0.5)
        assert result.size == (320, 240)
        arr = np.asarray(result)
        # Mosaic must be fully painted: no residual black background.
        black = np.all(arr < 8, axis=2)
        assert float(black.mean()) < 0.01
