# src/get_mega_pack.py
import os
import shutil
import requests
import tarfile
import zipfile
from pathlib import Path
from tqdm import tqdm

# Konfiguracja
TARGET_DIR = Path("data/tiles")
TEMP_DIR = Path("temp_extract")

# Lista źródeł
DATASETS = [
    {
        "name": "COCO Unlabeled 2017",
        "url": "http://images.cocodataset.org/zips/unlabeled2017.zip",
        "filename": "unlabeled2017.zip",
        "prefix": "coco_",
        "type": "zip"
    },
    {
        "name": "COCO Train 2017",
        "url": "http://images.cocodataset.org/zips/train2017.zip",
        "filename": "train2017.zip",
        "prefix": "coco_train_",
        "type": "zip"
    },
    {
        "name": "Food-101",
        "url": "http://data.vision.ee.ethz.ch/cvl/food-101.tar.gz",
        "filename": "food-101.tar.gz",
        "prefix": "food_",
        "type": "tar"
    },
    {
        "name": "Places365 (Val)",
        "url": "http://data.csail.mit.edu/places/places365/val_large.tar",
        "filename": "val_large.tar",
        "prefix": "places_",
        "type": "tar"
    }
]

def download_file_resume(url, filename):
    """
    Pobiera plik z obsługą wznawiania (Range Header).
    """
    # 1. Sprawdź ile już mamy
    existing_size = 0
    if os.path.exists(filename):
        existing_size = os.path.getsize(filename)

    # 2. Zapytaj serwer o całkowity rozmiar (HEAD request)
    try:
        head_resp = requests.head(url)
        total_size = int(head_resp.headers.get('content-length', 0))
    except:
        # Jeśli serwer nie podaje rozmiaru w HEAD, zakładamy 0 i pobieramy normalnie
        total_size = 0

    # 3. Decyzja
    if existing_size == total_size and total_size > 0:
        print(f"   [INFO] Plik {filename} jest kompletny ({total_size} bajtów). Pomijam.")
        return True # Sukces

    if existing_size > 0:
        print(f"   [WZNAWIANIE] Mamy {existing_size / (1024**3):.2f} GB. Pobieram resztę...")
        headers = {'Range': f'bytes={existing_size}-'}
        mode = 'ab' # Append (dopisz)
    else:
        print(f"   [POBIERANIE] {url}")
        headers = {}
        mode = 'wb' # Write (nowy)

    # 4. Pobieranie właściwe
    response = requests.get(url, headers=headers, stream=True)
    
    # Uwaga: przy wznawianiu content-length to tylko brakująca część
    chunk_size = 1024 * 1024 # 1MB
    
    # Pasek postępu musi wiedzieć, że startujemy od existing_size
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
    # Sprawdzamy czy już wypakowane (prosta heurystyka)
    sample_file = list(TARGET_DIR.glob(f"{ds['prefix']}00000*.jpg"))
    if len(sample_file) > 0:
        print(f"   [INFO] Wygląda na to, że {ds['name']} jest już w folderze. Pomijam rozpakowywanie.")
        return

    current_temp = TEMP_DIR / ds["name"].replace(" ", "_")
    current_temp.mkdir(parents=True, exist_ok=True)
    
    print(f"   [ROZPAKOWYWANIE] {ds['filename']}...")
    try:
        if ds["type"] == "zip":
            if not zipfile.is_zipfile(ds["filename"]):
                print(f"   [BŁĄD KRYTYCZNY] Plik {ds['filename']} jest uszkodzony! Usuń go i pobierz ponownie.")
                return
            with zipfile.ZipFile(ds["filename"], 'r') as zf:
                zf.extractall(current_temp)
        elif ds["type"] == "tar":
            with tarfile.open(ds["filename"], 'r:*') as tf:
                tf.extractall(current_temp)
    except Exception as e:
        print(f"   [BŁĄD ROZPAKOWYWANIA] {e}")
        return

    print(f"   [PRZENOSZENIE] Szukam zdjęć i przenoszę...")
    files = []
    # Szukamy rekurencyjnie wszystkich obrazków
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        files.extend(list(current_temp.rglob(ext)))
    
    for src in tqdm(files, desc="Przenoszenie"):
        try:
            # Flattening: zmieniamy strukturę folderów na płaską listę plików z prefiksem
            new_name = f"{ds['prefix']}{src.name}"
            shutil.move(str(src), str(TARGET_DIR / new_name))
        except: pass
            
    # Sprzątanie folderu tymczasowego
    shutil.rmtree(current_temp)

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print("--- START POBIERANIA (MEGA PACK - RESUME ENABLED) ---")
    
    for ds in DATASETS:
        # 1. Pobierz (z wznawianiem)
        download_file_resume(ds["url"], ds["filename"])
        
        # 2. Rozpakuj
        extract_and_flatten(ds)
        
    if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)
    print("\n--- ZAKOŃCZONO ---")

if __name__ == "__main__":
    main()