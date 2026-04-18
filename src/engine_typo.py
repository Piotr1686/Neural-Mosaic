"""
src/engine_typo.py
------------------
Symbol (typographic) mosaic renderer.

Replaces each grid cell of the target image with a glyph chosen from the
pre-built typo index so that its ink density matches the local brightness of
the source image.  Supports ASCII characters and CJK Unicode blocks.
"""
import colorsys
import numpy as np
import pickle
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps, ImageFilter
import bisect
import os
import random

from .font_groups import get_fonts_for_groups, GROUP_LABELS


class TypoEngine:
    def __init__(self, index_path="data/typo_index.pkl", selected_groups=None):
        self.library = []
        self.loaded_fonts = {}

        if os.path.exists(index_path):
            print(f"Loading Font Index: {index_path}...")
            with open(index_path, "rb") as f:
                raw_lib = pickle.load(f)

            # Step 1: existing ASCII + CJK character-level filter (keep as-is for density reasons)
            allowed_ascii = set(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                "0123456789.,:;i!lI|'\"-+=oO0?/"
            )

            # Step 2: filter by font group membership
            if selected_groups and "all" not in selected_groups:
                allowed_font_files = get_fonts_for_groups(selected_groups)
                active_labels = [GROUP_LABELS.get(g, g) for g in selected_groups]
                print(f"Font filter: {', '.join(active_labels)}")
            else:
                allowed_font_files = None  # None = accept all fonts
                print("Font filter: ALL groups")

            self.library = []
            for item in raw_lib:
                char = item["char"]
                code = ord(char)
                font_path = item["font"]
                font_filename = os.path.basename(font_path)

                # Character-level check (ASCII + CJK)
                is_ascii_safe = char in allowed_ascii
                is_cjk = (
                    (0x4E00 <= code <= 0x9FFF)
                    or (0x3040 <= code <= 0x309F)
                    or (0x30A0 <= code <= 0x30FF)
                    or (0xAC00 <= code <= 0xD7A3)
                )
                char_ok = is_ascii_safe or is_cjk

                # Font-level check (group filter)
                font_ok = (allowed_font_files is None) or (font_filename in allowed_font_files)

                if char_ok and font_ok:
                    self.library.append(item)

            if len(self.library) < 50:
                print(f"WARNING: Only {len(self.library)} glyphs after filter. "
                      f"Mosaic quality will be poor. Select more groups or 'All'.")

            self.library.sort(key=lambda x: x["norm_density"])

            self.densities = [x["norm_density"] for x in self.library]
            self.min_density = self.densities[0] if self.densities else 0.0
            self.max_density = self.densities[-1] if self.densities else 1.0

            print(f"TypoEngine Ready. Symbols: {len(self.library)}.")
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
            img = enhancer.enhance(1.3)  # was 2.5 — too aggressive, caused neon colors

        return img

    def process(self, input_path, output_path, res_key="4K", mode="black_on_white",
                scale=1.0, variation=20, palette_size=16):
        if not self.library:
            return

        print(f"--- TYPO MOSAIC: {mode} @ {res_key} | Scale: {scale} ---")

        res_map = {"2K": 2500, "4K": 4500, "8K": 9000, "16K": 16000}
        target_res = res_map.get(res_key, 4500)

        base_cell_w = 14
        if res_key == "8K":  base_cell_w = 20
        if res_key == "16K": base_cell_w = 35

        cell_w = int(base_cell_w * scale)
        if cell_w < 6:
            cell_w = 6
        cell_h = int(cell_w * 1.6)

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

        # Fix 3: Reduce palette to avoid "color noise" in output
        if mode in ("color_on_white", "color_on_black") and palette_size:
            map_img = (map_img
                       .quantize(colors=palette_size, method=Image.Quantize.MEDIANCUT)
                       .convert("RGB"))

        gray_data = np.array(map_img.convert("L")) / 255.0
        color_data = np.array(map_img)

        bg_color = (255, 255, 255)
        text_fill_base = (0, 0, 0)
        if mode in ("white_on_black", "color_on_black"):
            bg_color = (0, 0, 0)
            text_fill_base = (255, 255, 255)

        final_img = Image.new("RGB", (out_w, out_h), bg_color)
        draw = ImageDraw.Draw(final_img)

        lib_min = self.min_density
        lib_max = self.max_density
        lib_range = lib_max - lib_min

        ascii_lines = []

        print(f"Grid: {cols}x{rows} | Cell: {cell_w}x{cell_h}px | Rendering...")

        for r in range(rows):
            pos_y = r * cell_h
            current_line_chars = []

            for c in range(cols):
                pos_x = c * cell_w
                brightness = gray_data[r, c]

                if mode in ("white_on_black", "color_on_black"):
                    # Dark background — higher density glyphs for bright areas
                    val = np.power(brightness, 0.8)
                    target_density = lib_min + (val * lib_range)
                else:
                    # Light background — higher density glyphs for dark areas
                    val = 1.0 - np.power(brightness, 1.1)
                    target_density = lib_min + (val * lib_range)

                idx = bisect.bisect_left(self.densities, target_density)
                idx = min(idx, len(self.library) - 1)

                start = max(0, idx - variation)
                end = min(len(self.library), idx + variation)
                chosen = random.choice(self.library[start:end])

                char = chosen["char"]
                current_line_chars.append(char)

                font_path = chosen["font"]
                font_obj = self._get_font_object(font_path, font_size)

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
                    raw = color_data[r, c]
                    # Ensure numpy uint8 -> python int (colorsys requires floats)
                    pr, pg, pb = float(raw[0]) / 255.0, float(raw[1]) / 255.0, float(raw[2]) / 255.0
                    h_val, l_val, s_val = colorsys.rgb_to_hls(pr, pg, pb)

                    if mode == "color_on_white":
                        # Darker colors read well on white background
                        l_val = min(l_val, 0.45)
                        s_val = max(s_val, 0.4)  # avoid washed-out grays
                    elif mode == "color_on_black":
                        # Lighter, more saturated colors pop on black
                        l_val = max(l_val, 0.55)
                        s_val = max(s_val, 0.5)

                    rr, gg, bb = colorsys.hls_to_rgb(h_val, l_val, s_val)
                    rgb = (int(rr * 255), int(gg * 255), int(bb * 255))

                draw.text((render_x, render_y), char, font=font_obj, fill=rgb)

            ascii_lines.append("".join(current_line_chars))

            if r % 50 == 0:
                print(f"Progress: {(r/rows)*100:.1f}%", end='\r')

        print(f"\nSaved Symbol Mosaic: {output_path}")
        final_img.save(output_path, dpi=(300, 300))

        txt_path = os.path.splitext(output_path)[0] + ".txt"
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(ascii_lines))
            print(f"Saved UTF-8 Text: {txt_path}")
        except Exception as e:
            print(f"Could not save TXT: {e}")
