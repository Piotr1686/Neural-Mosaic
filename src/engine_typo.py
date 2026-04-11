"""
src/engine_typo.py
------------------
Symbol (typographic) mosaic renderer.

Replaces each grid cell of the target image with a glyph chosen from the
pre-built typo index so that its ink density matches the local brightness of
the source image.  Supports ASCII characters and CJK Unicode blocks.
"""
import numpy as np
import pickle
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter
import bisect
import os
import random


class TypoEngine:
    def __init__(self, index_path="data/typo_index.pkl"):
        self.library = []
        self.loaded_fonts = {} 
        
        if os.path.exists(index_path):
            print(f"Loading Font Index: {index_path}...")
            with open(index_path, "rb") as f:
                raw_lib = pickle.load(f)
            
            # --- HYBRID FILTER (ASCII + CJK) ---
            self.library = []
            # Safe ASCII character whitelist — visually distinct at small sizes.
            allowed_ascii = set(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                "0123456789.,:;i!lI|'\"-+=oO0?/"
            )

            print("Applying Hybrid Filter (ASCII + Chinese/Japanese/Korean)...")

            for item in raw_lib:
                char = item["char"]
                code = ord(char)

                # 1. Check if the character is in the safe ASCII set.
                is_ascii_safe = char in allowed_ascii

                # 2. Check for CJK Unicode blocks (dense, visually rich glyphs).
                #    CJK Unified Ideographs (Hanzi/Kanji): U+4E00–U+9FFF
                #    Hiragana:                              U+3040–U+309F
                #    Katakana:                              U+30A0–U+30FF
                #    Hangul Syllables:                      U+AC00–U+D7A3
                is_cjk = (
                    (0x4E00 <= code <= 0x9FFF)
                    or (0x3040 <= code <= 0x309F)
                    or (0x30A0 <= code <= 0x30FF)
                    or (0xAC00 <= code <= 0xD7A3)
                )

                # Accept the glyph if it satisfies either condition.
                if is_ascii_safe or is_cjk:
                    self.library.append(item)

            self.library.sort(key=lambda x: x["norm_density"])
            
            self.densities = [x["norm_density"] for x in self.library]
            self.min_density = self.densities[0] if self.densities else 0.0
            self.max_density = self.densities[-1] if self.densities else 1.0
            
            print(f"TypoEngine Ready. Symbols: {len(self.library)}. Mode: Fixed Matrix Grid + CJK Support.")
        else:
            print("Warning: Font Index not found.")
            self.densities = []

    def _get_font_object(self, font_path, size):
        key = (font_path, size)
        if key not in self.loaded_fonts:
            try:
                self.loaded_fonts[key] = ImageFont.truetype(font_path, size)
            except:
                self.loaded_fonts[key] = ImageFont.load_default()
        return self.loaded_fonts[key]

    def _preprocess_image(self, img, mode):
        img = ImageOps.autocontrast(img, cutoff=2)
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.4)
        
        if "color" in mode:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(2.5) 
            
        return img

    def process(self, input_path, output_path, res_key="4K", mode="black_on_white", scale=1.0):
        if not self.library: return

        print(f"--- TYPO MOSAIC: {mode} @ {res_key} | Scale: {scale} (CJK Enabled) ---")
        
        res_map = {"2K": 2500, "4K": 4500, "8K": 9000, "16K": 16000}
        target_res = res_map.get(res_key, 4500)
        
        # Determine base cell width based on output resolution.
        base_cell_w = 14
        if res_key == "8K":  base_cell_w = 20
        if res_key == "16K": base_cell_w = 35

        cell_w = int(base_cell_w * scale)
        if cell_w < 6:
            cell_w = 6
        cell_h = int(cell_w * 1.6)

        # Font slightly smaller than the cell so glyphs don't clip.
        font_size = int(cell_h * 0.9)
        
        original = Image.open(input_path).convert("RGB")
        w, h = original.size
        aspect = h / w
        out_w = target_res
        out_h = int(target_res * aspect)
        
        cols = out_w // cell_w
        rows = out_h // cell_h
        
        processed = self._preprocess_image(original, mode)
        map_img = processed.resize((cols, rows), Image.Resampling.LANCZOS)
        
        gray_data = np.array(map_img.convert("L")) / 255.0
        color_data = np.array(map_img)
        
        bg_color = (255, 255, 255)
        text_fill_base = (0, 0, 0)
        if mode == "white_on_black":
            bg_color = (0, 0, 0)
            text_fill_base = (255, 255, 255)

        final_img = Image.new("RGB", (out_w, out_h), bg_color)
        draw = ImageDraw.Draw(final_img)
        
        lib_min = self.min_density
        lib_max = self.max_density
        lib_range = lib_max - lib_min

        ascii_lines = []

        print(f"Grid: {cols}x{rows} | Cell: {cell_w}x{cell_h}px | Rendering with CJK...")
        
        for r in range(rows):
            pos_y = r * cell_h
            current_line_chars = []
            
            for c in range(cols):
                pos_x = c * cell_w
                brightness = gray_data[r, c]
                
                if mode == "white_on_black":
                    val = np.power(brightness, 0.8)
                    target_density = lib_min + (val * lib_range)
                else:
                    val = 1.0 - np.power(brightness, 1.1)
                    target_density = lib_min + (val * lib_range)
                
                idx = bisect.bisect_left(self.densities, target_density)
                idx = min(idx, len(self.library) - 1)
                
                variation = 20
                start = max(0, idx - variation)
                end = min(len(self.library), idx + variation)
                chosen = random.choice(self.library[start:end])
                
                char = chosen["char"]
                current_line_chars.append(char)
                
                font_path = chosen["font"]
                font_obj = self._get_font_object(font_path, font_size)
                
                # Centre the glyph in the cell (works for CJK characters too).
                bbox = font_obj.getbbox(char)
                if bbox:
                    cw = bbox[2] - bbox[0]
                    ch = bbox[3] - bbox[1]
                    off_x = (cell_w - cw) / 2
                    off_y = (cell_h - ch) / 2
                    render_x = pos_x + off_x - bbox[0]
                    render_y = pos_y + off_y - bbox[1]
                else:
                    continue
                
                rgb = text_fill_base
                if "color" in mode:
                    rgb = tuple(color_data[r, c])
                
                draw.text((render_x, render_y), char, font=font_obj, fill=rgb)
            
            ascii_lines.append("".join(current_line_chars))
            
            if r % 50 == 0:
                print(f"Progress: {(r/rows)*100:.1f}%", end='\r')

        print(f"\nSaved CJK Matrix Mosaic: {output_path}")
        final_img.save(output_path, dpi=(300, 300))

        txt_path = os.path.splitext(output_path)[0] + ".txt"
        try:
            # UTF-8 encoding to preserve CJK characters in the text file.
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(ascii_lines))
            print(f"Saved UTF-8 Text: {txt_path}")
        except Exception as e:
            print(f"Could not save TXT: {e}")