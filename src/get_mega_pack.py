"""
src/get_mega_pack.py
--------------------
Bulk dataset downloader with resume support for the NeuroMosaic tile library.

Downloads and extracts large public image datasets (COCO, Food-101,
Places365) into a flat tile directory.  Uses HTTP Range headers so an
interrupted download can be resumed without starting over.
"""
import os
import shutil
import requests
import tarfile
import zipfile
from pathlib import Path
from tqdm import tqdm

# --- CONFIGURATION ---
TARGET_DIR = Path("data/tiles")
TEMP_DIR   = Path("temp_extract")

# Datasets to fetch.
DATASETS = [
    {
        "name":     "COCO Unlabeled 2017",
        "url":      "http://images.cocodataset.org/zips/unlabeled2017.zip",
        "filename": "unlabeled2017.zip",
        "prefix":   "coco_",
        "type":     "zip"
    },
    {
        "name":     "COCO Train 2017",
        "url":      "http://images.cocodataset.org/zips/train2017.zip",
        "filename": "train2017.zip",
        "prefix":   "coco_train_",
        "type":     "zip"
    },
    {
        "name":     "Food-101",
        "url":      "http://data.vision.ee.ethz.ch/cvl/food-101.tar.gz",
        "filename": "food-101.tar.gz",
        "prefix":   "food_",
        "type":     "tar"
    },
    {
        "name":     "Places365 (Val)",
        "url":      "http://data.csail.mit.edu/places/places365/val_large.tar",
        "filename": "val_large.tar",
        "prefix":   "places_",
        "type":     "tar"
    }
]


def download_file_resume(url, filename):
    """Download a file with HTTP Range resume support.

    If a partial file already exists on disk, only the missing bytes are
    fetched.  If the file is already complete, it is skipped.

    Args:
        url:      Full URL of the resource to download.
        filename: Local destination filename (string).

    Returns:
        True on success (file complete or already present).
    """
    # 1. Check how much has already been downloaded.
    existing_size = 0
    if os.path.exists(filename):
        existing_size = os.path.getsize(filename)

    # 2. Ask the server for the total file size via a HEAD request.
    try:
        head_resp = requests.head(url)
        total_size = int(head_resp.headers.get('content-length', 0))
    except Exception:
        total_size = 0  # Proceed anyway if the server doesn't report size.

    # 3. Skip if the file is already complete.
    if existing_size == total_size and total_size > 0:
        print(f"   [INFO] {filename} is complete ({total_size} bytes). Skipping.")
        return True

    if existing_size > 0:
        print(f"   [RESUMING] Already have {existing_size / (1024**3):.2f} GB. Fetching the rest...")
        headers = {'Range': f'bytes={existing_size}-'}
        mode = 'ab'  # Append to existing partial file.
    else:
        print(f"   [DOWNLOADING] {url}")
        headers = {}
        mode = 'wb'  # Fresh download.

    # 4. Stream the response and write in 1 MB chunks.
    response = requests.get(url, headers=headers, stream=True)
    chunk_size = 1024 * 1024  # 1 MB

    with open(filename, mode) as file, tqdm(
        total=total_size,
        initial=existing_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
        desc=filename
    ) as bar:
        for data in response.iter_content(chunk_size):
            size = file.write(data)
            bar.update(size)

    return True


def extract_and_flatten(ds):
    """Extract an archive and copy all images into TARGET_DIR with a prefix.

    Uses a simple heuristic to skip extraction if images with the dataset's
    prefix are already present in TARGET_DIR.

    Args:
        ds: Dataset dict with keys: name, filename, prefix, type.
    """
    # Skip if the dataset appears to be extracted already.
    sample_file = list(TARGET_DIR.glob(f"{ds['prefix']}00000*.jpg"))
    if len(sample_file) > 0:
        print(f"   [INFO] {ds['name']} appears to be already extracted. Skipping.")
        return

    current_temp = TEMP_DIR / ds["name"].replace(" ", "_")
    current_temp.mkdir(parents=True, exist_ok=True)

    print(f"   [EXTRACTING] {ds['filename']}...")
    try:
        if ds["type"] == "zip":
            if not zipfile.is_zipfile(ds["filename"]):
                print(f"   [CRITICAL ERROR] {ds['filename']} is corrupted. Delete it and re-run.")
                return
            with zipfile.ZipFile(ds["filename"], 'r') as zf:
                zf.extractall(current_temp)
        elif ds["type"] == "tar":
            with tarfile.open(ds["filename"], 'r:*') as tf:
                tf.extractall(current_temp)
    except Exception as e:
        print(f"   [EXTRACTION ERROR] {e}")
        return

    print(f"   [MOVING] Locating images and flattening directory structure...")
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        files.extend(list(current_temp.rglob(ext)))

    for src in tqdm(files, desc="Moving"):
        try:
            # Flatten nested directory structure: prefix + original filename.
            new_name = f"{ds['prefix']}{src.name}"
            shutil.move(str(src), str(TARGET_DIR / new_name))
        except Exception:
            pass

    # Remove temporary extraction directory.
    shutil.rmtree(current_temp)


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print("--- MEGA PACK DOWNLOAD (RESUME ENABLED) ---")

    for ds in DATASETS:
        download_file_resume(ds["url"], ds["filename"])
        extract_and_flatten(ds)

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    print("\n--- COMPLETE ---")

if __name__ == "__main__":
    main()
