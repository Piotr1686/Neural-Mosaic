"""Tests for src/indexer_typo.py — analyze_font and density normalisation.

All tests are isolated: real font files are not required.
ImageFont.truetype is mocked so the test suite runs without TTF files on disk.
"""
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
from PIL import Image, ImageFont


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_font_mock(char_widths: dict):
    """
    Build a mock ImageFont that reports glyph bounding boxes for the given chars.

    char_widths: {char: (w, h)} — characters with non-zero glyphs.
                 Any char not in the dict returns a zero-size bbox.
    """
    font_mock = MagicMock(spec=ImageFont.FreeTypeFont)

    def _getbbox(char, *args, **kwargs):
        if char in char_widths:
            w, h = char_widths[char]
            return (0, 0, w, h)
        return (0, 0, 0, 0)

    font_mock.getbbox.side_effect = _getbbox
    return font_mock


# ---------------------------------------------------------------------------
# analyze_font — unit tests
# ---------------------------------------------------------------------------

class TestAnalyzeFont:
    """Tests for the top-level analyze_font() function."""

    def _run(self, font_mock, font_path="test.ttf"):
        """Run analyze_font with a mocked font and a mocked stat that reports ink on canvas.

        analyze_font filters out characters whose rendered canvas is too bright
        (mean brightness >= 254).  Because draw.text with a MagicMock font
        never produces real pixels, we also mock ImageStat.Stat to return a
        darkness value (mean=100) so that accepted characters pass the filter.
        """
        from src.indexer_typo import analyze_font
        mock_stat = MagicMock()
        mock_stat.mean = [100.0]  # < 254 → character passes the brightness filter
        with (
            patch("src.indexer_typo.ImageFont.truetype", return_value=font_mock),
            patch("src.indexer_typo.ImageStat.Stat", return_value=mock_stat),
            # PIL's draw.text() would crash when given a MagicMock font because
            # it tries to call real font-rendering methods internally.  Mocking
            # the Draw constructor makes rectangle() / text() silent no-ops.
            patch("src.indexer_typo.ImageDraw.Draw"),
        ):
            return analyze_font(font_path)

    def test_returns_list(self):
        result = self._run(_make_font_mock({"A": (20, 30)}))
        assert isinstance(result, list)

    def test_empty_font_returns_empty_list(self):
        """Font with no renderable glyphs in ASCII range → empty result."""
        result = self._run(_make_font_mock({}))
        assert result == []

    def test_char_with_nonzero_bbox_included(self):
        """A character whose bbox has positive w and h must appear in output."""
        result = self._run(_make_font_mock({"A": (20, 30)}))
        chars = [r["char"] for r in result]
        assert "A" in chars

    def test_char_keys_present(self):
        """Each entry must carry 'char', 'font', 'density', 'aspect' keys."""
        result = self._run(_make_font_mock({"B": (15, 25)}))
        if result:
            entry = result[0]
            assert "char" in entry
            assert "font" in entry
            assert "density" in entry
            assert "aspect" in entry

    def test_font_path_stored_in_entry(self):
        result = self._run(_make_font_mock({"X": (10, 20)}), font_path="myfont.ttf")
        if result:
            assert result[0]["font"] == "myfont.ttf"

    def test_aspect_ratio_is_positive(self):
        result = self._run(_make_font_mock({"M": (24, 30)}))
        if result:
            assert result[0]["aspect"] > 0

    def test_density_is_numeric(self):
        result = self._run(_make_font_mock({"Z": (18, 28)}))
        if result:
            assert isinstance(result[0]["density"], (int, float))

    def test_bad_font_file_returns_empty(self):
        """If truetype() raises, analyze_font must return [] without crashing."""
        from src.indexer_typo import analyze_font
        with patch("src.indexer_typo.ImageFont.truetype", side_effect=Exception("bad font")):
            result = analyze_font("broken.ttf")
        assert result == []


# ---------------------------------------------------------------------------
# Density normalisation logic — white-box tests (no PIL / fonts needed)
# ---------------------------------------------------------------------------

class TestDensityNormalisation:
    """
    Mirror the normalisation step from indexer_typo.main() and verify its maths.
    """

    @staticmethod
    def _normalise(library: list) -> list:
        """Reproduce the normalisation loop from main()."""
        if len(library) <= 1:
            if library:
                library[0]["norm_density"] = 0.5
            return library

        library.sort(key=lambda x: x["density"])
        min_d = library[0]["density"]
        max_d = library[-1]["density"]

        for item in library:
            item["norm_density"] = (item["density"] - min_d) / (max_d - min_d + 1e-9)
        return library

    def _make_lib(self, densities):
        return [{"char": chr(65 + i), "font": "f.ttf", "density": d, "aspect": 1.0}
                for i, d in enumerate(densities)]

    def test_min_density_normalises_to_zero(self):
        lib = self._normalise(self._make_lib([10.0, 50.0, 100.0, 200.0]))
        assert lib[0]["norm_density"] == pytest.approx(0.0, abs=1e-6)

    def test_max_density_normalises_to_one(self):
        lib = self._normalise(self._make_lib([10.0, 50.0, 100.0, 200.0]))
        assert lib[-1]["norm_density"] == pytest.approx(1.0, abs=1e-4)

    def test_all_norm_densities_in_0_1(self):
        lib = self._normalise(self._make_lib([5.0, 30.0, 80.0, 150.0, 230.0]))
        for item in lib:
            assert 0.0 <= item["norm_density"] <= 1.0, (
                f"norm_density {item['norm_density']} out of range for char {item['char']}"
            )

    def test_sorted_ascending_by_density(self):
        lib = self._normalise(self._make_lib([90.0, 10.0, 50.0]))
        densities = [x["density"] for x in lib]
        assert densities == sorted(densities)

    def test_single_entry_gets_0_5(self):
        lib = self._normalise(self._make_lib([42.0]))
        assert lib[0]["norm_density"] == pytest.approx(0.5)

    def test_uniform_densities_no_divide_by_zero(self):
        """All chars with identical brightness → must not raise ZeroDivisionError."""
        lib = self._normalise(self._make_lib([128.0, 128.0, 128.0]))
        for item in lib:
            assert not np.isnan(item["norm_density"])

    def test_relative_order_preserved(self):
        """Darker chars (lower density value) must have smaller norm_density."""
        lib = self._normalise(self._make_lib([20.0, 80.0, 160.0]))
        norms = [x["norm_density"] for x in lib]
        assert norms[0] < norms[1] < norms[2]


# ---------------------------------------------------------------------------
# main() — integration smoke test (filesystem mocked)
# ---------------------------------------------------------------------------

class TestIndexerTypoMain:
    def test_main_creates_index_file(self, tmp_path):
        """main() should write a pickle file when font analysis yields results."""
        from src.indexer_typo import main

        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()
        fake_font = fonts_dir / "test.ttf"
        fake_font.write_bytes(b"")
        index_path = tmp_path / "typo_index.pkl"

        fake_entry = {
            "char": "A",
            "font": str(fake_font),
            "density": 100.0,
            "aspect": 1.0,
        }

        with (
            patch("src.indexer_typo.FONTS_DIR", fonts_dir),
            patch("src.indexer_typo.INDEX_FILE", index_path),
            patch("src.indexer_typo.analyze_font", return_value=[fake_entry]),
        ):
            main()

        assert index_path.exists(), "main() must create the index pickle"

    def test_main_index_is_valid_pickle(self, tmp_path):
        """The written pickle must be loadable and contain a list."""
        from src.indexer_typo import main

        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()
        (fonts_dir / "f.ttf").write_bytes(b"")
        index_path = tmp_path / "typo_index.pkl"

        fake_entries = [
            {"char": "A", "font": "f.ttf", "density": 50.0, "aspect": 1.0},
            {"char": "i", "font": "f.ttf", "density": 200.0, "aspect": 0.5},
        ]

        with (
            patch("src.indexer_typo.FONTS_DIR", fonts_dir),
            patch("src.indexer_typo.INDEX_FILE", index_path),
            patch("src.indexer_typo.analyze_font", return_value=fake_entries),
        ):
            main()

        with open(index_path, "rb") as fh:
            data = pickle.load(fh)

        assert isinstance(data, list)
        assert len(data) == 2

    def test_main_skips_write_when_no_chars_found(self, tmp_path):
        """If no characters are found across all fonts, no index is written."""
        from src.indexer_typo import main

        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()
        (fonts_dir / "f.ttf").write_bytes(b"")
        index_path = tmp_path / "typo_index.pkl"

        with (
            patch("src.indexer_typo.FONTS_DIR", fonts_dir),
            patch("src.indexer_typo.INDEX_FILE", index_path),
            patch("src.indexer_typo.analyze_font", return_value=[]),
        ):
            main()

        assert not index_path.exists(), "No index must be written when library is empty"

    def test_main_index_has_norm_density_keys(self, tmp_path):
        """Every entry in the saved index must have a 'norm_density' field."""
        from src.indexer_typo import main

        fonts_dir = tmp_path / "fonts"
        fonts_dir.mkdir()
        (fonts_dir / "f.ttf").write_bytes(b"")
        index_path = tmp_path / "typo_index.pkl"

        fake_entries = [
            {"char": c, "font": "f.ttf", "density": d, "aspect": 1.0}
            for c, d in zip("ABCDi", [20.0, 60.0, 100.0, 150.0, 220.0])
        ]

        with (
            patch("src.indexer_typo.FONTS_DIR", fonts_dir),
            patch("src.indexer_typo.INDEX_FILE", index_path),
            patch("src.indexer_typo.analyze_font", return_value=fake_entries),
        ):
            main()

        with open(index_path, "rb") as fh:
            data = pickle.load(fh)

        for entry in data:
            assert "norm_density" in entry, f"Missing 'norm_density' in {entry}"
