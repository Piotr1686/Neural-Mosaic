"""
src/tools/make_showcase.py
--------------------------
Generates all images required for the README gallery section.

Produces (in assets/examples/):
    source_portrait.jpg        - resized source image (<=800 px wide)
    mosaic_portrait_square.jpg - Smart mosaic, square tiles
    mosaic_portrait_kite.jpg   - Smart mosaic, kite tiles
    detail_square.jpg          - Centre-crop detail of the square mosaic
    detail_kite.jpg            - Centre-crop detail of the kite mosaic
    symbol_bw.jpg              - Symbol mosaic, black_on_white
    symbol_detail.jpg          - Centre-crop detail of the B&W symbol mosaic

Full-resolution outputs go to output/showcase_<shape>_<timestamp>.jpg|png.

Manual step (cannot be automated):
    assets/demo.gif            - Screen-record the GUI, export as GIF/WebP

Usage:
    python -m src.tools.make_showcase --source input/my_portrait.jpg
    python -m src.tools.make_showcase --source input/my_portrait.jpg --res 4K
    python -m src.tools.make_showcase --source input/my_portrait.jpg --skip-typo
    python -m src.tools.make_showcase --list   # status only, no rendering

Default: 16K for both Smart and Symbol engines (best quality, long render time).
"""
import argparse
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EXAMPLES_DIR = PROJECT_ROOT / "assets" / "examples"
OUTPUT_DIR   = PROJECT_ROOT / "output"
INDEX_PATH   = PROJECT_ROOT / "data" / "smart_index.pkl"
TYPO_INDEX   = PROJECT_ROOT / "data" / "typo_index.pkl"

# Gallery images expected by README.md
GALLERY_FILES = [
    ("source_portrait.jpg",          "Source portrait (resized copy of input)"),
    ("mosaic_portrait_square.jpg",   "Smart mosaic - square tiles"),
    ("mosaic_portrait_triangle.jpg", "Smart mosaic - triangle tiles"),
    ("mosaic_portrait_hexagon.jpg",  "Smart mosaic - hexagon tiles"),
    ("mosaic_portrait_spectre.jpg",  "Smart mosaic - spectre tiles"),
    ("detail_square.jpg",            "Tile detail crop - square mosaic"),
    ("detail_triangle.jpg",          "Tile detail crop - triangle mosaic"),
    ("detail_hexagon.jpg",           "Tile detail crop - hexagon mosaic"),
    ("detail_spectre.jpg",           "Tile detail crop - spectre mosaic"),
    ("symbol_bw.jpg",                "Symbol mosaic - black_on_white"),
    ("symbol_detail.jpg",            "Glyph detail crop - B&W symbol mosaic"),
]
MANUAL_FILES = [
    ("../demo.gif", "GUI demo - record with OBS/ShareX and export as GIF"),
]

GALLERY_MAX_PX  = 1920   # long edge of mosaic gallery images
SOURCE_MAX_PX   = 800    # long edge of the resized source portrait
DETAIL_CROP_PCT = 0.20   # size of detail crop as fraction of image long edge
DETAIL_OUT_PX   = 900    # output size of detail crop


# -- helpers ------------------------------------------------------------------

def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resize_fit(img: Image.Image, max_px: int) -> Image.Image:
    """Downscale so the longer edge <= max_px. Upscale never happens."""
    w, h = img.size
    if max(w, h) <= max_px:
        return img
    scale = max_px / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def _centre_crop(img: Image.Image, crop_fraction: float, out_px: int) -> Image.Image:
    """Cut a square from the centre, resize to out_px × out_px."""
    w, h = img.size
    size = int(min(w, h) * crop_fraction)
    cx, cy = w // 2, h // 2
    box = (cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2)
    box = (max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3]))
    return img.crop(box).resize((out_px, out_px), Image.Resampling.LANCZOS)


def _save_gallery(full_path: Path, gallery_path: Path, max_px: int = GALLERY_MAX_PX):
    """Open full-res image, downscale, save to gallery path as JPEG."""
    with Image.open(full_path) as img:
        gallery = _resize_fit(img.convert("RGB"), max_px)
        gallery.save(gallery_path, quality=92)
    print(f"  -> gallery: {gallery_path.name}  ({gallery.size[0]}×{gallery.size[1]})")


def _save_detail(full_path: Path, gallery_path: Path):
    with Image.open(full_path) as img:
        detail = _centre_crop(img.convert("RGB"), DETAIL_CROP_PCT, DETAIL_OUT_PX)
        detail.save(gallery_path, quality=92)
    print(f"  -> detail:  {gallery_path.name}  ({DETAIL_OUT_PX}×{DETAIL_OUT_PX})")


# -- generation steps ---------------------------------------------------------

def step_source(source: Path):
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    dest = EXAMPLES_DIR / "source_portrait.jpg"
    with Image.open(source) as img:
        out = _resize_fit(img.convert("RGB"), SOURCE_MAX_PX)
        out.save(dest, quality=92)
    print(f"  OK source_portrait.jpg  ({out.size[0]}×{out.size[1]})")
    return dest


def step_smart(source: Path, shape: str, res: str, tile_scale: float = 1.0) -> Path | None:
    if not INDEX_PATH.exists():
        print(f"  [skip] smart/{shape} - index not found: {INDEX_PATH}")
        return None

    from src.engine_smart import SmartEngine
    engine = SmartEngine(index_path=str(INDEX_PATH))
    if not engine.paths:
        print(f"  [skip] smart/{shape} - index failed to load")
        return None

    engine.settings.update({
        "allow_mirror": False,
        "edge_aware": False,
        "freq_penalty": 30.0,
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    full_path = OUTPUT_DIR / f"showcase_{shape}_{_stamp()}.jpg"

    tile_px = max(10, int(100 * tile_scale))
    print(f"  Rendering smart/{shape} at {res}, tile_scale={tile_scale} ({tile_px}px tiles) …")
    t0 = time.perf_counter()
    engine.create_mosaic(
        target_path=str(source),
        output_path=str(full_path),
        resolution_key=res,
        shape_mode=shape,
        tile_scale=tile_scale,
    )
    elapsed = time.perf_counter() - t0
    print(f"  OK smart/{shape} done in {elapsed:.1f}s  ->  {full_path.name}")
    return full_path


def step_typo(source: Path, mode: str, res: str, scale: float = 1.0) -> Path | None:
    if not TYPO_INDEX.exists():
        print(f"  [skip] typo/{mode} - typo index not found: {TYPO_INDEX}")
        return None

    from src.engine_typo import TypoEngine
    engine = TypoEngine(index_path=str(TYPO_INDEX))
    if not engine.library:
        print(f"  [skip] typo/{mode} - typo index empty")
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ext = "png"
    full_path = OUTPUT_DIR / f"showcase_symbol_{mode}_{_stamp()}.{ext}"

    print(f"  Rendering typo/{mode} at {res}, scale={scale} …")
    t0 = time.perf_counter()
    engine.process(
        input_path=str(source),
        output_path=str(full_path),
        res_key=res,
        mode=mode,
        scale=scale,
    )
    elapsed = time.perf_counter() - t0
    print(f"  OK typo/{mode} done in {elapsed:.1f}s  ->  {full_path.name}")
    return full_path


# -- checklist printer ---------------------------------------------------------

def print_checklist(generated: dict):
    W   = 62
    SEP = "=" * W

    print(f"\n{SEP}")
    print("  SHOWCASE CHECKLIST")
    print(SEP)
    print(f"  {'File':<42} {'Status':>8}")
    print(f"  {'-'*42} {'-'*8}")

    for fname, label in GALLERY_FILES:
        path   = EXAMPLES_DIR / fname
        exists = path.exists()
        mark   = "OK exists" if exists else "!! missing"
        print(f"  {fname:<42} {mark}")

    print()
    for fname, label in MANUAL_FILES:
        path   = (EXAMPLES_DIR / fname).resolve()
        exists = path.exists()
        mark   = "OK exists" if exists else "[>] manual"
        print(f"  {fname:<42} {mark}")
        if not exists:
            print(f"     {label}")

    print(f"\n{SEP}")
    print("  NEXT STEPS")
    print(SEP)

    all_auto_ok = all((EXAMPLES_DIR / f).exists() for f, _ in GALLERY_FILES)
    demo_ok     = (PROJECT_ROOT / "assets" / "demo.gif").exists()

    if not all_auto_ok:
        print("  (!)  Some gallery images are missing - re-run make_showcase.")
    else:
        print("  OK  All auto-generated gallery images present.")

    if not demo_ok:
        print()
        print("  [>]  MANUAL: Record GUI demo -> assets/demo.gif")
        print("     Recommended tool: OBS Studio or ShareX")
        print("     Steps:")
        print("       1. python -m src.gui")
        print("       2. Load index, pick the same source portrait")
        print("       3. Record: Load Index -> set options -> RENDER")
        print("       4. Export as GIF (<=10 MB) or WebP, save to assets/demo.gif")
    else:
        print("  OK  assets/demo.gif present.")

    print()
    print("  [>]  COMMIT when ready:")
    print("       git add assets/examples/ assets/demo.gif")
    print("       git commit -m \"docs(assets): Faza 3 - showcase images for README\"")
    print(f"{SEP}\n")


# -- main ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate README gallery images for NeuroMosaic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source", type=Path, default=None, metavar="PATH",
        help="Source portrait image (required for rendering)",
    )
    parser.add_argument(
        "--res", choices=["2K", "4K", "8K", "16K"], default="16K",
        help="Output resolution for Smart + Symbol renders (default: 16K)",
    )
    parser.add_argument(
        "--skip-smart", action="store_true",
        help="Skip Smart Engine renders (square + kite)",
    )
    parser.add_argument(
        "--skip-typo", action="store_true",
        help="Skip Typo Engine renders (symbol mosaics)",
    )
    parser.add_argument(
        "--shape",
        choices=["square", "triangle", "hexagon", "hexagon_romb", "romb", "brick_wall",
                 "rectangle_3x1", "kite", "spectre"],
        default="square",
        help="Tile shape for Smart Engine (default: square)",
    )
    parser.add_argument(
        "--tile-scale", type=float, default=1.0, metavar="F",
        help="Tile size multiplier for Smart Engine (default 1.0 = 100px; 0.5 = 50px)",
    )
    parser.add_argument(
        "--symbol-mode",
        choices=["black_on_white", "white_on_black"],
        default="black_on_white",
        help="Colour mode for Symbol Engine (default: black_on_white)",
    )
    parser.add_argument(
        "--symbol-scale", type=float, default=1.0, metavar="F",
        help="Glyph size multiplier for Symbol Engine (default 1.0)",
    )
    parser.add_argument(
        "--list", dest="list_only", action="store_true",
        help="Print checklist status only - do not render anything",
    )
    args = parser.parse_args()

    print("=" * 62)
    print("  NeuroMosaic - Showcase Generator (Faza 3)")
    print("=" * 62)

    if args.list_only:
        print_checklist({})
        return

    if args.source is None:
        # Try to find an image in input/
        input_dir = PROJECT_ROOT / "input"
        candidates = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png"))
        if candidates:
            args.source = candidates[0]
            print(f"\n  Auto-selected source: {args.source}")
        else:
            print("\n  ERROR: --source is required (no images found in input/).")
            print("  Place a portrait in input/ or pass --source path/to/portrait.jpg")
            sys.exit(1)

    if not args.source.exists():
        print(f"\n  ERROR: source not found: {args.source}")
        sys.exit(1)

    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    generated = {}

    # -- Source portrait ----------------------------------------------------
    print("\n[1] SOURCE PORTRAIT")
    step_source(args.source)

    # -- Smart mosaics ------------------------------------------------------
    if not args.skip_smart:
        shape = args.shape
        print(f"\n[2] SMART MOSAICS  (res={args.res}, shape={shape}, tile_scale={args.tile_scale})")

        full = step_smart(args.source, shape, args.res, tile_scale=args.tile_scale)
        if full:
            _save_gallery(full, EXAMPLES_DIR / f"mosaic_portrait_{shape}.jpg")
            _save_detail(full, EXAMPLES_DIR / f"detail_{shape}.jpg")
            generated[shape] = full
    else:
        print("\n[2] SMART MOSAICS  - skipped")

    # -- Typo mosaics -------------------------------------------------------
    if not args.skip_typo:
        typo_res = args.res
        print(f"\n[3] SYMBOL MOSAICS  (res={typo_res}, mode={args.symbol_mode}, scale={args.symbol_scale})")

        sym_full = step_typo(args.source, args.symbol_mode, typo_res, scale=args.symbol_scale)
        if sym_full:
            _save_gallery(sym_full, EXAMPLES_DIR / "symbol_bw.jpg")
            _save_detail(sym_full, EXAMPLES_DIR / "symbol_detail.jpg")
            generated["symbol"] = sym_full
    else:
        print("\n[3] SYMBOL MOSAICS - skipped")

    print_checklist(generated)


if __name__ == "__main__":
    main()
