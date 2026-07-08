"""Tests for the Deep Zoom (DZI) pyramid export (src/tools/make_dzi).

Covers the pieces the A2 export left as a follow-up: the descriptor is
well-formed and reports the real source size, the pyramid directory is
populated, ``skip_existing`` is genuinely idempotent (and ``False`` forces a
rebuild), ``max_level_cap`` downscales, and the new ``progress_cb`` honours the
``(done, total)`` contract the GUI progress bar relies on.
"""
import math

from PIL import Image

from src.tools.make_dzi import make_dzi, TILE_SIZE


def _make_image(tmp_path, w=300, h=200, name="mosaic.png"):
    p = tmp_path / name
    Image.new("RGB", (w, h), (120, 60, 30)).save(p)
    return p


def _expected_total_tiles(w, h):
    max_level = math.ceil(math.log2(max(w, h)))
    total = 0
    for level in range(max_level, -1, -1):
        scale = 2 ** (level - max_level)
        lw = max(1, math.ceil(w * scale))
        lh = max(1, math.ceil(h * scale))
        total += math.ceil(lw / TILE_SIZE) * math.ceil(lh / TILE_SIZE)
    return total


def test_make_dzi_writes_descriptor_and_tiles(tmp_path):
    src = _make_image(tmp_path, 300, 200)
    out = tmp_path / "dzi"
    make_dzi(src, out)

    dzi = out / "mosaic.dzi"
    files = out / "mosaic_files"
    assert dzi.exists() and files.is_dir()

    xml = dzi.read_text(encoding="utf-8")
    # the DZI-format bug guard: tiles are .jpg, so Format must be "jpg"
    assert 'Format="jpg"' in xml
    assert f'TileSize="{TILE_SIZE}"' in xml
    assert 'Width="300"' in xml and 'Height="200"' in xml

    # every produced tile is a real jpg
    tiles = list(files.rglob("*.jpg"))
    assert tiles and all(t.stat().st_size > 0 for t in tiles)


def test_skip_existing_leaves_tiles_untouched(tmp_path):
    src = _make_image(tmp_path, 300, 200)
    out = tmp_path / "dzi"
    make_dzi(src, out)

    a_tile = next((out / "mosaic_files").rglob("*.jpg"))
    a_tile.write_bytes(b"SENTINEL")

    # skip_existing (default): the sentinel tile is left as-is
    make_dzi(src, out, skip_existing=True)
    assert a_tile.read_bytes() == b"SENTINEL"

    # skip_existing=False: forced rebuild overwrites it with a real jpeg
    make_dzi(src, out, skip_existing=False)
    assert a_tile.read_bytes() != b"SENTINEL"
    assert a_tile.stat().st_size > 0


def test_max_level_cap_downscales(tmp_path):
    src = _make_image(tmp_path, 300, 200)
    out = tmp_path / "dzi"
    make_dzi(src, out, max_level_cap=5)          # 2^5 = 32 px longest side

    xml = (out / "mosaic.dzi").read_text(encoding="utf-8")
    assert 'Width="32"' in xml                   # 300 -> 32, 200 -> 21
    assert 'Height="21"' in xml

    # no pyramid level beyond the cap exists
    levels = {int(d.name) for d in (out / "mosaic_files").iterdir() if d.is_dir()}
    assert max(levels) == 5


def test_progress_cb_contract(tmp_path):
    src = _make_image(tmp_path, 300, 200)
    out = tmp_path / "dzi"
    calls = []
    make_dzi(src, out, progress_cb=lambda done, total: calls.append((done, total)))

    assert calls, "progress_cb was never called"
    total = _expected_total_tiles(300, 200)
    assert all(t == total for _, t in calls)     # total is stable and correct
    dones = [d for d, _ in calls]
    assert dones == sorted(dones)                 # monotonic non-decreasing
    assert all(0 < d <= total for d in dones)
    assert dones[-1] == total                     # finishes at 100%
