"""
src/get_special_datasets.py
---------------------------
Downloader for curated specialty image datasets (dogs, cars, flowers).

Fetches tar archives from Stanford Vision Lab and Oxford VGG with HTTP
Range resume support, then extracts and flattens them into the tile
directory with a short identifying prefix per dataset.
"""
import os
import shutil
import requests
import tarfile
from pathlib import Path
from tqdm import tqdm

TARGET_DIR = Path("data/tiles")
TEMP_DIR   = Path("temp_special")

DATASETS = [
    {
        "name":     "Stanford Dogs",
        "url":      "http://vision.stanford.edu/aditya86/ImageNetDogs/images.tar",
        "filename": "dogs.tar",
        "prefix":   "dog_"
    },
    {
        "name":     "Stanford Cars",
        "url":      "http://ai.stanford.edu/~jkrause/car196/car_ims.tgz",
        "filename": "cars.tgz",
        "prefix":   "car_"
    },
    {
        "name":     "Oxford Flowers",
        "url":      "https://www.robots.ox.ac.uk/~vgg/data/flowers/102/102flowers.tgz",
        "filename": "flowers.tgz",
        "prefix":   "flower_"
    }
]


def download_file_resume(url, filename):
    """Download a file with HTTP Range resume support.

    Args:
        url:      Full URL of the resource to fetch.
        filename: Local destination filename (string).
    """
    existing_size = 0
    if os.path.exists(filename):
        existing_size = os.path.getsize(filename)

    try:
        head = requests.head(url)
        total_size = int(head.headers.get('content-length', 0))
    except Exception:
        total_size = 0

    if existing_size == total_size and total_size > 0:
        print(f"   [INFO] {filename} is already complete. Skipping.")
        return True

    mode = 'wb'
    headers = {}

    if existing_size > 0:
        print(f"   [RESUMING] {filename} (have {existing_size // 1024 // 1024} MB)...")
        headers = {'Range': f'bytes={existing_size}-'}
        mode = 'ab'  # Append to partial file.
    else:
        print(f"   [DOWNLOADING] {filename}...")

    resp = requests.get(url, headers=headers, stream=True)

    with open(filename, mode) as f, tqdm(
        total=total_size,
        initial=existing_size,
        unit='iB',
        unit_scale=True,
        desc=filename
    ) as bar:
        for chunk in resp.iter_content(1024 * 1024):
            if chunk:
                size = f.write(chunk)
                bar.update(size)


def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print("--- SPECIAL DATASETS DOWNLOAD (RESUME ENABLED) ---")

    for ds in DATASETS:
        # 1. Download with resume.
        download_file_resume(ds['url'], ds['filename'])

        # 2. Skip extraction if > 100 prefixed files already exist.
        if len(list(TARGET_DIR.glob(f"{ds['prefix']}*.jpg"))) > 100:
            print(f"   [INFO] {ds['name']} appears already extracted. Skipping.")
            continue

        # 3. Extract archive.
        print(f"   [EXTRACTING] {ds['name']}...")
        temp_extract = TEMP_DIR / ds['name'].replace(" ", "_")
        try:
            with tarfile.open(ds['filename'], 'r:*') as tar:
                tar.extractall(temp_extract)

            # 4. Flatten into tile directory with dataset prefix.
            files = list(temp_extract.rglob("*.jpg"))
            for src in tqdm(files, desc="Moving"):
                dest = TARGET_DIR / f"{ds['prefix']}{src.name}"
                shutil.move(str(src), str(dest))

            shutil.rmtree(temp_extract)

            # Optional: remove archive after successful extraction to save disk space.
            # os.remove(ds['filename'])

        except Exception as e:
            print(f"   [ERROR] Failed to extract {ds['filename']}: {e}")
            print("   If the file is corrupted, delete it and re-run this script.")

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    print("\nDone. Check the data/tiles folder.")

if __name__ == "__main__":
    main()
