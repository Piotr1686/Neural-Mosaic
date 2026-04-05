import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import customtkinter as ctk
from tkinter import filedialog
import threading
from datetime import datetime
from pathlib import Path
from .engine_smart import SmartEngine
from .engine_typo import TypoEngine
# Importujemy Indexer, żeby przycisk działał
from .indexer_smart import SmartIndexer

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

FONTS_DIR = Path("assets/fonts") 

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NeuroMosaic 5.7 (Solid Geometry)")
        self.geometry("1250x900")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.output_dir = None
        
        self._init_sidebar()
        self._init_tabs()
        
        self.smart_engine = None 
        self.typo_engine = TypoEngine()

    def _init_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo = ctk.CTkLabel(self.sidebar, text="NEURAL\nMOSAIC", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # --- SEKCJA INDEKSOWANIA ---
        self.btn_load_smart = ctk.CTkButton(self.sidebar, text="Load Smart Index", fg_color="darkgreen", command=self.load_index)
        self.btn_load_smart.grid(row=1, column=0, padx=20, pady=(10, 5))
        
        # NOWY PRZYCISK: Update / Create Index
        self.btn_update_smart = ctk.CTkButton(self.sidebar, text="Update / Create Index", fg_color="#1f538d", command=self.run_smart_indexer)
        self.btn_update_smart.grid(row=2, column=0, padx=20, pady=(5, 20))
        
        ctk.CTkLabel(self.sidebar, text="OUTPUT SETTINGS", font=ctk.CTkFont(size=12, weight="bold")).grid(row=3, column=0, pady=(10,5))
        
        self.btn_out_dir = ctk.CTkButton(self.sidebar, text="Set Output Folder", fg_color="gray", command=self.select_output_dir)
        self.btn_out_dir.grid(row=4, column=0, padx=20, pady=5)
        
        self.entry_project_name = ctk.CTkEntry(self.sidebar, placeholder_text="Project Name")
        self.entry_project_name.grid(row=5, column=0, padx=20, pady=5)
        
        self.console = ctk.CTkTextbox(self.sidebar, width=220)
        self.console.grid(row=6, column=0, padx=10, pady=20, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

    def _init_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.tab_photo = self.tabview.add("Smart Photo Mosaic")
        self.tab_typo = self.tabview.add("Symbol Mosaic (Typo)")
        
        self._setup_photo_tab()
        self._setup_typo_tab()

    def _setup_photo_tab(self):
        frame = self.tab_photo
        ctk.CTkLabel(frame, text="REGIONAL COLOR MOSAIC", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
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
        # Wszystkie kształty
        shapes = ["square", "rectangle_3x1", "brick_wall", "hexagon", "hexagon_romb", "romb", "triangle", "einstein_hat"]
        self.combo_shape = ctk.CTkComboBox(frame, values=shapes)
        self.combo_shape.set("hexagon_romb")
        self.combo_shape.pack(pady=5)
        
        # Checkboxy
        self.check_mirror = ctk.CTkCheckBox(frame, text="Allow Mirroring")
        self.check_mirror.select()
        self.check_mirror.pack(pady=(15, 5))
        
        self.check_border = ctk.CTkCheckBox(frame, text="Black Borders (Grout)")
        self.check_border.deselect()
        self.check_border.pack(pady=5)
        
        self.btn_run_p = ctk.CTkButton(frame, text="RENDER SMART MOSAIC", fg_color="green", height=50, command=self.run_photo)
        self.btn_run_p.pack(pady=30)

    def _setup_typo_tab(self):
        frame = self.tab_typo
        ctk.CTkLabel(frame, text="SYMBOL MOSAIC (GLOBAL FONTS)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
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
        
        ctk.CTkLabel(frame, text="Style Mode").pack(pady=(10,0))
        self.combo_mode = ctk.CTkComboBox(frame, values=["black_on_white", "white_on_black", "color_on_white"])
        self.combo_mode.pack(pady=5)
        
        self.btn_run_t = ctk.CTkButton(frame, text="RENDER SYMBOL MOSAIC", fg_color="purple", height=50, command=self.run_typo)
        self.btn_run_t.pack(pady=30)

    def log(self, msg):
        print(msg)
        def _update():
            self.console.insert("end", msg + "\n")
            self.console.see("end")
        self.after(0, _update)

    # --- OBSŁUGA SILNIKA I INDEKSÓW ---

    def run_smart_indexer(self):
        """Uruchamia indeksowanie zdjęć"""
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
            os.system("python -m src.indexer_typo")
            self.log("Scan Complete! Click 'Load Typo Index'.")
        threading.Thread(target=_scan).start()

    def select_output_dir(self):
        self.output_dir = filedialog.askdirectory()
        if self.output_dir: self.log(f"Output: {self.output_dir}")

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
        
        # Pobieranie ustawień z GUI
        self.smart_engine.settings["allow_mirror"] = bool(self.check_mirror.get())
        res = self.combo_res_p.get()
        shape = self.combo_shape.get()
        scale = self.seg_scale_p.get()
        border_mode = bool(self.check_border.get()) # Ramki
        
        if not scale: scale = "1.0"
        scale = float(scale)
        
        def _run():
            try:
                # Przekazujemy border_mode do silnika
                self.smart_engine.create_mosaic(self.path_p, out, res, shape, tile_scale=scale, border_mode=border_mode)
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
        
        def _run():
            self.log(f"Starting Multi-Font Render...")
            try:
                self.typo_engine.process(self.path_t, out, res, mode, scale=scale)
                self.log("DONE! Symbol Mosaic saved.")
            except Exception as e: self.log(f"Error: {e}")
        threading.Thread(target=_run).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()