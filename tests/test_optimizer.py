"""Tests for src/optimizer.py (Sprint 4, PLAN_HIRES.md).

Locks the guardrails added after the optimiser (default 250 px, in-place,
delete-on-error) silently softened and thinned the tile library:

* default short side is 512 (env OPTIMIZER_SHORT_SIDE overridable),
* oversized images are downscaled to the target, small ones untouched,
* corrupt files are KEPT unless delete_corrupt=True,
* the tiles_hires overlay dir is refused as a target.

process_image is called directly (not via the process pool) to keep the test
fast and free of Windows multiprocessing pickling.
"""
import importlib

from PIL import Image

import src.optimizer as opt


# ---------------------------------------------------------------------------
# Config: default + env override
# ---------------------------------------------------------------------------

def test_default_short_side_is_512():
    assert opt.TARGET_SHORT_SIDE == 512


def test_short_side_reads_env(monkeypatch):
    monkeypatch.setenv("OPTIMIZER_SHORT_SIDE", "300")
    reloaded = importlib.reload(opt)
    try:
        assert reloaded.TARGET_SHORT_SIDE == 300
    finally:
        monkeypatch.delenv("OPTIMIZER_SHORT_SIDE", raising=False)
        importlib.reload(opt)  # restore module default for other tests


# ---------------------------------------------------------------------------
# process_image
# ---------------------------------------------------------------------------

def test_downscales_oversized_image(tmp_path):
    p = tmp_path / "big.jpg"
    Image.new("RGB", (800, 600), (120, 60, 30)).save(p)

    changed = opt.process_image(p, target_short_side=512, delete_corrupt=False)
    assert changed is True
    with Image.open(p) as im:
        assert min(im.size) == 512


def test_leaves_small_image_untouched(tmp_path):
    p = tmp_path / "small.jpg"
    Image.new("RGB", (100, 100), (10, 10, 10)).save(p)

    changed = opt.process_image(p, target_short_side=512, delete_corrupt=False)
    assert changed is False
    with Image.open(p) as im:
        assert im.size == (100, 100)


def test_corrupt_file_kept_without_flag(tmp_path):
    p = tmp_path / "broken.jpg"
    p.write_bytes(b"not an image")

    changed = opt.process_image(p, target_short_side=512, delete_corrupt=False)
    assert changed is False
    assert p.exists()  # must NOT be silently deleted


def test_corrupt_file_deleted_with_flag(tmp_path):
    p = tmp_path / "broken.jpg"
    p.write_bytes(b"not an image")

    changed = opt.process_image(p, target_short_side=512, delete_corrupt=True)
    assert changed is False
    assert not p.exists()


# ---------------------------------------------------------------------------
# optimize_folder: refuse the overlay dir
# ---------------------------------------------------------------------------

def test_refuses_tiles_hires_overlay(tmp_path):
    overlay = tmp_path / "tiles_hires"
    overlay.mkdir()
    big = overlay / "coco_1.jpg"
    Image.new("RGB", (800, 600), (200, 30, 30)).save(big)

    total, resized = opt.optimize_folder(overlay, target_short_side=512,
                                         delete_corrupt=False)
    assert (total, resized) == (0, 0)
    with Image.open(big) as im:
        assert im.size == (800, 600)  # untouched
