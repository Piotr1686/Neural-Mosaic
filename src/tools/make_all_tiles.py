"""
src/tools/make_all_tiles.py
---------------------------
Batch DZI generator for GitHub Pages viewer.
Generates tiles for 2 mosaics into docs/tiles/.

Usage:
    python -m src.tools.make_all_tiles
    python -m src.tools.make_all_tiles --max-level 13
"""
import argparse
import sys
from pathlib import Path

from src.tools.make_dzi import make_dzi

MOSAICS = [
    "output/showcase_square_20260428_200622.jpg",
    "output/showcase_symbol_black_on_white_20260428_202842.png",
]

OUT_DIR = Path("docs/tiles")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DZI tiles for both showcase mosaics")
    parser.add_argument(
        "--max-level",
        type=int,
        default=None,
        metavar="N",
        help="Cap pyramid at level N. Use 13 for ~8K output (smaller repo).",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for path_str in MOSAICS:
        src = Path(path_str)
        if not src.exists():
            print(f"SKIP (not found): {src}", file=sys.stderr)
            continue
        print(f"\n{'='*60}")
        print(f"Processing: {src.name}")
        print(f"{'='*60}")
        make_dzi(src, OUT_DIR, max_level_cap=args.max_level)

    total = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"\nTotal docs/tiles/ size: {total / 1_048_576:.1f} MB")
    if total > 150 * 1_048_576:
        print("WARNING: > 150 MB -- consider re-running with --max-level 13", file=sys.stderr)


if __name__ == "__main__":
    main()
