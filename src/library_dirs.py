"""
src/library_dirs.py
-------------------
Single source of truth for the tile-library directories.

The smart indexer scans these; the maintenance tools (duplicate cleaner,
optimiser, sanity check) must operate on the SAME set or they silently drift
out of sync (cleaning/optimising only a subset, false orphan counts). Kept in
its own dependency-free module so every consumer can import it without pulling
in heavy deps (skimage, torch).
"""
from pathlib import Path

LIBRARY_DIRS = [
    Path("data/library_starter/tiles"),
    Path("data/library_public/tiles"),
    Path("data/library_public_2/tiles"),
    Path("data/library_extended/tiles"),
    Path("data/library_private/tiles"),
    Path("data/tiles"),  # legacy downloader.py / get_* target (config.DATA_DIR)
]
