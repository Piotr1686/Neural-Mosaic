# src/optimizer.py
import os
import concurrent.futures
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# --- KONFIGURACJA ---
# Lista folderów do optymalizacji
TARGET_DIRS = [
    Path("data/tiles"),                # Tu masz zrzut 800k zdjęć publicznych
    Path("data/library_private/tiles") # Tu masz swoje 32.5k zdjęć prywatnych
]

# Cel: Krótszy bok ma mieć 250px.
# Większe zdjęcia zostaną zmniejszone. Mniejsze pozostaną bez zmian.
TARGET_SHORT_SIDE = 250 

def process_image(file_path):
    try:
        with Image.open(file_path) as img:
            # Konwersja do RGB (naprawia błędy z dziwnymi formatami, np. CMYK)
            img = img.convert("RGB") 
            w, h = img.size
            current_short_side = min(w, h)
            
            # WARUNEK: Jeśli zdjęcie jest już małe (np. 200px), nie ruszamy go.
            if current_short_side <= TARGET_SHORT_SIDE:
                return False 

            # SKALOWANIE: Zmniejszamy giganty
            scale = TARGET_SHORT_SIDE / current_short_side
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Używamy filtra LANCZOS dla zachowania ostrości (ważne dla VGG)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Nadpisujemy plik (z optymalizacją kompresji JPEG)
            img.save(file_path, quality=90, optimize=True)
            return True
    except Exception:
        # Jeśli plik jest uszkodzony (nie da się otworzyć), usuwamy go
        try: os.remove(file_path)
        except: pass
        return False

def optimize_folder(folder_path):
    if not folder_path.exists():
        print(f"   [INFO] Folder nie istnieje, pomijam: {folder_path}")
        return 0, 0

    print(f"\n--- Skanowanie: {folder_path} ---")
    # Szukamy wszystkich obrazków
    files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.jpeg")) + list(folder_path.glob("*.png"))
    
    if not files:
        print("   [INFO] Folder pusty.")
        return 0, 0

    print(f"   Znaleziono {len(files)} plików. Optymalizacja...")
    
    # Wielowątkowe przetwarzanie
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(tqdm(executor.map(process_image, files), total=len(files), unit="img"))
    
    resized = sum(results)
    print(f"   Zmniejszono: {resized}")
    print(f"   Bez zmian: {len(files) - resized}")
    return len(files), resized

def main():
    print(f"--- GLOBALNY OPTYMALIZATOR ZDJĘĆ ---")
    print(f"Cel: Skalowanie w dół do {TARGET_SHORT_SIDE}px (krótszy bok).")
    
    total_files = 0
    total_resized = 0

    for folder in TARGET_DIRS:
        count, resized = optimize_folder(folder)
        total_files += count
        total_resized += resized

    print(f"\n--- PODSUMOWANIE ---")
    print(f"Łącznie przetworzono: {total_files} plików.")
    print(f"Zoptymalizowano (zmniejszono): {total_resized} plików.")

if __name__ == "__main__":
    main()