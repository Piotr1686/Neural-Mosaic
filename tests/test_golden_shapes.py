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
# 2026-08-20: ALL 90 regenerated after the anti-repetition penalty gained a
# colour-fidelity band (freq_tolerance_de). The penalty used to be unbounded, so
# used_counts**2 eventually outgrew any distance gap and flat regions filled
# with dark, badly-matching tiles; it is now confined to a dE budget around each
# sector's best match. The band re-ranks candidates in every sector that has
# seen a repeat, so nothing stayed bit-identical this time -- including
# square/False, which had survived both 2026-07-08 changes.
GOLDEN = {
    # 2026-07-21: square + hexagon_romb regenerated after the standard-grid /
    # hexagon_romb branches stopped BLACK-padding partial edge crops (they now
    # mean-fill the off-canvas remainder and paste the visible content at its
    # true position). Deliberate matching fix: black padding was dragging edge
    # tiles' LAB features dark and matching dark tiles (brick_wall's left
    # half-bricks). Only these grid goldens moved; kites/spectre/polygon use
    # branches that already pasted at the true offset and are unchanged.
    ("square", False): "868586c964f3a7f1cbd664d2f52bedbe780ba8939fcb8c3e9d798ec3111c724d",
    ("square", True): "177c3d78c936ed354377e77a16d8cd960c72b19acea9ee20e9cdfbedee8829f3",
    ("hexagon_romb", False): "08bb1d76af0776deb6e5980be4fabb1a0413984d26bf961eab704e0ecb948379",
    ("hexagon_romb", True): "9f2ddb02187ed8b41af41e5fb00f5180c6bd3c27138ed9f3368e936073640bb1",
    # 2026-07-26: kites regenerated after the border cull changed from
    # "centroid inside the frame" to "bbox overlaps the frame". The old test
    # dropped every border kite whose centre fell outside, leaving a saw-tooth
    # of bare canvas along the right/bottom/top edges (2.35% of the frame, up
    # to 12.6% inside the bottom band). Deliberate coverage fix — see
    # test_kites_covers_the_whole_frame in tests/test_grout_engine.py.
    ("kites", False): "97342d572b0a1b1ca8ba0ecaaa682ed6df1ddf07bec2bc2b1187c79efc1e0411",
    ("kites", True): "97925a937ced8cb2fe4e3ba171889f46f70a073c7f1436093f926e9b537835e1",
    ("spectre", False): "f94d8d5855307d91baf38d4882488eceaa9c7f69c18e4bcc745c4f5d3b822a2b",
    ("spectre", True): "fd3160717e51029d0726cb96ef7a3769f7a4e55ded56e81b41886975adc1621e",
    # New polygon shape wired via the generic dispatch + _polygon_sector
    # (2026-07-10). Geometry is deterministic (Vogel seeds + Voronoi, no RNG),
    # so these hashes lock the first render — no "before" to match against.
    ("sunflower_grande", False): "96e4536af00f06e48336d6d01daf1330d9245a7df3a8bd5266a29f5da31fa891",
    ("sunflower_grande", True): "05372f251353314e785675c085f8da9198de9856888754dc72e854df351601e8",
    ("sunflower_grande_inverse", False): "6142c5baf768869a7c909f9ab77b659351ccaa9e09993d466252a1ff1f1a31e8",
    ("sunflower_grande_inverse", True): "54d5b0a2e49ba1587142b512d51eb4f8c8f367fac69b7815c82cb53b2425781f",
    ("sunflower_soft", False): "3aedad57de60b3b39d91f20c045aae4c880ee2cc2f30820d4d90eb89617f9f77",
    ("sunflower_soft", True): "3173518a2a4f7ae502ba4a5b0dfeef3bef764beebadfa484ffea8c37ee8c1354",
    ("sunflower_rings", False): "77b98fdccc4d8635e85934a53a61c76461942478dbf6ff2abe506e0e119f5a8b",
    ("sunflower_rings", True): "8bfb06e0170a6c2719f8f0365e6ca9cf85d54ff6e368cc679bdd3ee942b56ba6",
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
    ("voronoi", False): "12a3f00ddc7280b9462d1746e00db514031089555092ee88a7963e28e4a25474",
    ("voronoi", True): "22de9d2e18cab871bd3ca18c5d89087659f57dbfbed6df9783b8910c81bd7c3a",
    ("phyllotaxis", False): "42bf7e9ef4717fc84943479e2905f84b2369dbd157622e5a23648dc1d83933b9",
    ("phyllotaxis", True): "31a84c2f0da0d96f5784f776386068933549428f917ed6fcdc2d56ddaf9a55e3",
    # Deterministic Fable tessellations (2026-07-11): geometry ported from
    # gen_fable_shape_schemes.py, pure constructions (no RNG). Hashes lock the
    # first render, verified identical across two separate processes.
    ("pinwheel", False): "5d44a338fd960f7870784d9f2902cab06086a88eca4fc18b33cc7f153ba8fec5",
    ("pinwheel", True): "ef34219a8992316b9734c7b58f9a16de4bdf8fedaa5928b09e7a634d916ca731",
    ("cairo", False): "92a8318b6ad0e3a08a2927675599572b6f5a05cd9cda38580eb909e3136b0a51",
    ("cairo", True): "36cd2b3fa74586bcde5fc8ffecc92e34a3af4d7998d966210838f4647064c80d",
    ("floret", False): "48fb92c262ea0169e5069930281a6ae84ed9c0d45f5af48fef5e1651c303fdc2",
    ("floret", True): "6f3fb9b708a4f7b0fe5bc755aba2d20524c8f78ce6e8b05ace7153516f5e91b4",
    ("gosper", False): "dab852a9e46434bb9c77c2307e6d64816511a0b87cdeff980027a737485bc6f7",
    ("gosper", True): "791dab9692fe907f721a9a89a222e4c88c33f6c0f1a20a35361e089021670dac",
    # Archimedean tessellations + sunburst (2026-07-11): rebuilt from the
    # scheme PNGs (original generator code was lost with the Opus scratchpad).
    # Pure constructions (no RNG); hashes lock the first render, verified
    # identical across two separate processes.
    ("trunc_square", False): "2a49e68f84df479a5614abcae2b5a1ade051d181e3670a726ce7feba9b04373f",
    ("trunc_square", True): "5ad385d38a17b0b9d722ad5bef8e0f4d71c9cbac8f5cc6a090d4d64c24361e85",
    ("trunc_hex", False): "fd17ee77f1519b85d84407ab9766dc027a02c8a2081c32e596d49939d02b2a13",
    ("trunc_hex", True): "e9c516d3218bb9d5fe5fb5fc5eb9eabfbe7657d63b4da80dab164d9d6e6b506b",
    ("rhombitrihex", False): "44aa33ea326c3a27677920d71a86b1c662069750f91fa36b3915cb49252bac1e",
    ("rhombitrihex", True): "b31c6fc8a0d20fe0b5520f7e27df9fe6d62000c774159d86db17db8f983d12a0",
    ("pythagorean", False): "e26f49a52ec4d1d45e6ace3e1c3f7724a77b3c0b37dc43314e8fa4665dbca9fc",
    ("pythagorean", True): "9d7220f96fbde2cdcbc1729ceac2b36637b194cb4365faca54696aa9ae40502f",
    # De Bruijn multigrid duals (2026-07-11): penrose P3 (pentagrid N=5,
    # gamma sum=1) + ammann_beenker (N=4). Deterministic (fixed generic
    # offsets, no RNG); hashes lock the first render, cross-process verified.
    ("penrose", False): "f11dd9ef55b75f11bef13cf327d66aaf8bf87e0c0a42c60d1271734ccf79724e",
    ("penrose", True): "96b2dcc9bf267a545fbc7fbf4d0aebf1714f34647bcd1d9e575a35b5a5788fb8",
    ("ammann_beenker", False): "5a1859b5c87f09cc106b533bceb9fc1538459922e6abe32a7ea8ead23800bafd",
    ("ammann_beenker", True): "71286be809853a404dc1164e8db4eabc6de634a98f79716c65b73eb3c506f15f",
    # Last three Fable shapes (2026-07-13): voderberg (rings of bent slivers,
    # bow made radius-relative), escher_lizard (p1 hexagon deformation) and
    # weave (basketweave rebuilt as a true partition: visible ribbon pieces +
    # knot cells). Pure constructions (no RNG); hashes lock the first render,
    # verified identical across two separate processes.
    ("voderberg", False): "db1226e2116ba98f905f8e1ac631b70933754511a40402f810a1241fcfb64b5c",
    ("voderberg", True): "384ce624b66c88815e6fdc8901b0172e6abe5cf1eecbb04f05a0d4b436006d41",
    ("escher_lizard", False): "d8426259cbadb63eafdcbdce4ff4b08a70a477abec17b5e6fe410094a56bb601",
    ("escher_lizard", True): "ede3696258362b30d436823cd1ae420e3b1d0820267b06fe9a41679c2583b964",
    ("weave", False): "c28717fe7c28af0abd2cd801dd4b184e6a78579027332b2cfe1d6579fefd0650",
    ("weave", True): "43f629ce2c1c6b2d6e5e7e8e500f66e108c3297c4722e1185baaa0930d2bdea0",
    # Truchet (2026-07-13): arcs polygonised by _sun_arc with a sagitta-driven
    # pitch (_arc_pitch), tile orientation from an integer hash of the lattice
    # index -> no RNG, same pattern at every resolution. Cross-process verified.
    ("truchet", False): "5ea7cdb0093c50881ab39b7d74941624016dfbbb16ed92ec57498e38744311ed",
    ("truchet", True): "5e7ff9814fc7fadf5df1a7c0720ceb398fde5688ebe022b11f5b6ef9a9dc8bed",
    ("truchet_hex", False): "3633abfb3866de4f68203f0b433e17154e9b8c21172aa354909cee77211f4e17",
    ("truchet_hex", True): "62838f7bd218827c9749d86a5afdd64edff394abd2e0f553b0b0b666874e998f",
    # girih (2026-07-14): decagon rosettes seeded on a Penrose-vertex
    # quasi-lattice, greedy fill between them, leftovers traced. Carries NO RNG
    # and no frozen seed (the plan expected one), so these hashes are stable
    # across processes — verified in two separate interpreters.
    ("girih", False): "9ac4cc5be2d3ccdec8cff4b83c1366a78efd849ff63e518bf3f11fb05cc0a932",
    ("girih", True): "0fdb9014b9d5f5d86cd7235afedcbbeca758dc79549f201cc2e71d320ca82f55",
    # poincare (2026-07-15, krok 4 b++): {7,3} band tiling, heptagons split into
    # 7 khatam kites, each subdivided by a hyperbolic transfinite quad mesh. BFS
    # over disc reflections + pure geometry, NO RNG and no frozen seed — hashes
    # verified byte-identical across two separate interpreters (like girih). The
    # tmp golden library (tile_NNN.png) shares no basename with data/tiles_hires
    # (coco_*.jpg), so the hi-res overlay is a no-op here and the hash is portable.
    ("poincare", False): "16a008851c69a7678745114fe2c3b10016b9ad9377b7111eede6e42544be699e",
    ("poincare", True): "efaef9d4d82d099220fbb2d890908e605e49ac8b59e00f8392ceb36f8e8a55fb",
    # penrose_p2 (2026-07-16, sprint E1): P2 kites & darts via P3 deflation +
    # Robinson B->A conversion + mirror-twin merge. No RNG; the merge iterates
    # dicts/int-sets only, so order is process-independent — hashes verified
    # identical across two interpreters, one with PYTHONHASHSEED=1.
    ("penrose_p2", False): "3efcdc4b6b652183510df835ac693e5fe4c3e9166a0c61a1505698f1c29105b5",
    ("penrose_p2", True): "80c4cf45a9d29066eaba664c9396073be0eb41aa2a551eb8654287bce6e9bc5a",
    # E2 (2026-07-17). bloom: Lucas-angle Vogel lattice — the `angle` parameter
    # defaults to the golden angle, so all eight sunflower goldens above stay
    # bit-identical (verified). pebbles: variable-density Voronoi, seeded from
    # dimensions via _shape_seed. Both verified across two interpreters, one
    # with PYTHONHASHSEED=1.
    ("bloom", False): "5686d653537d768f212a8045c8cb13f20d708666a31ed9388008b28cb369c1bb",
    ("bloom", True): "1f54d2b5f497bec7278656c278583839673cb59fac25b25d70bdc3bccfd35bf0",
    ("pebbles", False): "febe1ea64d0fdc3f295c442c446eae2d96af9a66ea23217b9756152c858ad5f7",
    ("pebbles", True): "c103f226a616d4064f48784ff4c67febbd777e789755ca68531711b6b1cba8be",
    # E3 (2026-07-17). stagger_tri: triangle rows at a constant x-phase, so the
    # rows slip and every row line is a T-junction seam. NOT `triangle`, which
    # shifts the phase by half a base each row via its (c+r)%2 flip rule — see
    # the translation-invariant gate in test_grout_engine. Pure arithmetic, no
    # RNG; verified across two interpreters, one with PYTHONHASHSEED=1.
    ("stagger_tri", False): "52713cc11967221a5978ecf59928e54ed143e077ae0e6680a718624afdbbca64",
    ("stagger_tri", True): "ff9b06374cd8bb57d52f948c8e790e615edbd0754b9cc2aca765594f95be7286",
    # braid (2026-07-18): basketweave rebuilt as a true partition — 2x1 bricks
    # in alternating horizontal/vertical pairs on a 2x2 checkerboard. NOT
    # `brick_wall` (single running bond, one orientation); the extra vertical
    # bricks are an orientation set no rigid motion adds, proven by the
    # translation-invariant gate in test_grout_engine. Pure arithmetic, no RNG;
    # verified across two interpreters, one with PYTHONHASHSEED=1.
    ("braid", False): "4395ed08c5770991a74cd3f996fad974888e8a0bfcf97de7c92f77c1c19dff3a",
    ("braid", True): "73b77d6da5199039973303254381ff2b33c66d6ede66a1bacd713bf13a432c9e",
    # moire (2026-07-18): a quad grid displaced by a two-grating interference
    # field. Cells stay gap-free (shared displaced vertices) but warp in
    # shape/size with the beat — verified on a real render NOT to collapse to
    # `square` (CV of cell area ~0.27, only ~28% of edges axis-aligned; a square
    # lattice would be 0 and 100%). Pure arithmetic, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("moire", False): "3f94f15cffa3f77773fce0035f07305769c5f5a01271ad6a9ea087eef2a5acf5",
    ("moire", True): "1d42784ec3b1da9f04b16e961b9b896068d2f036613dc178af3f5cbad4fa2431",
    # puzzle family (2026-07-19, sprint P): die-cut jigsaw tabs as per-edge
    # shared polylines (crc32-keyed, no RNG) on three lattices — classic
    # ribbon-cut grid, sine-warped ribbon grid, flat-top hex. Verified across
    # two interpreters, one with PYTHONHASHSEED=1. The dedup of the profile's
    # junction vertices is load-bearing: doubled consecutive points broke
    # Pillow's scanline parity inside the aa=4 masks (1-2 px strips).
    ("puzzle_classic", False): "d0e7e634bd486cc847c3b8b38c86db3c59bb189dfcc921b310c6696e7a239013",
    ("puzzle_classic", True): "880da15e26bb3e985f52212f5e83346692410f22942075599c9b4be22bc1d8aa",
    ("puzzle_ribbon", False): "102be32d1555c4403b4aac4c3322a5f756629bbe207e8132c5b8b2469534ab59",
    ("puzzle_ribbon", True): "29e5c3d8925bbf6f24e1352cac13f34f0240346380d0afa2b717738a0400125e",
    ("puzzle_hex", False): "ea96ce5aa111fdd83b43752e35c15d5d902ad501f1d06fdbb4952ca6ca6e034f",
    ("puzzle_hex", True): "b08807fc6b2af89ec7be565abe7c139f8e227311a7956ef2b759a0c7278ac68a",
    # E4 (2026-07-19). dragon: order-8 twindragon rep-tile, boundary chained
    # from edge-cancelled unit squares (sharpest-left at pinches); (1+i)^8=16
    # so the tile lattice is the square lattice, u=base_s/16 -> area exactly
    # base_s^2. Only int/int-tuple hashing (unsalted), verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("dragon", False): "21c94df025e2cf39447019c327f1c318446051815e66ef79faa1b1d64438f513",
    ("dragon", True): "63fed11629e161222bea9f2a69e95e8b8c0583edce7000e62d15b012dd1c2d87",
    # koch_island: depth-2 Minkowski teragon walked on an INTEGER turtle
    # (exact coords), period 4^2 = 16 units (NOT the bbox — the 2026-07-03
    # trap), area-preserving generator -> tile area base_s^2 exactly.
    # koch_snowflake: two-size tessellation (big flakes + 2x small 1/sqrt(3)
    # rotated 30 deg in the lattice holes), depth FIXED at 4 — finite-depth
    # seams are sub-pixel (min coverage 0.686 vs voderberg's shipped 0.502).
    # Both verified across two interpreters, one with PYTHONHASHSEED=1.
    ("koch_island", False): "ab6a6ee1f5cd666ed192c999ed6a3ac15c08e1e9a7ea784ab58b87cd8d2bc207",
    ("koch_island", True): "84a9599d6a5e75e3596acdc408e98851a822fe1c122ce29027493009f0a63a3b",
    ("koch_snowflake", False): "e10145db1c7a37f671891ba4a7b6e1eb26e4adf884695e47ed82416212a953e0",
    ("koch_snowflake", True): "b739f1158ee67101e50cf798cee96c36ce1822678adc90672acdcfa335842fc1",
    # E5 (2026-07-19). gereh: 4.8.8 with every octagon split into 16 kites
    # (8-point khatam star, r_in=0.60*apothem); the gap square is the DIAMOND
    # with vertices on the axes — the scheme's axis-aligned square (phase
    # pi/4) was a real bug hidden by the proposal PNG's outlines (11k hole px,
    # caught by the coverage gate). rosette: 3.12.12, dodecagon -> 12 core
    # kites + 12 petals + 12 edge triangles; interstitial holes anchored
    # analytically at lattice-triangle centroids (the filtered-centre trap
    # cannot occur). Both pure trig, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("gereh", False): "549c91dbed7ac30cf880c5fa2dd69cd24ca7084752ac7a6491457aaa526fe473",
    ("gereh", True): "cef33eaacefa744b890ea11e29fc6686166a26b68d057ad674f63ff0982eb34c",
    ("rosette", False): "deedd63d1617d4a51b3bc91805790891b2be978fd52aff08859803288100c660",
    ("rosette", True): "4462c94a26ac7c699a69447657e0959c7a83862996566fdc049d4b5336c66e84",
    # E6 (2026-07-20). scales: circles of r=base_s/sqrt(2) on the checkerboard
    # lattice (dx=2r, dy=r); each cell = its disk minus the two disks of the
    # row below, which cut it exactly at (+-r, 0) and (0, r). The boundary is
    # assembled from QUARTER arcs fetched through center(i, j), so a bite is
    # bit-for-bit the neighbour's dome quarter -> exact partition, no slivers.
    # Pitch from _arc_pitch (the scale radius does not grow with the frame —
    # the truchet_hex faceting trap). Pure trig, no RNG; verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("scales", False): "d4b4e273afff174ec4ce9ad33aa1da2b4961aebf9a7951ee6b9077af6a9d8cdb",
    ("scales", True): "383a1db024c11d539e7d9368f313e9116cf074c5bb501aae00f2f36f4e5aa037",
    # nautilus: log-polar chambers about a pole OUTSIDE the frame
    # (-0.55*cx, -0.30*cy — the scheme's (-1.55, -1.30) in half-frame units),
    # constant nsec + g = 1 + 2*pi/nsec so chambers stay square as they grow.
    # The outside pole IS the 'good centre' answer: the visible radius band is
    # bounded away from zero, so no cap fan and nothing collapses. Per-ring
    # swirl makes ring arcs T-junction (voderberg precedent) — coverage is
    # gated in FLOAT, not by a formal partition. Verified across two
    # interpreters, one with PYTHONHASHSEED=1.
    ("nautilus", False): "f3b9a18480ca1354cfad79a20cdebaaf6a39f0abff15ca35e1f75c6696bbdada",
    ("nautilus", True): "aa2b88225c34f744aeb0f15376c996f4a33d82264bd7086492160624f06a8caa",
    # rosette_fractal: triangulated log-polar aloe whose sector count doubles
    # outward (the pole fix). The rings-per-doubling is DERIVED, m =
    # round(ln2/ln(1+2pi/N)), not the scheme's fixed 3 — a fixed m doubles the
    # cell aspect ratio every period (64:1 by the 8th doubling, ~5 of which a
    # 16K frame spans); the derived m holds it at 0.79-1.00 and reproduces
    # m=3 at N=24. Seams are _edge polylines addressed by (ring, vertex), so
    # both sides sample identically -> formally verified exact partition.
    # Verified across two interpreters, one with PYTHONHASHSEED=1.
    ("rosette_fractal", False): "0747a8d5439d8e37c2404d4bbabc0829a1ef4c311a2c11b91ec77f7ec135a69f",
    ("rosette_fractal", True): "8b3813ca2c62b4bd14d1a57f52e155cd23251ced8d9d01cfcbd18421659a40e5",
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
    ("sierpinski", False): "30d1f503fc36c6b9bbf4b7feed596e56eb4183c2ce5168106b8658c1137fc0f1",
    ("sierpinski", True): "0e30f5051aa9e1fd906061b77bd926927beb69cc5ed7554f15a7e3c548ae416d",
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
    # freq_tolerance_de is pinned to a literal rather than left to the engine
    # default on purpose: these hashes lock the *matcher*, so re-tuning the
    # shipped default must not silently invalidate 90 goldens (and a golden run
    # must not quietly start testing a different band than the one it locked).
    e.settings = {"allow_mirror": True, "edge_aware": False,
                  "freq_penalty": 30.0, "freq_tolerance_de": 2.0}
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
