# src/get_special_datasets.py
import os
import shutil
import requests
import tarfile
from pathlib import Path
from tqdm import tqdm

TARGET_DIR = Path("data/tiles")
TEMP_DIR = Path("temp_special")

DATASETS = [
    {
        "name": "Stanford Dogs", 
        "url": "http://vision.stanford.edu/aditya86/ImageNetDogs/images.tar", 
        "filename": "dogs.tar", 
        "prefix": "dog_"
    },
    {
        "name": "Stanford Cars", 
        "url": "http://ai.stanford.edu/~jkrause/car196/car_ims.tgz", 
        "filename": "cars.tgz", 
        "prefix": "car_"
    },
    {
        "name": "Oxford Flowers", 
        "url": "https://www.robots.ox.ac.uk/~vgg/data/flowers/102/102flowers.tgz", 
        "filename": "flowers.tgz", 
        "prefix": "flower_"
    }
]

def download_file_resume(url, filename):
    """Pobieranie z obsługą wznawiania (Range Header)"""
    existing_size = 0
    if os.path.exists(filename):
        existing_size = os.path.getsize(filename)

    try:
        # Pobieramy rozmiar całkowity
        head = requests.head(url)
        total_size = int(head.headers.get('content-length', 0))
    except:
        total_size = 0

    if existing_size == total_size and total_size > 0:
        print(f"   [INFO] {filename} jest kompletny. Pomijam pobieranie.")
        return True

    mode = 'wb'
    headers = {}
    
    if existing_size > 0:
        print(f"   [WZNAWIANIE] {filename} (Mamy {existing_size//1024//1024} MB)...")
        headers = {'Range': f'bytes={existing_size}-'}
        mode = 'ab' # Append binary (dopisz)
    else:
        print(f"   [POBIERANIE] {filename}...")

    resp = requests.get(url, headers=headers, stream=True)
    
    with open(filename, mode) as f, tqdm(
        total=total_size, 
        initial=existing_size,
        unit='iB', 
        unit_scale=True,
        desc=filename
    ) as bar:
        for chunk in resp.iter_content(1024*1024):
            if chunk:
                size = f.write(chunk)
                bar.update(size)

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    print("--- POBIERANIE SPECJALNE (WZNAWIANIE AKTYWNE) ---")
    
    for ds in DATASETS:
        # 1. Pobieranie bezpieczne
        download_file_resume(ds['url'], ds['filename'])
        
        # 2. Sprawdzenie czy już rozpakowane (żeby nie robić tego 2x)
        # Sprawdzamy czy jest > 100 plików z tym prefiksem
        if len(list(TARGET_DIR.glob(f"{ds['prefix']}*.jpg"))) > 100:
            print(f"   [INFO] Zestaw {ds['name']} wygląda na wypakowany. Pomijam.")
            continue

        # 3. Rozpakowanie
        print(f"   [ROZPAKOWYWANIE] {ds['name']}...")
        temp_extract = TEMP_DIR / ds['name'].replace(" ", "_")
        try:
            with tarfile.open(ds['filename'], 'r:*') as tar:
                tar.extractall(temp_extract)
            
            # 4. Przenoszenie
            files = list(temp_extract.rglob("*.jpg"))
            for src in tqdm(files, desc="Przenoszenie"):
                dest = TARGET_DIR / f"{ds['prefix']}{src.name}"
                shutil.move(str(src), str(dest))
                
            shutil.rmtree(temp_extract)
            
            # Opcjonalnie: Usuń archiwum po sukcesie, żeby zwolnić miejsce
            # os.remove(ds['filename']) 
            
        except Exception as e:
            print(f"   [BŁĄD] Nie udało się rozpakować {ds['filename']}: {e}")
            print("   Jeśli plik jest uszkodzony, usuń go i uruchom skrypt ponownie.")

    if TEMP_DIR.exists(): shutil.rmtree(TEMP_DIR)
    print("\nGotowe. Sprawdź folder data/tiles.")

if __name__ == "__main__":
    main()