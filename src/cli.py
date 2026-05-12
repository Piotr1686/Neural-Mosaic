"""
src/cli.py
----------
CLI entry point for Neural-Mosaic.

Usage:
    python -m src.cli render <input> --engine smart [options]
    python -m src.cli render <input> --engine typo  [options]
    python -m src.cli --help
    python -m src.cli render --help
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

_LOG_PATH = Path("logs/cli.log")

_RESOLUTIONS = ["2K", "4K", "8K", "16K"]
_SMART_SHAPES = [
    "square", "rectangle_3x1", "brick_wall",
    "hexagon", "hexagon_romb", "romb", "triangle", "kite",
]
_TYPO_MODES = ["black_on_white", "white_on_black"]
_FONT_GROUPS = [
    "A_cjk", "B_ancient", "C_symbols",
    "D_latin_clean", "E_decorative", "F_handwriting", "G_uncategorized",
]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool) -> logging.Logger:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s  %(levelname)-8s  %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_LOG_PATH, encoding="utf-8"),
        ],
    )
    return logging.getLogger("cli")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Neural-Mosaic — command-line renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m src.cli render photo.jpg --engine smart --res 8K\n"
            "  python -m src.cli render photo.jpg --engine smart --res 16K --shape hexagon --blend 0.2\n"
            "  python -m src.cli render photo.jpg --engine typo --res 8K --mode white_on_black\n"
        ),
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── render ────────────────────────────────────────────────────────────
    rp = sub.add_parser(
        "render",
        help="Render a single mosaic from a source image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    rp.add_argument("input", metavar="INPUT", help="Source image path (.jpg / .png)")
    rp.add_argument(
        "--engine", required=True, choices=["smart", "typo"],
        help="Rendering engine: smart (photo tiles) | typo (font glyphs)",
    )
    rp.add_argument(
        "--res", default="8K", choices=_RESOLUTIONS, metavar="RES",
        help="Output resolution — 2K / 4K / 8K / 16K  (default: 8K)",
    )
    rp.add_argument(
        "--output", metavar="PATH",
        help="Output file path. Auto-named as output/<stem>_<engine>_<res>_<ts>.jpg if omitted.",
    )
    rp.add_argument(
        "--index", metavar="PATH",
        help=(
            "Pre-built index .pkl path. "
            "Defaults: data/smart_index.pkl (smart) | data/typo_index.pkl (typo)"
        ),
    )
    rp.add_argument("--verbose", action="store_true", help="Enable debug-level logging")

    # Smart engine options
    sg = rp.add_argument_group("Smart engine options (--engine smart)")
    sg.add_argument(
        "--shape", default="square", choices=_SMART_SHAPES, metavar="SHAPE",
        help=(
            "Tile geometry (default: square). "
            "Choices: " + ", ".join(_SMART_SHAPES)
        ),
    )
    sg.add_argument(
        "--scale", type=float, default=1.0, metavar="FLOAT",
        help="Tile size multiplier: 0.5 / 0.75 / 1.0 / 1.75 / 2.0  (default: 1.0)",
    )
    sg.add_argument(
        "--border", action="store_true",
        help="Add dark grout lines between tiles",
    )
    sg.add_argument(
        "--blend", type=float, default=0.0, metavar="FLOAT",
        help="Blend original image over mosaic, 0.0–0.3  (default: 0.0)",
    )
    sg.add_argument(
        "--tint", type=float, default=0.0, metavar="FLOAT",
        help="Tint each tile toward target sector colour, 0.0–0.4  (default: 0.0)",
    )
    sg.add_argument(
        "--mirror", action=argparse.BooleanOptionalAction, default=True,
        help="Allow horizontal tile mirroring (default: on). Use --no-mirror to disable.",
    )
    sg.add_argument(
        "--edge-aware", action="store_true", dest="edge_aware",
        help="Use edge-aware matching (requires 79-dim index built with edge features).",
    )

    # Typo engine options
    tg = rp.add_argument_group("Typo engine options (--engine typo)")
    tg.add_argument(
        "--mode", default="black_on_white", choices=_TYPO_MODES, metavar="MODE",
        help="Render style: black_on_white | white_on_black  (default: black_on_white)",
    )
    tg.add_argument(
        "--font-groups", nargs="+", choices=_FONT_GROUPS,
        default=None, metavar="GROUP", dest="font_groups",
        help=(
            "Font groups to use (default: all). "
            "Choices: " + ", ".join(_FONT_GROUPS)
        ),
    )
    tg.add_argument(
        "--variation", type=int, default=20, metavar="INT",
        help="Glyph density variation window ±N  (default: 20)",
    )

    return parser


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _default_index(engine: str) -> Path:
    return Path("data") / f"{engine}_index.pkl"


def _validate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"Input file not found: {input_path}")
    if not input_path.is_file():
        parser.error(f"Input path is not a file: {input_path}")
    args.input = input_path

    index_path = Path(args.index) if args.index else _default_index(args.engine)
    if not index_path.exists():
        indexer = f"src.indexer_{args.engine}"
        parser.error(
            f"Index not found: {index_path}\n"
            f"  Build it first:  python -m {indexer}"
        )
    args.index = index_path

    if args.output:
        out = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".png" if args.engine == "typo" else ".jpg"
        out = Path("output") / f"{args.input.stem}_{args.engine}_{args.res}_{ts}{ext}"
    out.parent.mkdir(parents=True, exist_ok=True)
    args.output = out

    if not (0.0 <= args.blend <= 0.3):
        parser.error("--blend must be in range [0.0, 0.3]")
    if not (0.0 <= args.tint <= 0.4):
        parser.error("--tint must be in range [0.0, 0.4]")
    if args.variation < 1:
        parser.error("--variation must be >= 1")


# ---------------------------------------------------------------------------
# Render dispatch  (Sprint 1.1: validated stub — engine calls in 1.2 / 1.3)
# ---------------------------------------------------------------------------

def _run_render(args: argparse.Namespace, log: logging.Logger) -> None:
    log.info("=== Neural-Mosaic CLI  render ===")
    log.info("  Input  : %s", args.input)
    log.info("  Engine : %s", args.engine)
    log.info("  Res    : %s", args.res)
    log.info("  Index  : %s", args.index)
    log.info("  Output : %s", args.output)

    if args.engine == "smart":
        _run_smart(args, log)
    else:
        groups = args.font_groups or _FONT_GROUPS
        log.info(
            "  Mode=%s  Scale=%.2f  Variation=%d  Groups=%s",
            args.mode, args.scale, args.variation, groups,
        )
        # Sprint 1.3 will add TypoEngine call.
        log.warning("Typo engine not yet wired to CLI (Sprint 1.3). Use the GUI for now.")


def _run_smart(args: argparse.Namespace, log: logging.Logger) -> None:
    log.info(
        "  Shape=%s  Scale=%.2f  Border=%s  Blend=%.2f  Tint=%.2f  Mirror=%s  EdgeAware=%s",
        args.shape, args.scale, args.border, args.blend, args.tint,
        args.mirror, args.edge_aware,
    )

    from .engine_smart import SmartEngine

    log.info("Loading SmartEngine index...")
    engine = SmartEngine(index_path=str(args.index))
    if not engine.paths:
        log.error("Index loaded but contains no tiles — aborting.")
        sys.exit(1)

    engine.settings["allow_mirror"] = args.mirror
    engine.settings["edge_aware"] = args.edge_aware

    log.info("Rendering...")
    engine.create_mosaic(
        args.input,
        args.output,
        args.res,
        args.shape,
        tile_scale=args.scale,
        border_mode=args.border,
        blend_strength=args.blend,
        tint_strength=args.tint,
    )
    log.info("Done. Saved to: %s", args.output)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    log = _setup_logging(getattr(args, "verbose", False))

    if args.command == "render":
        _validate(args, parser)
        _run_render(args, log)


if __name__ == "__main__":
    main()
