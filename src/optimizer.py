"""
src/optimizer.py
----------------
Batch image optimiser for the tile library.

Resizes large images IN-PLACE so the short side is at most --short-side pixels
(default OPTIMIZER_SHORT_SIDE env or 512), then re-saves with JPEG quality 90.
Uses multiprocessing for throughput on large datasets.

WARNING: this operation is DESTRUCTIVE — it overwrites originals. Historically
the default was 250 px, which is what softened the whole tile library (a 640 px
COCO photo crushed to 250 px cannot be un-crushed; recovery means re-downloading
the source, see src/tools/upgrade_tiles.py). The default is now 512 px so fresh
libraries keep enough resolution for tile_scale up to ~5. Corrupt files are only
deleted when --delete-corrupt is passed (otherwise they are logged and skipped),
so a single unreadable file never silently disappears.

The hi-res overlay dir (data/tiles_hires, engine_smart.HIRES_DIR) is explicitly
refused as a target: optimising it would undo the whole point of the overlay.
"""
import os
import argparse
import functools
import concurrent.futures
from pathlib import Path
from PIL import Image
from tqdm import tqdm

from src.library_dirs import LIBRARY_DIRS

# --- CONFIGURATION ---
# Folders to scan and optimise — the full library set (see library_dirs).
TARGET_DIRS = LIBRARY_DIRS

# Default target: resize images whose short side exceeds this value. Images
# already smaller or equal are left untouched. Overridable via env or --short-side.
TARGET_SHORT_SIDE = int(os.getenv("OPTIMIZER_SHORT_SIDE", "512"))

# The overlay dir must never be optimised (it holds the sharp re-fetched tiles).
_REFUSED_DIR_NAMES = {"tiles_hires"}


def process_image(file_path, target_short_side, delete_corrupt):
    """Resize a single image file to target_short_side on its short side.

    Args:
        file_path:         Path to the image file to process.
        target_short_side: Max short-side length; larger images are downscaled.
        delete_corrupt:    When True, unreadable files are removed; otherwise
                           they are left on disk (and reported as skipped).

    Returns:
        True if the image was resized, False if it was already small enough
        or could not be opened.
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB to handle unusual formats (e.g. CMYK, RGBA).
            img = img.convert("RGB")
            w, h = img.size
            current_short_side = min(w, h)

            # Skip images that are already within the size limit.
            if current_short_side <= target_short_side:
                return False

            # Downscale so the short side equals target_short_side.
            scale = target_short_side / current_short_side
            new_w = int(w * scale)
            new_h = int(h * scale)

            # LANCZOS gives the sharpest result, important for colour matching.
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Overwrite the original file with optimised JPEG compression.
            img.save(file_path, quality=90, optimize=True)
            return True
    except Exception:
        # A corrupt/unreadable file: deleting silently once cost us data before,
        # so removal is now opt-in only.
        if delete_corrupt:
            try:
                os.remove(file_path)
            except Exception:
                pass
        return False


def optimize_folder(folder_path, target_short_side, delete_corrupt):
    """Optimise all images inside *folder_path* using a process pool.

    Returns:
        Tuple of (total_files, resized_count).
    """
    if folder_path.name in _REFUSED_DIR_NAMES:
        print(f"   [REFUSED] {folder_path} is the hi-res overlay; never optimise it.")
        return 0, 0

    if not folder_path.exists():
        print(f"   [INFO] Folder does not exist, skipping: {folder_path}")
        return 0, 0

    print(f"\n--- Scanning: {folder_path} ---")
    files = (
        list(folder_path.glob("*.jpg"))
        + list(folder_path.glob("*.jpeg"))
        + list(folder_path.glob("*.png"))
    )

    if not files:
        print("   [INFO] Folder is empty.")
        return 0, 0

    print(f"   Found {len(files)} files. Optimising to {target_short_side} px...")

    worker = functools.partial(
        process_image,
        target_short_side=target_short_side,
        delete_corrupt=delete_corrupt,
    )
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(
            tqdm(executor.map(worker, files), total=len(files), unit="img")
        )

    resized = sum(results)
    print(f"   Resized:   {resized}")
    print(f"   Unchanged: {len(files) - resized}")
    return len(files), resized


def main(argv=None):
    """Entry point — optimise all configured tile directories."""
    parser = argparse.ArgumentParser(
        description="Downscale oversized tile images in-place (DESTRUCTIVE)."
    )
    parser.add_argument(
        "--short-side", type=int, default=TARGET_SHORT_SIDE,
        help=f"Max short side in px (default: {TARGET_SHORT_SIDE}, "
             f"env OPTIMIZER_SHORT_SIDE).",
    )
    parser.add_argument(
        "--delete-corrupt", action="store_true",
        help="Remove files that cannot be opened (default: keep and skip).",
    )
    args = parser.parse_args(argv)

    print("--- IMAGE OPTIMISER (in-place, destructive) ---")
    print(f"Target: downscale to {args.short_side} px on the short side.")
    if not args.delete_corrupt:
        print("Corrupt files: kept (pass --delete-corrupt to remove).")

    total_files = 0
    total_resized = 0

    for folder in TARGET_DIRS:
        count, resized = optimize_folder(folder, args.short_side, args.delete_corrupt)
        total_files += count
        total_resized += resized

    print(f"\n--- SUMMARY ---")
    print(f"Total files processed: {total_files}")
    print(f"Files resized:         {total_resized}")


if __name__ == "__main__":
    main()
