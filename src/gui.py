"""
src/gui.py
----------
Main application window for NeuroMosaic built with CustomTkinter.

Provides two tabs:
  * Smart Photo Mosaic — colour-matched photomosaic using SmartEngine.
  * Symbol Mosaic (Typo) — typography-based mosaic using TypoEngine.
"""
import os
import subprocess
import sys
import shutil
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import customtkinter as ctk
from tkinter import filedialog
import threading
from datetime import datetime
from pathlib import Path
from .engine_smart import SmartEngine
from .engine_typo import TypoEngine
from .indexer_smart import SmartIndexer, LIBRARY_DIRS
from .font_groups import GROUP_LABELS
from .downloader_v2 import PoliteDownloader, DEFAULT_OUTPUT_DIR

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FONTS_DIR = Path("assets/fonts")
STARTER_TARGET = 500


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Neural-Mosaic 5.7 (Solid Geometry)")
        self.geometry("1250x900")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.output_dir = None
        self._active_dl: PoliteDownloader | None = None

        self._init_sidebar()
        self._init_tabs()

        self.smart_engine = None
        self.typo_engine = TypoEngine()

    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo = ctk.CTkLabel(self.sidebar, text="NEURAL\nMOSAIC", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        # --- INDEXING SECTION ---
        self.btn_load_smart = ctk.CTkButton(self.sidebar, text="Load Smart Index", fg_color="darkgreen", command=self.load_index)
        self.btn_load_smart.grid(row=1, column=0, padx=20, pady=(10, 5))

        self.btn_update_smart = ctk.CTkButton(self.sidebar, text="Update / Create Index", fg_color="#1f538d", command=self.run_smart_indexer)
        self.btn_update_smart.grid(row=2, column=0, padx=20, pady=(5, 10))

        # --- TILE LIBRARY SECTION ---
        ctk.CTkLabel(self.sidebar, text="TILE LIBRARY", font=ctk.CTkFont(size=12, weight="bold")).grid(row=3, column=0, pady=(10, 2))

        self.lbl_library_status = ctk.CTkLabel(self.sidebar, text="EMPTY", text_color="red")
        self.lbl_library_status.grid(row=4, column=0, pady=(0, 4))

        self.btn_dl_starter = ctk.CTkButton(
            self.sidebar, text="Download Starter (500 · ~25 MB)",
            fg_color="#5a3e8a", width=220, command=self.download_starter,
        )
        self.btn_dl_starter.grid(row=5, column=0, padx=15, pady=2)

        self.btn_dl_public = ctk.CTkButton(
            self.sidebar, text="Download Gallery (5K · ~250 MB)",
            fg_color="#5a3e8a", width=220, command=self.download_public,
        )
        self.btn_dl_public.grid(row=6, column=0, padx=15, pady=2)

        self.btn_dl_extended = ctk.CTkButton(
            self.sidebar, text="Download Extended (30K · ~2.5 GB)",
            fg_color="#5a3e8a", width=220, command=self.download_extended,
        )
        self.btn_dl_extended.grid(row=7, column=0, padx=15, pady=2)

        self.btn_import = ctk.CTkButton(
            self.sidebar, text="Import Your Photos...",
            fg_color="gray", width=220, command=self.import_photos,
        )
        self.btn_import.grid(row=8, column=0, padx=15, pady=(2, 6))

        self.progress_dl = ctk.CTkProgressBar(self.sidebar, width=220)
        self.progress_dl.set(0)
        self.progress_dl.grid(row=9, column=0, padx=15, pady=(0, 4))
        self.progress_dl.grid_remove()

        self.btn_stop_dl = ctk.CTkButton(
            self.sidebar, text="Stop Download",
            fg_color="#8a1a1a", hover_color="#a83232", width=220,
            command=self._stop_download,
        )
        self.btn_stop_dl.grid(row=10, column=0, padx=15, pady=(0, 6))
        self.btn_stop_dl.grid_remove()

        # --- OUTPUT SETTINGS ---
        ctk.CTkLabel(self.sidebar, text="OUTPUT SETTINGS", font=ctk.CTkFont(size=12, weight="bold")).grid(row=11, column=0, pady=(10, 5))

        self.btn_out_dir = ctk.CTkButton(self.sidebar, text="Set Output Folder", fg_color="gray", command=self.select_output_dir)
        self.btn_out_dir.grid(row=12, column=0, padx=20, pady=5)

        self.entry_project_name = ctk.CTkEntry(self.sidebar, placeholder_text="Project Name")
        self.entry_project_name.grid(row=13, column=0, padx=20, pady=5)

        self.console = ctk.CTkTextbox(self.sidebar, width=220)
        self.console.grid(row=14, column=0, padx=10, pady=20, sticky="nsew")
        self.sidebar.grid_rowconfigure(14, weight=1)

        self._check_library_status()

    def _init_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_photo = self.tabview.add("Smart Photo Mosaic")
        self.tab_typo = self.tabview.add("Symbol Mosaic (Typo)")

        self._setup_photo_tab()
        self._setup_typo_tab()

    def _make_quickstart_frame(self, parent, steps: list):
        box = ctk.CTkFrame(parent, fg_color=("#d4d4e8", "#23233a"), corner_radius=8)
        box.pack(fill="x", padx=10, pady=(0, 14))
        ctk.CTkLabel(
            box,
            text="Quick Start",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#555555", "#9999bb"),
        ).pack(anchor="w", padx=12, pady=(8, 3))
        for i, step in enumerate(steps, 1):
            ctk.CTkLabel(
                box,
                text=f"  {i}.  {step}",
                font=ctk.CTkFont(size=11),
                text_color=("#333333", "#cccccc"),
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=12, pady=1)
        ctk.CTkLabel(box, text="").pack(pady=3)

    def _setup_photo_tab(self):
        outer = self.tab_photo
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=0)

        frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        ctk.CTkLabel(frame, text="REGIONAL COLOR MOSAIC", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self._make_quickstart_frame(frame, [
            "Download tiles  —  sidebar → Download Starter  (or Import Your Photos)",
            "Build index  —  sidebar → Update / Create Index",
            "Load index  —  sidebar → Load Smart Index",
            "Select input image  (button below)",
            "Set output folder & project name  (sidebar)",
            "Configure settings and click  RENDER",
        ])

        self.btn_input_p = ctk.CTkButton(frame, text="Select Input Image", command=self.select_input_p)
        self.btn_input_p.pack(pady=10)

        self.combo_res_p = ctk.CTkComboBox(frame, values=["2K", "4K", "8K", "16K"])
        self.combo_res_p.set("4K")
        self.combo_res_p.pack(pady=5)

        # BUTTON PHOTO SCALE
        ctk.CTkLabel(frame, text="Tile Size Multiplier", font=("Arial", 12, "bold")).pack(pady=(15,0))
        self.seg_scale_p = ctk.CTkSegmentedButton(frame, values=["0.5", "0.75", "1.0", "1.75", "2.0"])
        self.seg_scale_p.set("1.0")
        self.seg_scale_p.pack(pady=5)

        ctk.CTkLabel(frame, text="Tile Shape").pack(pady=(10,0))
        shapes = ["square", "rectangle_3x1", "brick_wall", "hexagon", "hexagon_romb", "romb", "triangle", "kite"]
        self.combo_shape = ctk.CTkComboBox(frame, values=shapes)
        self.combo_shape.set("hexagon_romb")
        self.combo_shape.pack(pady=5)

        # Checkboxes
        self.check_mirror = ctk.CTkCheckBox(
            frame, text="Allow Mirroring  (small library)",
            command=self._on_mirror_toggled)
        self.check_mirror.select()
        self.check_mirror.pack(pady=(15, 5))

        self.check_border = ctk.CTkCheckBox(frame, text="Black Borders (Grout)")
        self.check_border.deselect()
        self.check_border.pack(pady=5)

        self.check_edge_aware = ctk.CTkCheckBox(
            frame, text="Edge-Aware Matching  (large library)",
            command=self._on_edge_aware_toggled,
            state="disabled")
        self.check_edge_aware.deselect()
        self.check_edge_aware.pack(pady=5)

        # --- POST-PROCESSING ---
        ctk.CTkLabel(frame, text="POST-PROCESSING",
                     font=("Arial", 12, "bold")).pack(pady=(20, 5))

        ctk.CTkLabel(frame, text="Color Blend").pack(pady=(10, 0))
        self.seg_blend = ctk.CTkSegmentedButton(frame, values=["0%", "10%", "20%", "30%"])
        self.seg_blend.set("0%")
        self.seg_blend.pack(pady=5)

        ctk.CTkLabel(frame, text="Tile Tint").pack(pady=(10, 0))
        self.seg_tint = ctk.CTkSegmentedButton(frame, values=["0%", "10%", "20%", "30%", "40%"])
        self.seg_tint.set("0%")
        self.seg_tint.pack(pady=5)

        # RENDER button pinned outside the scroll area — always visible
        self.btn_run_p = ctk.CTkButton(
            outer,
            text="RENDER SMART MOSAIC",
            fg_color="green",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_photo,
        )
        self.btn_run_p.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 15))

    def _setup_typo_tab(self):
        outer = self.tab_typo
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=0)

        frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        ctk.CTkLabel(frame, text="SYMBOL MOSAIC (GLOBAL FONTS)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self._make_quickstart_frame(frame, [
            "Select input image  (button below)",
            "Set output folder & project name  (sidebar)",
            "Configure font/symbol settings and click  RENDER",
        ])

        self.btn_load_typo = ctk.CTkButton(frame, text="Load Typo Index (Fast)", command=self.load_typo_index)
        self.btn_load_typo.pack(pady=5)

        self.lbl_typo_status = ctk.CTkLabel(frame, text="Status: Not Loaded", text_color="red")
        self.lbl_typo_status.pack(pady=(0, 10))

        self.btn_scan_fonts = ctk.CTkButton(frame, text="Update Database (Scan Assets)", fg_color="gray", width=200, command=self.scan_fonts)
        self.btn_scan_fonts.pack(pady=5)

        ctk.CTkLabel(frame, text="--------------------------------").pack(pady=10)

        self.btn_input_t = ctk.CTkButton(frame, text="Select Input Image", command=self.select_input_t)
        self.btn_input_t.pack(pady=10)

        ctk.CTkLabel(frame, text="Output Resolution").pack()
        self.combo_res_t = ctk.CTkComboBox(frame, values=["4K", "8K", "16K"])
        self.combo_res_t.set("8K")
        self.combo_res_t.pack(pady=5)

        # BUTTON TYPO SCALE
        ctk.CTkLabel(frame, text="Symbol Size Multiplier", font=("Arial", 12, "bold")).pack(pady=(15,0))
        self.seg_scale_t = ctk.CTkSegmentedButton(frame, values=["0.5", "0.75", "1.0", "1.75", "2.0"])
        self.seg_scale_t.set("1.0")
        self.seg_scale_t.pack(pady=5)

        # --- FONT GROUPS ---
        ctk.CTkLabel(frame, text="Font Groups (select one or more)",
                     font=("Arial", 12, "bold")).pack(pady=(15, 5))

        self.font_group_vars = {}
        groups_frame = ctk.CTkFrame(frame, fg_color="transparent")
        groups_frame.pack(pady=5, padx=20, fill="x")

        # Default: D_latin_clean selected (safest choice for first-time users)
        default_selected = {"D_latin_clean"}
        for group_key, label in GROUP_LABELS.items():
            var = ctk.BooleanVar(value=(group_key in default_selected))
            cb = ctk.CTkCheckBox(groups_frame, text=label, variable=var)
            cb.pack(anchor="w", pady=2)
            self.font_group_vars[group_key] = var

        ctk.CTkLabel(frame, text="Style Mode").pack(pady=(10, 0))
        self.combo_mode = ctk.CTkComboBox(
            frame,
            values=["black_on_white", "white_on_black", "color_on_white", "color_on_black"]
        )
        self.combo_mode.set("black_on_white")
        self.combo_mode.pack(pady=5)

        ctk.CTkLabel(frame, text="Color Palette Size (color modes only)").pack(pady=(10, 0))
        self.seg_palette = ctk.CTkSegmentedButton(frame, values=["8", "16", "32", "Full"])
        self.seg_palette.set("16")
        self.seg_palette.pack(pady=5)

        ctk.CTkLabel(frame, text="Variation (lower = sharper, higher = organic)").pack(pady=(10, 0))
        self.seg_variation = ctk.CTkSegmentedButton(frame, values=["5", "20", "50"])
        self.seg_variation.set("20")
        self.seg_variation.pack(pady=5)

        # RENDER button pinned outside the scroll area — always visible
        self.btn_run_t = ctk.CTkButton(
            outer,
            text="RENDER SYMBOL MOSAIC",
            fg_color="purple",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_typo,
        )
        self.btn_run_t.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 15))

    # --- TILE LIBRARY ---

    def _check_library_status(self):
        all_dirs = list(LIBRARY_DIRS) + [DEFAULT_OUTPUT_DIR]
        total = sum(
            len(list(d.glob("*.jpg"))) + len(list(d.glob("*.png")))
            for d in all_dirs if d.exists()
        )
        if total == 0:
            text, color = "EMPTY", "red"
        elif total < STARTER_TARGET:
            text, color = f"{total} images", "orange"
        elif total < 5000:
            text, color = f"{total} images", "yellow"
        else:
            text, color = f"{total} images", "green"
        self.lbl_library_status.configure(text=text, text_color=color)

        # Starter button turns green once the 500-image target is reached
        starter_color = "darkgreen" if total >= STARTER_TARGET else "#5a3e8a"
        self.btn_dl_starter.configure(fg_color=starter_color)

    def _run_download(self, plan: str):
        def _work():
            self.after(0, self.progress_dl.grid)
            self.after(0, lambda: self.progress_dl.configure(mode="indeterminate"))
            self.after(0, self.progress_dl.start)
            self.after(0, self.btn_stop_dl.grid)
            try:
                dl = PoliteDownloader()
                dl.on_progress = self.log
                self._active_dl = dl
                saved = dl.download(plan)
                self.log(f"Download complete: {saved} images saved.")
            except Exception as exc:
                self.log(f"Download error: {exc}")
            finally:
                self._active_dl = None
                self.after(0, self.progress_dl.stop)
                self.after(0, self.progress_dl.grid_remove)
                self.after(0, self.btn_stop_dl.grid_remove)
                self.after(0, self._check_library_status)
        threading.Thread(target=_work, daemon=True).start()

    def _stop_download(self):
        if self._active_dl is not None:
            self._active_dl.stop()
            self.log("Stop requested — finishing current image and saving state...")

    def download_starter(self):
        self._run_download("starter")

    def download_public(self):
        if not os.environ.get("OPENVERSE_CLIENT_ID"):
            self.log("⚠ OPENVERSE_CLIENT_ID not set!")
            self.log("Gallery requires an Openverse API key.")
            self.log("Register: see .env.example for instructions.")
            self.log("Starter (500 images) works without a key.")
            return
        self._run_download("public")

    def download_extended(self):
        if not os.environ.get("OPENVERSE_CLIENT_ID"):
            self.log("⚠ OPENVERSE_CLIENT_ID not set!")
            self.log("Extended requires an Openverse API key.")
            self.log("Register: see .env.example for instructions.")
            self.log("Starter (500 images) works without a key.")
            return
        self._run_download("extended")

    def import_photos(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp"), ("All", "*.*")]
        )
        if not paths:
            return
        dest = DEFAULT_OUTPUT_DIR
        dest.mkdir(parents=True, exist_ok=True)
        copied = 0
        for p in paths:
            src = Path(p)
            target = dest / src.name
            if not target.exists():
                shutil.copy2(src, target)
                copied += 1
        self.log(f"Imported {copied} photos to {dest}")
        self._check_library_status()

    def log(self, msg):
        print(msg)
        def _update():
            self.console.insert("end", msg + "\n")
            self.console.see("end")
        self.after(0, _update)

    # --- ENGINE AND INDEX MANAGEMENT ---

    def run_smart_indexer(self):
        """Rebuild the Smart Index in a background thread."""
        def _run():
            self.log("Starting Smart Indexer... (Wait)")
            try:
                idx = SmartIndexer()
                idx.run()
                self.log("Indexing Complete! Reloading Engine...")
                self.smart_engine = SmartEngine()
                self.log("Engine Reloaded with new data.")
            except Exception as e:
                self.log(f"Indexer Error: {e}")
        threading.Thread(target=_run).start()

    def load_index(self):
        def _load():
            self.log("Loading Smart Index from disk...")
            try:
                self.smart_engine = SmartEngine()
                self.log("Smart Engine Ready!")
            except Exception as e: self.log(f"Error: {e}")
        threading.Thread(target=_load).start()

    def load_typo_index(self):
        def _load():
            self.log("Loading Font Index from disk...")
            try:
                self.typo_engine = TypoEngine()
                if self.typo_engine.library:
                    count = len(self.typo_engine.library)
                    self.log(f"SUCCESS: Loaded {count} symbols.")
                    self.lbl_typo_status.configure(text=f"Status: Ready ({count} sym)", text_color="green")
                else:
                    self.log("ERROR: Index empty.")
                    self.lbl_typo_status.configure(text="Status: Missing", text_color="red")
            except Exception as e:
                self.log(f"Error loading typo index: {e}")
                self.lbl_typo_status.configure(text="Status: Error", text_color="red")
        threading.Thread(target=_load).start()

    def scan_fonts(self):
        def _scan():
            self.log("Starting Font Scan...")
            subprocess.run([sys.executable, "-m", "src.indexer_typo"], check=False)
            self.log("Scan Complete! Click 'Load Typo Index'.")
        threading.Thread(target=_scan).start()

    def select_output_dir(self):
        self.output_dir = filedialog.askdirectory()
        if self.output_dir: self.log(f"Output: {self.output_dir}")

    def _on_mirror_toggled(self):
        if self.check_mirror.get():
            self.check_edge_aware.deselect()
            self.check_edge_aware.configure(state="disabled")
        else:
            self.check_edge_aware.configure(state="normal")

    def _on_edge_aware_toggled(self):
        if self.check_edge_aware.get():
            self.check_mirror.deselect()
            self.check_mirror.configure(state="disabled")
        else:
            self.check_mirror.configure(state="normal")

    def select_input_p(self): self.path_p = filedialog.askopenfilename()
    def select_input_t(self): self.path_t = filedialog.askopenfilename()

    def _get_auto_filename(self, prefix, ext):
        if not self.output_dir:
            self.log("ERROR: Set Output Folder first!")
            return None
        proj = self.entry_project_name.get().strip() or "Mosaic"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"{proj}_{prefix}_{ts}{ext}")

    def run_photo(self):
        if not self.smart_engine or not hasattr(self, 'path_p'):
            self.log("Error: Load Smart Index and Select Image first!")
            return
        out = self._get_auto_filename("Smart", ".jpg")
        if not out: return

        self.smart_engine.settings["allow_mirror"] = bool(self.check_mirror.get())
        self.smart_engine.settings["edge_aware"] = bool(self.check_edge_aware.get())
        res = self.combo_res_p.get()
        shape = self.combo_shape.get()
        scale = self.seg_scale_p.get()
        border_mode = bool(self.check_border.get())

        if not scale:
            scale = "1.0"
        scale = float(scale)

        blend_val = self.seg_blend.get()
        blend_strength = int(blend_val.replace("%", "")) / 100.0
        tint_val = self.seg_tint.get()
        tint_strength = int(tint_val.replace("%", "")) / 100.0

        if res in ("8K", "16K"):
            self.log(f"NOTE: {res} rendering requires ~2-4 GB free RAM. "
                     f"Close other applications for best performance.")

        def _run():
            try:
                self.smart_engine.create_mosaic(
                    self.path_p, out, res, shape,
                    tile_scale=scale, border_mode=border_mode,
                    blend_strength=blend_strength, tint_strength=tint_strength,
                )
                self.log("DONE! Smart Mosaic saved.")
            except Exception as e:
                self.log(f"Error: {e}")
                import traceback
                traceback.print_exc()
        threading.Thread(target=_run).start()

    def run_typo(self):
        if not hasattr(self, 'path_t'):
            self.log("Error: Select Input Image first")
            return
        out = self._get_auto_filename("Symbol", ".png")
        if not out: return

        res = self.combo_res_t.get()
        mode = self.combo_mode.get()
        scale = self.seg_scale_t.get()
        if not scale: scale = "1.0"
        scale = float(scale)

        selected_groups = [k for k, v in self.font_group_vars.items() if v.get()]
        if not selected_groups:
            self.log("ERROR: Select at least one Font Group!")
            return

        palette_raw = self.seg_palette.get()
        palette_size = None if palette_raw == "Full" else int(palette_raw)

        variation = int(self.seg_variation.get())

        def _run():
            self.log(f"Starting Multi-Font Render...")
            self.log(f"Groups: {', '.join(selected_groups)}")
            try:
                from .engine_typo import TypoEngine
                active_engine = TypoEngine(selected_groups=selected_groups)
                if not active_engine.library:
                    self.log("ERROR: No glyphs after filter. Select more groups.")
                    return

                active_engine.process(
                    self.path_t, out, res, mode,
                    scale=scale,
                    variation=variation,
                    palette_size=palette_size,
                )
                self.log("DONE! Symbol Mosaic saved.")
            except Exception as e:
                self.log(f"Error: {e}")
                import traceback
                traceback.print_exc()
        threading.Thread(target=_run).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
