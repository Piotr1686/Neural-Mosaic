# NeuroMosaic

> Turn any photograph into a high-resolution mosaic — assembled from thousands of real images or typographic glyphs. Desktop app with real-time preview.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white&color=3776AB)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1a1a2e?style=flat-square)
![Resolution](https://img.shields.io/badge/Output-up%20to%2016K-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows)
![Last Commit](https://img.shields.io/github/last-commit/Piotr1686/neuromosaic?style=flat-square)
![Repo Size](https://img.shields.io/github/repo-size/Piotr1686/neuromosaic?style=flat-square)

---

## Gallery

### Smart Photo Mosaic

<p align="center">
  <img src="assets/examples/source_portrait.jpg" width="30%" alt="Source" />
  <img src="assets/examples/mosaic_portrait_square.jpg" width="30%" alt="Square tiles" />
  <img src="assets/examples/mosaic_portrait_kite.jpg" width="30%" alt="Kite tiling" />
</p>

<p align="center">
  <em>Left: source image · Center: square tiles · Right: kite tiling</em>
</p>

<details>
<summary>🔍 Tile detail — click to expand</summary>
<p align="center">
  <img src="assets/examples/detail_square.jpg" width="45%" />
  <img src="assets/examples/detail_kite.jpg" width="45%" />
</p>
</details>

### Symbol Mosaic

<p align="center">
  <img src="assets/examples/symbol_bw.jpg" width="45%" alt="Black on white" />
  <img src="assets/examples/symbol_color.jpg" width="45%" alt="Color on white" />
</p>

<details>
<summary>🔍 Glyph detail — click to expand</summary>
<p align="center">
  <img src="assets/examples/symbol_detail.jpg" width="60%" />
</p>
</details>

### GUI Demo

<p align="center">
  <img src="assets/demo.gif" width="80%" alt="NeuroMosaic GUI demo" />
</p>

---

## Quick Start

```bash
git clone https://github.com/Piotr1686/neuromosaic.git
cd neuromosaic
pip install -r requirements.txt
python -m src.gui
```

> **GPU acceleration:** For CUDA support, install the matching [PyTorch build](https://pytorch.org/get-started/locally/) first.
> **Symbol Mosaic:** Place `.ttf` / `.otf` fonts in `assets/fonts/` before use. Free CJK fonts: [Noto Fonts](https://fonts.google.com/noto).

---

## Features

NeuroMosaic is a standalone desktop tool with two independent creative engines, both accessible from a single dark-themed GUI. Load an image, configure a handful of options, and click **Render** — the application handles the rest in a background thread while keeping the interface fully responsive.

### Smart Photo Mosaic

Reconstructs the target image by tiling it with photographs from your personal library. Matching is performed in **CIE-LAB colour space** using a 5×5 regional grid per tile, which preserves both overall hue and local colour transitions. A `cKDTree` index allows the engine to search hundreds of thousands of candidates in milliseconds.

**What you can control in the GUI:**

| Control | Options |
|---|---|
| Output resolution | 2K · 4K · 8K · **16K** |
| Tile size multiplier | 0.5 · 0.75 · 1.0 · 1.75 · 2.0 |
| Tile shape | `square` · `rectangle_3x1` · `brick_wall` · `hexagon` · `hexagon_romb` · `romb` · `triangle` · `kite` |
| Allow Mirroring | Horizontally flips tiles on the fly, doubling the effective library size without using extra disk space |
| Black Borders (Grout) | Adds a dark gap between tiles — simulates real mosaic grout lines |
| Color Blend | 0%–30% — blends the original photo over the mosaic for softer colour transitions |
| Tile Tint | 0%–40% — shifts each tile's colours toward the target sector mean for tighter colour accuracy |

The `kite` shape arranges tiles in a distinctive non-rectangular diamond geometry.

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

## Use Cases

NeuroMosaic is built for projects that demand both photographic detail *and* physical-print scale. Three scenarios where the app delivers immediate value:

### Personalised Keepsake Prints — Weddings, Anniversaries, "First Year"

Turn a portrait of a couple, a child, or a jubilarian into a 16K mosaic assembled from 2,000–5,000 of their **own** photos — phone archives, social-media exports, family albums. Printed at 100×150 cm on canvas, the portrait reads across the room, while every tile up close is a real memory.

> **Why it works:** the anti-repetition engine guarantees no single photograph dominates the composition, and the `kite` tile shape gives the print a distinctly non-rectangular, gallery-ready geometry.

### Brand & Campaign Visuals — Hero Images from Product or UGC Libraries

Build a campaign hero — logo, ambassador portrait, or key brand symbol — from a product catalogue or user-generated content (e.g. an Instagram contest). Export at 16K for billboards and annual-report covers; downscale the same render to 4K for reels, web banners, and social posts. One source render → every channel.

> **Why it works:** `Tile Tint (0–40%)` nudges tile colours toward the brand palette without erasing the recognisability of each source image; `Color Blend (0–30%)` produces a softer variant ready for use as a background layer.

### Typography Wall Art — Schools, Bookstores, Cafés, Museums

Use the Symbol Mosaic engine to compose literary or educational posters: a portrait of an author or historical figure assembled entirely from glyphs — 50,000 Hanzi forming Murakami, the letters of a sonnet forming Shakespeare. The `color_on_white` mode suits modern interiors, `black_on_white` delivers a classic editorial look.

> **Why it works:** zero library cost (fonts replace thousands of photos), CJK Unicode coverage is built in, and 16K output holds up at A0 print size and beyond.

---

## How It Works

### Smart Engine — colour matching

Every tile in the library is represented as a **75-dimensional feature vector**: a 5×5 grid of cells, each described by its mean LAB (L\*, a\*, b\*) values. This captures both the dominant colour and the spatial colour gradient across the tile. At render time a `cKDTree` finds the nearest neighbours for each sector of the target image in milliseconds, even with 300,000+ tiles indexed.

### Typo Engine — brightness matching

Each glyph is pre-rendered at the target tile size and its **normalised ink density** (fraction of dark pixels) is computed and stored. At render time the engine maps each cell's mean brightness to the closest glyph by density, then renders it in the chosen style mode.

### Anti-repetition (Smart Engine)

- **Hard constraint:** A tile's source file may not appear in any of the 4 direct neighbours of the current cell.
- **Frequency penalty:** Each use of a source file increments a global counter. The penalised score is `raw_score + (usage_count × W_FREQ)`, which continuously pushes the engine toward less-used tiles.
- Both constraints treat all mirrored variants of the same image as a single source identity.

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

## Configuration

Copy `.env.example` to `.env` and adjust values for your setup:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|---|---|---|
| `TILE_SIZE` | `75` | Base tile size in pixels |
| `TARGET_SHORT_SIDE` | `18000` | Output short side in pixels (16K ≈ 18000) |
| `USE_CUDA` | `True` | Enable CUDA GPU acceleration |
| `GHOSTING_OPACITY` | `0.25` | Overlay opacity (0.0 = pure mosaic) |
| `NUM_TILES` | `300000` | Maximum tiles loaded from index |

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

## Project Structure

```
neuromosaic/
├── src/
│   ├── gui.py              # Entry point — CustomTkinter application
│   ├── engine_smart.py     # Colour-matched photomosaic engine
│   ├── engine_typo.py      # Typography / glyph mosaic engine
│   ├── indexer_smart.py    # Builds data/smart_index.pkl
│   ├── indexer_typo.py     # Builds data/typo_index.pkl
│   ├── ai_core.py          # [Legacy] MiDaS depth model — retained for future depth-aware features
│   ├── downloader.py       # Async public-domain image fetcher
│   ├── optimizer.py        # Image normalisation & cleanup
│   └── config.py           # Settings dataclass (reads .env)
├── assets/
│   ├── fonts/              # Place .ttf / .otf fonts here
│   └── examples/           # Example mosaics and source images
├── data/
│   ├── library_public/tiles/
│   └── library_private/tiles/
├── tests/
├── .env.example            # Configuration template
├── .gitignore
├── CONTRIBUTING.md
├── Makefile
└── requirements.txt
```

---

## Requirements

- Python 3.10+
- PyTorch (CPU or CUDA)
- `customtkinter`, `Pillow`, `numpy`, `scipy`, `scikit-image`, `tqdm`

Full list: `requirements.txt`

---

## Performance

Benchmarked on: i5-12500H · RTX 3050 Laptop 4 GB · 32 GB DDR4

| Operation | GPU (CUDA) | CPU only |
|---|---|---|
| Index 10,000 tiles | — s | — s |
| Index 50,000 tiles | — s | — s |
| Render 4K · square tiles | — s | — s |
| Render 8K · hexagon tiles | — s | — s |
| Render 16K · kite tiles | — s | — s |
| Symbol mosaic 8K · B&W | — s | — s |
| Peak VRAM | — GB | N/A |
| Peak RAM | — GB | — GB |

> Values marked with — are placeholders. Run `python -m tests.benchmark` to generate values for your hardware.

---

## Development History

NeuroMosaic grew from an iterative design conversation that explored several approaches before arriving at the current architecture:

- **v1–v2:** Semantic matching with OpenAI CLIP (ViT-B/32) — perceptually aware but colour-inaccurate.
- **v3–v4:** Hybrid CLIP + RGB scoring with VGG-19 structural analysis and tile transformations (mirroring, 90°/180°/270° rotation).
- **v5 (current):** Replaced learned embeddings with direct LAB colour matching. This eliminated the GPU memory bottleneck of large neural models while producing sharper colour fidelity. The 5×5 LAB grid preserves the spatial structure awareness that motivated the earlier VGG approach.

Each iteration kept the anti-repetition logic and the multi-shape tile geometry, which remain the most distinctive aspects of the engine.

---

## Roadmap

- [ ] Real-time mosaic preview in GUI (downscaled)
- [ ] Tile library browser with visual search
- [ ] CLI mode for batch processing
- [ ] Export to SVG (symbol mosaic)
- [ ] Plugin system for custom tile shapes

---

## Contributing

Contributions, issues, and feature requests are welcome.
See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

---

## Acknowledgements

- [Art Institute of Chicago API](https://api.artic.edu/) — public domain artwork for the default tile library
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — modern dark-themed GUI framework

---

## License

MIT — use it, fork it, build on it.
