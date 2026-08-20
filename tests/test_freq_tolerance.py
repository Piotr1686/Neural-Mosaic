"""Tests for `freq_tolerance_de` — the colour-fidelity band bounding the
anti-repetition penalty (src/engine_smart.py, matching loop).

The penalty `used_counts**2 * freq_penalty * 0.001` used to be unbounded, so in
a flat region (sky) the counter eventually outgrew every distance gap in the
top-K list and the engine reached past all the tiles that actually matched,
down to dark, badly-matching ones. Measured at 8K on a real photo: 6.52% dark
pixels in the sky patch and sky_std 8.1x the original.

`freq_tolerance_de` bounds the penalty to a fixed colour budget (CIELAB dE per
feature cell) around the sector's best distance, so the penalty may reorder
candidates *inside* the band but can never promote one from outside it. The
band is absolute rather than a fraction of the best distance: a relative band
collapses where the library holds a near-exact match and widens exactly where
the match is poor. These tests lock:

* out-of-band tiles are never reached, however high the counters climb,
* the penalty still does its job inside the band (usage stays spread),
* the band is what does the work (unbounded tolerance reproduces the old bug),
* legacy settings dicts without the key keep working.
"""
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image

from src.engine_smart import DEFAULT_FREQ_TOLERANCE_DE, SmartEngine

# One badly-matching tile (near-black) among many near-identical sky-blues.
# The blues differ just enough to be ordered but all sit close together; the
# dark tile is far outside any sane band.
#
# The count matters: `forbidden_indices` (the hard neighbour ban) is a SECOND,
# independent way to reach an out-of-band tile — when every good tile is already
# on a neighbour, the ban's +1e6 pushes the choice onto the dark one no matter
# what the penalty does. With too few blues the ban exhausts them and every test
# here measures the ban instead of the penalty. 40 comfortably outnumbers the
# neighbourhood, isolating the penalty as intended.
#
# None of them matches the target exactly, so the sector's best distance is > 0,
# as it is on real photos.
DARK = (12, 12, 14)
BLUES = [(120 + (i % 5), 150 + (i // 5) % 5, 200 + (i // 25))
         for i in range(40)]


def _make_engine(tmp_path):
    """SmartEngine over 12 near-identical blues + 1 dark outlier (index 0)."""
    e = SmartEngine(index_path="__none__.pkl")
    paths, feats = [], []
    for i, col in enumerate([DARK] + BLUES):
        p = tmp_path / f"tile_{i:03d}.png"
        Image.new("RGB", (120, 120), col).save(p)
        paths.append(str(p))
        feats.append(e._compute_sector_feature(
            Image.new("RGB", (120, 120), col), edge_aware=True))
    e.paths = paths
    e.features = np.array(feats, dtype=np.float32)
    e.settings = {"allow_mirror": False, "edge_aware": False,
                  "freq_penalty": 30.0, "freq_tolerance_de": 2.0}
    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    return e


def _flat_sky(tmp_path):
    """A flat sky-blue target: every sector gets the same top-K list, which is
    exactly the situation that used to inflate the counters without bound.

    Rendered at 4K, so the ~1100 sectors drive the counters past the point where
    an unbounded penalty (count**2 * 0.03) outgrows the ~3.8 distance gap to the
    dark tile. At 2K the counters top out around 10 and the old defect does not
    reproduce at all — the sector count is part of the fixture, not a detail."""
    p = tmp_path / "sky.png"
    Image.new("RGB", (900, 600), (126, 156, 206)).save(p)
    return p


def _render(engine, tmp_path, name, **settings):
    """Render the flat sky; return (counts by tile name, dark pixels on canvas).

    Two observables, because they answer different questions. `counts` comes
    from used_counts and includes the off-canvas wedge sectors the grid walk
    emits from index -1 — a handful of those legitimately match the dark tile
    (their target crop runs off the image) and never reach a visible pixel. The
    dark-pixel count is what the viewer actually sees.
    """
    engine.settings.update(settings)
    out = tmp_path / f"{name}.jpg"
    engine.create_mosaic(
        _flat_sky(tmp_path), out, "4K", "square", tile_scale=1.0,
        border_mode=False, blend_strength=0.0, tint_strength=0.0,
        grout_preset=None, save_used_tiles=True,
    )
    report = json.loads(
        out.with_name(f"{out.stem}_used_tiles.json").read_text(encoding="utf-8"))
    counts = {t["name"]: t["count"] for t in report["tiles"]}
    arr = np.asarray(Image.open(out).convert("RGB"), dtype=np.int16)
    dark_px = int((arr.sum(axis=2) < 200).sum())
    return counts, dark_px


# ---------------------------------------------------------------------------
# The invariant: the penalty can never promote an out-of-band candidate
# ---------------------------------------------------------------------------

def test_dark_outlier_never_reaches_the_canvas(tmp_path):
    """The defect this bound exists to stop, stated as the viewer sees it."""
    e = _make_engine(tmp_path)
    _, dark_px = _render(e, tmp_path, "banded", freq_tolerance_de=2.0)
    assert dark_px == 0, (
        f"the dark tile is ~30 dE outside the band and must never be painted, "
        f"however high the counters climb; got {dark_px} dark pixels")


def test_penalty_adds_no_out_of_band_placements(tmp_path):
    """Sharper form: with the band on, the penalty places the dark tile no more
    often than a matcher with the penalty switched off entirely does."""
    e = _make_engine(tmp_path)
    banded, _ = _render(e, tmp_path, "banded_cnt", freq_tolerance_de=2.0)
    e2 = _make_engine(tmp_path)
    strict, _ = _render(e2, tmp_path, "strict_cnt", freq_tolerance_de=0.0)
    assert banded.get("tile_000.png", 0) <= strict.get("tile_000.png", 0), (
        f"penalty added dark placements: {banded.get('tile_000.png', 0)} "
        f"vs {strict.get('tile_000.png', 0)} with the penalty off")


def test_unbounded_band_reproduces_the_old_defect(tmp_path):
    """Guards the claim that the *band* is what fixes this: with the bound
    effectively removed the penalty still walks off the end of the list and
    paints the dark tile into the sky."""
    e = _make_engine(tmp_path)
    _, dark_px = _render(e, tmp_path, "unbounded", freq_tolerance_de=1e9)
    assert dark_px > 0, (
        "without a band the counters should still push the choice onto the "
        "dark tile - if they no longer do, this fixture stopped testing the "
        "defect it was built for")


# ---------------------------------------------------------------------------
# The penalty must still work inside the band
# ---------------------------------------------------------------------------

def test_penalty_still_spreads_usage_inside_the_band(tmp_path):
    """Bounding the penalty must not amount to switching it off: usage inside
    the band stays far more even than with the penalty disabled."""
    e = _make_engine(tmp_path)
    banded, _ = _render(e, tmp_path, "spread_banded", freq_tolerance_de=2.0)
    e2 = _make_engine(tmp_path)
    off, _ = _render(e2, tmp_path, "spread_off", freq_tolerance_de=0.0)

    assert max(banded.values()) * 2 < max(off.values()), (
        f"banded max={max(banded.values())} should be far below "
        f"unpenalised max={max(off.values())}")
    assert len(banded) > 3 * len(off), (
        f"banded should use many more distinct tiles: "
        f"{len(banded)} vs {len(off)}")


def test_zero_tolerance_gives_a_strict_matcher(tmp_path):
    """tol=0 collapses the band to nothing, so nothing is ever penalised and
    the best colour always wins — a strict matcher, not the old runaway."""
    e = _make_engine(tmp_path)
    _, dark_px = _render(e, tmp_path, "strict", freq_tolerance_de=0.0)
    assert dark_px == 0


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

def test_engine_default_and_matcher_fallback_cannot_drift():
    """The budget is written in two places — the settings dict the engine
    builds on load, and the fallback the matcher reads for dicts that predate
    the key. A silent divergence would make hand-built callers render
    differently from the GUI, so both come from one constant."""
    src = Path("src/engine_smart.py").read_text(encoding="utf-8")
    assert '"freq_tolerance_de": DEFAULT_FREQ_TOLERANCE_DE' in src
    assert '"freq_tolerance_de", DEFAULT_FREQ_TOLERANCE_DE' in src
    assert DEFAULT_FREQ_TOLERANCE_DE > 0.0


def test_legacy_settings_dict_without_the_key_still_renders(tmp_path):
    """Tests and tools hand-build settings dicts that predate the key; the
    matcher reads it with a default rather than raising KeyError."""
    e = _make_engine(tmp_path)
    e.settings = {"allow_mirror": False, "edge_aware": False,
                  "freq_penalty": 30.0}                   # no freq_tolerance_de
    out = tmp_path / "legacy.jpg"
    e.create_mosaic(
        _flat_sky(tmp_path), out, "4K", "square", tile_scale=1.0,
        border_mode=False, blend_strength=0.0, tint_strength=0.0,
        grout_preset=None,
    )
    assert out.exists()
