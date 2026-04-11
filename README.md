# NeuroMosaic

> A desktop application that turns any photo into a high-resolution mosaic — assembled from thousands of real photographs or typographic glyphs.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-darkblue)
![Resolution](https://img.shields.io/badge/Output-up%20to%2016K-orange)

---

## Overview

NeuroMosaic is a standalone desktop tool with two independent creative engines, both accessible from a single dark-themed GUI. Load an image, configure a handful of options, and click **Render** — the application handles the rest in a background thread while keeping the interface fully responsive.

![NeuroMosaic GUI](assets/preview.jpg)

---

## Two Modes, One Window

### Smart Photo Mosaic

Reconstructs the target image by tiling it with photographs from your personal library. Matching is performed in **CIE-LAB colour space** using a 3×3 regional grid per tile, which preserves both overall hue and local colour transitions. A `cKDTree` index allows the engine to search hundreds of thousands of candidates in milliseconds.

**What you can control in the GUI:**

| Control | Options |
|---|---|
| Output resolution | 2K · 4K · 8K · **16K** |
| Tile size multiplier | 0.5 · 0.75 · 1.0 · 1.75 · 2.0 |
| Tile shape | `square` · `rectangle_3x1` · `brick_wall` · `hexagon` · `hexagon_romb` · `romb` · `triangle` · `kite` |
| Allow Mirroring | Horizontally flips tiles on the fly, doubling the effective library size without using extra disk space |
| Black Borders (Grout) | Adds a dark gap between tiles — simulates real mosaic grout lines |

The `kite` shape implements the aperiodic **Einstein "hat" polykite** tiling — a mathematically unique geometry that never repeats periodically.

**Anti-repetition system:** The engine enforces a hard neighbour constraint (no tile from the same source image may touch another) combined with a frequency penalty that gradually discourages reuse of popular tiles across the entire composition. Together these prevent any single photograph from dominating the output.

---

### Symbol Mosaic (Typo)

Reconstructs the target image using typographic glyphs instead of photographs. Each cell is replaced by a character whose **ink density** best matches the local brightness of the source image. The glyph set spans standard Latin/ASCII characters and **CJK Unicode blocks** (Chinese Hanzi, Japanese Hiragana & Katakana, Korean Hangul), giving the output a distinctive East Asian aesthetic when desired.

**What you can control in the GUI:**

| Control | Options |
|---|---|
| Output resolution | 4K · 8K · **16K** |
| Symbol size multiplier | 0.5 · 0.75 · 1.0 · 1.75 · 2.0 |
| Style mode | `black_on_white` · `white_on_black` · `color_on_white` |

Font scanning is triggered from the GUI with a single click. Any `.ttf` or `.otf` fonts placed in `assets/fonts/` are indexed automatically.

---

## Getting Started

### 1. Clone & install

```bash
git clone https://github.com/your-username/neural-mosaic.git
cd neural-mosaic
pip install -r requirements.txt
```

> GPU is recommended but not required. For CUDA support, install the PyTorch build that matches your hardware before running the above.

### 2. Add fonts (Symbol Mosaic only)

The `assets/fonts/` directory is excluded from the repository due to file sizes. Place any `.ttf` or `.otf` fonts there before using the Symbol Mosaic tab. Free sources: [Google Fonts](https://fonts.google.com), [Noto Fonts](https://fonts.google.com/noto) (recommended for CJK support).

### 3. Configure (optional)

Copy `.env.example` to `.env` and adjust values for your setup:

```bash
cp .env.example .env
```

Key settings: `TILE_SIZE`, `TARGET_SHORT_SIDE` (output resolution), `USE_CUDA`.

### 4. Launch the GUI

```bash
python -m src.gui
```

---

## Workflow Inside the GUI

### Smart Photo Mosaic

1. **Sidebar → "Update / Create Index"** — scans `data/library_public/tiles/` (and `data/library_private/tiles/` if present) and builds `data/smart_index.pkl`. Run once after adding new photos; subsequent loads take seconds.
2. **Sidebar → "Load Smart Index"** — loads the pre-built index into memory.
3. **Tab: Smart Photo Mosaic** — select your input image, choose resolution, tile shape, and rendering options.
4. **Sidebar → "Set Output Folder"** + optionally enter a **Project Name**.
5. Click **RENDER SMART MOSAIC**. Progress is logged live in the sidebar console. The file is saved automatically as `<ProjectName>_Smart_<timestamp>.jpg`.

### Symbol Mosaic (Typo)

1. **Tab: Symbol Mosaic → "Update Database (Scan Assets)"** — indexes all fonts in `assets/fonts/`. Run once after adding new fonts.
2. **"Load Typo Index (Fast)"** — loads the font index. The status label shows how many symbols are ready.
3. Select your input image, choose resolution, symbol size, and style mode.
4. Click **RENDER SYMBOL MOSAIC**. The file is saved as `<ProjectName>_Symbol_<timestamp>.png`.

---

## Building the Tile Library

The included async downloader fetches public-domain artwork (Chicago Art Institute API) and Creative Commons images:

```bash
python -m src.fast_downloader
```

After downloading, run the image optimizer to normalise sizes and remove corrupt files:

```bash
python -m src.optimizer
```

Place your own photos directly in `data/library_private/tiles/` — they are indexed alongside the public library without any additional steps.

---

## How It Works

### Smart Engine — colour matching

Every tile in the library is represented as a **27-dimensional feature vector**: a 3×3 grid of cells, each described by its mean LAB (L\*, a\*, b\*) values. This captures both the dominant colour and the spatial colour gradient across the tile. At render time a `cKDTree` finds the nearest neighbours for each sector of the target image in milliseconds, even with 300,000+ tiles indexed.

### Typo Engine — brightness matching

Each glyph is pre-rendered at the target tile size and its **normalised ink density** (fraction of dark pixels) is computed and stored. At render time the engine maps each cell's mean brightness to the closest glyph by density, then renders it in the chosen style mode.

### Anti-repetition (Smart Engine)

- **Hard constraint:** A tile's source file may not appear in any of the 4 direct neighbours of the current cell.
- **Frequency penalty:** Each use of a source file increments a global counter. The penalised score is `raw_score + (usage_count × W_FREQ)`, which continuously pushes the engine toward less-used tiles.
- Both constraints treat all mirrored variants of the same image as a single source identity.

---

## Development

NeuroMosaic grew from an iterative design conversation that explored several approaches before arriving at the current architecture:

- **v1–v2:** Semantic matching with OpenAI CLIP (ViT-B/32) — perceptually aware but colour-inaccurate.
- **v3–v4:** Hybrid CLIP + RGB scoring with VGG-19 structural analysis and tile transformations (mirroring, 90°/180°/270° rotation).
- **v5 (current):** Replaced learned embeddings with direct LAB colour matching. This eliminated the GPU memory bottleneck of large neural models while producing sharper colour fidelity. The 3×3 LAB grid preserves the spatial structure awareness that motivated the earlier VGG approach.

Each iteration kept the anti-repetition logic and the multi-shape tile geometry, which remain the most distinctive aspects of the engine.

---

## Project Structure

```
neural-mosaic/
├── src/
│   ├── gui.py              # Entry point — CustomTkinter application
│   ├── engine_smart.py     # Colour-matched photomosaic engine
│   ├── engine_typo.py      # Typography / glyph mosaic engine
│   ├── indexer_smart.py    # Builds data/smart_index.pkl
│   ├── indexer_typo.py     # Builds data/typo_index.pkl
│   ├── ai_core.py          # MiDaS depth model (lazy-loaded singleton)
│   ├── downloader.py       # Async public-domain image fetcher
│   ├── optimizer.py        # Image normalisation & cleanup
│   └── config.py           # Settings dataclass (reads .env)
├── assets/
│   └── fonts/              # Place .ttf / .otf fonts here
├── data/
│   ├── library_public/tiles/
│   └── library_private/tiles/
├── tests/
└── requirements.txt
```

---

## Requirements

- Python 3.10+
- PyTorch (CPU or CUDA)
- `customtkinter`, `Pillow`, `numpy`, `scipy`, `scikit-image`, `tqdm`

Full list: `requirements.txt`

---

## License

MIT — use it, fork it, build on it.
