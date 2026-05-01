"""
src/tools/make_dzi.py
---------------------
Generates a Deep Zoom Image (DZI) pyramid from a mosaic (JPG or PNG).

Output layout:
    <out_dir>/<stem>.dzi          -- XML descriptor
    <out_dir>/<stem>_files/<N>/   -- tile directories per level

Tile size: 256 px, overlap: 1 px, JPEG quality: 70.
Optimised for GitHub Pages hosting (small tile count, low quality).

Usage:
    python -m src.tools.make_dzi <input> <out_dir>
    python -m src.tools.make_dzi <input> <out_dir> --max-level 13
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image

TILE_SIZE = 256
OVERLAP = 1
JPEG_QUALITY = 70

DZI_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Image TileSize="{tile_size}" Overlap="{overlap}" Format="jpg"'
    ' xmlns="http://schemas.microsoft.com/deepzoom/2008">\n'
    '  <Size Width="{width}" Height="{height}"/>\n'
    '</Image>\n'
)


def _level_size(orig_w: int, orig_h: int, max_level: int, level: int) -> tuple[int, int]:
    scale = 2 ** (level - max_level)
    w = max(1, math.ceil(orig_w * scale))
    h = max(1, math.ceil(orig_h * scale))
    return w, h


def make_dzi(input_path: Path, out_dir: Path, max_level_cap: int | None = None) -> None:
    print(f"Loading {input_path.name} ...")
    img = Image.open(input_path).convert("RGB")
    orig_w, orig_h = img.size
    print(f"  Source: {orig_w}x{orig_h} px")

    max_level = math.ceil(math.log2(max(orig_w, orig_h)))

    if max_level_cap is not None and max_level_cap < max_level:
        cap_size = 2 ** max_level_cap
        # Downscale so longest side == cap_size
        ratio = cap_size / max(orig_w, orig_h)
        new_w = max(1, round(orig_w * ratio))
        new_h = max(1, round(orig_h * ratio))
        print(f"  Capping at level {max_level_cap} -> resizing to {new_w}x{new_h}")
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        orig_w, orig_h = new_w, new_h
        max_level = max_level_cap

    stem = input_path.stem
    dzi_path = out_dir / f"{stem}.dzi"
    files_dir = out_dir / f"{stem}_files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Build pyramid level by level (top-down: level 0 = 1x1)
    # We iterate from max_level down to 0
    level_img = img
    for level in range(max_level, -1, -1):
        lw, lh = _level_size(orig_w, orig_h, max_level, level)

        if level < max_level:
            level_img = img.resize((lw, lh), Image.Resampling.LANCZOS)

        level_dir = files_dir / str(level)
        level_dir.mkdir(exist_ok=True)

        cols = math.ceil(lw / TILE_SIZE)
        rows = math.ceil(lh / TILE_SIZE)

        for row in range(rows):
            for col in range(cols):
                x0 = max(0, col * TILE_SIZE - OVERLAP)
                y0 = max(0, row * TILE_SIZE - OVERLAP)
                x1 = min(lw, (col + 1) * TILE_SIZE + OVERLAP)
                y1 = min(lh, (row + 1) * TILE_SIZE + OVERLAP)
                tile = level_img.crop((x0, y0, x1, y1))
                tile.save(level_dir / f"{col}_{row}.jpg", "JPEG", quality=JPEG_QUALITY)

        if level % 3 == 0 or level == max_level:
            print(f"  Level {level:2d}  {lw}x{lh}  ({cols}x{rows} tiles)")

    dzi_path.write_text(
        DZI_TEMPLATE.format(
            tile_size=TILE_SIZE,
            overlap=OVERLAP,
            width=orig_w,
            height=orig_h,
        ),
        encoding="utf-8",
    )
    print(f"  Saved: {dzi_path}")

    # Report disk usage
    total = sum(f.stat().st_size for f in files_dir.rglob("*") if f.is_file())
    print(f"  Tiles: {total / 1_048_576:.1f} MB in {files_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DZI pyramid from mosaic image")
    parser.add_argument("input", help="Input image (JPG or PNG)")
    parser.add_argument("out_dir", help="Output directory (will be created if missing)")
    parser.add_argument(
        "--max-level",
        type=int,
        default=None,
        metavar="N",
        help="Cap pyramid at level N (2^N px on longest side). Use 13 for ~8K.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    make_dzi(input_path, out_dir, max_level_cap=args.max_level)


if __name__ == "__main__":
    main()
