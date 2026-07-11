"""Tests for the used-tiles report (Sprint 2, PLAN_HIRES.md).

create_mosaic dumps <stem>_used_tiles.json listing which library tiles were
actually placed — the selective input for the hi-res upgrade tool (Sprint 3).
These tests lock:

* _used_tiles_report -> only count>0, sorted by count desc then path,
* _write_used_tiles  -> JSON beside the mosaic, correct totals, no-op without
                        counts,
* create_mosaic      -> writes the report only with save_used_tiles=True
                        (opt-in, default OFF); sum of counts is consistent,
* render_preview     -> writes NO file (stays a no-I/O path).
"""
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image

from src.engine_smart import SmartEngine


def _make_engine(tmp_path, colors=((20, 20, 20), (200, 30, 30),
                                   (30, 200, 30), (30, 30, 200))):
    """SmartEngine backed by solid-colour tile files on disk."""
    e = SmartEngine(index_path="__none__.pkl")
    paths, feats = [], []
    for i, col in enumerate(colors):
        p = tmp_path / f"tile_{i:03d}.png"
        Image.new("RGB", (120, 120), col).save(p)
        paths.append(str(p))
        feats.append(e._compute_sector_feature(
            Image.new("RGB", (120, 120), col), edge_aware=True))
    e.paths = paths
    e.features = np.array(feats, dtype=np.float32)
    e.settings = {"allow_mirror": True, "edge_aware": False, "freq_penalty": 30.0}
    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    return e


# ---------------------------------------------------------------------------
# _used_tiles_report
# ---------------------------------------------------------------------------

def test_report_excludes_zero_and_sorts_by_count(tmp_path):
    e = _make_engine(tmp_path)
    report = e._used_tiles_report(np.array([3, 0, 5, 1], dtype=np.int64))
    assert [r["count"] for r in report] == [5, 3, 1]        # desc, zero dropped
    assert report[0]["name"] == "tile_002.png"
    assert all(set(r) == {"path", "name", "count"} for r in report)


def test_report_empty_when_nothing_used(tmp_path):
    e = _make_engine(tmp_path)
    assert e._used_tiles_report(np.zeros(4, dtype=np.int64)) == []


# ---------------------------------------------------------------------------
# _write_used_tiles
# ---------------------------------------------------------------------------

def test_write_creates_json_beside_output(tmp_path):
    e = _make_engine(tmp_path)
    e.last_used_counts = np.array([2, 0, 1, 4], dtype=np.int64)
    out = tmp_path / "mymosaic.jpg"
    e._write_used_tiles(out, "square")

    json_path = tmp_path / "mymosaic_used_tiles.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["engine"] == "smart"
    assert data["shape_mode"] == "square"
    assert data["mosaic"] == "mymosaic.jpg"
    assert data["unique_tiles"] == 3
    assert data["total_placements"] == 7
    assert sum(t["count"] for t in data["tiles"]) == 7


def test_write_is_noop_without_counts(tmp_path):
    e = _make_engine(tmp_path)
    # No last_used_counts attribute set.
    e._write_used_tiles(tmp_path / "x.jpg", "square")
    assert not (tmp_path / "x_used_tiles.json").exists()


def test_write_is_idempotent(tmp_path):
    e = _make_engine(tmp_path)
    e.last_used_counts = np.array([1, 1, 1, 1], dtype=np.int64)
    out = tmp_path / "m.png"
    e._write_used_tiles(out, "square")
    e._write_used_tiles(out, "square")  # same name, overwrites
    assert list(tmp_path.glob("*_used_tiles.json")) == [tmp_path / "m_used_tiles.json"]


# ---------------------------------------------------------------------------
# create_mosaic integration
# ---------------------------------------------------------------------------

def test_create_mosaic_writes_report(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    e = _make_engine(lib)

    target = tmp_path / "target.png"
    arr = np.zeros((120, 160, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, 160, dtype=np.uint8)
    arr[:, :, 1] = np.linspace(0, 255, 120, dtype=np.uint8)[:, None]
    Image.fromarray(arr).save(target)

    out = tmp_path / "out.jpg"
    # 2K + high tile_scale keeps the sector count (and runtime) small.
    e.create_mosaic(target, out, "2K", "square", tile_scale=3.0,
                    save_used_tiles=True)

    assert out.exists()
    json_path = tmp_path / "out_used_tiles.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["total_placements"] > 0
    assert data["total_placements"] == sum(t["count"] for t in data["tiles"])
    assert data["unique_tiles"] <= len(e.paths)


def test_create_mosaic_default_writes_no_report(tmp_path):
    # save_used_tiles defaults to False: routine renders must not litter the
    # output directory with JSON reports.
    lib = tmp_path / "lib"
    lib.mkdir()
    e = _make_engine(lib)

    target = tmp_path / "target.png"
    Image.new("RGB", (160, 120), (90, 90, 90)).save(target)

    out = tmp_path / "plain.jpg"
    e.create_mosaic(target, out, "2K", "square", tile_scale=3.0)

    assert out.exists()
    assert list(tmp_path.rglob("*_used_tiles.json")) == []


def test_preview_writes_no_report(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    e = _make_engine(lib)

    target = tmp_path / "t.png"
    Image.new("RGB", (160, 120), (100, 100, 100)).save(target)

    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    img = e.render_preview(target, short_edge=128, shape_mode="square", tile_scale=2.0)

    assert img.size[0] > 0
    # Preview sets counts in memory but must not write anything to disk.
    assert hasattr(e, "last_used_counts")
    assert list(tmp_path.rglob("*_used_tiles.json")) == []
