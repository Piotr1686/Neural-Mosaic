"""Golden pixel-regression guard for SmartEngine._do_render.

Sprint 2 (PLAN_SHAPES.md) extracts a shared `_polygon_sector` helper out of the
kites/spectre branches and introduces the SHAPE_MODES registry. This test locks
the exact rendered output of four representative shapes (two grid, two polygon)
BEFORE the refactor so the refactor can be proven byte-for-byte identical.

The library, target and render parameters are fully deterministic (fixed RNG
seed, solid-colour PNG tiles, analytic gradient target), so the SHA-256 of each
render is stable. If a golden hash changes, either the render output genuinely
changed (regression — investigate) or an intentional pixel change was made (e.g.
bumping a new shape's `aa`, which is a deliberate break — regenerate the golden
via scratch tooling and note it in the commit).
"""
import hashlib
import threading

import numpy as np
import pytest
from PIL import Image

from src.engine_smart import SmartEngine

# Golden hashes (env `mosaic`). Keyed by (shape_mode, border_mode).
# 2026-07-08: square/True + hexagon_romb regenerated after the grid branches
# gained _mean_fill_outside_mask (deliberate matching improvement — sectors
# no longer match against neighbouring content outside their mask). square/
# False is bit-identical (full-canvas mask -> mean-fill is a no-op), as are
# kites/spectre (already mean-filled before the change).
GOLDEN = {
    ("square", False): "a1c3eefa031fbee1d02f13dcd53303b6539cab58cab9f1a23934e2565022c599",
    ("square", True): "12d7b630fc29c2333abb59e2faa518497abc51005011d5717f16930d1ce8b5f0",
    ("hexagon_romb", False): "844500406175b54629905c8c06c81a3ed3f8f370f085dd2cd4d769b4fd82298e",
    ("hexagon_romb", True): "6a3a7fe403afd12a0fdf97b35ef6a659be5d3557708085acf6465b302f638c45",
    ("kites", False): "c4de330c559aa15ac1c8d2a455de33db8c9757f9773389b4c1b7c6873eb0ac28",
    ("kites", True): "0233840e783e6c1450c410267ed9ac08e2bbd5f979268d1bbb0a9673b3a8de30",
    ("spectre", False): "f3fb7b078a1d4ef5047528623e805013ee93f8679c465d53dce65923c74db677",
    ("spectre", True): "c31d75ff863a6fb357c73378ea429bbfd7d043b7e7361e569ddb52de6e9a0049",
}


def _build_library(tmp_path, n=32):
    """Write n deterministic solid-colour PNG tiles; return (paths, features)."""
    e = SmartEngine(index_path="__none__.pkl")
    rng = np.random.default_rng(12345)
    paths, feats = [], []
    for i in range(n):
        col = tuple(int(v) for v in rng.integers(0, 256, size=3))
        p = tmp_path / f"tile_{i:03d}.png"
        Image.new("RGB", (120, 120), col).save(p)
        paths.append(str(p))
        feats.append(
            e._compute_sector_feature(Image.new("RGB", (120, 120), col), edge_aware=True)
        )
    return paths, np.array(feats, dtype=np.float32)


def _make_target(w=384, h=288):
    """Deterministic analytic RGB gradient (matches the golden-generation script)."""
    xs = np.linspace(0, 255, w, dtype=np.float32)
    ys = np.linspace(0, 255, h, dtype=np.float32)
    r = np.tile(xs, (h, 1))
    g = np.tile(ys[:, None], (1, w))
    b = r * 0.5 + g * 0.5
    arr = np.stack([r, g, b], axis=-1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


@pytest.fixture(scope="module")
def golden_engine(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("golden_lib")
    paths, feats = _build_library(tmp)
    e = SmartEngine(index_path="__none__.pkl")
    e.paths = paths
    e.features = feats
    e.settings = {"allow_mirror": True, "edge_aware": False, "freq_penalty": 30.0}
    return e


@pytest.mark.parametrize("shape,border", list(GOLDEN.keys()))
def test_render_matches_golden(golden_engine, shape, border):
    """_do_render output must be byte-for-byte identical to the locked golden."""
    # Isolate each render's neighbour cache so ordering can't leak between cases.
    golden_engine._neighbors_cache = {}
    golden_engine._neighbors_lock = threading.Lock()
    out = golden_engine._do_render(
        _make_target(), shape, tile_scale=0.5, border_mode=border
    )
    digest = hashlib.sha256(out.tobytes()).hexdigest()
    assert digest == GOLDEN[(shape, border)], (
        f"Render changed for shape={shape} border={border}: "
        f"got {digest}, expected {GOLDEN[(shape, border)]}"
    )
