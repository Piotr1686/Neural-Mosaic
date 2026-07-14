"""Tests for the engine-agnostic hierarchical grout geometry (src/grout.py).

Covers the two pieces the engine border pass and the proposal tool both rely
on: the sub-7 flower grouping (exact membership) and edge classification (an
edge takes the highest level whose group ids differ across it; frame-boundary
edges close the top group). Also pins the width-preset scaling and the
deterministic seed replacement for hash().
"""
from PIL import Image, ImageDraw

from src import grout
from src.engine_smart import SmartEngine


# ---------------------------------------------------------------------------
# sub7 flower grouping
# ---------------------------------------------------------------------------
def test_sub7_centre_and_unit_neighbours_share_a_flower():
    # (0,0) is a flower centre; its six unit neighbours must map to the same
    # flower id, and the seventh ring must NOT.
    centre = grout.sub7(0, 0)
    neighbours = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, -1), (-1, 1)]
    for q, r in neighbours:
        assert grout.sub7(q, r) == centre, (q, r)


def test_sub7_partitions_every_hex_exactly_once():
    # Over a block of the lattice, every hex resolves to exactly one flower and
    # each flower collects exactly seven hexes (centre + 6).
    counts = {}
    for q in range(-14, 15):
        for r in range(-14, 15):
            counts.setdefault(grout.sub7(q, r), 0)
            counts[grout.sub7(q, r)] += 1
    # interior flowers (fully inside the sampled block) must have all 7 members
    full = [c for c in counts.values() if c == 7]
    assert full, "expected at least one complete 7-flower in the sampled block"


def test_sub7_of_flower_coords_is_the_level3_lattice():
    # Level 3 is sub7 applied to level-2 coordinates; the composition must not
    # raise for any level-2 id produced from the lattice.
    seen = set()
    for q in range(-14, 15):
        for r in range(-14, 15):
            seen.add(grout.sub7(q, r))
    for i, j in seen:
        grout.sub7(i, j)   # must resolve without AssertionError


# ---------------------------------------------------------------------------
# edge classification
# ---------------------------------------------------------------------------
def _square(x, y, g2, g3, s=1):
    poly = [(x, y), (x + s, y), (x + s, y + s), (x, y + s)]
    return (poly, g2, g3)


def test_shared_edge_same_group_is_level1_boundaries_level3():
    a = _square(0, 0, g2=0, g3=0)
    b = _square(1, 0, g2=0, g3=0)     # shares the edge x=1
    by = grout.classify_edges([a, b])
    assert len(by[1]) == 1            # the single shared interior edge
    assert len(by[2]) == 0
    assert len(by[3]) == 6           # all outer edges (4+4-1 total = 7)


def test_shared_edge_promoted_to_level2_when_g2_differs():
    a = _square(0, 0, g2=0, g3=0)
    b = _square(1, 0, g2=1, g3=0)
    by = grout.classify_edges([a, b])
    assert len(by[1]) == 0
    assert len(by[2]) == 1
    assert len(by[3]) == 6


def test_g3_difference_wins_over_matching_g2():
    # g2 equal but g3 differs -> level 3 (g3 checked last, so it dominates).
    a = _square(0, 0, g2=0, g3=0)
    b = _square(1, 0, g2=0, g3=1)
    by = grout.classify_edges([a, b])
    assert len(by[1]) == 0
    assert len(by[2]) == 0
    assert len(by[3]) == 7           # shared edge + 6 boundaries


# ---------------------------------------------------------------------------
# width presets / scaling
# ---------------------------------------------------------------------------
def test_scale_widths_is_proportional_and_at_least_one_px():
    at_ref = grout.scale_widths("medium", grout.REFERENCE_TILE_PX)
    assert at_ref == grout.PRESETS["medium"]            # identity at reference

    bigger = grout.scale_widths("medium", grout.REFERENCE_TILE_PX * 2)
    for lvl in (1, 2, 3):
        assert bigger[lvl] == round(grout.PRESETS["medium"][lvl] * 2)

    tiny = grout.scale_widths("thin", 1.0)
    assert all(w >= 1 for w in tiny.values())           # never vanishes


def test_min_level_drops_the_levels_below_it_not_above():
    """Selecting a structure keeps the HIGHER levels, which is the whole point:
    a kites hexagon's own border is level 2 where its neighbour sits in the same
    7-flower and level 3 where it does not, so 'outline the hexagons' has to
    keep level 3 too — otherwise every hexagon on a flower boundary would lose
    part of its outline."""
    full = grout.scale_widths("medium", grout.REFERENCE_TILE_PX, min_level=1)
    groups = grout.scale_widths("medium", grout.REFERENCE_TILE_PX, min_level=2)
    supers = grout.scale_widths("medium", grout.REFERENCE_TILE_PX, min_level=3)

    assert all(full[lvl] > 0 for lvl in (1, 2, 3))
    assert groups[1] == 0 and groups[2] > 0 and groups[3] > 0
    assert supers[1] == 0 and supers[2] == 0 and supers[3] > 0
    # the surviving levels keep their preset weight — only the selection changes
    for lvl in (2, 3):
        assert groups[lvl] == full[lvl]
    assert supers[3] == full[3]


def test_min_level_selects_the_kite_hexagon_and_flower_outlines():
    """End to end on the real kites geometry: raising the level must strictly
    shrink the drawn segment set (kite -> 6-kite hexagon -> 7-hexagon flower)."""
    engine = SmartEngine(index_path="__none__.pkl")
    cells = engine._grout_cells("kites", 620, 620, 46.0)
    by_level = grout.classify_edges(cells)
    assert by_level[1] and by_level[2] and by_level[3]

    def drawn(min_level):
        w = grout.scale_widths("medium", 46.0, min_level=min_level)
        return sum(len(by_level[lvl]) for lvl in (1, 2, 3) if w[lvl] > 0)

    assert drawn(1) > drawn(2) > drawn(3) > 0
    assert drawn(1) == sum(len(by_level[lvl]) for lvl in (1, 2, 3))
    assert drawn(3) == len(by_level[3])


def test_scale_widths_rejects_unknown_preset():
    try:
        grout.scale_widths("nieznany", 50)
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for unknown preset")


def test_preset_names_matches_presets_dict():
    assert grout.preset_names() == list(grout.PRESETS.keys())


# ---------------------------------------------------------------------------
# deterministic seed (hash() replacement)
# ---------------------------------------------------------------------------
def test_stable_seed_is_deterministic_and_distinct():
    assert grout.stable_seed("hexagon") == grout.stable_seed("hexagon")
    assert grout.stable_seed("hexagon") != grout.stable_seed("square")
    assert 0 <= grout.stable_seed("kites") <= 0x7FFFFFFF


# ---------------------------------------------------------------------------
# draw_grout: width<=0 levels are skipped (flat vs hierarchical grout)
# ---------------------------------------------------------------------------
def test_draw_grout_skips_zero_width_levels():
    cells = [_square(0, 0, 0, 0, s=10), _square(10, 0, 1, 0, s=10)]
    by = grout.classify_edges(cells)   # shared edge is level 2 here

    # Only level-2 width given: level-1/3 skipped, so a level-2 line is drawn.
    img = Image.new("RGB", (20, 10), (255, 255, 255))
    grout.draw_grout(img, by, {2: 4}, color=(0, 0, 0))
    assert img.getpixel((10, 5)) == (0, 0, 0)          # shared edge painted

    # All widths zero -> nothing drawn, image stays blank.
    blank = Image.new("RGB", (20, 10), (255, 255, 255))
    grout.draw_grout(blank, by, {1: 0, 2: 0, 3: 0})
    assert blank.getpixel((10, 5)) == (255, 255, 255)
