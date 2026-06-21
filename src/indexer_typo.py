"""
src/indexer_typo.py
-------------------
Builds the TypoEngine glyph density index from a folder of font files.

Scans every .ttf/.otf file in FONTS_DIR, renders each supported glyph at
SAMPLE_SIZE pixels, measures its ink density, and writes the resulting
library to INDEX_FILE as a pickle so TypoEngine can load it at runtime.

The probed Unicode blocks cover every script the bundled font groups ship
(see src/font_groups.py): Latin, CJK, Hiragana/Katakana, Hangul, the ancient
& exotic scripts (Egyptian/Anatolian hieroglyphs, cuneiform, Linear A/B,
Phoenician, runic, ...), symbols/math/music/emoji, and Arabic/Bengali/Sinhala.
Each font only contributes the blocks its cmap actually defines, so probing
many blocks is cheap: unsupported codepoints are skipped via an O(1) lookup.
"""
import argparse
import os
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat
from pathlib import Path
from tqdm import tqdm

# --- CONFIGURATION ---
FONTS_DIR = Path("assets/fonts")
INDEX_FILE = Path("data/typo_index.pkl")
SAMPLE_SIZE = 40  # Glyph render size (px) used for density analysis.

# Blocks scanned in full. (first, last, name) — inclusive bounds. Listing a
# block a given font does not define costs nothing: the cmap guard skips it.
FULL_BLOCKS = [
    # --- Latin / readable ---
    (0x0021, 0x007E, "Basic Latin"),
    (0x00A1, 0x00FF, "Latin-1 Supplement"),
    # --- CJK kana ---
    (0x3041, 0x309F, "Hiragana"),
    (0x30A0, 0x30FF, "Katakana"),
    # --- Symbols / geometric / math / music ---
    (0x2190, 0x21FF, "Arrows"),
    (0x2200, 0x22FF, "Mathematical Operators"),
    (0x2500, 0x257F, "Box Drawing"),
    (0x2580, 0x259F, "Block Elements"),
    (0x25A0, 0x25FF, "Geometric Shapes"),
    (0x2600, 0x26FF, "Miscellaneous Symbols"),
    (0x2700, 0x27BF, "Dingbats"),
    (0x2B00, 0x2BFF, "Misc Symbols and Arrows"),
    (0x1D100, 0x1D1FF, "Musical Symbols"),
    (0x1D2E0, 0x1D2FF, "Mayan Numerals"),
    (0x1F300, 0x1F5FF, "Misc Symbols & Pictographs"),
    (0x1F600, 0x1F64F, "Emoticons"),
    (0x1F680, 0x1F6FF, "Transport & Map"),
    (0x1F900, 0x1F9FF, "Supplemental Symbols & Pictographs"),
    # --- Other living scripts ---
    (0x0600, 0x06FF, "Arabic"),
    (0x0700, 0x074F, "Syriac"),
    (0x0780, 0x07BF, "Thaana"),
    (0x0980, 0x09FF, "Bengali"),
    (0x0D80, 0x0DFF, "Sinhala"),
    (0x1900, 0x194F, "Limbu"),
    (0x1A00, 0x1A1F, "Buginese"),
    (0x1BC0, 0x1BFF, "Batak"),
    (0x1C50, 0x1C7F, "Ol Chiki"),
    (0xA500, 0xA63F, "Vai"),
    (0xA6A0, 0xA6FF, "Bamum"),
    (0xA930, 0xA95F, "Rejang"),
    # --- Ancient & exotic scripts ---
    (0x1680, 0x169F, "Ogham"),
    (0x16A0, 0x16FF, "Runic"),
    (0x10000, 0x1007F, "Linear B Syllabary"),
    (0x10080, 0x100FF, "Linear B Ideograms"),
    (0x102A0, 0x102DF, "Carian"),
    (0x10380, 0x1039F, "Ugaritic"),
    (0x103A0, 0x103DF, "Old Persian"),
    (0x10400, 0x1044F, "Deseret"),
    (0x10450, 0x1047F, "Shavian"),
    (0x10600, 0x1077F, "Linear A"),
    (0x10800, 0x1083F, "Cypriot Syllabary"),
    (0x10900, 0x1091F, "Phoenician"),
    (0x10980, 0x109FF, "Meroitic"),
    (0x10A80, 0x10A9F, "Old North Arabian"),
    (0x11C00, 0x11C6F, "Bhaiksuki"),
    (0x12000, 0x123FF, "Cuneiform"),
    (0x12400, 0x1247F, "Cuneiform Numbers"),
    (0x13000, 0x1342F, "Egyptian Hieroglyphs"),
    (0x14400, 0x14646, "Anatolian Hieroglyphs"),
    (0x1B170, 0x1B2FF, "Nushu"),
]

# Very large blocks. Sampled by stride unless --full-scan is given, so the scan
# stays fast while still covering the full light-to-dark density range.
LARGE_BLOCKS = [
    (0x4E00, 0x9FFF, "CJK Unified Ideographs"),
    (0xAC00, 0xD7A3, "Hangul Syllables"),
]
SAMPLE_PER_LARGE_BLOCK = 400  # codepoints sampled per large block in sample mode


def _supported_codepoints(font_path):
    """Return the set of Unicode codepoints the font actually maps.

    Used to skip codepoints a font does not define: those render as the
    font's ``.notdef`` glyph (often a visible "tofu" box) whose ink density
    passes the blank-glyph filter, scattering identical boxes through the
    mosaic. Returns None if the cmap cannot be read, so analyse falls back
    to bbox-only filtering.
    """
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(str(font_path), fontNumber=0, lazy=True)
        try:
            cps = set()
            for table in tt["cmap"].tables:
                if table.isUnicode():
                    cps.update(table.cmap.keys())
            return cps
        finally:
            tt.close()
    except Exception:
        return None


def _iter_codepoints(full_scan: bool):
    """Yield every codepoint to probe, across all configured Unicode blocks.

    Large blocks (CJK, Hangul) are stride-sampled unless ``full_scan`` is set.
    """
    for first, last, _name in FULL_BLOCKS:
        yield from range(first, last + 1)

    for first, last, _name in LARGE_BLOCKS:
        if full_scan:
            yield from range(first, last + 1)
        else:
            step = max(1, (last - first) // SAMPLE_PER_LARGE_BLOCK)
            yield from range(first, last + 1, step)


def analyze_font(font_path, full_scan: bool = False):
    """Analyse a single font file and return character density data.

    Renders every supported glyph at SAMPLE_SIZE and measures its ink density
    (mean brightness of the rendered bitmap).

    Args:
        font_path: Path to a .ttf or .otf file.
        full_scan: If True, scan the full CJK Unified Ideographs and Hangul
                   Syllables blocks (~31K glyphs combined). If False, stride-
                   sample those two blocks (default, much faster).

    Returns:
        List of dicts with keys: char, font, density, aspect.
        Returns an empty list if the font cannot be loaded.
    """
    chars_data = []
    try:
        font = ImageFont.truetype(str(font_path), SAMPLE_SIZE)
    except Exception:
        return []

    # Codepoints the font actually maps; None => cmap unreadable, fall back
    # to the bbox/brightness filters only.
    supported = _supported_codepoints(font_path)

    # Reuse a single canvas for all glyphs (white background).
    canvas = Image.new("L", (SAMPLE_SIZE * 2, SAMPLE_SIZE * 2), 255)
    draw = ImageDraw.Draw(canvas)

    for code in _iter_codepoints(full_scan):
        # Skip codepoints the font does not define (they render as .notdef
        # tofu boxes that slip past the brightness filter).
        if supported is not None and code not in supported:
            continue
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


def main(full_scan: bool = False):
    """Entry point — scan all fonts and write the typo index to disk.

    Args:
        full_scan: If True, scan the full CJK and Hangul blocks (slower).
                   If False, stride-sample them (default, much faster).
    """
    print("--- TYPO INDEXER: GLOBAL FONT SCAN ---")
    if full_scan:
        print("Mode: FULL SCAN (full CJK + Hangul; this takes significantly longer)")
    else:
        print("Mode: SAMPLE (use --full-scan for complete CJK + Hangul blocks)")

    if not FONTS_DIR.exists():
        os.makedirs(FONTS_DIR)
        print(f"Error: {FONTS_DIR} is empty. Please place .ttf/.otf files there first.")
        return

    # Collect both TTF and OTF font files.
    font_files = list(FONTS_DIR.glob("*.ttf")) + list(FONTS_DIR.glob("*.otf"))
    print(f"Found {len(font_files)} font files. Scanning glyphs...")

    global_library = []
    for fpath in tqdm(font_files):
        global_library.extend(analyze_font(fpath, full_scan=full_scan))

    if not global_library:
        print("No glyphs found. Check that your font files are valid.")
        return

    # Sort globally by density: darkest (low value) -> lightest (high value).
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
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(global_library, f)

    print("SUCCESS! Font index created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan fonts and build typo_index.pkl")
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Scan full CJK + Hangul blocks (slower but more glyphs)",
    )
    args = parser.parse_args()
    main(full_scan=args.full_scan)
