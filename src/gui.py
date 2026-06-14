"""
src/gui.py
----------
Main application window for NeuroMosaic built with CustomTkinter.

Provides three tabs:
  * Smart Photo Mosaic — colour-matched photomosaic using SmartEngine.
  * Symbol Mosaic (Typo) — typography-based mosaic using TypoEngine.
  * Tile Library — visual browser for data/library_* tile collections.
"""
import os
import pickle
import subprocess
import sys
import shutil
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import customtkinter as ctk
from tkinter import filedialog
import threading
from datetime import datetime
from pathlib import Path
from PIL import Image
from sklearn.decomposition import PCA
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from .engine_smart import SmartEngine
from .engine_typo import TypoEngine
from .preview import PreviewRenderer
from .indexer_smart import SmartIndexer, LIBRARY_DIRS
from .font_groups import GROUP_LABELS
from .downloader_v2 import PoliteDownloader, DEFAULT_OUTPUT_DIR

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FONTS_DIR = Path("assets/fonts")
STARTER_TARGET = 500

_THUMB_DIR = Path("data/.thumbs")
_THUMB_CACHE_PX = 200    # resolution stored on disk
_THUMB_DISPLAY_PX = 120  # size rendered in grid
_GRID_COLS = 5
_SMART_INDEX = Path("data/smart_index.pkl")

# Lightness thresholds (normalised 0–1, derived from PIL grayscale mean)
_L_RANGES = {
    "Dark":   (0.00, 0.35),
    "Mid":    (0.35, 0.65),
    "Bright": (0.65, 1.00),
}
# Texture threshold: std-dev of grayscale channel (normalised)
_TEX_THRESHOLD = 0.10

# Tile Library pagination — hard caps so huge libraries (hundreds of
# thousands of tiles) can never flood the Tk widget tree or RAM.
_LIB_PAGE_SIZE = 200   # tiles added to the grid per Refresh / Load More
_LIB_SCAN_CAP = 2000   # max files examined per click (thumbnail cost)


class _TextboxStream:
    """Mirror a stdout/stderr stream into a CTkTextbox.

    Everything written to the wrapped stream (plain ``print`` from the
    engines, indexers, AND ``tqdm`` progress bars) is forwarded both to the
    original terminal stream and to the GUI console, so the sidebar shows
    exactly what PowerShell shows.  Carriage returns (used by tqdm to redraw
    a bar in place) overwrite the current console line instead of spamming
    new ones.  Writes are marshalled onto the Tk main loop via ``after``.
    """

    def __init__(self, textbox: "ctk.CTkTextbox", after_fn, original):
        self._textbox = textbox
        self._after = after_fn
        self._original = original

    def write(self, s):
        if self._original is not None:
            try:
                self._original.write(s)
                self._original.flush()
            except Exception:
                pass
        if s:
            self._after(0, lambda text=s: self._append(text))
        return len(s)

    def _append(self, s):
        try:
            tb = self._textbox
            s = s.replace("\r\n", "\n")
            if "\r" in s:
                # tqdm redraw — keep only the text after the last CR and
                # overwrite the current (last) console line.
                tail = s.split("\r")[-1]
                tb.delete("end-1c linestart", "end-1c")
                tb.insert("end", tail)
            else:
                tb.insert("end", s)
            tb.see("end")
        except Exception:
            pass

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self):
        # Delegate so tqdm keeps its rich, in-place progress format when the
        # app was launched from a real terminal.
        return bool(self._original is not None and self._original.isatty())


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Slightly enlarge every widget/font for readability.
        ctk.set_widget_scaling(1.1)

        self.title("Neural-Mosaic 5.7 (Solid Geometry)")
        self.geometry("1250x900")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Shared fonts (created after the root window exists).
        self.FONT_CONSOLE = ctk.CTkFont(size=12)
        self.FONT_SMALL = ctk.CTkFont(size=12)

        self.output_dir = None
        self._active_dl: PoliteDownloader | None = None
        self._lib_images: list = []   # keeps CTkImage refs alive
        self._lib_loading = False
        self._lib_selected: set[Path] = set()
        self._lib_cell_frames: dict[Path, ctk.CTkFrame] = {}
        self._lib_paths: list[Path] = []  # filtered+sorted scan list (paginated)
        self._lib_scan_pos = 0            # resume index into _lib_paths
        self._lib_shown = 0               # tiles currently in the grid
        self._preview_smart = PreviewRenderer()
        self._preview_typo = PreviewRenderer()
        self._preview_img_ref_p = None
        self._preview_img_ref_t = None
        self._preview_pil_p = None        # last full-res preview (for refit on resize)
        self._preview_pil_t = None
        self._preview_last_fit_p = None
        self._preview_last_fit_t = None

        self._init_sidebar()
        self._init_tabs()

        # Mirror all stdout/stderr (engine prints + tqdm bars) into the
        # sidebar console so the GUI shows exactly what the terminal shows.
        self._stdout_orig = sys.stdout
        self._stderr_orig = sys.stderr
        sys.stdout = _TextboxStream(self.console, self.after, self._stdout_orig)
        sys.stderr = _TextboxStream(self.console, self.after, self._stderr_orig)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.smart_engine = None
        self.typo_engine = TypoEngine()

    def _on_close(self):
        sys.stdout = self._stdout_orig
        sys.stderr = self._stderr_orig
        self.destroy()

    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo = ctk.CTkLabel(self.sidebar, text="NEURAL\nMOSAIC", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))

        # --- INDEXING SECTION ---
        self.btn_load_smart = ctk.CTkButton(self.sidebar, text="Load Smart Index", fg_color="#1a6b1a", hover_color="#22891a", command=self.load_index)
        self.btn_load_smart.grid(row=1, column=0, padx=20, pady=(10, 5))

        self.btn_update_smart = ctk.CTkButton(self.sidebar, text="Update / Create Index", fg_color="#1f538d", command=self.run_smart_indexer)
        self.btn_update_smart.grid(row=2, column=0, padx=20, pady=(5, 10))

        # --- TILE LIBRARY SECTION ---
        ctk.CTkLabel(self.sidebar, text="TILE LIBRARY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaaaaa").grid(row=3, column=0, pady=(10, 2))

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
        ctk.CTkLabel(self.sidebar, text="OUTPUT SETTINGS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#aaaaaa").grid(row=11, column=0, pady=(10, 5))

        self.btn_out_dir = ctk.CTkButton(self.sidebar, text="Set Output Folder", fg_color="gray", command=self.select_output_dir)
        self.btn_out_dir.grid(row=12, column=0, padx=20, pady=5)

        self.entry_project_name = ctk.CTkEntry(self.sidebar, placeholder_text="Project Name")
        self.entry_project_name.grid(row=13, column=0, padx=20, pady=5)

        self.console = ctk.CTkTextbox(self.sidebar, width=220, font=self.FONT_CONSOLE)
        self.console.grid(row=14, column=0, padx=10, pady=20, sticky="nsew")
        self.sidebar.grid_rowconfigure(14, weight=1)

        self._check_library_status()

    def _init_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_photo = self.tabview.add("Smart Photo Mosaic")
        self.tab_typo = self.tabview.add("Symbol Mosaic (Typo)")
        self.tab_library = self.tabview.add("Tile Library")

        self._setup_photo_tab()
        self._setup_typo_tab()
        self._setup_library_tab()

    def _make_quickstart_frame(self, parent, steps: list):
        outer = ctk.CTkFrame(parent, fg_color=("#d4d4e8", "#23233a"), corner_radius=8)
        outer.pack(fill="x", padx=10, pady=(0, 14))

        ctk.CTkFrame(outer, width=3, fg_color="#4a3a7a", corner_radius=0).pack(
            side="left", fill="y"
        )

        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(8, 12), pady=10)

        ctk.CTkLabel(
            content,
            text="Quick Start",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#4a3a7a", "#c0b8e8"),
        ).pack(anchor="w", pady=(0, 8))

        for i, step in enumerate(steps, 1):
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(anchor="w", fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=str(i),
                width=22, height=22,
                corner_radius=11,
                fg_color="#3a2e6a",
                text_color="#9999bb",
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(side="left", padx=(0, 10))

            ctk.CTkLabel(
                row,
                text=step,
                font=ctk.CTkFont(size=13),
                text_color=("#333333", "#b8b0d8"),
                justify="left",
                anchor="w",
                wraplength=400,
            ).pack(side="left", anchor="w")

    def _make_info_banner(self, parent, title, subtitle, steps, warn=None):
        """Return (not place) an explainer banner frame; caller grids/packs it."""
        outer = ctk.CTkFrame(parent, fg_color=("#d4d4e8", "#23233a"), corner_radius=8)

        ctk.CTkFrame(outer, width=3, fg_color="#4a3a7a", corner_radius=0).pack(
            side="left", fill="y"
        )

        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(8, 12), pady=10)

        ctk.CTkLabel(
            content, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#4a3a7a", "#c0b8e8"),
        ).pack(anchor="w", pady=(0, 2))

        ctk.CTkLabel(
            content, text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=("#444444", "#a8a0c8"),
            justify="left", anchor="w", wraplength=820,
        ).pack(anchor="w", pady=(0, 8))

        for i, step in enumerate(steps, 1):
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(anchor="w", fill="x", pady=2)
            ctk.CTkLabel(
                row, text=str(i),
                width=22, height=22, corner_radius=11,
                fg_color="#3a2e6a", text_color="#9999bb",
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                row, text=step,
                font=ctk.CTkFont(size=12),
                text_color=("#333333", "#b8b0d8"),
                justify="left", anchor="w", wraplength=780,
            ).pack(side="left", anchor="w")

        if warn:
            ctk.CTkLabel(
                content, text="⚠  " + warn,
                font=ctk.CTkFont(size=12),
                text_color=("#8a5a00", "#e0b060"),
                justify="left", anchor="w", wraplength=820,
            ).pack(anchor="w", pady=(8, 0))

        return outer

    def _setup_photo_tab(self):
        outer = self.tab_photo
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=0)

        # LEFT — settings
        frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=(10, 0))

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

        ctk.CTkLabel(frame, text="Output Resolution").pack(pady=(10, 0))
        self.seg_res_p = ctk.CTkSegmentedButton(frame, values=["2K", "4K", "8K", "16K"])
        self.seg_res_p.set("4K")
        self.seg_res_p.pack(pady=5)

        ctk.CTkLabel(frame, text="Tile Size Multiplier", font=("Arial", 12, "bold")).pack(pady=(15, 0))
        self.seg_scale_p = ctk.CTkSegmentedButton(
            frame, values=["0.5", "0.75", "1.0", "1.75", "2.0"],
        )
        self.seg_scale_p.set("1.0")
        self.seg_scale_p.pack(pady=5)

        ctk.CTkLabel(frame, text="Tile Shape").pack(pady=(10, 0))
        shapes = ["square", "rectangle_3x1", "brick_wall", "hexagon", "hexagon_romb", "romb", "triangle", "kite", "spectre"]
        self.combo_shape = ctk.CTkComboBox(
            frame, values=shapes,
        )
        self.combo_shape.set("hexagon_romb")
        self.combo_shape.pack(pady=5)

        self.check_mirror = ctk.CTkCheckBox(
            frame, text="Allow Mirroring  (small library)",
            command=self._on_mirror_toggled)
        self.check_mirror.select()
        self.check_mirror.pack(pady=(15, 5))

        self.check_border = ctk.CTkCheckBox(
            frame, text="Black Borders (Grout)",
        )
        self.check_border.deselect()
        self.check_border.pack(pady=5)

        self.check_edge_aware = ctk.CTkCheckBox(
            frame, text="Edge-Aware Matching  (large library)",
            command=self._on_edge_aware_toggled,
            state="disabled")
        self.check_edge_aware.deselect()
        self.check_edge_aware.pack(pady=5)

        ctk.CTkLabel(frame, text="POST-PROCESSING",
                     font=("Arial", 12, "bold")).pack(pady=(20, 5))

        ctk.CTkLabel(frame, text="Color Blend").pack(pady=(10, 0))
        self.seg_blend = ctk.CTkSegmentedButton(
            frame, values=["0%", "10%", "20%", "30%"],
        )
        self.seg_blend.set("0%")
        self.seg_blend.pack(pady=5)

        ctk.CTkLabel(frame, text="Tile Tint").pack(pady=(10, 0))
        self.seg_tint = ctk.CTkSegmentedButton(
            frame, values=["0%", "10%", "20%", "30%", "40%"],
        )
        self.seg_tint.set("0%")
        self.seg_tint.pack(pady=5)

        # RIGHT — preview pane
        prev_frame = ctk.CTkFrame(outer, fg_color=("#e0e0e0", "#1a1a2a"), corner_radius=8)
        prev_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 10), pady=(10, 0))
        prev_frame.grid_columnconfigure(0, weight=1)
        prev_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            prev_frame, text="PREVIEW",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888888",
        ).grid(row=0, column=0, pady=(10, 0))

        ctrl_p = ctk.CTkFrame(prev_frame, fg_color="transparent")
        ctrl_p.grid(row=1, column=0, pady=(4, 0))

        self.seg_zoom_p = ctk.CTkSegmentedButton(
            ctrl_p,
            values=["¼", "½", "Full"],
            font=ctk.CTkFont(size=11),
            width=160,
        )
        self.seg_zoom_p.set("½")
        self.seg_zoom_p.pack(side="left", padx=(0, 8))

        self.btn_preview_p = ctk.CTkButton(
            ctrl_p, text="Generate Preview", width=130,
            command=self._trigger_smart_preview,
        )
        self.btn_preview_p.pack(side="left")

        self.lbl_preview_p = ctk.CTkLabel(
            prev_frame,
            text="Select image and load index\nto enable preview",
            text_color="#555555",
            font=ctk.CTkFont(size=14),
        )
        self.lbl_preview_p.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self.lbl_preview_p.bind("<Configure>", self._on_preview_resize_p)

        self.lbl_preview_status_p = ctk.CTkLabel(
            prev_frame, text="", text_color="#777777",
            font=self.FONT_SMALL,
        )
        self.lbl_preview_status_p.grid(row=3, column=0, pady=(0, 8))

        self.progress_render_p = ctk.CTkProgressBar(prev_frame, width=260)
        self.progress_render_p.set(0)
        self.progress_render_p.grid(row=4, column=0, pady=(0, 10))
        self.progress_render_p.grid_remove()

        self.btn_run_p = ctk.CTkButton(
            outer,
            text="RENDER SMART MOSAIC",
            fg_color="#1a7a1a",
            hover_color="#22991a",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_photo,
        )
        self.btn_run_p.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 15))

    def _setup_typo_tab(self):
        outer = self.tab_typo
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=1)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_rowconfigure(1, weight=0)

        # LEFT — settings
        frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=(10, 0))

        ctk.CTkLabel(frame, text="SYMBOL MOSAIC (GLOBAL FONTS)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self._make_quickstart_frame(frame, [
            "Select input image  (button below)",
            "Set output folder & project name  (sidebar)",
            "Configure font/symbol settings and click  RENDER",
        ])

        self.btn_load_typo = ctk.CTkButton(frame, text="Load Typo Index (Fast)", fg_color="#1f538d", hover_color="#2a6ab0", command=self.load_typo_index)
        self.btn_load_typo.pack(pady=5)

        self.lbl_typo_status = ctk.CTkLabel(frame, text="Status: Not Loaded", text_color="red")
        self.lbl_typo_status.pack(pady=(0, 10))

        self.btn_scan_fonts = ctk.CTkButton(frame, text="Update Database (Scan Assets)", fg_color="gray", width=200, command=self.scan_fonts)
        self.btn_scan_fonts.pack(pady=5)

        ctk.CTkLabel(frame, text="--------------------------------").pack(pady=10)

        self.btn_input_t = ctk.CTkButton(frame, text="Select Input Image", command=self.select_input_t)
        self.btn_input_t.pack(pady=10)

        ctk.CTkLabel(frame, text="Output Resolution").pack(pady=(10, 0))
        self.seg_res_t = ctk.CTkSegmentedButton(frame, values=["4K", "8K", "16K"])
        self.seg_res_t.set("8K")
        self.seg_res_t.pack(pady=5)

        ctk.CTkLabel(frame, text="Symbol Size Multiplier", font=("Arial", 12, "bold")).pack(pady=(15, 0))
        self.seg_scale_t = ctk.CTkSegmentedButton(
            frame, values=["0.5", "0.75", "1.0", "1.75", "2.0"],
        )
        self.seg_scale_t.set("1.0")
        self.seg_scale_t.pack(pady=5)

        ctk.CTkLabel(frame, text="Font Groups (select one or more)",
                     font=("Arial", 12, "bold")).pack(pady=(15, 5))

        self.font_group_vars = {}
        groups_frame = ctk.CTkFrame(frame, fg_color="transparent")
        groups_frame.pack(pady=5, padx=20, fill="x")

        default_selected = {"D_latin_clean"}
        for group_key, label in GROUP_LABELS.items():
            var = ctk.BooleanVar(value=(group_key in default_selected))
            cb = ctk.CTkCheckBox(
                groups_frame, text=label, variable=var,
            )
            cb.pack(anchor="w", pady=2)
            self.font_group_vars[group_key] = var

        ctk.CTkLabel(frame, text="Style Mode").pack(pady=(10, 0))
        self.combo_mode = ctk.CTkComboBox(
            frame,
            values=["black_on_white", "white_on_black"],
        )
        self.combo_mode.set("black_on_white")
        self.combo_mode.pack(pady=5)

        ctk.CTkLabel(frame, text="Variation (lower = sharper, higher = organic)").pack(pady=(10, 0))
        self.seg_variation = ctk.CTkSegmentedButton(
            frame, values=["5", "20", "50"],
        )
        self.seg_variation.set("20")
        self.seg_variation.pack(pady=5)

        # RIGHT — preview pane
        prev_frame = ctk.CTkFrame(outer, fg_color=("#e0e0e0", "#1a1a2a"), corner_radius=8)
        prev_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 10), pady=(10, 0))
        prev_frame.grid_columnconfigure(0, weight=1)
        prev_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            prev_frame, text="PREVIEW",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#888888",
        ).grid(row=0, column=0, pady=(10, 0))

        ctrl_t = ctk.CTkFrame(prev_frame, fg_color="transparent")
        ctrl_t.grid(row=1, column=0, pady=(4, 0))

        self.seg_zoom_t = ctk.CTkSegmentedButton(
            ctrl_t,
            values=["¼", "½", "Full"],
            font=ctk.CTkFont(size=11),
            width=160,
        )
        self.seg_zoom_t.set("½")
        self.seg_zoom_t.pack(side="left", padx=(0, 8))

        self.btn_preview_t = ctk.CTkButton(
            ctrl_t, text="Generate Preview", width=130,
            command=self._trigger_typo_preview,
        )
        self.btn_preview_t.pack(side="left")

        self.lbl_preview_t = ctk.CTkLabel(
            prev_frame,
            text="Select image and load typo index\nto enable preview",
            text_color="#555555",
            font=ctk.CTkFont(size=14),
        )
        self.lbl_preview_t.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self.lbl_preview_t.bind("<Configure>", self._on_preview_resize_t)

        self.lbl_preview_status_t = ctk.CTkLabel(
            prev_frame, text="", text_color="#777777",
            font=self.FONT_SMALL,
        )
        self.lbl_preview_status_t.grid(row=3, column=0, pady=(0, 8))

        self.progress_render_t = ctk.CTkProgressBar(prev_frame, width=260)
        self.progress_render_t.set(0)
        self.progress_render_t.grid(row=4, column=0, pady=(0, 10))
        self.progress_render_t.grid_remove()

        self.btn_run_t = ctk.CTkButton(
            outer,
            text="RENDER SYMBOL MOSAIC",
            fg_color="#6b2f9e",
            hover_color="#7d35b8",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.run_typo,
        )
        self.btn_run_t.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 15))

    # --- PREVIEW ---

    _ZOOM_SHORT_EDGE = {"¼": 450, "½": 900, "Full": 1800}

    def _trigger_smart_preview(self):
        if self.smart_engine is None or not getattr(self, "path_p", None):
            self.lbl_preview_status_p.configure(
                text="Load index and select an image first")
            return
        # allow_mirror / edge_aware affect matching but render_preview reads them
        # from engine.settings (not kwargs). Sync from the checkboxes here, on the
        # main thread before the debounced render fires, so the preview reflects
        # the current settings instead of the last full render's state.
        self.smart_engine.settings["allow_mirror"] = bool(self.check_mirror.get())
        self.smart_engine.settings["edge_aware"] = bool(self.check_edge_aware.get())
        params = {
            "shape_mode": self.combo_shape.get(),
            "tile_scale": float(self.seg_scale_p.get() or "1.0"),
            "border_mode": bool(self.check_border.get()),
        }
        short_edge = self._ZOOM_SHORT_EDGE.get(self.seg_zoom_p.get(), 900)
        self.btn_preview_p.configure(state="disabled")
        self.lbl_preview_status_p.configure(text="Rendering preview...")
        self._preview_smart.request(
            self.smart_engine,
            self.path_p,
            short_edge=short_edge,
            params=params,
            on_done=lambda img: self.after(0, lambda i=img: self._show_smart_preview(i)),
            on_error=lambda msg: self.after(
                0, lambda m=msg: self._on_smart_preview_error(m)),
        )

    def _on_smart_preview_error(self, msg):
        self.btn_preview_p.configure(state="normal")
        self.lbl_preview_status_p.configure(text=f"Preview error: {msg}")

    def _fit_preview(self, label, pil_img, which, avail):
        """Scale pil_img to fill the available label area and show it.

        Allows upscaling so small zoom levels still fill the (large) preview
        pane — the old hard 440x560 cap left the image tiny in a big frame.
        """
        avail_w = max(avail[0] - 16, 80)
        avail_h = max(avail[1] - 16, 80)
        img_w, img_h = pil_img.size
        scale = min(avail_w / img_w, avail_h / img_h)
        disp_w = max(1, int(img_w * scale))
        disp_h = max(1, int(img_h * scale))
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(disp_w, disp_h))
        if which == "p":
            self._preview_img_ref_p = ctk_img
        else:
            self._preview_img_ref_t = ctk_img
        label.configure(image=ctk_img, text="")

    def _avail_for(self, label):
        w, h = label.winfo_width(), label.winfo_height()
        if w <= 1 or h <= 1:
            w, h = 560, 620
        return w, h

    def _show_smart_preview(self, pil_img):
        self._preview_pil_p = pil_img
        self._preview_last_fit_p = None
        self._fit_preview(self.lbl_preview_p, pil_img, "p", self._avail_for(self.lbl_preview_p))
        self.lbl_preview_status_p.configure(
            text=f"Preview  {pil_img.size[0]}×{pil_img.size[1]} px")
        self.btn_preview_p.configure(state="normal")

    def _on_preview_resize_p(self, event):
        if self._preview_pil_p is None:
            return
        size = (event.width, event.height)
        if size == self._preview_last_fit_p:
            return
        self._preview_last_fit_p = size
        self._fit_preview(self.lbl_preview_p, self._preview_pil_p, "p", size)

    def _typo_engine_for_groups(self, selected_groups):
        """Return a TypoEngine filtered to selected_groups, cached by group set.

        Rebuilds (re-reads the index) only when the selection changes, so
        previews that only tweak scale/mode/zoom reuse the same engine.
        """
        key = frozenset(selected_groups)
        if getattr(self, "_typo_preview_key", None) != key:
            self._typo_preview_engine = TypoEngine(selected_groups=selected_groups)
            self._typo_preview_key = key
        return self._typo_preview_engine

    def _trigger_typo_preview(self):
        if not getattr(self, "path_t", None):
            self.lbl_preview_status_t.configure(
                text="Load typo index and select an image first")
            return
        # Match run_typo: the preview must reflect the selected Font Groups,
        # not the all-groups self.typo_engine used only as a load sanity check.
        selected_groups = [k for k, v in self.font_group_vars.items() if v.get()]
        if not selected_groups:
            self.lbl_preview_status_t.configure(
                text="Select at least one Font Group")
            return
        engine = self._typo_engine_for_groups(selected_groups)
        if not engine.library:
            self.lbl_preview_status_t.configure(
                text="No glyphs after filter — select more groups")
            return
        params = {
            "mode": self.combo_mode.get(),
            "scale": float(self.seg_scale_t.get() or "1.0"),
            "variation": int(self.seg_variation.get()),
        }
        short_edge = self._ZOOM_SHORT_EDGE.get(self.seg_zoom_t.get(), 900)
        self.btn_preview_t.configure(state="disabled")
        self.lbl_preview_status_t.configure(text="Rendering preview...")
        self._preview_typo.request(
            engine,
            self.path_t,
            short_edge=short_edge,
            params=params,
            on_done=lambda img: self.after(0, lambda i=img: self._show_typo_preview(i)),
            on_error=lambda msg: self.after(
                0, lambda m=msg: self._on_typo_preview_error(m)),
        )

    def _on_typo_preview_error(self, msg):
        self.btn_preview_t.configure(state="normal")
        self.lbl_preview_status_t.configure(text=f"Preview error: {msg}")

    def _show_typo_preview(self, pil_img):
        self._preview_pil_t = pil_img
        self._preview_last_fit_t = None
        self._fit_preview(self.lbl_preview_t, pil_img, "t", self._avail_for(self.lbl_preview_t))
        self.lbl_preview_status_t.configure(
            text=f"Preview  {pil_img.size[0]}×{pil_img.size[1]} px")
        self.btn_preview_t.configure(state="normal")

    def _on_preview_resize_t(self, event):
        if self._preview_pil_t is None:
            return
        size = (event.width, event.height)
        if size == self._preview_last_fit_t:
            return
        self._preview_last_fit_t = size
        self._fit_preview(self.lbl_preview_t, self._preview_pil_t, "t", size)

    # --- TILE LIBRARY ---

    def _check_library_status(self):
        all_dirs = list(LIBRARY_DIRS) + [DEFAULT_OUTPUT_DIR]
        total = sum(
            len(list(d.glob("*.jpg"))) + len(list(d.glob("*.png")))
            for d in all_dirs if d.exists()
        )
        if total == 0:
            text, color = "EMPTY", "#ff4444"
        elif total < STARTER_TARGET:
            text, color = f"{total} images", "#ff9900"
        elif total < 5000:
            text, color = f"{total} images", "#ffdd00"
        else:
            text, color = f"{total} images", "#33cc55"
        self.lbl_library_status.configure(text=text, text_color=color)

        starter_color = "#1a6b1a" if total >= STARTER_TARGET else "#5a3e8a"
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
        # stdout is mirrored into the sidebar console by _TextboxStream, so a
        # plain print reaches both the terminal and the GUI exactly once.
        print(msg)

    # --- ENGINE AND INDEX MANAGEMENT ---

    def run_smart_indexer(self):
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
        threading.Thread(target=_run, daemon=True).start()

    def load_index(self):
        def _load():
            self.log("Loading Smart Index from disk...")
            try:
                self.smart_engine = SmartEngine()
                self.log("Smart Engine Ready!")
            except Exception as e:
                self.log(f"Error: {e}")
        threading.Thread(target=_load, daemon=True).start()

    def load_typo_index(self):
        def _set_status(text, color):
            # Tkinter is not thread-safe: marshal the widget update onto the
            # main loop instead of configuring from this worker thread.
            self.after(0, lambda: self.lbl_typo_status.configure(
                text=text, text_color=color))

        def _load():
            self.log("Loading Font Index from disk...")
            try:
                self.typo_engine = TypoEngine()
                if self.typo_engine.library:
                    count = len(self.typo_engine.library)
                    self.log(f"SUCCESS: Loaded {count} symbols.")
                    _set_status(f"Status: Ready ({count} sym)", "#33cc55")
                else:
                    self.log("ERROR: Index empty.")
                    _set_status("Status: Missing", "#ff4444")
            except Exception as e:
                self.log(f"Error loading typo index: {e}")
                _set_status("Status: Error", "#ff4444")
        threading.Thread(target=_load, daemon=True).start()

    def scan_fonts(self):
        def _scan():
            self.log("Starting Font Scan...")
            subprocess.run([sys.executable, "-m", "src.indexer_typo"], check=False)
            self.log("Scan Complete! Click 'Load Typo Index'.")
        threading.Thread(target=_scan, daemon=True).start()

    def select_output_dir(self):
        self.output_dir = filedialog.askdirectory()
        if self.output_dir:
            self.log(f"Output: {self.output_dir}")

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

    def select_input_p(self):
        self.path_p = filedialog.askopenfilename()
        if self.path_p:
            self.lbl_preview_status_p.configure(
                text="Image selected — click Generate Preview")

    def select_input_t(self):
        self.path_t = filedialog.askopenfilename()
        if self.path_t:
            self.lbl_preview_status_t.configure(
                text="Image selected — click Generate Preview")

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
        if not out:
            return

        self.smart_engine.settings["allow_mirror"] = bool(self.check_mirror.get())
        self.smart_engine.settings["edge_aware"] = bool(self.check_edge_aware.get())
        res = self.seg_res_p.get()
        shape = self.combo_shape.get()
        scale = float(self.seg_scale_p.get() or "1.0")
        border_mode = bool(self.check_border.get())
        blend_strength = int(self.seg_blend.get().replace("%", "")) / 100.0
        tint_strength = int(self.seg_tint.get().replace("%", "")) / 100.0

        if res in ("8K", "16K"):
            self.log(f"NOTE: {res} rendering requires ~2-4 GB free RAM. "
                     f"Close other applications for best performance.")

        self.btn_run_p.configure(state="disabled")
        self.progress_render_p.set(0)
        self.progress_render_p.grid()

        def _progress(done, total):
            frac = done / total if total else 0
            self.after(0, lambda f=frac: self.progress_render_p.set(f))

        def _run():
            try:
                self.smart_engine.create_mosaic(
                    self.path_p, out, res, shape,
                    tile_scale=scale, border_mode=border_mode,
                    blend_strength=blend_strength, tint_strength=tint_strength,
                    progress_cb=_progress,
                )
                self.log("DONE! Smart Mosaic saved.")
            except Exception as e:
                self.log(f"Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.after(0, self._finish_render_p)
        threading.Thread(target=_run, daemon=True).start()

    def _finish_render_p(self):
        self.progress_render_p.grid_remove()
        self.btn_run_p.configure(state="normal")

    def run_typo(self):
        if not hasattr(self, 'path_t'):
            self.log("Error: Select Input Image first")
            return
        out = self._get_auto_filename("Symbol", ".png")
        if not out:
            return

        res = self.seg_res_t.get()
        mode = self.combo_mode.get()
        scale = float(self.seg_scale_t.get() or "1.0")
        selected_groups = [k for k, v in self.font_group_vars.items() if v.get()]
        if not selected_groups:
            self.log("ERROR: Select at least one Font Group!")
            return
        variation = int(self.seg_variation.get())

        self.btn_run_t.configure(state="disabled")
        self.progress_render_t.set(0)
        self.progress_render_t.grid()

        def _progress(done, total):
            frac = done / total if total else 0
            self.after(0, lambda f=frac: self.progress_render_t.set(f))

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
                    progress_cb=_progress,
                )
                self.log("DONE! Symbol Mosaic saved.")
            except Exception as e:
                self.log(f"Error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.after(0, self._finish_render_t)
        threading.Thread(target=_run, daemon=True).start()

    def _finish_render_t(self):
        self.progress_render_t.grid_remove()
        self.btn_run_t.configure(state="normal")

    # ------------------------------------------------------------------ #
    # Tab 3: Tile Library Browser                                         #
    # ------------------------------------------------------------------ #

    def _setup_library_tab(self):
        outer = self.tab_library
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(0, weight=0)   # explainer
        outer.grid_rowconfigure(1, weight=0)   # header
        outer.grid_rowconfigure(2, weight=0)   # filter
        outer.grid_rowconfigure(3, weight=1)   # grid
        outer.grid_rowconfigure(4, weight=0)   # action bar

        # Explainer banner — what this tab is for and how to use it
        self._make_info_banner(
            outer,
            "What is the Tile Library?",
            "This is the quality-control panel for your tile collection — the "
            "photos used as mosaic pieces. Use it BEFORE rendering.",
            [
                "Click  Refresh  to load thumbnails of every tile "
                "(library + imported photos).",
                "Filter by filename, lightness or texture to find weak tiles "
                "(too dark, flat/boring).",
                "Click tiles to select them, then  Export Bad Tiles  to add them "
                "to excluded.txt — the indexer skips them, no files deleted.",
                "LAB Coverage Map  shows whether your tiles cover the full colour "
                "range (gaps = poorer matches).",
            ],
            warn="Tiles load in pages of "
                 f"{_LIB_PAGE_SIZE} — click  Load More  to continue scanning. "
                 "With huge libraries use the filters to narrow the search.",
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        # Header row
        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.grid(row=1, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="TILE LIBRARY BROWSER",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.lbl_lib_count = ctk.CTkLabel(header, text="-- tiles", text_color="#aaaaaa")
        self.lbl_lib_count.grid(row=0, column=2, sticky="e", padx=10)

        ctk.CTkButton(
            header, text="Refresh", width=90, fg_color="#1f538d",
            command=self._lib_refresh,
        ).grid(row=0, column=3, sticky="e")

        # Filter bar — row 0: filename + sort / row 1: lightness + texture
        filter_frame = ctk.CTkFrame(outer, fg_color=("#e8e8e8", "#1e1e2e"), corner_radius=6)
        filter_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 0))
        filter_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(filter_frame, text="Filter:", width=50).grid(
            row=0, column=0, padx=(10, 4), pady=(8, 4))

        self.entry_lib_filter = ctk.CTkEntry(
            filter_frame, placeholder_text="filename contains...")
        self.entry_lib_filter.grid(row=0, column=1, sticky="ew", padx=4, pady=(8, 4))
        self.entry_lib_filter.bind("<Return>", lambda _e: self._lib_refresh())

        ctk.CTkLabel(filter_frame, text="Sort:", width=40).grid(
            row=0, column=2, padx=(8, 4), pady=(8, 4))

        self.combo_lib_sort = ctk.CTkComboBox(
            filter_frame, width=160,
            values=["Name A-Z", "Name Z-A", "Newest first", "Oldest first"],
            command=lambda _v: self._lib_refresh(),
        )
        self.combo_lib_sort.set("Name A-Z")
        self.combo_lib_sort.grid(row=0, column=3, padx=(0, 10), pady=(8, 4))

        row1 = ctk.CTkFrame(filter_frame, fg_color="transparent")
        row1.grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 8))

        ctk.CTkLabel(row1, text="Lightness:", width=72,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.seg_lib_light = ctk.CTkSegmentedButton(
            row1, values=["All", "Dark", "Mid", "Bright"], width=260,
            command=lambda _v: self._lib_refresh(),
        )
        self.seg_lib_light.set("All")
        self.seg_lib_light.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row1, text="Texture:", width=60,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))
        self.seg_lib_texture = ctk.CTkSegmentedButton(
            row1, values=["All", "Flat", "Textured"], width=210,
            command=lambda _v: self._lib_refresh(),
        )
        self.seg_lib_texture.set("All")
        self.seg_lib_texture.pack(side="left")

        # Main scrollable grid
        self.lib_scroll = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        self.lib_scroll.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        for c in range(_GRID_COLS):
            self.lib_scroll.grid_columnconfigure(c, weight=1)

        self._lib_show_placeholder("Click  Refresh  to load the tile grid")

        # Action bar
        action_bar = ctk.CTkFrame(outer, fg_color="transparent")
        action_bar.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.lbl_lib_status = ctk.CTkLabel(action_bar, text="Ready", text_color="#aaaaaa")
        self.lbl_lib_status.pack(side="left", padx=5)

        self.btn_export_bad = ctk.CTkButton(
            action_bar, text="Export Bad Tiles...", width=160,
            fg_color="gray", state="disabled",
            command=self._lib_export_bad_tiles,
        )
        self.btn_export_bad.pack(side="right", padx=5)

        self.btn_lib_more = ctk.CTkButton(
            action_bar, text="Load More", width=110,
            fg_color="gray", state="disabled",
            command=self._lib_load_more,
        )
        self.btn_lib_more.pack(side="right", padx=5)

        ctk.CTkButton(
            action_bar, text="LAB Coverage Map", width=160,
            fg_color="#4a3070",
            command=self._lib_show_lab_map,
        ).pack(side="right", padx=5)

    # ---- Library helpers ----

    def _lib_show_placeholder(self, text: str):
        for w in self.lib_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.lib_scroll,
            text=text,
            text_color="#555555",
            font=ctk.CTkFont(size=14),
        ).grid(row=0, column=0, columnspan=_GRID_COLS, pady=80)

    def _lib_collect_paths(self) -> list[Path]:
        all_dirs = list(LIBRARY_DIRS) + [DEFAULT_OUTPUT_DIR]
        paths: list[Path] = []
        for d in all_dirs:
            if d.exists():
                paths.extend(d.glob("*.jpg"))
                paths.extend(d.glob("*.jpeg"))
                paths.extend(d.glob("*.png"))

        filter_text = self.entry_lib_filter.get().strip().lower()
        if filter_text:
            paths = [p for p in paths if filter_text in p.name.lower()]

        sort_mode = self.combo_lib_sort.get()
        if sort_mode == "Name A-Z":
            paths.sort(key=lambda p: p.name.lower())
        elif sort_mode == "Name Z-A":
            paths.sort(key=lambda p: p.name.lower(), reverse=True)
        elif sort_mode == "Newest first":
            paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        elif sort_mode == "Oldest first":
            paths.sort(key=lambda p: p.stat().st_mtime)

        return paths

    def _lib_make_thumb(self, src: Path) -> tuple[Path, dict]:
        """Return (thumb_path, stats) — stats = {L, texture} normalised 0–1.

        Thumbnail is cached in _THUMB_DIR. Stats are computed from the cached
        thumbnail so repeated refreshes are free.
        """
        _THUMB_DIR.mkdir(parents=True, exist_ok=True)
        size_tag = src.stat().st_size
        dest = _THUMB_DIR / f"{src.stem}_{size_tag}.jpg"

        if dest.exists():
            with Image.open(dest) as thumb:
                arr = np.array(thumb.convert("L"), dtype=np.float32)
        else:
            with Image.open(src) as img:
                img.thumbnail((_THUMB_CACHE_PX, _THUMB_CACHE_PX), Image.LANCZOS)
                rgb = img.convert("RGB")
                rgb.save(dest, "JPEG", quality=85)
                arr = np.array(rgb.convert("L"), dtype=np.float32)

        return dest, {
            "L": float(arr.mean() / 255.0),
            "texture": float(arr.std() / 255.0),
        }

    def _lib_passes_filter(self, stats: dict) -> bool:
        L, tex = stats["L"], stats["texture"]

        light_mode = self.seg_lib_light.get()
        if light_mode != "All":
            lo, hi = _L_RANGES[light_mode]
            if not (lo <= L < hi):
                return False

        texture_mode = self.seg_lib_texture.get()
        if texture_mode == "Flat" and tex >= _TEX_THRESHOLD:
            return False
        if texture_mode == "Textured" and tex < _TEX_THRESHOLD:
            return False

        return True

    def _lib_refresh(self):
        if self._lib_loading:
            return
        self._lib_loading = True
        self._lib_selected.clear()
        self._lib_cell_frames.clear()
        self.btn_export_bad.configure(state="disabled")
        self.btn_lib_more.configure(state="disabled", fg_color="gray")
        self.after(0, lambda: self.lbl_lib_status.configure(text="Scanning..."))
        threading.Thread(target=self._lib_load_grid,
                         kwargs={"fresh": True}, daemon=True).start()

    def _lib_load_more(self):
        if self._lib_loading:
            return
        self._lib_loading = True
        self.btn_lib_more.configure(state="disabled", fg_color="gray")
        self.after(0, lambda: self.lbl_lib_status.configure(text="Loading more..."))
        threading.Thread(target=self._lib_load_grid,
                         kwargs={"fresh": False}, daemon=True).start()

    def _lib_load_grid(self, fresh: bool = True):
        """Scan the library incrementally and append one page to the grid.

        Pagination guards: at most _LIB_PAGE_SIZE thumbnails are added and
        at most _LIB_SCAN_CAP files are examined per call, so a huge
        library (hundreds of thousands of tiles) can never flood the Tk
        widget tree or RAM. 'Load More' resumes from self._lib_scan_pos.
        """
        try:
            if fresh:
                self._lib_paths = self._lib_collect_paths()
                self._lib_scan_pos = 0
                self._lib_shown = 0
                self._lib_images = []
                self._lib_cell_frames.clear()
                # Runs on a worker thread; _check_library_status configures
                # sidebar widgets, so marshal it onto the main loop (Tk is
                # not thread-safe).
                self.after(0, self._check_library_status)

                if not self._lib_paths:
                    self.after(0, lambda: self.lbl_lib_count.configure(
                        text="0 tiles"))
                    self.after(0, lambda: self._lib_show_placeholder(
                        "No tiles found. Download tiles using the sidebar."))
                    self.after(0, lambda: self.lbl_lib_status.configure(
                        text="Ready — 0 tiles"))
                    return

                self.after(0, lambda: [w.destroy()
                                       for w in self.lib_scroll.winfo_children()])

            paths = self._lib_paths
            total = len(paths)
            px = _THUMB_DISPLAY_PX
            page_shown = 0
            scanned = 0

            while self._lib_scan_pos < total:
                if not self._lib_loading:
                    break
                if page_shown >= _LIB_PAGE_SIZE or scanned >= _LIB_SCAN_CAP:
                    break

                src = paths[self._lib_scan_pos]
                self._lib_scan_pos += 1
                scanned += 1

                try:
                    thumb_path, stats = self._lib_make_thumb(src)
                    if not self._lib_passes_filter(stats):
                        continue

                    pil_img = Image.open(thumb_path).copy()
                    ctk_img = ctk.CTkImage(
                        light_image=pil_img, dark_image=pil_img,
                        size=(px, px),
                    )
                    self._lib_images.append(ctk_img)

                    r = self._lib_shown // _GRID_COLS
                    c = self._lib_shown % _GRID_COLS
                    name = src.name if len(src.name) <= 16 else src.name[:14] + ".."

                    def _add(row=r, col=c, img=ctk_img, lbl=name, path=src):
                        cell = ctk.CTkFrame(
                            self.lib_scroll,
                            fg_color=("#dddddd", "#2a2a3a"),
                            corner_radius=6,
                            width=px + 14,
                            height=px + 28,
                        )
                        cell.grid(row=row, column=col, padx=4, pady=4, sticky="n")
                        cell.grid_propagate(False)
                        img_lbl = ctk.CTkLabel(cell, image=img, text="")
                        img_lbl.pack(pady=(5, 2))
                        name_lbl = ctk.CTkLabel(
                            cell, text=lbl,
                            font=ctk.CTkFont(size=11),
                            text_color="#999999",
                        )
                        name_lbl.pack()
                        self._lib_cell_frames[path] = cell
                        handler = lambda _e, p=path, c=cell: self._lib_toggle_tile(p, c)
                        cell.bind("<Button-1>", handler)
                        img_lbl.bind("<Button-1>", handler)
                        name_lbl.bind("<Button-1>", handler)

                    self.after(0, _add)
                    self._lib_shown += 1
                    page_shown += 1

                except Exception:
                    pass

                if scanned % 25 == 0:
                    done = self._lib_scan_pos
                    self.after(0, lambda n=done: self.lbl_lib_status.configure(
                        text=f"Scanning {n}/{total}..."))

            remaining = total - self._lib_scan_pos

            if self._lib_shown == 0 and remaining == 0:
                self.after(0, lambda: self._lib_show_placeholder(
                    "No tiles match the current filters."))

            n_shown = self._lib_shown
            self.after(0, lambda: self.lbl_lib_count.configure(
                text=f"{n_shown} / {total} tiles"))

            if remaining > 0:
                self.after(0, lambda: self.btn_lib_more.configure(
                    state="normal", fg_color="#1f538d"))
                status = (f"Ready — {n_shown} tiles shown, "
                          f"{remaining} files not scanned yet (Load More)")
            else:
                status = f"Ready — {n_shown} tiles shown of {total} scanned"
            self.after(0, lambda s=status: self.lbl_lib_status.configure(text=s))

        finally:
            self._lib_loading = False

    # ---- Tile selection + export ----

    def _lib_toggle_tile(self, path: Path, cell: ctk.CTkFrame):
        if path in self._lib_selected:
            self._lib_selected.discard(path)
            cell.configure(fg_color=("#dddddd", "#2a2a3a"))
        else:
            self._lib_selected.add(path)
            cell.configure(fg_color=("#7722bb", "#4a1a88"))

        n = len(self._lib_selected)
        if n == 0:
            self.btn_export_bad.configure(state="disabled")
            self.lbl_lib_status.configure(text="Ready")
        else:
            self.btn_export_bad.configure(state="normal")
            word = "tile" if n == 1 else "tiles"
            self.lbl_lib_status.configure(
                text=f"{n} {word} selected — click Export Bad Tiles to save")

    def _lib_export_bad_tiles(self):
        if not self._lib_selected:
            return
        by_dir: dict[Path, list[Path]] = {}
        for p in self._lib_selected:
            by_dir.setdefault(p.parent, []).append(p)

        newly_added = 0
        for parent, paths in by_dir.items():
            excluded_file = parent / "excluded.txt"
            existing: set[str] = set()
            if excluded_file.exists():
                existing = set(excluded_file.read_text(encoding="utf-8").splitlines())
            new_names = {p.name for p in paths}
            combined = existing | new_names
            excluded_file.write_text("\n".join(sorted(combined)), encoding="utf-8")
            newly_added += len(new_names - existing)

        total = len(self._lib_selected)
        self.lbl_lib_status.configure(
            text=f"Exported {newly_added} new tile(s) ({total} selected) to excluded.txt")

    # ---- LAB Coverage Map ----

    def _lib_show_lab_map(self):
        if not _SMART_INDEX.exists():
            self.lbl_lib_status.configure(
                text="LAB Map: smart_index.pkl not found — run Update / Create Index first")
            return

        self.lbl_lib_status.configure(text="Building LAB map...")
        threading.Thread(target=self._lib_build_lab_map, daemon=True).start()

    def _lib_build_lab_map(self):
        try:
            with open(_SMART_INDEX, "rb") as f:
                data = pickle.load(f)

            features = data["features"]          # (N, 79)
            N = len(features)

            # Mean LAB per tile — first 75 dims, every 3rd channel
            mean_L = features[:, 0:75:3].mean(axis=1) * 100           # 0..100
            mean_a = features[:, 1:75:3].mean(axis=1) * 255 - 128     # -128..127
            mean_b = features[:, 2:75:3].mean(axis=1) * 255 - 128     # -128..127

            # 2-component PCA of the full 75-dim LAB vectors
            pca = PCA(n_components=2, random_state=0)
            proj = pca.fit_transform(features[:, :75])
            var1 = pca.explained_variance_ratio_[0]
            var2 = pca.explained_variance_ratio_[1]

            self.after(0, lambda: self._lib_open_map_window(
                N, mean_L, mean_a, mean_b, proj, var1, var2))

        except Exception as exc:
            msg = f"LAB Map error: {exc}"
            self.after(0, lambda: self.lbl_lib_status.configure(text=msg))

    def _lib_open_map_window(self, N, mean_L, mean_a, mean_b, proj, var1, var2):
        win = ctk.CTkToplevel(self)
        win.title(f"LAB Coverage Map — {N} tiles indexed")
        win.geometry("960x500")
        win.grab_set()

        bg = "#1a1a2e"
        panel_bg = "#0d0d1a"
        tick_col = "#666688"
        label_col = "#aaaacc"
        title_col = "#ccccee"

        fig = Figure(figsize=(9.6, 4.8), facecolor=bg)

        # --- Plot 1: a-b hex bin (colour gamut coverage) ---
        ax1 = fig.add_subplot(121)
        ax1.set_facecolor(panel_bg)
        hb = ax1.hexbin(
            mean_a, mean_b,
            C=mean_L, reduce_C_function=np.mean,
            gridsize=28, cmap="RdYlGn", mincnt=1,
        )
        ax1.axhline(0, color="#334", lw=0.6, zorder=0)
        ax1.axvline(0, color="#334", lw=0.6, zorder=0)
        ax1.set_xlabel("a*  (green ←→ red)", color=label_col, fontsize=10)
        ax1.set_ylabel("b*  (blue ←→ yellow)", color=label_col, fontsize=10)
        ax1.set_title("Colour Gamut Coverage (a–b)", color=title_col, fontsize=11, pad=8)
        ax1.tick_params(colors=tick_col, labelsize=8)
        for spine in ax1.spines.values():
            spine.set_edgecolor("#334466")
        cb1 = fig.colorbar(hb, ax=ax1, pad=0.02)
        cb1.set_label("mean L*", color=label_col, fontsize=9)
        cb1.ax.yaxis.set_tick_params(color=tick_col, labelcolor=tick_col)

        # --- Plot 2: PCA scatter coloured by L* ---
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor(panel_bg)
        sc = ax2.scatter(
            proj[:, 0], proj[:, 1],
            c=mean_L, cmap="plasma",
            s=3, alpha=0.45, linewidths=0, rasterized=True,
        )
        ax2.set_xlabel(f"PC1  ({var1:.0%} var)", color=label_col, fontsize=10)
        ax2.set_ylabel(f"PC2  ({var2:.0%} var)", color=label_col, fontsize=10)
        ax2.set_title("PCA Diversity  (colour = L*)", color=title_col, fontsize=11, pad=8)
        ax2.tick_params(colors=tick_col, labelsize=8)
        for spine in ax2.spines.values():
            spine.set_edgecolor("#334466")
        cb2 = fig.colorbar(sc, ax=ax2, pad=0.02)
        cb2.set_label("L*", color=label_col, fontsize=9)
        cb2.ax.yaxis.set_tick_params(color=tick_col, labelcolor=tick_col)

        fig.tight_layout(pad=1.8)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        self.lbl_lib_status.configure(
            text=f"LAB Map — {N} tiles, PC1+PC2 = {var1+var2:.0%} variance")


if __name__ == "__main__":
    app = App()
    app.mainloop()
