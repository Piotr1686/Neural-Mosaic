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
    # rhombs family: log-spiral quad mesh, k solved from base_s (density scales
    # with tile_scale). Deterministic (no RNG), so these lock the first render.
    ("rhombs_nopole", False): "af0aa741c12502e7422eede95421851d0b64f99d8aa81f55abaaa69215e5229e",
    ("rhombs_nopole", True): "f419f7ed7c560cc7d4a331e515acf5b245962eaad94db6a59f4fbd58adfc64b7",
    ("rhombs_funnel", False): "e8cac6477aa9b685769b2ecf25e07e04ab3c931dd24390595faeda0098db89c1",
    ("rhombs_funnel", True): "f6daa0ccc63ffd58f7b03a986ce5d92575f9848cf2b5a67fae16482f23c30023",
    ("rhombs_star", False): "558b2d187ecbf9e4f8a5723712f43c7e91e3c995383e9975b16773f9ba9b3554",
    ("rhombs_star", True): "e92d5357a4b9cf18d03c7857fe250673a79d4d35dacbe8ac8dfe1ed1eb56c382",
    # S5 variable-cell shapes: uniform Voronoi (seeded RNG from dims -> stable
    # per size) and canonical phyllotaxis (Vogel power=0.5, no RNG).
    # voronoi regenerated 2026-07-17 (hull-cell recovery in _voronoi_cells):
    # unbounded hull cells used to be dropped, which at the golden frame left
    # rim holes (6 recovered cells, 61 -> 67; ~5% of pixels changed, ALL at the
    # frame rim — interior verified untouched via a pixel-diff mask against the
    # old render, which still matched the old hash bit-for-bit). The other 20
    # family goldens (pebbles/sunflowers/phyllotaxis/bloom) did NOT change —
    # the two-pass fix keeps bounded cells bit-identical by design.
    ("voronoi", False): "7bb07e64b6dfd2b48313d9204df9c65eb462ef02b537e61a4e9165e640d51ff2",
    ("voronoi", True): "d84c8a55ec3bc44d365ac905df7aeb76bd0ca6b740fb5e958ac6070c2cb89876",
    ("phyllotaxis", False): "2d6f0e07782ed19945bfbd135faa42aa0bb3bdfa5545dffecb8ecde83ae42245",
    ("phyllotaxis", True): "70161b6c52e4b54077e4bf6ada6b832eb92a6858e09c9bb7e27ff2eb553e15a8",
    # Deterministic Fable tessellations (2026-07-11): geometry ported from
    # gen_fable_shape_schemes.py, pure constructions (no RNG). Hashes lock the
    # first render, verified identical across two separate processes.
    ("pinwheel", False): "849334cb7fb68dfbea20db7b241343fa19ff45b2fc98fdf0ab472ff490f5b631",
    ("pinwheel", True): "6ddc04111b5666c51ae243a3a67805fc5b48af28b72b6ebee9cc75a55f0b6360",
    ("cairo", False): "ee0a3e2805ab523ca9937d36d2424c450ac9cceb5bae4fbc1e4f8e58a24882b6",
    ("cairo", True): "bdbf84f6026859d22c91d2fc5ac494eb699c769b52674164e45facf74dc1dd2c",
    ("floret", False): "6dbdb8df7b6ce1f04ad46132e7264e0eacc5e8f1c2591a1747c391c65a2f234e",
    ("floret", True): "ecb63302aa87873000f21265c55b4c1506ce6ebb4fa273c94410ce7b13542bfd",
    ("gosper", False): "538de3f57939ff27cbd028a80cf6c6641bd58117baa1fcf940fe3376e6787b4a",
    ("gosper", True): "fcbab1c1ee1255eb96ce6ca559925c14e5844770621f2a0d830e3e6a00e7e45e",
    # Archimedean tessellations + sunburst (2026-07-11): rebuilt from the
    # scheme PNGs (original generator code was lost with the Opus scratchpad).
    # Pure constructions (no RNG); hashes lock the first render, verified
    # identical across two separate processes.
    ("trunc_square", False): "9d29997b93a6d429676e3e00d1fb34795ebd9c92e1efc98a24be40e6ec04c88d",
    ("trunc_square", True): "9c4630fe5e7bdf93107999fbed26d5a8243664c9d193b1fa8df19f8d4260bc6a",
    ("trunc_hex", False): "dfcc610fb2cb4bf5977faa785ba5480fbe797675fb67437a55f68201899ac29e",
    ("trunc_hex", True): "f7374628b0e61420253e5a15990ab83e305327e744042f79449c22979ac8acc6",
    ("rhombitrihex", False): "250c47b38741c2c8b4598f4beb0464d5125339974d4b87e323ced60bda5170fa",
    ("rhombitrihex", True): "9a655d0a8b08c0ffc3ad353f8296afe818ad1db7eecdc77540cf661d2773a0a7",
    ("pythagorean", False): "ed656e63f7eecebb19d1eb3185b742c4316ec0fd1c5f787e4400b5cc97c5d78f",
    ("pythagorean", True): "112af310279de9d5eb3354d10c0e635cb82fef8de699fb9c302cee05535ec024",
    ("sunburst", False): "36997d500713f7d41dd38137eaf038ef9b6b9e7c925350be2806ab6edcf8ddb5",
    ("sunburst", True): "0949671235dd370533908e49bee1d954ef404423eaa3e59ea3d9054d29b9e7d5",
    # De Bruijn multigrid duals (2026-07-11): penrose P3 (pentagrid N=5,
    # gamma sum=1) + ammann_beenker (N=4). Deterministic (fixed generic
    # offsets, no RNG); hashes lock the first render, cross-process verified.
    ("penrose", False): "107789f68531f74f9c2147a8d44b1a6bff536d149622bf8bb406d31aa95c41dc",
    ("penrose", True): "bdcda867688ea52ece9911555455e10f7da2876523fa3e32acb7715cb643293e",
    ("ammann_beenker", False): "ccf9124eeb90c012eaa5aca4824a8f6fbea447b0dd083f92681686104077fba2",
    ("ammann_beenker", True): "20b42e242ca75161aaabc7d47caa21cbc14c0a2e915186c21cce66f8669a6b0f",
    # Last three Fable shapes (2026-07-13): voderberg (rings of bent slivers,
    # bow made radius-relative), escher_lizard (p1 hexagon deformation) and
    # weave (basketweave rebuilt as a true partition: visible ribbon pieces +
    # knot cells). Pure constructions (no RNG); hashes lock the first render,
    # verified identical across two separate processes.
    ("voderberg", False): "7b191e564c955628214a8fa899360ddb59d29105d8c520daf04dd42dbb53a7f7",
    ("voderberg", True): "06c1039433643f6d01872b20f6e4da29b3459cd9e01759d5b21b500825d59004",
    ("escher_lizard", False): "1ed4b6eba6fd871cd91cd591e7209fb5f4ed114b2912e68ee773d7f580614bc1",
    ("escher_lizard", True): "c8f3ba54034e80033d7bc62dcb1d00fb7627d4705fb73083d7e8299103a6cf7e",
    ("weave", False): "454a1cf18000cf2325cbd3efda358ed9f0d54d8c92171a7a5e0feec9afa6c701",
    ("weave", True): "a02877e16975c8c1df7d23b2b73426a0dc9215fb4dcd4e0c9839a7adcaf607bd",
    # Truchet (2026-07-13): arcs polygonised by _sun_arc with a sagitta-driven
    # pitch (_arc_pitch), tile orientation from an integer hash of the lattice
    # index -> no RNG, same pattern at every resolution. Cross-process verified.
    ("truchet", False): "60a2c76342a46440daf07bd0528a85e7faf49c944d969c775e24f48f3c84ed17",
    ("truchet", True): "40e5f0463098e046b349f16a1c2cb7b9f9986ab5376cae6211858f893e128556",
    ("truchet_hex", False): "5637078ccaafc47f70a62902eff96e3b8aed89231082f20a7c42e70c949e1d36",
    ("truchet_hex", True): "4ee3a40ab8a4dbe8fbf43983113d52522f0fb0fe196cb215270d326add23b0f1",
    # girih (2026-07-14): decagon rosettes seeded on a Penrose-vertex
    # quasi-lattice, greedy fill between them, leftovers traced. Carries NO RNG
    # and no frozen seed (the plan expected one), so these hashes are stable
    # across processes — verified in two separate interpreters.
    ("girih", False): "99dc1692e6ae6ba29fa785091d49b380b7aba825d1f3620a7b5c2f81aa0abc4a",
    ("girih", True): "d0fd5e9f6906fbd8b9271155fccc3d96f9d86d9c2702af856249cd7addcd0ab2",
    # poincare (2026-07-15, krok 4 b++): {7,3} band tiling, heptagons split into
    # 7 khatam kites, each subdivided by a hyperbolic transfinite quad mesh. BFS
    # over disc reflections + pure geometry, NO RNG and no frozen seed — hashes
    # verified byte-identical across two separate interpreters (like girih). The
    # tmp golden library (tile_NNN.png) shares no basename with data/tiles_hires
    # (coco_*.jpg), so the hi-res overlay is a no-op here and the hash is portable.
    ("poincare", False): "d8dad4aa080306dbe56068578232fc327e1730334c8fa239666d11a1681cb68d",
    ("poincare", True): "c51950e0aee13e7e40feddf1a08ed0eb2d0af72d7d1e7f068a39f3bee48044f8",
    # penrose_p2 (2026-07-16, sprint E1): P2 kites & darts via P3 deflation +
    # Robinson B->A conversion + mirror-twin merge. No RNG; the merge iterates
    # dicts/int-sets only, so order is process-independent — hashes verified
    # identical across two interpreters, one with PYTHONHASHSEED=1.
    ("penrose_p2", False): "e6d9874805f1bd79ff9777387ac88b7655018022a4a9c2943924bbb9e0a8df07",
    ("penrose_p2", True): "ae1a8d87c18fee77a959b12393fc798a9d459d9d1c6b594eaa72755c8fdaff76",
    # E2 (2026-07-17). bloom: Lucas-angle Vogel lattice — the `angle` parameter
    # defaults to the golden angle, so all eight sunflower goldens above stay
    # bit-identical (verified). pebbles: variable-density Voronoi, seeded from
    # dimensions via _shape_seed. Both verified across two interpreters, one
    # with PYTHONHASHSEED=1.
    ("bloom", False): "c65bcb4a6ff6df9b6722c7bad4fc6f67b6da99531943cd713c01d2c525d1c0d7",
    ("bloom", True): "3b16cef41605f943bf7e9cacfcaf485d843e027a7a1a7c83f1c57cc7b41f1db8",
    ("pebbles", False): "ed4f1f3ea203a442d19ea5008a6d9caf5e725ed36b50b7829afc898653ac7279",
    ("pebbles", True): "28868e8dc325fa6cb9fcb2770ac9a6702c6a7a2e0050e9571e3c67e6549fedf9",
    # E3 (2026-07-17). stagger_tri: triangle rows at a constant x-phase, so the
    # rows slip and every row line is a T-junction seam. NOT `triangle`, which
    # shifts the phase by half a base each row via its (c+r)%2 flip rule — see
    # the translation-invariant gate in test_grout_engine. Pure arithmetic, no
    # RNG; verified across two interpreters, one with PYTHONHASHSEED=1.
    ("stagger_tri", False): "cee4b15ccb044f46d3e5c7ab4935a56773ccff7e4bc414dfb699a447b56aec72",
    ("stagger_tri", True): "97524a19731c816d29c497f97530ddabf7d488ca9c5725bb942b29369104970b",
    # braid (2026-07-18): basketweave rebuilt as a true partition — 2x1 bricks
    # in alternating horizontal/vertical pairs on a 2x2 checkerboard. NOT
    # `brick_wall` (single running bond, one orientation); the extra vertical
    # bricks are an orientation set no rigid motion adds, proven by the
    # translation-invariant gate in test_grout_engine. Pure arithmetic, no RNG;
    # verified across two interpreters, one with PYTHONHASHSEED=1.
    ("braid", False): "e76a5d546a82f1d3f9af17c72471f266f032aefbe9e7196e06a279cea8faba6f",
    ("braid", True): "db6356dd1d1f377d7dfde8bf1f133e26c989b006bbca970f6761e08c29fd9c7c",
    # moire (2026-07-18): a quad grid displaced by a two-grating interference
    # field. Cells stay gap-free (shared displaced vertices) but warp in
    # shape/size with the beat — verified on a real render NOT to collapse to
    # `square` (CV of cell area ~0.27, only ~28% of edges axis-aligned; a square
    # lattice would be 0 and 100%). Pure arithmetic, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("moire", False): "e45f0fae165786bf9f56815a580212c8769ef260f6be61424f0a710c6d7d3dc7",
    ("moire", True): "7ad9dedb3421380057c92b805c9391d623e89a36ab724a88f3bf982ae934b9cb",
    # puzzle family (2026-07-19, sprint P): die-cut jigsaw tabs as per-edge
    # shared polylines (crc32-keyed, no RNG) on three lattices — classic
    # ribbon-cut grid, sine-warped ribbon grid, flat-top hex. Verified across
    # two interpreters, one with PYTHONHASHSEED=1. The dedup of the profile's
    # junction vertices is load-bearing: doubled consecutive points broke
    # Pillow's scanline parity inside the aa=4 masks (1-2 px strips).
    ("puzzle_classic", False): "8783330ea9c21030435c347cd8b27ffb5232cea3c49a39b864de1d5ef480dae4",
    ("puzzle_classic", True): "c8fe3cbc096dd835e54b88948a90fa333608b92b66a5804f4bce7f7f0d8de06a",
    ("puzzle_ribbon", False): "2c264a757630e7218cbf369a4e6a09a5da94e305397cae29ab31dff9da394a53",
    ("puzzle_ribbon", True): "8886b6ad048bd342dbb4cc3dcc5a52bf3e2c8826624211d839a8c60ec6831097",
    ("puzzle_hex", False): "6e034c3376f2e98ccb80b1e07e166d91ea8e83287797a247cf36af14e0d52351",
    ("puzzle_hex", True): "d2c5dff49f91161218023e48d2d815fa962cb41c65c4b32253319fa9e7d9b97b",
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
