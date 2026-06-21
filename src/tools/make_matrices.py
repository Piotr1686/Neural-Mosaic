"""
src/tools/make_matrices.py
--------------------------
Assembles README showcase composites from already-rendered 16K masters.

This tool does NO rendering — it only crops, downscales and tiles existing
master images into the labelled composites used by README.md. Rendering of
the masters is done separately (via src.cli) so this assembly step is cheap
and re-runnable.

Inputs (in output/github_readme/, produced by src.cli):
    spectre_parrot_16K.jpg                 - spectre + black-border hero
    typo_grp_<key>_16K.png  (6 panels)     - font-group matrix panels
    typo_size_<scale>_16K.png  (3 panels)  - font-size matrix panels

Outputs (in assets/examples/):
    spectre_full.jpg / spectre_zoom1.jpg / spectre_zoom2.jpg
    typo_matrix_groups.jpg / typo_ancient_detail.jpg
    typo_matrix_size.jpg

Usage:
    python -m src.tools.make_matrices            # build everything available
    python -m src.tools.make_matrices --list     # status only
"""
import argparse
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Our own 16K masters exceed PIL's default decompression-bomb guard (~178 Mpx).
Image.MAX_IMAGE_PIXELS = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MASTERS_DIR  = PROJECT_ROOT / "output" / "github_readme"
EXAMPLES_DIR = PROJECT_ROOT / "assets" / "examples"
LABEL_FONT   = PROJECT_ROOT / "assets" / "fonts" / "NotoSans-Regular.ttf"

# Panel order + short labels for the font-group matrix (3x2).
GROUP_PANELS = [
    ("cjk",     "CJK (Hanzi / Kana / Hangul)"),
    ("latin",   "Latin Monospace"),
    ("hand",    "Handwriting / Script"),
    ("deco",    "Decorative / Display"),
    ("ancient", "Egyptian Hieroglyphs"),
    ("symbols", "Symbols / Math / Emoji"),
]
SIZE_PANELS = [
    ("05", "0.5x - small, dense"),
    ("10", "1.0x - default"),
    ("20", "2.0x - large, legible"),
]
# Same crop region across groups, shown up close so the actual glyphs are visible.
GLYPH_DETAIL = [
    ("cjk",     "CJK"),
    ("ancient", "Hieroglyphs / Cuneiform"),
    ("hand",    "Handwriting"),
]

LABEL_H   = 46     # label bar height (px)
PAD       = 14     # gap between panels (px)
PANEL_W   = 760    # panel image width in the composite (px)
BG        = (17, 17, 30)      # dark background (matches GUI theme)
FG        = (235, 235, 245)   # label text colour


# -- helpers ------------------------------------------------------------------

def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(LABEL_FONT), size)
    except Exception:
        return ImageFont.load_default()


def _fit_width(img: Image.Image, width: int) -> Image.Image:
    """Scale image so its width == `width` (preserve aspect; downscale only sensibly)."""
    w, h = img.size
    new_h = max(1, round(h * width / w))
    return img.resize((width, new_h), Image.Resampling.LANCZOS)


def _panel(img: Image.Image, label: str, width: int) -> Image.Image:
    """Return a labelled panel: a label bar on top of the scaled image."""
    body = _fit_width(img.convert("RGB"), width)
    panel = Image.new("RGB", (width, LABEL_H + body.size[1]), BG)
    draw = ImageDraw.Draw(panel)
    font = _font(26)
    tb = draw.textbbox((0, 0), label, font=font)
    tx = (width - (tb[2] - tb[0])) // 2
    ty = (LABEL_H - (tb[3] - tb[1])) // 2 - tb[1]
    draw.text((tx, ty), label, fill=FG, font=font)
    panel.paste(body, (0, LABEL_H))
    return panel


def _grid(panels: list, cols: int) -> Image.Image:
    """Tile panels into a grid with padding; rows aligned to tallest panel."""
    rows = (len(panels) + cols - 1) // cols
    col_w = max(p.size[0] for p in panels)
    row_hs = []
    for r in range(rows):
        row = panels[r * cols:(r + 1) * cols]
        row_hs.append(max(p.size[1] for p in row))
    total_w = cols * col_w + (cols + 1) * PAD
    total_h = sum(row_hs) + (rows + 1) * PAD
    canvas = Image.new("RGB", (total_w, total_h), BG)
    y = PAD
    for r in range(rows):
        x = PAD
        for c in range(cols):
            i = r * cols + c
            if i >= len(panels):
                break
            canvas.paste(panels[i], (x, y))
            x += col_w + PAD
        y += row_hs[r] + PAD
    return canvas


def _crop_centre(img: Image.Image, frac: float, out_w: int) -> Image.Image:
    """Crop a centred region `frac` of the long edge, scale to out_w wide."""
    w, h = img.size
    cw, ch = int(w * frac), int(h * frac)
    cx, cy = w // 2, h // 2
    box = (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)
    crop = img.convert("RGB").crop(box)
    return _fit_width(crop, out_w)


def _crop_box(img: Image.Image, box_w: int, box_h: int, out_w: int,
              cx_frac: float = 0.5, cy_frac: float = 0.5) -> Image.Image:
    """Crop a fixed-pixel box anchored at (cx_frac, cy_frac), scale to out_w wide.

    Using the same box across panels keeps glyph scale honest, so size/script
    differences are directly comparable. The anchor lets callers target a
    mid-tone band (clean black-on-white glyphs) instead of the darkest region.
    """
    w, h = img.size
    box_w, box_h = min(box_w, w), min(box_h, h)
    cx, cy = int(w * cx_frac), int(h * cy_frac)
    x0 = max(0, min(cx - box_w // 2, w - box_w))
    y0 = max(0, min(cy - box_h // 2, h - box_h))
    return _fit_width(img.convert("RGB").crop((x0, y0, x0 + box_w, y0 + box_h)), out_w)


# -- build steps --------------------------------------------------------------

def build_spectre_triptych() -> bool:
    master = MASTERS_DIR / "spectre_parrot_16K.jpg"
    if not master.exists():
        print(f"  [skip] spectre triptych - master not found: {master.name}")
        return False
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    with Image.open(master) as img:
        img.load()
        _fit_width(img, 1500).save(EXAMPLES_DIR / "spectre_full.jpg", quality=92)
        _crop_centre(img, 0.40, 1100).save(EXAMPLES_DIR / "spectre_zoom1.jpg", quality=92)
        _crop_centre(img, 0.13, 1100).save(EXAMPLES_DIR / "spectre_zoom2.jpg", quality=93)
    print("  OK spectre_full.jpg / spectre_zoom1.jpg / spectre_zoom2.jpg")
    return True


def build_group_matrix() -> bool:
    panels, missing = [], []
    for key, label in GROUP_PANELS:
        p = MASTERS_DIR / f"typo_grp_{key}_16K.png"
        if not p.exists():
            missing.append(p.name)
            continue
        with Image.open(p) as img:
            panels.append(_panel(img, label, PANEL_W))
    if missing:
        print(f"  [skip] group matrix - missing panels: {', '.join(missing)}")
        return False
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _grid(panels, cols=2).save(EXAMPLES_DIR / "typo_matrix_groups.jpg", quality=92)
    print("  OK typo_matrix_groups.jpg")
    return True


def build_glyph_detail() -> bool:
    """Same crop region across three scripts, zoomed so individual glyphs read."""
    panels, missing = [], []
    for key, label in GLYPH_DETAIL:
        p = MASTERS_DIR / f"typo_grp_{key}_16K.png"
        if not p.exists():
            missing.append(p.name)
            continue
        with Image.open(p) as img:
            crop = _crop_box(img, 1100, 700, PANEL_W, cy_frac=0.34)
            panels.append(_panel(crop, label, PANEL_W))
    if missing:
        print(f"  [skip] glyph detail - missing panels: {', '.join(missing)}")
        return False
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _grid(panels, cols=3).save(EXAMPLES_DIR / "typo_glyph_detail.jpg", quality=93)
    print("  OK typo_glyph_detail.jpg")
    return True


def build_size_matrix() -> bool:
    panels, missing = [], []
    for key, label in SIZE_PANELS:
        p = MASTERS_DIR / f"typo_size_{key}_16K.png"
        if not p.exists():
            missing.append(p.name)
            continue
        with Image.open(p) as img:
            # Full panel keeps a clean, consistent black-on-white look across all
            # three; the glyph-size difference reads as texture coarseness.
            panels.append(_panel(img, label, PANEL_W))
    if missing:
        print(f"  [skip] size matrix - missing panels: {', '.join(missing)}")
        return False
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _grid(panels, cols=3).save(EXAMPLES_DIR / "typo_matrix_size.jpg", quality=92)
    print("  OK typo_matrix_size.jpg")
    return True


def list_status():
    print("Masters in", MASTERS_DIR)
    expected = (
        ["spectre_parrot_16K.jpg"]
        + [f"typo_grp_{k}_16K.png" for k, _ in GROUP_PANELS]
        + [f"typo_size_{k}_16K.png" for k, _ in SIZE_PANELS]
    )
    for name in expected:
        p = MASTERS_DIR / name
        print(f"  {'OK  ' if p.exists() else 'MISS'} {name}")


def main():
    parser = argparse.ArgumentParser(description="Assemble README showcase composites.")
    parser.add_argument("--list", action="store_true", help="Print master status only.")
    args = parser.parse_args()

    print("=" * 60)
    print("  Neural-Mosaic - README composite builder")
    print("=" * 60)

    if args.list:
        list_status()
        return

    build_spectre_triptych()
    build_group_matrix()
    build_glyph_detail()
    build_size_matrix()
    print("Done.")


if __name__ == "__main__":
    main()
