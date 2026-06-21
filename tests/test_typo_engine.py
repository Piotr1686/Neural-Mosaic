"""Tests for src/engine_typo.py — character filtering and library sorting."""
import pickle
from unittest.mock import mock_open, patch

import pytest

from src.engine_typo import TypoEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: A font that belongs to a Latin-family group (curated ASCII subset applies).
_LATIN_FONT = "NotoSans-Regular.ttf"
#: A font from an exotic group (trusted as-is; ASCII subset does NOT apply).
_EXOTIC_FONT = "NotoSansEgyptianHieroglyphs-Regular.ttf"


def _make_lib(*chars, font="test.ttf"):
    """Build a minimal raw_lib list as produced by indexer_typo."""
    return [
        {"char": c, "norm_density": round(i * 0.1, 1), "font": font, "density": i * 25}
        for i, c in enumerate(chars)
    ]


def _load_engine(raw_lib):
    """Instantiate TypoEngine with a mocked index file."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open()):
            with patch("pickle.load", return_value=raw_lib):
                return TypoEngine()


# ---------------------------------------------------------------------------
# ASCII filtering
# ---------------------------------------------------------------------------

class TestAsciiFilter:
    def test_uppercase_letters_accepted(self):
        engine = _load_engine(_make_lib("A", "Z", "M"))
        chars = [x["char"] for x in engine.library]
        assert "A" in chars
        assert "Z" in chars
        assert "M" in chars

    def test_lowercase_letters_accepted(self):
        engine = _load_engine(_make_lib("a", "z", "m"))
        chars = [x["char"] for x in engine.library]
        assert "a" in chars

    def test_digits_accepted(self):
        engine = _load_engine(_make_lib("0", "5", "9"))
        chars = [x["char"] for x in engine.library]
        assert "0" in chars
        assert "9" in chars

    def test_unsafe_ascii_rejected_for_latin_font(self):
        """For Latin-family fonts, chars outside the curated set are filtered out."""
        engine = _load_engine(_make_lib("@", "#", "~", "^", "&", "*", font=_LATIN_FONT))
        assert len(engine.library) == 0

    def test_mixed_accepted_and_rejected_for_latin_font(self):
        engine = _load_engine(_make_lib("A", "@", "B", "#", font=_LATIN_FONT))
        chars = [x["char"] for x in engine.library]
        assert "A" in chars
        assert "B" in chars
        assert "@" not in chars
        assert "#" not in chars


# ---------------------------------------------------------------------------
# CJK filtering
# ---------------------------------------------------------------------------

class TestCjkFilter:
    def test_chinese_hanzi_accepted(self):
        zhong = chr(0x4E2D)  # 中
        engine = _load_engine(_make_lib(zhong))
        assert len(engine.library) == 1
        assert engine.library[0]["char"] == zhong

    def test_hiragana_accepted(self):
        ha = chr(0x306F)  # は
        engine = _load_engine(_make_lib(ha))
        assert len(engine.library) == 1

    def test_katakana_accepted(self):
        ka = chr(0x30AB)  # カ
        engine = _load_engine(_make_lib(ka))
        assert len(engine.library) == 1

    def test_hangul_accepted(self):
        ga = chr(0xAC00)  # 가
        engine = _load_engine(_make_lib(ga))
        assert len(engine.library) == 1

    def test_non_ascii_rejected_for_latin_font(self):
        """For a Latin-family font, a non-ASCII glyph (Greek) is filtered out."""
        alpha = chr(0x03B1)  # α
        engine = _load_engine(_make_lib(alpha, font=_LATIN_FONT))
        assert len(engine.library) == 0


# ---------------------------------------------------------------------------
# Exotic-script filtering (Option B: ancient/symbol/other groups are trusted)
# ---------------------------------------------------------------------------

class TestExoticFilter:
    def test_hieroglyph_accepted_for_ancient_font(self):
        """A glyph from an exotic-group font bypasses the ASCII subset filter."""
        glyph = chr(0x13000)  # Egyptian Hieroglyph A001
        engine = _load_engine(_make_lib(glyph, font=_EXOTIC_FONT))
        assert len(engine.library) == 1
        assert engine.library[0]["char"] == glyph

    def test_unsafe_ascii_kept_for_exotic_font(self):
        """Non-Latin fonts are trusted, so the indexer's glyph set is preserved."""
        engine = _load_engine(_make_lib("@", "#", font=_EXOTIC_FONT))
        assert len(engine.library) == 2


# ---------------------------------------------------------------------------
# Library sorting and density metadata
# ---------------------------------------------------------------------------

class TestLibrarySorting:
    def test_library_sorted_ascending_by_norm_density(self):
        raw = [
            {"char": "A", "norm_density": 0.8, "font": "f.ttf", "density": 200},
            {"char": "i", "norm_density": 0.1, "font": "f.ttf", "density": 25},
            {"char": "0", "norm_density": 0.5, "font": "f.ttf", "density": 128},
        ]
        engine = _load_engine(raw)
        densities = [x["norm_density"] for x in engine.library]
        assert densities == sorted(densities)

    def test_densities_list_matches_library(self):
        engine = _load_engine(_make_lib("A", "i", "0"))
        assert len(engine.densities) == len(engine.library)
        for item, d in zip(engine.library, engine.densities):
            assert item["norm_density"] == d

    def test_min_max_density_attributes(self):
        raw = [
            {"char": "A", "norm_density": 0.2, "font": "f.ttf", "density": 50},
            {"char": "i", "norm_density": 0.9, "font": "f.ttf", "density": 230},
        ]
        engine = _load_engine(raw)
        assert engine.min_density == pytest.approx(0.2)
        assert engine.max_density == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Missing index — graceful fallback
# ---------------------------------------------------------------------------

class TestMissingIndex:
    def test_empty_library_when_index_missing(self):
        with patch("os.path.exists", return_value=False):
            engine = TypoEngine(index_path="nonexistent.pkl")
        assert engine.library == []

    def test_empty_densities_when_index_missing(self):
        with patch("os.path.exists", return_value=False):
            engine = TypoEngine(index_path="nonexistent.pkl")
        assert engine.densities == []
