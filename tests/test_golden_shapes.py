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
    # 2026-07-21: square + hexagon_romb regenerated after the standard-grid /
    # hexagon_romb branches stopped BLACK-padding partial edge crops (they now
    # mean-fill the off-canvas remainder and paste the visible content at its
    # true position). Deliberate matching fix: black padding was dragging edge
    # tiles' LAB features dark and matching dark tiles (brick_wall's left
    # half-bricks). Only these grid goldens moved; kites/spectre/polygon use
    # branches that already pasted at the true offset and are unchanged.
    ("square", False): "d69fdf1cae64499be5679b495ee165fc559c83af57745b74628ce4926cae8968",
    ("square", True): "41b4218a579b160081a13ec14beb6b9d40f7190f325577272446f19c6651a4ee",
    ("hexagon_romb", False): "6e549f03d91bc27f2ec2950ac14ad2746e97c05232f3ac4ae9ae5ffe5c6259a8",
    ("hexagon_romb", True): "d12fae64c86ef0352504ddcd23b3c3d13d2dbeaed5ed49d585527f23f8d4755f",
    # 2026-07-26: kites regenerated after the border cull changed from
    # "centroid inside the frame" to "bbox overlaps the frame". The old test
    # dropped every border kite whose centre fell outside, leaving a saw-tooth
    # of bare canvas along the right/bottom/top edges (2.35% of the frame, up
    # to 12.6% inside the bottom band). Deliberate coverage fix — see
    # test_kites_covers_the_whole_frame in tests/test_grout_engine.py.
    ("kites", False): "475e55cee9db9121041dc081b3f58658f3e434b6b1d9184374d948c5da3c39aa",
    ("kites", True): "f282c01b9e2ceec9748386542d341ca446c5cba2a438c38c25f41cbabf30b038",
    ("spectre", False): "ed5ad4f4c582341daba6cb2cf61ec021bac48d9bfa7f0fac9fd41cc4ca5bc5dc",
    ("spectre", True): "998a645f47ef0d222add0f32fce9276002fdd8505f10944e1b3860ac19a500a8",
    # New polygon shape wired via the generic dispatch + _polygon_sector
    # (2026-07-10). Geometry is deterministic (Vogel seeds + Voronoi, no RNG),
    # so these hashes lock the first render — no "before" to match against.
    ("sunflower_grande", False): "58b658768dfd4d0d26c5af12f761b06375f69ade9fb7c69e414e051383a2bb99",
    ("sunflower_grande", True): "b658d937874bd1d54204d0c64bd897a2cb130cb05edc28babee3f5d8ab74e7b9",
    ("sunflower_grande_inverse", False): "75c3f0fdb9a4c9bc2ef6e95b297bcad83799c70f9818987908cd3c164049ba5d",
    ("sunflower_grande_inverse", True): "e05e89c5e4d84b6fc81f1569eb3b071c7a0a8cb7abb60ee90e4e968e1342463c",
    ("sunflower_soft", False): "f2e18a0654a7d11e0ea8d3d52d84b88783e62b8a420f8eb010d5b48646938249",
    ("sunflower_soft", True): "85afad72de8104116dbef0d1190a36fb8c5ede4499f0cc028b72d2cf8cdb6b9b",
    ("sunflower_rings", False): "52dce57a15ad2fd4f5350a423a654f6f9b581344c30ef495ab925add65f28a29",
    ("sunflower_rings", True): "179a3173d1a2220c70f02b9d7142d489e5e67530296ba39ab4f241f191b52696",
    # rhombs family: log-spiral quad mesh, k solved from base_s (density scales
    # with tile_scale). Deterministic (no RNG), so these lock the first render.
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
    # E4 (2026-07-19). dragon: order-8 twindragon rep-tile, boundary chained
    # from edge-cancelled unit squares (sharpest-left at pinches); (1+i)^8=16
    # so the tile lattice is the square lattice, u=base_s/16 -> area exactly
    # base_s^2. Only int/int-tuple hashing (unsalted), verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("dragon", False): "993c8e6089f946ca03f086d85b3bcb0bff938da7dc7d7c9d50a11c054b8b14d9",
    ("dragon", True): "b122cf51161b96bd0c4f03de5772f1039e0fc2d506f42984389ea34762233336",
    # koch_island: depth-2 Minkowski teragon walked on an INTEGER turtle
    # (exact coords), period 4^2 = 16 units (NOT the bbox — the 2026-07-03
    # trap), area-preserving generator -> tile area base_s^2 exactly.
    # koch_snowflake: two-size tessellation (big flakes + 2x small 1/sqrt(3)
    # rotated 30 deg in the lattice holes), depth FIXED at 4 — finite-depth
    # seams are sub-pixel (min coverage 0.686 vs voderberg's shipped 0.502).
    # Both verified across two interpreters, one with PYTHONHASHSEED=1.
    ("koch_island", False): "5f665567a85a6e23325cb77d5c58431ffb1112499d54317c54a60c10ddbb3442",
    ("koch_island", True): "81735781d8fe5db7dc2dad90f8372dd0ab08689040adce27b1b8999abab4317b",
    ("koch_snowflake", False): "a1d9eea35b8b1002d407250d28b4f234abcf3cd424f9937009e9bc41eef56439",
    ("koch_snowflake", True): "83ce7abf36893a3fa8b6a808d4fcb97f4f0a158de8c2d422d9ce448c6ae7e825",
    # E5 (2026-07-19). gereh: 4.8.8 with every octagon split into 16 kites
    # (8-point khatam star, r_in=0.60*apothem); the gap square is the DIAMOND
    # with vertices on the axes — the scheme's axis-aligned square (phase
    # pi/4) was a real bug hidden by the proposal PNG's outlines (11k hole px,
    # caught by the coverage gate). rosette: 3.12.12, dodecagon -> 12 core
    # kites + 12 petals + 12 edge triangles; interstitial holes anchored
    # analytically at lattice-triangle centroids (the filtered-centre trap
    # cannot occur). Both pure trig, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("gereh", False): "6aa90a7ce86be7cab5ed15a2f94e678aa878e31e50191efba43aeaa963908ae6",
    ("gereh", True): "e35cf3a98363541bc808963b38a2ee2a75a6c703fe1912726e6782c7f41e3ebe",
    ("rosette", False): "79566de37822130179642527ed067573af28ccc6fa8c4bad35c51624d2e7a5c4",
    ("rosette", True): "9f279666088fa1df78d0a29842a7eda47f10f2745ab0f5a4cff4c36095594d72",
    # E6 (2026-07-20). scales: circles of r=base_s/sqrt(2) on the checkerboard
    # lattice (dx=2r, dy=r); each cell = its disk minus the two disks of the
    # row below, which cut it exactly at (+-r, 0) and (0, r). The boundary is
    # assembled from QUARTER arcs fetched through center(i, j), so a bite is
    # bit-for-bit the neighbour's dome quarter -> exact partition, no slivers.
    # Pitch from _arc_pitch (the scale radius does not grow with the frame —
    # the truchet_hex faceting trap). Pure trig, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("scales", False): "400f430b60ebbb176506e09f8b8b68546a277adffe525c00baa933d62407d084",
    ("scales", True): "de4a239d4e444e68f30a6ab3dc050ddb86b4fa42face787dd72e37dcadd2f34e",
    # nautilus: log-polar chambers about a pole OUTSIDE the frame
    # (-0.55*cx, -0.30*cy — the scheme's (-1.55, -1.30) in half-frame units),
    # constant nsec + g = 1 + 2*pi/nsec so chambers stay square as they grow.
    # The outside pole IS the 'good centre' answer: the visible radius band is
    # bounded away from zero, so no cap fan and nothing collapses. Per-ring
    # swirl makes ring arcs T-junction (voderberg precedent) — coverage is
    # gated in FLOAT, not by a formal partition. Verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("nautilus", False): "384d829b93e441f460c70d691f77e5cf0a1e6e9976fed43561fe544e199bf514",
    ("nautilus", True): "249bd49993a4f37efc547628490c367fc86c3e19c1e2383ba9305c1fa1ae404a",
    # rosette_fractal: triangulated log-polar aloe whose sector count doubles
    # outward (the pole fix). The rings-per-doubling is DERIVED, m =
    # round(ln2/ln(1+2pi/N)), not the scheme's fixed 3 — a fixed m doubles the
    # cell aspect ratio every period (64:1 by the 8th doubling, ~5 of which a
    # 16K frame spans); the derived m holds it at 0.79-1.00 and reproduces
    # m=3 at N=24. Seams are _edge polylines addressed by (ring, vertex), so
    # both sides sample identically -> formally verified exact partition.
    # Verified across two interpreters, one with PYTHONHASHSEED=1.
    ("rosette_fractal", False): "fe32fdc187f5544e3e9ac1596f31d062a260115e10bd3b27a6437dccd4225d0f",
    ("rosette_fractal", True): "d794018172c7f4c23319dd196c8c27fe90c9415cc3ec5c93a087da668fffe1bf",
    # E7 (2026-07-20). The Sierpinski family emits EVERY triangle/square as a
    # cell, gasket and hole alike — the fractal reads through photo SCALE
    # (holes become progressively larger single photos), not empty space.
    # T-junctions are inherent and intended: a hole is one cell facing
    # subdivided gasket neighbours, so coverage (min == 1.000, straight edges)
    # is the instrument, never a formal partition. sierpinski: depth 3 with an
    # S/2 brick stagger, verified to add no T-junctions beyond the inherent
    # ones (S/3 and S/5 do). sierpinski_d: checkerboard carrier (t+r)%2 on a
    # deliberately UNstaggered grid, big holes offset half a period per row.
    # carpet: depth 4, holes only from level 2 so the smallest is always 3x
    # the background cell; recursion pruned against the frame (42k -> 167
    # cells at 800x600). Pure integer/midpoint arithmetic, no RNG; verified
    # across two interpreters, one with PYTHONHASHSEED=1.
    ("sierpinski", False): "2077d0b94a11d64eb5eaebec1b51ddeeef24151978f1f0561c88042cbfb41122",
    ("sierpinski", True): "98d2601095731c9f246ac3545de0efa78f10e2bf860633d0bc2b8b064faacfe7",
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
