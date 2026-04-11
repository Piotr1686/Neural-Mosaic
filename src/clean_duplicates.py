"""
src/clean_duplicates.py
-----------------------
MD5-based duplicate image remover for the tile library.

Scans the configured library folders, computes a hash for every image,
and moves any duplicates to a trash folder so they can be reviewed or
deleted manually.  The original (first-seen) copy is always kept.
"""
import os
import hashlib
import shutil
from pathlib import Path
from tqdm import tqdm

# --- CONFIGURATION ---
FOLDERS_TO_SCAN = [
    Path("data/library_public/tiles"),
    Path("data/library_private/tiles")
]
TRASH_FOLDER = Path("data/duplicates_trash")

def get_file_hash(filepath):
    """Compute the MD5 hash of a file.

    Reads in 64 KB chunks to avoid loading large files into RAM entirely.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Hex-string MD5 digest, or None if the file cannot be read.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def main():
    print("--- DUPLICATE CLEANER (MD5) ---")

    # Create the trash folder if it does not exist.
    if not TRASH_FOLDER.exists():
        os.makedirs(TRASH_FOLDER)

    # 1. Collect all image files across configured folders.
    all_files = []
    print("Scanning folders...")
    for folder in FOLDERS_TO_SCAN:
        if folder.exists():
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp']:
                all_files.extend(list(folder.rglob(ext)))

    print(f"Found {len(all_files)} files in total. Checking for duplicates...")

    unique_hashes = {}
    duplicates_count = 0

    # 2. Hash every file and move duplicates to the trash folder.
    for file_path in tqdm(all_files):
        file_hash = get_file_hash(file_path)

        if file_hash is None:
            continue

        if file_hash in unique_hashes:
            # Duplicate detected — move to trash with a unique name.
            try:
                new_name = f"{file_path.stem}_{duplicates_count}{file_path.suffix}"
                dest = TRASH_FOLDER / new_name
                shutil.move(str(file_path), str(dest))
                duplicates_count += 1
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
        else:
            # First occurrence — mark as the canonical original.
            unique_hashes[file_hash] = file_path

    print("-" * 30)
    print("DONE.")
    print(f"Files processed : {len(all_files)}")
    print(f"Duplicates moved: {duplicates_count}")
    print(f"Trash folder    : {TRASH_FOLDER}")
    print("-" * 30)

if __name__ == "__main__":
    main()
