"""
src/tools/make_all_tiles.py
---------------------------
Batch DZI generator for GitHub Pages viewer.
Auto-detects the newest photo mosaic and symbol mosaic from output/,
generates tiles into docs/tiles/, then renames outputs to canonical
fixed names so docs/index.html never needs to be updated.

Canonical outputs:
    docs/tiles/photo_mosaic.dzi   +   photo_mosaic_files/
    docs/tiles/symbol_mosaic.dzi  +   symbol_mosaic_files/

Usage:
    python -m src.tools.make_all_tiles
    python -m src.tools.make_all_tiles --max-level 13
"""
import argparse
import shutil
import sys
from pathlib import Path

from src.tools.make_dzi import make_dzi

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "output"
OUT_DIR      = PROJECT_ROOT / "docs" / "tiles"

CANONICAL = [
    ("showcase_square_*.jpg",              "photo_mosaic"),
    ("showcase_symbol_white_on_black_*.png", "symbol_mosaic"),
]
FALLBACK_SYMBOL = "showcase_symbol_*.png"


def _latest(pattern: str) -> Path | None:
    candidates = sorted(OUTPUT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _rename_to_canonical(src_stem: str, canonical: str) -> None:
    """Rename <src_stem>.dzi + <src_stem>_files/ to <canonical>.dzi + <canonical>_files/."""
    old_dzi   = OUT_DIR / f"{src_stem}.dzi"
    old_files = OUT_DIR / f"{src_stem}_files"
    new_dzi   = OUT_DIR / f"{canonical}.dzi"
    new_files = OUT_DIR / f"{canonical}_files"

    if new_dzi.exists():
        new_dzi.unlink()
    if new_files.exists():
        shutil.rmtree(new_files)

    old_dzi.rename(new_dzi)
    old_files.rename(new_files)
    print(f"  Renamed -> {canonical}.dzi  +  {canonical}_files/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DZI tiles for showcase mosaics")
    parser.add_argument(
        "--max-level",
        type=int,
        default=None,
        metavar="N",
        help="Cap pyramid at level N. Use 13 for ~8K output (smaller repo).",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    glob_sym, canonical_sym = CANONICAL[1]
    sources = []
    for glob_pat, canonical in CANONICAL:
        src = _latest(glob_pat)
        if src is None and glob_pat == glob_sym:
            src = _latest(FALLBACK_SYMBOL)
        if src is None:
            print(f"WARNING: no file matching '{glob_pat}' found in output/", file=sys.stderr)
            continue
        sources.append((src, canonical))

    if not sources:
        print("ERROR: no mosaic files found in output/", file=sys.stderr)
        sys.exit(1)

    for src, canonical in sources:
        print(f"\n{'='*60}")
        print(f"Processing: {src.name}  ->  {canonical}")
        print(f"{'='*60}")
        make_dzi(src, OUT_DIR, max_level_cap=args.max_level)
        _rename_to_canonical(src.stem, canonical)

    total = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"\nTotal docs/tiles/ size: {total / 1_048_576:.1f} MB")
    if total > 150 * 1_048_576:
        print("WARNING: > 150 MB -- consider re-running with --max-level 13", file=sys.stderr)


if __name__ == "__main__":
    main()
