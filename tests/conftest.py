"""Shared pytest fixtures for the Neural-Mosaic test suite.

IMPORTANT: os.environ must be patched before any torch import.
KMP_DUPLICATE_LIB_OK is required on Windows with MKL + OpenMP to prevent
a fatal abort when both Intel MKL and libgomp try to initialise OpenMP.
This module-level assignment runs first because pytest loads conftest.py
before it collects and imports any test files.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import pickle
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture
def solid_image():
    """Factory: create a solid-colour PIL image of any size, colour, and mode."""
    def _make(width=100, height=100, color=(128, 128, 128), mode="RGB"):
        return Image.new(mode, (width, height), color)
    return _make


@pytest.fixture
def sample_rgb_image():
    """A 200×150 RGB image with a simple colour gradient (no real file needed)."""
    arr = np.zeros((150, 200, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, 200, dtype=np.uint8)          # R: left→right
    arr[:, :, 1] = np.linspace(0, 255, 150, dtype=np.uint8)[:, None] # G: top→bottom
    return Image.fromarray(arr)


@pytest.fixture
def tiny_tile_library(tmp_path):
    """Minimal tile library: 3 solid-colour JPEGs + an index output path.

    Returns:
        (lib_dir: Path, index_path: Path)
    """
    lib_dir = tmp_path / "tiles"
    lib_dir.mkdir()
    index_path = tmp_path / "smart_index.pkl"

    for i, color in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
        Image.new("RGB", (60, 60), color).save(lib_dir / f"tile_{i}.jpg")

    return lib_dir, index_path


@pytest.fixture
def prebuilt_smart_index(tmp_path):
    """A pre-built smart index (27-dim features, 3 tiles) written to a temp file."""
    features = np.random.rand(3, 27).astype(np.float32)
    paths = [str(tmp_path / f"tile_{i}.jpg") for i in range(3)]
    index_path = tmp_path / "smart_index.pkl"
    with open(index_path, "wb") as fh:
        pickle.dump({"paths": paths, "features": features}, fh)
    return index_path


@pytest.fixture
def nonexistent_index(tmp_path):
    """Path that points to a missing index file (useful for fallback tests)."""
    return tmp_path / "missing_index.pkl"
