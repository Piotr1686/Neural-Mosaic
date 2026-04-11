"""
src/indexer_typo.py
-------------------
Builds the TypoEngine glyph density index from a folder of font files.

Scans every .ttf/.otf file in FONTS_DIR, renders each supported glyph at
SAMPLE_SIZE pixels, measures its ink density, and writes the resulting
library to INDEX_FILE as a pickle so TypoEngine can load it at runtime.
"""
import os
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat
from pathlib import Path
from tqdm import tqdm
import glob

# --- CONFIGURATION ---
FONTS_DIR = Path("assets/fonts")
INDEX_FILE = Path("data/typo_index.pkl")
SAMPLE_SIZE = 40  # Glyph render size (px) used for density analysis.


def analyze_font(font_path):
    """Analyse a single font file and return character density data.

    Renders every supported glyph at SAMPLE_SIZE and measures its ink density
    (mean brightness of the rendered bitmap).

    Args:
        font_path: Path to a .ttf or .otf file.

    Returns:
        List of dicts with keys: char, font, density, aspect.
        Returns an empty list if the font cannot be loaded.
    """
    chars_data = []
    try:
        font = ImageFont.truetype(str(font_path), SAMPLE_SIZE)
    except Exception:
        return []

    # Unicode ranges to probe.
    ranges = [
        (33,    126),   # Basic Latin (printable ASCII)
        (161,   255),   # Latin-1 Supplement
        (8592,  8703),  # Arrows
        (8704,  8959),  # Mathematical Operators
        (9472,  9631),  # Box Drawing
        (9632,  9727),  # Block Elements
        (5792,  5880),  # Runic
        (12353, 12447), # Hiragana
        (19968, 20100), # CJK Unified Ideographs (sample)
    ]

    # Reuse a single canvas for all glyphs (white background).
    canvas = Image.new("L", (SAMPLE_SIZE * 2, SAMPLE_SIZE * 2), 255)
    draw = ImageDraw.Draw(canvas)

    for start, end in ranges:
        for code in range(start, end):
            char = chr(code)
            try:
                # 1. Check that the glyph has non-zero dimensions.
                bbox = font.getbbox(char)
                if bbox is None:
                    continue
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if w == 0 or h == 0:
                    continue

                # 2. Render the glyph centred on the canvas.
                draw.rectangle((0, 0, SAMPLE_SIZE * 2, SAMPLE_SIZE * 2), fill=255)
                x = (SAMPLE_SIZE * 2 - w) / 2
                y = (SAMPLE_SIZE * 2 - h) / 2
                draw.text((x, y), char, font=font, fill=0)  # Black glyph on white

                # 3. Compute ink density as mean brightness (lower = darker).
                stat = ImageStat.Stat(canvas)
                mean_brightness = stat.mean[0]

                # Skip invisible (blank) glyphs.
                if mean_brightness >= 254:
                    continue

                chars_data.append({
                    "char":    char,
                    "font":    str(font_path),
                    "density": mean_brightness,
                    "aspect":  w / h if h > 0 else 1.0,
                })

            except Exception:
                continue

    return chars_data


def main():
    """Entry point — scan all fonts and write the typo index to disk."""
    print("--- TYPO INDEXER: GLOBAL FONT SCAN ---")

    if not FONTS_DIR.exists():
        os.makedirs(FONTS_DIR)
        print(f"Error: {FONTS_DIR} is empty. Please place .ttf/.otf files there first.")
        return

    # Collect both TTF and OTF font files.
    font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    print(f"Found {len(font_files)} font files. Scanning glyphs...")

    global_library = []
    for fpath in tqdm(font_files):
        global_library.extend(analyze_font(fpath))

    if not global_library:
        print("No glyphs found. Check that your font files are valid.")
        return

    # Sort globally by density: darkest (low value) → lightest (high value).
    global_library.sort(key=lambda x: x["density"])

    # Normalise density values to [0, 1].
    if len(global_library) > 1:
        min_d = global_library[0]["density"]
        max_d = global_library[-1]["density"]
        print(f"Normalisation: darkest={min_d:.1f}, lightest={max_d:.1f}")
        for item in global_library:
            item["norm_density"] = (item["density"] - min_d) / (max_d - min_d + 1e-9)
    else:
        global_library[0]["norm_density"] = 0.5

    print(f"Saving {len(global_library)} glyphs to {INDEX_FILE}...")
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(global_library, f)

    print("SUCCESS! Font index created.")

if __name__ == "__main__":
    main()