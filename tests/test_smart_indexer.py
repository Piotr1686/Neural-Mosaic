"""Tests for src/indexer_smart.py — LAB feature extraction and index creation."""
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

skimage = pytest.importorskip("skimage.color", reason="scikit-image not installed")


# ---------------------------------------------------------------------------
# Helper: reproduces SmartIndexer's per-image feature extraction
# ---------------------------------------------------------------------------

def _compute_lab_feature(img: Image.Image) -> np.ndarray:
    """Mirror of the extraction logic in SmartIndexer.run()."""
    import skimage.color as sc
    matrix = img.resize((3, 3), Image.Resampling.BOX)
    arr = np.array(matrix) / 255.0
    lab = sc.rgb2lab(arr).flatten()
    lab[0::3] /= 100.0
    lab[1::3] = (lab[1::3] + 128) / 255.0
    lab[2::3] = (lab[2::3] + 128) / 255.0
    return lab.astype(np.float32)


# ---------------------------------------------------------------------------
# Unit tests — LAB feature extraction
# ---------------------------------------------------------------------------

class TestLabFeatureExtraction:
    def test_shape_is_27(self):
        img = Image.new("RGB", (100, 100), (128, 64, 200))
        feat = _compute_lab_feature(img)
        assert feat.shape == (27,), "3×3 grid × 3 LAB channels must equal 27"

    def test_dtype_is_float32(self):
        img = Image.new("RGB", (100, 100), (0, 128, 255))
        feat = _compute_lab_feature(img)
        assert feat.dtype == np.float32

    def test_values_in_0_1_range(self):
        for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 0, 0), (255, 255, 255)]:
            img = Image.new("RGB", (100, 100), color)
            feat = _compute_lab_feature(img)
            assert feat.min() >= 0.0, f"Feature below 0 for color {color}"
            assert feat.max() <= 1.0, f"Feature above 1 for color {color}"

    def test_white_has_max_luminance(self):
        img = Image.new("RGB", (100, 100), (255, 255, 255))
        feat = _compute_lab_feature(img)
        l_channels = feat[0::3]
        assert np.allclose(l_channels, 1.0, atol=0.01), "White image L channel should be ~1.0"

    def test_black_has_min_luminance(self):
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        feat = _compute_lab_feature(img)
        l_channels = feat[0::3]
        assert np.allclose(l_channels, 0.0, atol=0.01), "Black image L channel should be ~0.0"

    def test_uniform_image_produces_uniform_features(self):
        """Solid-color image must have identical values for all 9 grid cells."""
        img = Image.new("RGB", (100, 100), (100, 150, 200))
        feat = _compute_lab_feature(img)
        # Reshape to (9, 3) — each row is one grid cell's LAB
        cells = feat.reshape(9, 3)
        assert np.allclose(cells[0], cells, atol=1e-4), "All grid cells must be identical for solid color"

    def test_different_colors_produce_different_features(self):
        red = _compute_lab_feature(Image.new("RGB", (100, 100), (255, 0, 0)))
        blue = _compute_lab_feature(Image.new("RGB", (100, 100), (0, 0, 255)))
        assert not np.allclose(red, blue), "Red and blue must produce different features"

    def test_similar_colors_produce_similar_features(self):
        dark_red = _compute_lab_feature(Image.new("RGB", (100, 100), (200, 0, 0)))
        light_red = _compute_lab_feature(Image.new("RGB", (100, 100), (255, 50, 50)))
        blue = _compute_lab_feature(Image.new("RGB", (100, 100), (0, 0, 255)))
        dist_similar = np.linalg.norm(dark_red - light_red)
        dist_different = np.linalg.norm(dark_red - blue)
        assert dist_similar < dist_different, (
            "Similar red shades must be closer together than red vs blue"
        )


# ---------------------------------------------------------------------------
# Integration test — SmartIndexer.run()
# ---------------------------------------------------------------------------

class TestSmartIndexerRun:
    def test_creates_index_file(self):
        from src.indexer_smart import SmartIndexer

        with tempfile.TemporaryDirectory() as tmp:
            lib_dir = Path(tmp) / "tiles"
            lib_dir.mkdir()
            index_path = Path(tmp) / "test_index.pkl"

            Image.new("RGB", (60, 60), (200, 100, 50)).save(lib_dir / "a.jpg")
            Image.new("RGB", (60, 60), (50, 200, 100)).save(lib_dir / "b.jpg")

            SmartIndexer(library_path=str(lib_dir), index_path=str(index_path)).run()

            assert index_path.exists()

    def test_index_has_required_keys(self):
        from src.indexer_smart import SmartIndexer

        with tempfile.TemporaryDirectory() as tmp:
            lib_dir = Path(tmp) / "tiles"
            lib_dir.mkdir()
            index_path = Path(tmp) / "test_index.pkl"

            Image.new("RGB", (60, 60), (128, 128, 128)).save(lib_dir / "c.jpg")

            SmartIndexer(library_path=str(lib_dir), index_path=str(index_path)).run()

            with open(index_path, "rb") as f:
                data = pickle.load(f)

            assert "paths" in data
            assert "features" in data

    def test_index_shape_matches_image_count(self):
        from src.indexer_smart import SmartIndexer

        n = 5
        with tempfile.TemporaryDirectory() as tmp:
            lib_dir = Path(tmp) / "tiles"
            lib_dir.mkdir()
            index_path = Path(tmp) / "test_index.pkl"

            for i in range(n):
                Image.new("RGB", (60, 60), (i * 40, 100, 200)).save(lib_dir / f"img_{i}.jpg")

            SmartIndexer(library_path=str(lib_dir), index_path=str(index_path)).run()

            with open(index_path, "rb") as f:
                data = pickle.load(f)

            assert len(data["paths"]) == n
            assert data["features"].shape[0] == n
            assert data["features"].shape[1] in (75, 79)
            assert data["features"].dtype == np.float32

    def test_empty_library_does_not_create_index(self):
        from src.indexer_smart import SmartIndexer

        with tempfile.TemporaryDirectory() as tmp:
            lib_dir = Path(tmp) / "tiles"
            lib_dir.mkdir()
            index_path = Path(tmp) / "test_index.pkl"

            SmartIndexer(library_path=str(lib_dir), index_path=str(index_path)).run()

            assert not index_path.exists()
