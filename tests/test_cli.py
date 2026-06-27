"""Tests for src/cli.py — argparse, validation, batch naming + optional smoke renders.

The bulk of the tests are pure unit tests (no engine instantiation, no disk I/O
beyond `tmp_path`). Two end-to-end smoke renders at 2K are included at the bottom
and are auto-skipped when the real `data/*_index.pkl` files or `input/portrait.jpg`
are not available — so CI without indexes still passes.
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from src import cli


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    """Create empty smart_index.pkl + typo_index.pkl under tmp_path/data and chdir there.

    The CLI's validation only checks `Path.exists()` for the index — content is
    not parsed until the engine actually loads it. Empty files are enough for
    every test that does NOT call the engine.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "smart_index.pkl").write_bytes(b"")
    (tmp_path / "data" / "typo_index.pkl").write_bytes(b"")
    return tmp_path


@pytest.fixture
def fake_input(tmp_path):
    img = tmp_path / "in.jpg"
    img.write_bytes(b"fake")
    return img


def _parse(*argv):
    parser = cli.build_parser()
    return parser.parse_args(list(argv)), parser


# ---------------------------------------------------------------------------
# build_parser — subcommands, defaults, choice validation
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_render_subcommand_recognised(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.command == "render"
        assert args.engine == "smart"

    def test_batch_subcommand_recognised(self):
        args, _ = _parse("batch", "in", "out", "--engine", "typo")
        assert args.command == "batch"
        assert args.engine == "typo"

    def test_default_resolution_is_8K(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.res == "8K"

    def test_default_shape_is_square(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.shape == "square"

    def test_default_mode_is_black_on_white(self):
        args, _ = _parse("render", "x.jpg", "--engine", "typo")
        assert args.mode == "black_on_white"

    def test_default_scale_is_one(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.scale == 1.0

    def test_default_variation_is_20(self):
        args, _ = _parse("render", "x.jpg", "--engine", "typo")
        assert args.variation == 20

    def test_mirror_default_true(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.mirror is True

    def test_no_mirror_flag(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart", "--no-mirror")
        assert args.mirror is False

    def test_edge_aware_default_false(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart")
        assert args.edge_aware is False

    def test_edge_aware_flag(self):
        args, _ = _parse("render", "x.jpg", "--engine", "smart", "--edge-aware")
        assert args.edge_aware is True

    def test_font_groups_default_none(self):
        args, _ = _parse("render", "x.jpg", "--engine", "typo")
        assert args.font_groups is None

    def test_font_groups_multiple(self):
        args, _ = _parse(
            "render", "x.jpg", "--engine", "typo",
            "--font-groups", "A_cjk", "C_symbols",
        )
        assert args.font_groups == ["A_cjk", "C_symbols"]

    def test_batch_pattern_default(self):
        args, _ = _parse("batch", "in", "out", "--engine", "smart")
        assert args.pattern == "*.jpg"

    def test_batch_pattern_custom(self):
        args, _ = _parse("batch", "in", "out", "--engine", "smart", "--pattern", "*.png")
        assert args.pattern == "*.png"

    def test_invalid_shape_rejected(self):
        with pytest.raises(SystemExit):
            _parse("render", "x.jpg", "--engine", "smart", "--shape", "octagon")

    def test_invalid_resolution_rejected(self):
        with pytest.raises(SystemExit):
            _parse("render", "x.jpg", "--engine", "smart", "--res", "1K")

    def test_invalid_mode_rejected(self):
        with pytest.raises(SystemExit):
            _parse("render", "x.jpg", "--engine", "typo", "--mode", "rainbow")

    def test_invalid_font_group_rejected(self):
        with pytest.raises(SystemExit):
            _parse(
                "render", "x.jpg", "--engine", "typo",
                "--font-groups", "Z_nonexistent",
            )

    def test_engine_is_required(self):
        with pytest.raises(SystemExit):
            _parse("render", "x.jpg")

    def test_dzi_subcommand_recognised(self):
        args, _ = _parse("dzi", "mosaic.jpg", "out_dir")
        assert args.command == "dzi"
        assert args.input == "mosaic.jpg"
        assert args.out_dir == "out_dir"

    def test_dzi_max_level_default_none(self):
        args, _ = _parse("dzi", "mosaic.jpg", "out_dir")
        assert args.max_level is None

    def test_dzi_max_level_custom(self):
        args, _ = _parse("dzi", "mosaic.jpg", "out_dir", "--max-level", "13")
        assert args.max_level == 13

    def test_dzi_no_skip_default_false(self):
        args, _ = _parse("dzi", "mosaic.jpg", "out_dir")
        assert args.no_skip is False

    def test_dzi_no_skip_flag(self):
        args, _ = _parse("dzi", "mosaic.jpg", "out_dir", "--no-skip")
        assert args.no_skip is True

    def test_dzi_out_dir_is_required(self):
        with pytest.raises(SystemExit):
            _parse("dzi", "mosaic.jpg")


# ---------------------------------------------------------------------------
# _validate_render
# ---------------------------------------------------------------------------

class TestValidateRender:
    def test_missing_input_raises(self, fake_index, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(tmp_path / "ghost.jpg"), "--engine", "smart",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_input_is_directory_raises(self, fake_index, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(tmp_path), "--engine", "smart",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_missing_index_raises(self, tmp_path, fake_input, monkeypatch):
        monkeypatch.chdir(tmp_path)  # no data/ subdir → default index missing
        parser = cli.build_parser()
        args = parser.parse_args(["render", str(fake_input), "--engine", "smart"])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_blend_above_range_raises(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart", "--blend", "0.5",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_blend_below_range_raises(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart", "--blend", "-0.1",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_tint_above_range_raises(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart", "--tint", "0.6",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_variation_zero_raises(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "typo", "--variation", "0",
        ])
        with pytest.raises(SystemExit):
            cli._validate_render(args, parser)

    def test_output_auto_named_smart_jpg(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart", "--res", "4K",
        ])
        cli._validate_render(args, parser)
        assert args.output.suffix == ".jpg"
        assert args.output.parent.name == "output"
        assert args.output.name.startswith("in_smart_4K_")

    def test_output_auto_named_typo_png(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "typo",
        ])
        cli._validate_render(args, parser)
        assert args.output.suffix == ".png"
        assert args.output.name.startswith("in_typo_8K_")

    def test_output_explicit_path_preserved(self, fake_index, fake_input, tmp_path):
        out = tmp_path / "custom.jpg"
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart", "--output", str(out),
        ])
        cli._validate_render(args, parser)
        assert args.output == out

    def test_index_path_resolved_to_default(self, fake_index, fake_input):
        parser = cli.build_parser()
        args = parser.parse_args(["render", str(fake_input), "--engine", "smart"])
        cli._validate_render(args, parser)
        assert args.index == Path("data/smart_index.pkl")

    def test_explicit_index_used(self, fake_index, fake_input, tmp_path):
        custom = tmp_path / "custom_index.pkl"
        custom.write_bytes(b"")
        parser = cli.build_parser()
        args = parser.parse_args([
            "render", str(fake_input), "--engine", "smart",
            "--index", str(custom),
        ])
        cli._validate_render(args, parser)
        assert args.index == custom


# ---------------------------------------------------------------------------
# _validate_batch
# ---------------------------------------------------------------------------

class TestValidateBatch:
    def test_missing_input_dir_raises(self, fake_index, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args([
            "batch", str(tmp_path / "ghost"), str(tmp_path / "out"),
            "--engine", "smart",
        ])
        with pytest.raises(SystemExit):
            cli._validate_batch(args, parser)

    def test_input_is_file_raises(self, fake_index, fake_input, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args([
            "batch", str(fake_input), str(tmp_path / "out"),
            "--engine", "smart",
        ])
        with pytest.raises(SystemExit):
            cli._validate_batch(args, parser)

    def test_output_dir_created_if_missing(self, fake_index, tmp_path):
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        out_dir = tmp_path / "freshly_made"
        parser = cli.build_parser()
        args = parser.parse_args([
            "batch", str(in_dir), str(out_dir), "--engine", "smart",
        ])
        cli._validate_batch(args, parser)
        assert out_dir.exists() and out_dir.is_dir()


# ---------------------------------------------------------------------------
# _batch_output_path — deterministic, timestamp-free
# ---------------------------------------------------------------------------

class TestBatchOutputNaming:
    def _make_args(self, **overrides):
        ns = argparse.Namespace(
            engine="smart", res="8K", shape="square",
            mode="black_on_white",
        )
        for k, v in overrides.items():
            setattr(ns, k, v)
        return ns

    def test_smart_naming_uses_shape(self, tmp_path):
        args = self._make_args(engine="smart", shape="hexagon", res="4K")
        out = cli._batch_output_path(tmp_path, "photo", args)
        assert out.name == "photo_smart_4K_hexagon.jpg"

    def test_typo_naming_uses_mode(self, tmp_path):
        args = self._make_args(engine="typo", mode="white_on_black", res="8K")
        out = cli._batch_output_path(tmp_path, "photo", args)
        assert out.name == "photo_typo_8K_white_on_black.png"

    def test_naming_is_deterministic(self, tmp_path):
        """No timestamp → batch can re-run and skip already-rendered files."""
        args = self._make_args(engine="smart", shape="square", res="2K")
        out1 = cli._batch_output_path(tmp_path, "photo", args)
        out2 = cli._batch_output_path(tmp_path, "photo", args)
        assert out1 == out2

    def test_naming_includes_output_dir(self, tmp_path):
        args = self._make_args(engine="smart", shape="square", res="2K")
        out = cli._batch_output_path(tmp_path, "photo", args)
        assert out.parent == tmp_path


# ---------------------------------------------------------------------------
# _validate_dzi
# ---------------------------------------------------------------------------

class TestValidateDzi:
    def test_missing_input_raises(self, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args(["dzi", str(tmp_path / "ghost.jpg"), str(tmp_path / "out")])
        with pytest.raises(SystemExit):
            cli._validate_dzi(args, parser)

    def test_input_is_directory_raises(self, tmp_path):
        parser = cli.build_parser()
        args = parser.parse_args(["dzi", str(tmp_path), str(tmp_path / "out")])
        with pytest.raises(SystemExit):
            cli._validate_dzi(args, parser)

    def test_out_dir_created_if_missing(self, tmp_path):
        img = tmp_path / "m.jpg"
        img.write_bytes(b"fake")
        out_dir = tmp_path / "freshly_made"
        parser = cli.build_parser()
        args = parser.parse_args(["dzi", str(img), str(out_dir)])
        cli._validate_dzi(args, parser)
        assert out_dir.exists() and out_dir.is_dir()
        assert args.input == img and args.out_dir == out_dir


# ---------------------------------------------------------------------------
# dzi end-to-end — make_dzi needs only an image (no index), so this runs in CI
# ---------------------------------------------------------------------------

class TestDziEndToEnd:
    def _run(self, img, out_dir, *extra):
        parser = cli.build_parser()
        args = parser.parse_args(["dzi", str(img), str(out_dir), *extra])
        cli._validate_dzi(args, parser)
        cli._run_dzi(args, logging.getLogger("test_dzi"))

    def test_builds_pyramid(self, tmp_path):
        img = tmp_path / "mosaic.png"
        Image.new("RGB", (600, 400), (123, 50, 200)).save(img)
        out_dir = tmp_path / "dzi_out"

        self._run(img, out_dir)

        assert (out_dir / "mosaic.dzi").exists()
        tiles = list((out_dir / "mosaic_files").rglob("*.jpg"))
        assert tiles, "no pyramid tiles produced"

    def test_skip_if_exists_preserves_tiles(self, tmp_path):
        """Default skip_existing must not rewrite tiles already on disk."""
        img = tmp_path / "mosaic.png"
        Image.new("RGB", (600, 400), (10, 200, 90)).save(img)
        out_dir = tmp_path / "dzi_out"

        self._run(img, out_dir)
        victim = next((out_dir / "mosaic_files").rglob("*.jpg"))
        victim.write_bytes(b"SENTINEL")

        self._run(img, out_dir)  # second run, default skip
        assert victim.read_bytes() == b"SENTINEL"

    def test_no_skip_regenerates_tiles(self, tmp_path):
        """--no-skip must overwrite an existing tile with a fresh render."""
        img = tmp_path / "mosaic.png"
        Image.new("RGB", (600, 400), (10, 200, 90)).save(img)
        out_dir = tmp_path / "dzi_out"

        self._run(img, out_dir)
        victim = next((out_dir / "mosaic_files").rglob("*.jpg"))
        victim.write_bytes(b"SENTINEL")

        self._run(img, out_dir, "--no-skip")
        assert victim.read_bytes() != b"SENTINEL"


# ---------------------------------------------------------------------------
# Smoke end-to-end renders — gated by presence of real index + input image
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SMART_INDEX = REPO_ROOT / "data" / "smart_index.pkl"
TYPO_INDEX  = REPO_ROOT / "data" / "typo_index.pkl"
SMOKE_INPUT = REPO_ROOT / "input" / "portrait.jpg"


@pytest.mark.skipif(
    not (SMART_INDEX.exists() and SMOKE_INPUT.exists()),
    reason="data/smart_index.pkl or input/portrait.jpg missing — skipping smoke render",
)
def test_smoke_render_smart_2K(tmp_path, monkeypatch):
    """End-to-end 2K render via main(). Slow but covers the full happy path."""
    monkeypatch.chdir(REPO_ROOT)
    out = tmp_path / "smoke_smart.jpg"
    argv = [
        "src.cli", "render", str(SMOKE_INPUT),
        "--engine", "smart", "--res", "2K",
        "--output", str(out),
    ]
    with patch.object(sys, "argv", argv):
        cli.main()
    assert out.exists()
    assert out.stat().st_size > 0


@pytest.mark.skipif(
    not (TYPO_INDEX.exists() and SMOKE_INPUT.exists()),
    reason="data/typo_index.pkl or input/portrait.jpg missing — skipping smoke render",
)
def test_smoke_render_typo_2K(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    out = tmp_path / "smoke_typo.png"
    argv = [
        "src.cli", "render", str(SMOKE_INPUT),
        "--engine", "typo", "--res", "2K",
        "--output", str(out),
    ]
    with patch.object(sys, "argv", argv):
        cli.main()
    assert out.exists()
    assert out.stat().st_size > 0
