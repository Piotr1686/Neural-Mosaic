"""Tests for upgrade_tiles.py (Sprint 3, PLAN_HIRES.md). No network.

Locks the pure logic that decides WHAT to fetch and WHETHER to keep it:

* classify_tile   -> correct source/url per prefix, coco_train_ before coco_,
                     malformed ids -> skip,
* verify_identity -> same photo accepted, different photo rejected, missing
                     original -> unverified,
* collect_used    -> merges reports, sums counts, sorts by count desc,
* plan            -> classifies, drops already-present overlay files.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from src.tools import upgrade_tiles as ut


# ---------------------------------------------------------------------------
# classify_tile
# ---------------------------------------------------------------------------

def test_coco_train_routed_to_train2017():
    src, url = ut.classify_tile("coco_train_000000000009.jpg")
    assert src == "coco"
    assert url == "http://images.cocodataset.org/train2017/000000000009.jpg"


def test_coco_unlabeled_routed_to_unlabeled2017():
    src, url = ut.classify_tile("coco_000000000008.jpg")
    assert src == "coco"
    assert url == "http://images.cocodataset.org/unlabeled2017/000000000008.jpg"


def test_coco_train_takes_precedence_over_coco():
    # The invariant: coco_train_ must NOT fall through to the unlabeled route.
    _, url = ut.classify_tile("coco_train_000000000123.jpg")
    assert "train2017" in url and "unlabeled" not in url


def test_coco_non_numeric_is_skipped():
    assert ut.classify_tile("coco_abc.jpg") == ("skip", None)
    assert ut.classify_tile("coco_train_xyz.jpg") == ("skip", None)


def test_picsum_seed_from_index():
    src, url = ut.classify_tile("tile_000005.jpg", size=512)
    assert src == "picsum"
    assert url == "https://picsum.photos/seed/5/512"


def test_picsum_size_is_honoured():
    _, url = ut.classify_tile("tile_000010.jpg", size=1024)
    assert url.endswith("/seed/10/1024")


def test_picsum_malformed_skipped():
    assert ut.classify_tile("tile_abc.jpg") == ("skip", None)


def test_archive_prefixes():
    for name in ("food_1.jpg", "places_Places365_val_00000001.jpg",
                 "dog_n02085936_1.jpg", "flower_image_00001.jpg"):
        assert ut.classify_tile(name) == ("archive", None)


def test_loremflickr_keyword_skipped():
    assert ut.classify_tile("abstract_3363459.jpg") == ("skip", None)
    assert ut.classify_tile("nature_1.jpg") == ("skip", None)


def test_non_image_extension_skipped():
    assert ut.classify_tile("coco_000000000008.txt") == ("skip", None)


# ---------------------------------------------------------------------------
# verify_identity
# ---------------------------------------------------------------------------

def _photo(path, seed):
    """A deterministic non-solid RGB image; identical seed => identical pixels."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(40, 40, 3), dtype=np.uint8)
    Image.fromarray(arr).save(path)


def test_same_photo_different_size_accepted(tmp_path):
    _photo(tmp_path / "lib.png", seed=1)
    # A larger copy of the SAME source content.
    with Image.open(tmp_path / "lib.png") as im:
        im.resize((160, 160), Image.Resampling.LANCZOS).save(tmp_path / "hi.png")
    assert ut.verify_identity(tmp_path / "hi.png", tmp_path / "lib.png", 8.0) == "ok"


def test_different_photo_rejected(tmp_path):
    Image.new("RGB", (40, 40), (10, 10, 10)).save(tmp_path / "lib.png")
    Image.new("RGB", (40, 40), (240, 20, 200)).save(tmp_path / "hi.png")
    assert ut.verify_identity(tmp_path / "hi.png", tmp_path / "lib.png", 8.0) == "reject"


def test_missing_original_is_unverified(tmp_path):
    Image.new("RGB", (40, 40), (100, 100, 100)).save(tmp_path / "hi.png")
    assert ut.verify_identity(tmp_path / "hi.png", tmp_path / "gone.png", 8.0) == "unverified"
    assert ut.verify_identity(tmp_path / "hi.png", None, 8.0) == "unverified"


# ---------------------------------------------------------------------------
# collect_used
# ---------------------------------------------------------------------------

def _write_report(path, tiles):
    path.write_text(json.dumps({"tiles": tiles}), encoding="utf-8")


def test_collect_merges_and_sums_counts(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_report(a, [{"name": "x.jpg", "path": "lib/x.jpg", "count": 3},
                      {"name": "y.jpg", "path": "lib/y.jpg", "count": 1}])
    _write_report(b, [{"name": "x.jpg", "path": "lib/x.jpg", "count": 4}])

    entries = ut.collect_used([a, b])
    names = [e[0] for e in entries]
    counts = {e[0]: e[2] for e in entries}
    assert counts["x.jpg"] == 7  # 3 + 4
    assert counts["y.jpg"] == 1
    assert names[0] == "x.jpg"    # sorted by count desc


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------

def test_plan_classifies_and_skips_existing(tmp_path):
    dest = tmp_path / "hires"
    dest.mkdir()
    # coco_1 already present in overlay -> must be skipped.
    (dest / "coco_000000000001.jpg").write_bytes(b"x" * 2000)

    entries = [
        ("coco_000000000001.jpg", "lib/coco_000000000001.jpg", 5),  # exists -> skip
        ("coco_train_000000000002.jpg", "lib/c2.jpg", 4),           # fetch
        ("tile_000003.jpg", "lib/tile_000003.jpg", 3),              # picsum: NOT by default
        ("food_x.jpg", "lib/food_x.jpg", 2),                        # archive
        ("abstract_9.jpg", "lib/abstract_9.jpg", 1),                # skip
    ]
    result = ut.plan(entries, dest, size=512)

    assert result["breakdown"] == {"coco": 2, "picsum": 1, "archive": 1, "skip": 1}
    assert result["skipped_exists"] == 1
    # picsum drifted -> not fetched by default; only the fresh COCO tile.
    fetch_names = {t[0] for t in result["to_fetch"]}
    assert fetch_names == {"coco_train_000000000002.jpg"}


def test_plan_include_picsum_opt_in(tmp_path):
    dest = tmp_path / "hires"
    dest.mkdir()
    entries = [
        ("coco_train_000000000002.jpg", "lib/c2.jpg", 4),
        ("tile_000003.jpg", "lib/tile_000003.jpg", 3),
    ]
    result = ut.plan(entries, dest, size=512, include_picsum=True)
    fetch_names = {t[0] for t in result["to_fetch"]}
    assert fetch_names == {"coco_train_000000000002.jpg", "tile_000003.jpg"}


def test_plan_fetch_order_preserves_count_desc(tmp_path):
    dest = tmp_path / "hires"
    dest.mkdir()
    entries = ut.collect_used([_report_file(tmp_path)])
    result = ut.plan(entries, dest, size=512)
    counts = [t[3] for t in result["to_fetch"]]
    assert counts == sorted(counts, reverse=True)


def _report_file(tmp_path):
    p = tmp_path / "r.json"
    _write_report(p, [
        {"name": "coco_000000000010.jpg", "path": "l/a.jpg", "count": 2},
        {"name": "coco_000000000020.jpg", "path": "l/b.jpg", "count": 9},
        {"name": "tile_000030.jpg", "path": "l/c.jpg", "count": 5},
    ])
    return p
