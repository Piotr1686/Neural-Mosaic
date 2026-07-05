"""Tests for mid-render cancellation (cancel_event) in both engines.

The GUI passes a threading.Event to create_mosaic/process; the engines poll it
at loop boundaries and raise RenderCancelled. A cancelled render must abort
BEFORE the output file is written.
"""
import pickle
import threading
from unittest.mock import mock_open, patch

import pytest
from PIL import Image

from src.engine_smart import SmartEngine
from src.engine_typo import TypoEngine
from src.render_control import RenderCancelled
from tests.test_golden_shapes import _build_library, _make_target


@pytest.fixture()
def small_engine(tmp_path):
    paths, feats = _build_library(tmp_path)
    e = SmartEngine(index_path="__none__.pkl")
    e.paths = paths
    e.features = feats
    e.settings = {"allow_mirror": False, "edge_aware": False, "freq_penalty": 30.0}
    e._neighbors_cache = {}
    e._neighbors_lock = threading.Lock()
    return e


class TestSmartCancel:
    def test_preset_event_raises_render_cancelled(self, small_engine):
        ev = threading.Event()
        ev.set()
        with pytest.raises(RenderCancelled):
            small_engine._do_render(
                _make_target(), "square", tile_scale=0.5, cancel_event=ev
            )

    @pytest.mark.parametrize("shape", ["kites", "spectre"])
    def test_polygon_branches_poll_cancel(self, small_engine, shape):
        ev = threading.Event()
        ev.set()
        with pytest.raises(RenderCancelled):
            small_engine._do_render(
                _make_target(), shape, tile_scale=0.5, cancel_event=ev
            )

    def test_cancelled_create_mosaic_writes_no_file(self, small_engine, tmp_path):
        target_path = tmp_path / "target.png"
        _make_target().save(target_path)
        out_path = tmp_path / "out.jpg"
        ev = threading.Event()
        ev.set()
        with pytest.raises(RenderCancelled):
            small_engine.create_mosaic(
                str(target_path), str(out_path), "2K", "square",
                tile_scale=0.5, cancel_event=ev,
            )
        assert not out_path.exists(), "cancelled render must not write output"

    def test_unset_event_renders_normally(self, small_engine):
        ev = threading.Event()  # never set
        out = small_engine._do_render(
            _make_target(), "square", tile_scale=0.5, cancel_event=ev
        )
        assert out is not None and out.size == _make_target().size


class TestTypoCancel:
    def _engine(self):
        raw_lib = [
            {"char": c, "norm_density": round(i * 0.1, 1),
             "font": "NotoSans-Regular.ttf", "density": i * 25}
            for i, c in enumerate("ABCDE")
        ]
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()):
                with patch("pickle.load", return_value=raw_lib):
                    return TypoEngine()

    def test_preset_event_raises_render_cancelled(self):
        e = self._engine()
        ev = threading.Event()
        ev.set()
        img = Image.new("RGB", (200, 200), (128, 128, 128))
        # Poll fires on the first row, before any glyph/font work happens.
        with pytest.raises(RenderCancelled):
            e._do_render(img, 200, 200, 14, 22, "black_on_white", 5,
                         cancel_event=ev)
