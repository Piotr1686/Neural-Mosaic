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

        return img

    def process(self, input_path, output_path, res_key="4K", mode="black_on_white",
                scale=1.0, variation=20, progress_cb=None):
        """Public API — resolves res_key and delegates to _do_render."""
        if not self.library:
            return
        print(f"--- TYPO MOSAIC: {mode} @ {res_key} | Scale: {scale} ---")
        res_map = {"2K": 2500, "4K": 4500, "8K": 9000, "16K": 16000}
        target_res = res_map.get(res_key, 4500)
        base_cell_w = 14
        if res_key == "8K":  base_cell_w = 20
        if res_key == "16K": base_cell_w = 35
        cell_w = max(6, int(base_cell_w * scale))
        cell_h = int(cell_w * 1.6)
        original = Image.open(input_path).convert("RGB")
        w, h = original.size
        out_w = target_res
        out_h = int(target_res * h / w)
        result = self._do_render(original, out_w, out_h, cell_w, cell_h, mode, variation, progress_cb=progress_cb)
        result.save(output_path, dpi=(300, 300))

    def render_sized(self, input_path, output_path, out_w, out_h, mode="black_on_white",
                     scale=1.0, variation=20, progress_cb=None):
        """Render at explicit pixel dimensions — used by the preview pipeline."""
        if not self.library:
            return
        cell_w = max(6, int(14 * scale))
        cell_h = int(cell_w * 1.6)
        original = Image.open(input_path).convert("RGB")
        result = self._do_render(original, out_w, out_h, cell_w, cell_h, mode, variation, progress_cb=progress_cb)
        result.save(output_path, dpi=(300, 300))

    def render_preview(self, input_path, short_edge=512, mode="black_on_white",
                       scale=1.0, variation=20):
        """Return a PIL Image preview at ~short_edge px short side — no file I/O."""
        if not self.library:
            raise RuntimeError("Typo index not loaded.")
        original = Image.open(input_path).convert("RGB")
        img_w, img_h = original.size
        sc = short_edge / min(img_w, img_h)
        out_w = max(1, int(img_w * sc))
        out_h = max(1, int(img_h * sc))
        cell_w = max(6, int(14 * scale))
        cell_h = int(cell_w * 1.6)
        return self._do_render(original, out_w, out_h, cell_w, cell_h, mode, variation)

    def _do_render(self, original, out_w, out_h, cell_w, cell_h, mode, variation, progress_cb=None):
        """Core rendering kernel — accepts a pre-opened PIL Image, returns PIL Image.

        ``progress_cb``, if given, is called ``progress_cb(done, total)`` every 50 rows
        (and once at completion), where ``total`` is the row count. Used by the GUI to
        drive a progress bar.
        """
        font_size = int(cell_h * 0.9)
        cols = out_w // cell_w
        rows = out_h // cell_h

        processed = self._preprocess_image(original, mode)
        map_img = processed.resize((cols, rows), Image.Resampling.LANCZOS)
        gray_data = np.array(map_img.convert("L")) / 255.0

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

        print(f"Grid: {cols}x{rows} | Cell: {cell_w}x{cell_h}px | Rendering...")

        for r in range(rows):
            pos_y = r * cell_h
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

                start = max(0, idx - variation)
                end = min(len(self.library), idx + variation)
                chosen = random.choice(self.library[start:end])

                char = chosen["char"]
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

                draw.text((render_x, render_y), char, font=font_obj, fill=text_fill_base)

            if r % 50 == 0:
                print(f"Progress: {(r/rows)*100:.1f}%", end='\r')
                if progress_cb is not None:
                    progress_cb(r, rows)

        if progress_cb is not None:
            progress_cb(rows, rows)
        return final_img
