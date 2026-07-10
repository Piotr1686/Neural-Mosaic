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
# 2026-07-08 (a): square/True + hexagon_romb regenerated after the grid
# branches gained _mean_fill_outside_mask (deliberate matching improvement).
# 2026-07-08 (b): all shaped cases regenerated again for masked top-K
# re-scoring (_mask_cell_weights — out-of-mask cells no longer influence the
# match). square/False stays bit-identical through BOTH changes: its
# full-canvas mask makes mean-fill a numeric no-op and yields wmask=None,
# which skips the weighted re-scoring — the plain GEMM path is untouched.
GOLDEN = {
    ("square", False): "a1c3eefa031fbee1d02f13dcd53303b6539cab58cab9f1a23934e2565022c599",
    ("square", True): "dd0806d49fcf2ebdaa6353c50c38f2d709884465cd9be50da027f4eb823a1c46",
    ("hexagon_romb", False): "eb6b5e97c966b70236626d85c1c4e7911201927fdf96502ec2b514d7d0a5020a",
    ("hexagon_romb", True): "2877bad908ef6b6b7a167394959c635868e136b7764416d8d2c97ed9f7f4f71b",
    ("kites", False): "7689265c540dd537b1f3a42ed26354c577ff78a1d02601fe2747543b061b8ed5",
    ("kites", True): "d9f3c83beb7b4f5be302af04e54016f4cba52ee2838a916031efee8fe95d31ae",
    ("spectre", False): "ed5ad4f4c582341daba6cb2cf61ec021bac48d9bfa7f0fac9fd41cc4ca5bc5dc",
    ("spectre", True): "998a645f47ef0d222add0f32fce9276002fdd8505f10944e1b3860ac19a500a8",
    # New polygon shape wired via the generic dispatch + _polygon_sector
    # (2026-07-10). Geometry is deterministic (Vogel seeds + Voronoi, no RNG),
    # so these hashes lock the first render — no "before" to match against.
    ("sunflower_grande", False): "58b658768dfd4d0d26c5af12f761b06375f69ade9fb7c69e414e051383a2bb99",
    ("sunflower_grande", True): "b658d937874bd1d54204d0c64bd897a2cb130cb05edc28babee3f5d8ab74e7b9",
    ("sunflower_grande_xl", False): "01a35aedf9d5dcf40dcf831086309c4531c9773268bb78f7836deda22bbc3cf6",
    ("sunflower_grande_xl", True): "3ce0214c22e3baf40acd95ee5cb09f83f5afceffadb4d7dde5f3a8ded03c8ac1",
    ("sunflower_grande_soft", False): "467a5b409fce4408f5ee5721da1b184de9867a890d2954776687076b87426795",
    ("sunflower_grande_soft", True): "68ef85a27ef9ba69842c1d94c18c76ef28d3c2d25d5f47ccc97b927ab898d470",
    ("sunflower_grande_inverse", False): "75c3f0fdb9a4c9bc2ef6e95b297bcad83799c70f9818987908cd3c164049ba5d",
    ("sunflower_grande_inverse", True): "e05e89c5e4d84b6fc81f1569eb3b071c7a0a8cb7abb60ee90e4e968e1342463c",
    ("sunflower_soft", False): "f2e18a0654a7d11e0ea8d3d52d84b88783e62b8a420f8eb010d5b48646938249",
    ("sunflower_soft", True): "85afad72de8104116dbef0d1190a36fb8c5ede4499f0cc028b72d2cf8cdb6b9b",
    ("sunflower_rings", False): "52dce57a15ad2fd4f5350a423a654f6f9b581344c30ef495ab925add65f28a29",
    ("sunflower_rings", True): "179a3173d1a2220c70f02b9d7142d489e5e67530296ba39ab4f241f191b52696",
    ("sunflower_disc", False): "271518f173191cca4d0a5bd6978193239f562e354bfe6254bc835412cafcdaa7",
    ("sunflower_disc", True): "71be46ac6c2ec200af542276dc206f133df11313beb1eff60f191170b4265ae0",
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
