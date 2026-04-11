"""
src/optimizer.py
----------------
Batch image optimiser for the tile library.

Resizes large images in-place so the short side is at most TARGET_SHORT_SIDE
pixels, then re-saves with JPEG quality 90.  Corrupted files are deleted
automatically.  Uses multiprocessing for throughput on large datasets.
"""
import os
import concurrent.futures
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# --- CONFIGURATION ---
# Folders to scan and optimise.
TARGET_DIRS = [
    Path("data/tiles"),                 # Public-domain tile dump (~800 k images)
    Path("data/library_private/tiles"), # Private tile library (~32.5 k images)
]

# Target: resize images whose short side exceeds this value.
# Images already smaller or equal are left untouched.
TARGET_SHORT_SIDE = 250


def process_image(file_path):
    """Resize a single image file to TARGET_SHORT_SIDE on its short side.

    Args:
        file_path: Path to the image file to process.

    Returns:
        True if the image was resized, False if it was already small enough
        or if the file was corrupt (and subsequently deleted).
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB to handle unusual formats (e.g. CMYK, RGBA).
            img = img.convert("RGB")
            w, h = img.size
            current_short_side = min(w, h)

            # Skip images that are already within the size limit.
            if current_short_side <= TARGET_SHORT_SIDE:
                return False

            # Downscale so the short side equals TARGET_SHORT_SIDE.
            scale = TARGET_SHORT_SIDE / current_short_side
            new_w = int(w * scale)
            new_h = int(h * scale)

            # LANCZOS gives the sharpest result, important for colour matching.
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Overwrite the original file with optimised JPEG compression.
            img.save(file_path, quality=90, optimize=True)
            return True
    except Exception:
        # Remove corrupt files that cannot be opened.
        try:
            os.remove(file_path)
        except Exception:
            pass
        return False


def optimize_folder(folder_path):
    """Optimise all images inside *folder_path* using a process pool.

    Args:
        folder_path: Path object pointing to the directory to scan.

    Returns:
        Tuple of (total_files, resized_count).
    """
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

    print(f"   Found {len(files)} files. Optimising...")

    # Multiprocessing for speed across large datasets.
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(
            tqdm(executor.map(process_image, files), total=len(files), unit="img")
        )

    resized = sum(results)
    print(f"   Resized:   {resized}")
    print(f"   Unchanged: {len(files) - resized}")
    return len(files), resized


def main():
    """Entry point — optimise all configured tile directories."""
    print(f"--- IMAGE OPTIMISER ---")
    print(f"Target: downscale to {TARGET_SHORT_SIDE} px on the short side.")

    total_files = 0
    total_resized = 0

    for folder in TARGET_DIRS:
        count, resized = optimize_folder(folder)
        total_files += count
        total_resized += resized

    print(f"\n--- SUMMARY ---")
    print(f"Total files processed: {total_files}")
    print(f"Files resized:         {total_resized}")


if __name__ == "__main__":
    main()