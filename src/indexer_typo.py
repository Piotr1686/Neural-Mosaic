import os
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat
from pathlib import Path
from tqdm import tqdm
import glob

# CONFIG
FONTS_DIR = Path("assets/fonts")
INDEX_FILE = Path("data/typo_index.pkl")
SAMPLE_SIZE = 40  # Rozmiar próbki do badania gęstości

def analyze_font(font_path):
    """
    Analizuje jeden plik czcionki i zwraca listę dostępnych znaków wraz z ich gęstością.
    """
    chars_data = []
    try:
        # Ładujemy font
        font = ImageFont.truetype(str(font_path), SAMPLE_SIZE)
    except:
        return []

    # Zakresy znaków do sprawdzenia (ASCII, Latin, Math, CJK, Runes, Arrows)
    ranges = [
        (33, 126),      # Basic Latin
        (161, 255),     # Latin-1
        (8592, 8703),   # Arrows
        (8704, 8959),   # Math Operators
        (9472, 9631),   # Box Drawing
        (9632, 9727),   # Block Elements
        (5792, 5880),   # Runic
        (12353, 12447), # Hiragana
        (19968, 20100)  # CJK (Chińskie - próbka)
    ]

    # Płótno testowe
    canvas = Image.new("L", (SAMPLE_SIZE*2, SAMPLE_SIZE*2), 255) # Białe tło
    draw = ImageDraw.Draw(canvas)

    for start, end in ranges:
        for code in range(start, end):
            char = chr(code)
            try:
                # 1. Sprawdź czy znak istnieje
                bbox = font.getbbox(char)
                if bbox is None: continue
                
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w == 0 or h == 0: continue

                # 2. Narysuj znak
                draw.rectangle((0,0,SAMPLE_SIZE*2,SAMPLE_SIZE*2), fill=255)
                
                # Centrowanie
                x = (SAMPLE_SIZE*2 - w) / 2
                y = (SAMPLE_SIZE*2 - h) / 2
                draw.text((x, y), char, font=font, fill=0) # Czarny tekst
                
                # 3. Oblicz gęstość
                stat = ImageStat.Stat(canvas)
                mean_brightness = stat.mean[0]
                
                # Ignorujemy puste znaki (białe)
                if mean_brightness >= 254: continue

                # ZAPISUJEMY DANE O ZNAKU
                chars_data.append({
                    "char": char,
                    "font": str(font_path), # Ścieżka do pliku .ttf
                    "density": mean_brightness,
                    "aspect": w / h if h > 0 else 1.0
                })

            except Exception:
                continue
                
    return chars_data

def main():
    print("--- TYPO INDEXER: GLOBAL FONT SCAN ---")
    
    if not FONTS_DIR.exists():
        os.makedirs(FONTS_DIR)
        print(f"Error: {FONTS_DIR} is empty. Please put .ttf files there first!")
        return

    # Szukamy zarówno ttf jak i otf
    font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    print(f"Found {len(font_files)} font files. Scanning symbols...")

    global_library = []

    for fpath in tqdm(font_files):
        font_chars = analyze_font(fpath)
        global_library.extend(font_chars)

    if not global_library:
        print("No characters found! Check your font files.")
        return

    # SORTOWANIE GLOBALNE PO GĘSTOŚCI
    # Od najciemniejszego (density małe) do najjaśniejszego (density duże)
    global_library.sort(key=lambda x: x["density"])

    # Normalizacja gęstości
    if len(global_library) > 1:
        min_d = global_library[0]["density"]
        max_d = global_library[-1]["density"]
        
        print(f"Normalization: Darkest={min_d:.1f}, Lightest={max_d:.1f}")
        
        for item in global_library:
            # Skalujemy density do zakresu 0-1
            norm = (item["density"] - min_d) / (max_d - min_d + 1e-9)
            item["norm_density"] = norm 
    else:
        global_library[0]["norm_density"] = 0.5

    print(f"Saving {len(global_library)} symbols to {INDEX_FILE}...")
    
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(global_library, f)
        
    print("SUCCESS! Font Index Created.")

if __name__ == "__main__":
    main()