"""Montaz zbiorczy wszystkich schematow ksztaltow (E8 krok 1).

Sklada miniatury z assets/shape_schemes/*.png w jedna plansze 8x8 z podpisem
nazwy pod kazda miniatura. Kolejnosc = shape_names() z engine_smart (single
source of truth, zgodna z GUI/CLI) -- NIE listing katalogu.

Bramka: dla KAZDEJ nazwy z shape_names() musi istniec PNG w shape_schemes/.
Jesli ktoregos brak -- wypisuje liste brakow i przerywa (regeneruj Z SILNIKA
wzorcem gen_e6_schemes.py / gen_e7_schemes.py, nie podstawiaj proposals/).

ASCII-only w print() (terminal CP1250).

Uruchom:
    python -m src.tools.gen_shape_montage
"""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.engine_smart import shape_names

logger = logging.getLogger(__name__)

# --- katalogi --------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
SCHEMES_DIR = ROOT / "assets" / "shape_schemes"
FONT_PATH = ROOT / "assets" / "fonts" / "IBMPlexMono-SemiBold.ttf"
OUT_PATH = ROOT / "assets" / "shape_montage.png"

# --- parametry planszy -----------------------------------------------------
COLS = 8
THUMB = 260              # bok miniatury (downscale z 720)
GAP = 18                 # odstep miedzy komorkami
MARGIN = 26              # margines zewnetrzny
LABEL_H = 36             # wysokosc paska podpisu
LABEL_PAD = 4            # margines poziomy podpisu w komorce
FONT_BASE = 18           # bazowy rozmiar fontu (kurczony per-podpis, jesli za dlugi)
FONT_MIN = 11            # dolna granica kurczenia

BG = (30, 33, 40)        # charcoal -- rama i pasek podpisow
LABEL_FG = (235, 238, 242)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int) -> ImageFont.FreeTypeFont:
    """Najwiekszy font (<= FONT_BASE) mieszczacy `text` w `max_w` px."""
    for size in range(FONT_BASE, FONT_MIN - 1, -1):
        font = _load_font(size)
        if draw.textlength(text, font=font) <= max_w:
            return font
    return _load_font(FONT_MIN)


def _gate(names: list[str]) -> list[str]:
    """Zwraca liste brakujacych PNG (pusta = OK)."""
    missing = [n for n in names if not (SCHEMES_DIR / f"{n}.png").is_file()]
    return missing


def build_montage() -> Path:
    names = shape_names()
    total = len(names)
    rows = (total + COLS - 1) // COLS

    missing = _gate(names)
    if missing:
        print("BRAK schematow PNG dla nazw z shape_names():")
        for n in missing:
            print("  - " + n)
        print("Zregeneruj Z SILNIKA (gen_e6_schemes.py / gen_e7_schemes.py),")
        print("nie podstawiaj starych PNG z assets/proposals/.")
        raise SystemExit(1)

    cell_w = THUMB
    cell_h = THUMB + LABEL_H
    sheet_w = MARGIN * 2 + COLS * cell_w + (COLS - 1) * GAP
    sheet_h = MARGIN * 2 + rows * cell_h + (rows - 1) * GAP

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)

    for idx, name in enumerate(names):
        col = idx % COLS
        row = idx // COLS
        x0 = MARGIN + col * (cell_w + GAP)
        y0 = MARGIN + row * (cell_h + GAP)

        thumb = Image.open(SCHEMES_DIR / f"{name}.png").convert("RGB")
        if thumb.size != (THUMB, THUMB):
            thumb = thumb.resize((THUMB, THUMB), Image.LANCZOS)
        sheet.paste(thumb, (x0, y0))

        # podpis wysrodkowany pod miniatura
        font = _fit_font(draw, name, cell_w - 2 * LABEL_PAD)
        tw = draw.textlength(name, font=font)
        tx = x0 + (cell_w - tw) / 2
        ty = y0 + THUMB + (LABEL_H - font.size) / 2
        draw.text((tx, ty), name, font=font, fill=LABEL_FG)

    sheet.save(OUT_PATH)
    print("Montaz zapisany: " + str(OUT_PATH))
    print("Ksztaltow: %d | siatka: %dx%d | plansza: %dx%d px"
          % (total, COLS, rows, sheet_w, sheet_h))
    return OUT_PATH


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_montage()
