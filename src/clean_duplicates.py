import os
import hashlib
import shutil
from pathlib import Path
from tqdm import tqdm

# KONFIGURACJA
FOLDERS_TO_SCAN = [
    Path("data/library_public/tiles"),
    Path("data/library_private/tiles")
]
TRASH_FOLDER = Path("data/duplicates_trash")

def get_file_hash(filepath):
    """Oblicza unikalny skrót MD5 dla pliku."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Czytamy w kawałkach, żeby nie zapchać RAM przy dużych plikach
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def main():
    print("--- DUPLICATE CLEANER (MD5) ---")
    
    # Tworzymy folder na śmieci
    if not TRASH_FOLDER.exists():
        os.makedirs(TRASH_FOLDER)

    # 1. Zbieranie wszystkich plików
    all_files = []
    print("Skanowanie folderów...")
    for folder in FOLDERS_TO_SCAN:
        if folder.exists():
            # Szukamy obrazków
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp']:
                all_files.extend(list(folder.rglob(ext)))
    
    print(f"Znaleziono łącznie {len(all_files)} plików. Analiza unikalności...")

    unique_hashes = {}
    duplicates_count = 0
    
    # 2. Skanowanie hashów
    for file_path in tqdm(all_files):
        file_hash = get_file_hash(file_path)
        
        if file_hash is None:
            continue

        if file_hash in unique_hashes:
            # TO JEST DUPLIKAT!
            original = unique_hashes[file_hash]
            
            # Przenosimy do kosza
            try:
                # Generujemy nową nazwę w koszu, żeby się nie nadpisały
                new_name = f"{file_path.stem}_{duplicates_count}{file_path.suffix}"
                dest = TRASH_FOLDER / new_name
                
                shutil.move(str(file_path), str(dest))
                duplicates_count += 1
            except Exception as e:
                print(f"Błąd przenoszenia {file_path}: {e}")
        else:
            # To jest oryginał (pierwsze wystąpienie)
            unique_hashes[file_hash] = file_path

    print("-" * 30)
    print(f"ZAKOŃCZONO.")
    print(f"Przetworzono: {len(all_files)} plików.")
    print(f"Znaleziono i usunięto duplikatów: {duplicates_count}")
    print(f"Duplikaty są bezpieczne w folderze: {TRASH_FOLDER}")
    print("-" * 30)

if __name__ == "__main__":
    main()