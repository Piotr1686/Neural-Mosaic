"""Tests for the hi-res tile overlay (Sprint 1, PLAN_HIRES.md).

The overlay lets a sharp copy of a tile in data/tiles_hires/ (keyed by
filename) be pasted instead of the downscaled library original, without
touching the colour-matching path. These tests lock:

* _resolve_tile_path  -> redirects only when the name is in the overlay set,
                         empty set is a no-op, accepts str and Path,
* _load_hires_overlay -> lists files in HIRES_DIR, empty when dir is absent,
                         ignores subdirectories,
* _do_render          -> actually opens the overlay copy (its pixels win),
* invariant           -> data/tiles_hires is NEVER a library source dir.
"""
import threading
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import src.engine_smart as engine_smart
from src.engine_smart import SmartEngine
from src.library_dirs import LIBRARY_DIRS

RESOLVE = SmartEngine._resolve_tile_path
LOAD = SmartEngine._load_hires_overlay


# ---------------------------------------------------------------------------
# _resolve_tile_path
# ---------------------------------------------------------------------------

def test_empty_overlay_returns_original():
    p = "data/library_public/tiles/coco_123.jpg"
    assert RESOLVE(p, set()) == Path(p)


def test_name_in_overlay_redirects_to_hires_dir():
    got = RESOLVE("data/library_public/tiles/coco_123.jpg", {"coco_123.jpg"})
    assert got == engine_smart.HIRES_DIR / "coco_123.jpg"


def test_name_not_in_overlay_untouched():
    p = "data/library_public/tiles/coco_123.jpg"
    assert RESOLVE(p, {"other.jpg"}) == Path(p)


def test_accepts_str_and_path_equivalently():
    s = "data/tiles/tile_000000.jpg"
    assert RESOLVE(s, {"tile_000000.jpg"}) == RESOLVE(Path(s), {"tile_000000.jpg"})


def test_redirect_keyed_by_basename_only():
    # A tile from any library dir maps to the same overlay file by name.
    a = RESOLVE("data/library_public/tiles/x.jpg", {"x.jpg"})
    b = RESOLVE("data/library_private/tiles/x.jpg", {"x.jpg"})
    assert a == b == engine_smart.HIRES_DIR / "x.jpg"


# ---------------------------------------------------------------------------
# _load_hires_overlay
# ---------------------------------------------------------------------------

def test_missing_dir_returns_empty_set(monkeypatch, tmp_path):
    monkeypatch.setattr(engine_smart, "HIRES_DIR", tmp_path / "does_not_exist")
    assert LOAD() == set()


def test_empty_dir_returns_empty_set(monkeypatch, tmp_path):
    monkeypatch.setattr(engine_smart, "HIRES_DIR", tmp_path)
    assert LOAD() == set()


def test_lists_files_ignoring_subdirs(monkeypatch, tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"y")
    (tmp_path / "nested").mkdir()  # must be ignored
    monkeypatch.setattr(engine_smart, "HIRES_DIR", tmp_path)
    assert LOAD() == {"a.jpg", "b.png"}


# ---------------------------------------------------------------------------
# _do_render integration — overlay pixels must win
# ---------------------------------------------------------------------------

def _make_engine(tmp_path, tile_color):
    """SmartEngine with a 4-tile solid-colour library at native res."""
    e = SmartEngine(index_path="__none__.pkl")
    paths, feats = [], []
    for i in range(4):
        p = tmp_path / f"tile_{i:03d}.png"
        Image.new("RGB", (120, 120), tile_color).save(p)
        paths.append(str(p))
        feats.append(e._compute_sector_feature(
            Image.new("RGB", (120, 120), tile_color), edge_aware=True))
    e.paths = paths
    e.features = np.array(feats, dtype=np.float32)
    e.settings = {"allow_mirror": True, "edge_aware": False, "freq_penalty": 30.0}
    return e


def _target(w=192, h=144):
    return Image.new("RGB", (w, h), (90, 90, 90))


def test_render_uses_overlay_copy(monkeypatch, tmp_path):
    """With every library tile shadowed by a red overlay, the square-mode
    mosaic is composed of the red copies — proving the overlay path is taken."""
    lib = tmp_path / "lib"
    lib.mkdir()
    engine = _make_engine(lib, tile_color=(20, 20, 20))  # dark grey library

    engine._neighbors_cache = {}
    engine._neighbors_lock = threading.Lock()
    baseline = engine._do_render(_target(), "square", tile_scale=0.5)

    # Overlay: same basenames, pure red content.
    overlay = tmp_path / "tiles_hires"
    overlay.mkdir()
    for p in engine.paths:
        Image.new("RGB", (120, 120), (255, 0, 0)).save(overlay / Path(p).name)
    monkeypatch.setattr(engine_smart, "HIRES_DIR", overlay)

    engine._neighbors_cache = {}
    engine._neighbors_lock = threading.Lock()
    with_overlay = engine._do_render(_target(), "square", tile_scale=0.5)

    assert with_overlay.tobytes() != baseline.tobytes()
    # Centre of a full-canvas square render is a solid tile => red overlay wins.
    arr = np.array(with_overlay.convert("RGB"))
    cy, cx = arr.shape[0] // 2, arr.shape[1] // 2
    r, g, b = arr[cy, cx]
    assert r > 200 and g < 60 and b < 60, f"centre not red: {(r, g, b)}"


def test_absent_overlay_matches_no_overlay(monkeypatch, tmp_path):
    """A missing overlay dir must render identically to having no overlay
    logic at all (golden invariant: bit-for-bit unchanged)."""
    lib = tmp_path / "lib"
    lib.mkdir()
    engine = _make_engine(lib, tile_color=(20, 20, 20))

    monkeypatch.setattr(engine_smart, "HIRES_DIR", tmp_path / "absent")
    engine._neighbors_cache = {}
    engine._neighbors_lock = threading.Lock()
    a = engine._do_render(_target(), "square", tile_scale=0.5)

    monkeypatch.setattr(engine_smart, "HIRES_DIR", tmp_path / "also_absent")
    engine._neighbors_cache = {}
    engine._neighbors_lock = threading.Lock()
    b = engine._do_render(_target(), "square", tile_scale=0.5)

    assert a.tobytes() == b.tobytes()


# ---------------------------------------------------------------------------
# Invariant: the overlay dir is never a library source
# ---------------------------------------------------------------------------

def test_hires_dir_not_in_library_dirs():
    assert engine_smart.HIRES_DIR.name == "tiles_hires"
    names = {p.name for p in LIBRARY_DIRS}
    assert "tiles_hires" not in names
    hires_resolved = engine_smart.HIRES_DIR.resolve()
    repo_root = engine_smart.HIRES_DIR.parents[1]
    for p in LIBRARY_DIRS:
        assert (repo_root / p).resolve() != hires_resolved
