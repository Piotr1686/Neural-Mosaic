# Neural-Mosaic

**English** · [Polski](README.pl.md)

> Turn any photograph into a high-resolution mosaic — assembled from thousands of real images or typographic glyphs. Desktop app, renders up to 16K, with manual on-demand preview.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white&color=3776AB)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1a1a2e?style=flat-square)
![Resolution](https://img.shields.io/badge/Output-up%20to%2016K-orange?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows)
![Last Commit](https://img.shields.io/github/last-commit/Piotr1686/Neural-Mosaic?style=flat-square)
![Repo Size](https://img.shields.io/github/repo-size/Piotr1686/Neural-Mosaic?style=flat-square)
![CI](https://github.com/Piotr1686/Neural-Mosaic/actions/workflows/ci.yml/badge.svg)

<p align="center">
  <img src="assets/examples/spectre_full.jpg" width="80%" alt="Neural-Mosaic — spectre tiling with black grout" />
</p>
<p align="center">
  <em>A single photograph, rebuilt from thousands of others — here on the chiral aperiodic <strong>spectre</strong> monotile with black grout.</em>
</p>

---

## Table of Contents

- [Live Demo](#live-demo)
- [Gallery](#gallery)
- [Quick Start](#quick-start)
- [Features](#features)
- [Tech Highlights](#tech-highlights)
- [Use Cases](#use-cases)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Building the Tile Library](#building-the-tile-library)
- [Configuration](#configuration)
- [Workflow Inside the GUI](#workflow-inside-the-gui)
- [CLI Usage](#cli-usage)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Performance](#performance)
- [Print Size Guide](#print-size-guide)
- [Development History](#development-history)
- [Roadmap](#roadmap)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [Author](#author)
- [License](#license)

---

## Live Demo

**[Open the Interactive Viewer](https://piotr1686.github.io/Neural-Mosaic/)** — zoom into 8K mosaics right in your browser (OpenSeadragon · keyboard: `1`/`2` switch · `H` reset · `F` fullscreen).

---

## Gallery

### Smart Photo Mosaic — one portrait, many tile geometries

<p align="center">
  <img src="assets/examples/source_portrait.jpg" width="30%" alt="Source" />
  <img src="assets/examples/mosaic_portrait_square.jpg" width="30%" alt="Square tiles" />
  <img src="assets/examples/mosaic_portrait_triangle.jpg" width="30%" alt="Triangle tiling" />
</p>
<p align="center"><em>Left: source image · Center: square tiles · Right: triangle tiling</em></p>

<p align="center">
  <img src="assets/examples/mosaic_portrait_hexagon.jpg" width="44%" alt="Hexagon tiling" />
  <img src="assets/examples/mosaic_portrait_kite.jpg" width="44%" alt="Kite tiling" />
</p>
<p align="center"><em>Left: hexagon (honeycomb) · Right: kite — a non-rectangular diamond geometry on a hexagonal grid</em></p>

<details>
<summary>🔍 Tile detail — click to expand</summary>
<p align="center">
  <img src="assets/examples/detail_square.jpg" width="30%" />
  <img src="assets/examples/detail_triangle.jpg" width="30%" />
  <img src="assets/examples/detail_hexagon.jpg" width="30%" />
</p>
<p align="center">
  <img src="assets/examples/detail_kite.jpg" width="30%" />
  <img src="assets/examples/detail_spectre.jpg" width="30%" />
</p>
</details>

### Spectre monotile + black grout — progressive zoom

The **spectre** is the chiral aperiodic monotile ([Smith, Myers, Kaplan, Goodman-Strauss, 2023](https://arxiv.org/abs/2305.17743)) — a 14-sided shape that tiles the plane in a pattern that *never repeats*. Black grout makes the geometry legible: step in and every tile resolves into a separate photograph.

<table>
  <tr>
    <td align="center"><b>Full mosaic</b><br><img src="assets/examples/spectre_full.jpg" width="320" alt="Spectre full"></td>
    <td align="center"><b>Zoom ×2.5</b><br><img src="assets/examples/spectre_zoom1.jpg" width="320" alt="Spectre mid zoom"></td>
    <td align="center"><b>Zoom — single tiles</b><br><img src="assets/examples/spectre_zoom2.jpg" width="320" alt="Spectre extreme zoom"></td>
  </tr>
</table>
<p align="center"><em>16K render · spectre monotile · black grout · 15% tile tint.</em></p>

### Output resolution comparison — same source, same tile shape

<table>
  <tr>
    <td align="center"><b>2K</b> — 1920 × 1080 px<br><img src="assets/examples/res_2K.jpg" width="420" alt="2K mosaic"></td>
    <td align="center"><b>4K</b> — 3840 × 2160 px<br><img src="assets/examples/res_4K.jpg" width="420" alt="4K mosaic"></td>
  </tr>
  <tr>
    <td align="center"><b>8K</b> — 7680 × 4320 px<br><img src="assets/examples/res_8K.jpg" width="420" alt="8K mosaic"></td>
    <td align="center"><b>16K</b> — 15360 × 8640 px<br><img src="assets/examples/res_16K.jpg" width="420" alt="16K mosaic"></td>
  </tr>
</table>
<p align="center"><em>Tile size 75 px — higher resolution means more tiles and finer detail. Square (mirrored) shape, blend 20%, tint 20%.</em></p>

### Symbol Mosaic — the same photo, seven font groups

The typographic engine rebuilds an image from glyphs whose **ink density** matches the local brightness. Every font group produces a distinct aesthetic — from CJK and clean monospace to **Egyptian hieroglyphs**, mathematical symbols and emoji.

<p align="center">
  <img src="assets/examples/typo_matrix_groups.jpg" width="92%" alt="Symbol mosaic — font group comparison" />
</p>
<p align="center"><em>Same source, six of the seven font groups · 16K · black-on-white. (The seventh group, <em>Other / uncategorized</em>, is omitted here.)</em></p>

<p align="center">
  <img src="assets/examples/typo_glyph_detail.jpg" width="92%" alt="Glyph close-up: CJK, hieroglyphs/cuneiform, handwriting" />
</p>
<p align="center"><em>Same region up close — CJK, ancient scripts and handwriting. Every glyph is fully formed (no ".notdef" tofu boxes), even cuneiform and hieroglyphs.</em></p>

### Symbol Mosaic — font size vs. legibility

<p align="center">
  <img src="assets/examples/typo_matrix_size.jpg" width="92%" alt="Symbol mosaic — font size comparison" />
</p>
<p align="center"><em>Smaller glyphs pack denser detail; larger glyphs stay individually readable. 16K · black-on-white.</em></p>

<p align="center">
  <img src="assets/examples/symbol_zoom.gif" width="70%" alt="Symbol mosaic zoom-in" />
</p>
<p align="center"><em>Glyphs resolve into recognisable characters as you zoom in — 16K output, black-on-white mode.</em></p>

### Symbol Mosaic — two style modes

The same render in both style modes. `black_on_white` reads as classic editorial; `white_on_black` suits dark modern interiors. Toggle it from the GUI or with `--mode` on the CLI.

<p align="center">
  <img src="assets/examples/typo_mode_compare.jpg" width="92%" alt="Symbol mosaic — black-on-white vs white-on-black" />
</p>
<p align="center"><em>Identical photo and font group (Latin monospace) — only the style mode differs. 8K.</em></p>

### GUI Demo

<p align="center">
  <img src="assets/demo.gif" width="80%" alt="Neural-Mosaic GUI demo" />
</p>

---

## Quick Start

```bash
git clone https://github.com/Piotr1686/Neural-Mosaic.git
cd Neural-Mosaic
pip install -r requirements.txt
python -m src.gui
```

> **GPU note:** the mosaic engines run entirely on **CPU** — no GPU is required. PyTorch is only used by an optional, currently-dormant depth module; install the matching [PyTorch build](https://pytorch.org/get-started/locally/) only if you plan to experiment with it.
>
> **Fonts for the Symbol Mosaic are bundled** in `assets/fonts/` — nothing to download. To add your own, drop `.ttf` / `.otf` files there and re-scan from the GUI.

---

## Features

Neural-Mosaic is a standalone desktop tool with two independent creative engines, both reachable from a single dark-themed GUI plus a headless CLI. Load an image, configure a handful of options, and click **Render** — the work runs in a background thread while the interface stays responsive.

### Smart Photo Mosaic

Reconstructs the target image by tiling it with photographs from your library. Matching is done in **CIE-LAB colour space** using a 5×5 regional grid per tile (75 dimensions), which preserves both overall hue and local colour transitions. A `cKDTree` index searches hundreds of thousands of candidates in milliseconds.

| Control | Options |
|---|---|
| Output resolution | 2K · 4K · 8K · **16K** |
| Tile size multiplier | 0.5 · 0.75 · 1.0 · 1.75 · 2.0 |
| Tile shape | `square` · `rectangle_3x1` · `brick_wall` · `hexagon` · `hexagon_romb` · `romb` · `triangle` · `kite` · `spectre` |
| Allow Mirroring | Horizontally flips tiles on the fly, doubling the effective library without using extra disk |
| Black Borders (Grout) | Adds a dark gap between tiles — simulates real mosaic grout lines |
| Color Blend | 0%–30% — blends the original photo over the mosaic for softer transitions |
| Tile Tint | 0%–40% — shifts each tile toward the target sector mean for tighter colour accuracy |

The **`kite`** shape arranges tiles as diamonds on a flat-topped hexagonal grid. The **`spectre`** shape tiles the image with the strictly chiral aperiodic monotile — see [Tech Highlights](#tech-highlights).

**Anti-repetition system.** A neighbour constraint discourages any tile from the same source image touching itself, combined with a frequency penalty that grows as a tile is reused. Together they stop any single photograph from dominating the composition (details in [How It Works](#how-it-works)).

### Symbol Mosaic (Typo)

Reconstructs the target using typographic glyphs instead of photographs. Each cell is replaced by a character whose **normalised ink density** best matches the local brightness. The glyph set spans **seven font groups** and a wide range of Unicode scripts.

| Control | Options |
|---|---|
| Output resolution | 4K · 8K · **16K** |
| Symbol size multiplier | 0.5 · 0.75 · 1.0 · 1.75 · 2.0 |
| Style mode | `black_on_white` · `white_on_black` |
| Font groups | CJK · Ancient · Symbols · Latin · Decorative · Handwriting · Other |

Font scanning is one click in the GUI (or `python -m src.indexer_typo`). All bundled fonts live in `assets/fonts/` under the SIL Open Font License 1.1 or Apache License 2.0 (texts in `assets/fonts/licenses/`).

| Group | `--font-groups` code | Scripts / fonts |
|---|---|---|
| **CJK** | `A_cjk` | Noto Sans/Serif JP·SC·KR·TC, Sawarabi Mincho, M PLUS — Hanzi, Kana, Hangul |
| **Ancient & Exotic** | `B_ancient` | Egyptian & Anatolian hieroglyphs, cuneiform, Linear A/B, Phoenician, runic, Ogham, … |
| **Symbols & Geometric** | `C_symbols` | Noto Math, Music, Emoji, Symbols, Yarndings |
| **Latin Clean** | `D_latin_clean` | Noto Sans, IBM Plex Mono, JetBrains Mono, Inconsolata, Space Mono |
| **Decorative / Display** | `E_decorative` | Creepster, Monoton, Matemasie, Bitcount, Danfo, Splash |
| **Handwriting / Script** | `F_handwriting` | Dancing Script, Sacramento, Tangerine, Allura, Pinyon |
| **Other** | `G_uncategorized` | Arabic, Bengali, Sinhala, Amiri, Tajawal |

### Tile Library Browser

The **Tile Library** tab lets you inspect, filter and curate the collection before rendering.

| Feature | Details |
|---|---|
| Thumbnail grid | Lazy-loaded 120 px previews, paginated (200 per page, "Load More"), cached on first load |
| Filters | **Lightness** (Dark / Mid / Bright), **Texture** (Flat / Textured), **Filename** substring |
| Sort | Name A–Z / Z–A, Newest first, Oldest first |
| LAB Coverage Map | matplotlib popup: a\*–b\* hex-bin gamut coverage + PCA diversity scatter for the full index |
| Tile selection | Click any tile to mark it (purple highlight); click again to deselect |
| Export Bad Tiles | Saves selected filenames to `data/library_*/excluded.txt` — idempotent, safe to re-run |

`excluded.txt` is read by future index rebuilds to skip known-bad tiles without deleting the originals.

### Manual Preview

Both the **Smart Photo Mosaic** and **Symbol Mosaic** tabs have a preview pane on the right. The preview is **on-demand**: configure your options, then click **Generate Preview**. There are no automatic triggers — nothing renders until you ask for it.

- Preview resolution: 512 px on the short edge (fast; the full-resolution render is unaffected)
- Rapid repeat clicks are debounced (300 ms) so only the final request renders
- The button is enabled once both an input image and an index are loaded

---

## Tech Highlights

A few parts of this project were genuinely non-trivial to build:

- **Aperiodic spectre tiling from scratch.** The `spectre` shape cannot sit on any regular grid, so the engine ports the authors' nine-metatile substitution system (Γ Δ Θ Λ Ξ Π Σ Φ Ψ, including the Γ "mystic" pair) to compute the exact tiling, then places one photograph per tile — every spectre with the same handedness, no reflections. See `src/spectre_tiling.py`.
- **Non-convex tile masking.** Kite and spectre tiles are non-rectangular; the engine renders each photo into a polygon mask and mean-fills the outside so neighbouring content never leaks across tile borders.
- **Density-matched typography across 44 Unicode blocks.** The typo indexer renders every supported glyph, measures its ink density, and skips undefined codepoints via the font's `cmap` so no ".notdef" tofu boxes scatter through the output — making even hieroglyph- and cuneiform-only mosaics readable.
- **Concurrency-safe live preview.** A generation-token scheme plus a double-checked lock on the neighbour-adjacency cache keep background preview renders race-free.

---

## Use Cases

Neural-Mosaic is built for projects that need both photographic detail *and* physical-print scale.

### Personalised Keepsake Prints — weddings, anniversaries, "first year"

Turn a portrait into a 16K mosaic assembled from 2,000–5,000 of someone's **own** photos — phone archives, social exports, family albums. Printed at 100×150 cm on canvas, the portrait reads across the room while every tile up close is a real memory.

> **Why it works:** the anti-repetition engine guarantees no single photograph dominates, and the `kite` shape gives the print a gallery-ready, non-rectangular geometry.

### Brand & Campaign Visuals — hero images from product or UGC libraries

Build a campaign hero — logo, ambassador portrait, key symbol — from a product catalogue or user-generated content. Export at 16K for billboards and report covers; downscale the same render to 4K for reels and web. One render → every channel.

> **Why it works:** `Tile Tint (0–40%)` nudges tiles toward the brand palette without erasing each source image; `Color Blend (0–30%)` produces a softer variant for background layers.

### Typography Wall Art — schools, bookstores, cafés, museums

Compose literary or educational posters with the Symbol Mosaic engine: an author's portrait built from glyphs — Hanzi forming Murakami, the letters of a sonnet forming Shakespeare, or hieroglyphs forming a pharaoh. `black_on_white` reads as classic editorial; `white_on_black` suits dark modern interiors.

> **Why it works:** zero library cost (fonts replace thousands of photos), seven font families from CJK to ancient scripts, and 16K output that holds up at A0 and beyond.

---

## How It Works

### Smart Engine — colour matching

Every tile is a **79-dimensional feature vector**: a 5×5 grid of cells described by their mean LAB (L\*, a\*, b\*) values (75 dims) plus four edge-luminance features. This captures the dominant colour, the spatial colour gradient and local edge structure. At render time a `cKDTree` finds the nearest tiles for each sector of the target in milliseconds, even with 400,000+ tiles indexed. The index is **always** built at 79 dimensions; the `--edge-aware` flag only switches whether the four edge features are *used* during matching (mutually exclusive with mirroring) — it does not change how the index is built.

### Typo Engine — brightness matching

Each glyph is pre-rendered and its **normalised ink density** (fraction of dark pixels) stored. At render time the engine maps each cell's mean brightness to the closest glyph by density, picks one at random from a small window around that density for variety, and draws it in the chosen style mode.

### Anti-repetition (Smart Engine)

- **Neighbour constraint:** for every tile, the engine collects the tiles already placed within a radius of ~1.5× the tile spacing and adds a very large penalty (effectively forbidding) to reusing the same *source file* among them.
- **Frequency penalty:** each use of a source file increments a counter; the score becomes `distance + used_count² × freq_penalty × 0.001` (`freq_penalty = 30.0` by default), so popular tiles grow progressively more expensive — a quadratic, self-balancing pressure toward variety.
- Both rules treat all mirrored variants of an image as a single source identity.

---

## Architecture

```mermaid
flowchart LR
    DL["Downloader<br/>Picsum · LoremFlickr · Openverse"] --> LIB["Tile Library<br/>data/library_*/tiles"]
    LIB --> IDX["Indexer<br/>5x5 LAB → 75-dim"]
    IDX --> SPKL[("smart_index.pkl")]
    FON["Fonts<br/>assets/fonts"] --> TIDX["Typo Indexer<br/>glyph ink density"]
    TIDX --> TPKL[("typo_index.pkl")]
    SPKL --> SE["SmartEngine<br/>cKDTree match"]
    TPKL --> TE["TypoEngine<br/>brightness match"]
    SRC["Source image"] --> SE
    SRC --> TE
    SE --> OUT["Mosaic — up to 16K"]
    TE --> OUT
```

Full module dependency graph: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Building the Tile Library

Two downloaders are provided, depending on what you need.

**Quick & varied (no API key):**

```bash
python -m src.fast_downloader
```

Fetches free photos from **Picsum Photos** and **LoremFlickr** (keyword-rotated for variety) into `data/tiles/`. Fast, no registration, great for getting started.

**Curated CC0 / public-domain (museum sources):**

```bash
python -m src.downloader_v2
```

A polite, multi-source downloader pulling Creative-Commons-Zero and public-domain artwork from **Openverse** (primary), the **Metropolitan Museum** and the **Art Institute of Chicago**, in `starter` / `public` / `extended` tiers. An Openverse API key (optional, raises rate limits) goes in `.env` — see `.env.example`.

After downloading, normalise sizes and drop corrupt files:

```bash
python -m src.optimizer
```

Drop your own photos straight into `data/library_private/tiles/` — they are indexed alongside the rest with no extra steps.

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `TILE_SIZE` | `75` | Base tile size in pixels |
| `TARGET_SHORT_SIDE` | `18000` | Legacy/downloader hint. **The render resolution is fixed by the `--res` preset, not this value** — the Smart engine ignores it |
| `USE_CUDA` | `True` | Reserved for the optional depth module; the mosaic engines are CPU-only |
| `GHOSTING_OPACITY` | `0.25` | Overlay opacity for the optional ghosting pass (0.0 = pure mosaic) |
| `NUM_TILES` | `300000` | **Download target** for the downloader only — *not* a cap on the indexer or engine, which process every tile they find |
| `OPENVERSE_CLIENT_ID` / `_SECRET` | empty | Optional Openverse API credentials for `downloader_v2` |

---

## Workflow Inside the GUI

### Smart Photo Mosaic

1. **Sidebar → "Update / Create Index"** — scans `data/library_public/tiles/` (and `data/library_private/tiles/` if present) and builds `data/smart_index.pkl`. Run once after adding photos; later loads take seconds.
2. **Sidebar → "Load Smart Index"** — loads the pre-built index into memory.
3. **Tab: Smart Photo Mosaic** — select the input image, choose resolution, tile shape and options. Click **Generate Preview** to see a 512 px proof.
4. **Sidebar → "Set Output Folder"** + optionally a **Project Name**.
5. Click **RENDER SMART MOSAIC**. Progress is logged live in the sidebar console. The file is saved as `<ProjectName>_Smart_<timestamp>.jpg`.

### Symbol Mosaic (Typo)

1. **Tab: Symbol Mosaic → "Update Database (Scan Assets)"** — indexes every font in `assets/fonts/`. Run once after adding fonts.
2. **"Load Typo Index (Fast)"** — loads the font index; the status label shows how many symbols are ready.
3. Select the input image, choose resolution, symbol size, font groups and style mode. Click **Generate Preview** for a proof.
4. Click **RENDER SYMBOL MOSAIC**. The file is saved as `<ProjectName>_Symbol_<timestamp>.png`.

### Tile Library

1. **Tab: Tile Library → Refresh** — scans all library directories and loads thumbnails lazily (paginated; cached in `data/.thumbs/`).
2. Filter by **Lightness**, **Texture** or filename substring. The counter shows matches out of the total.
3. Click **LAB Coverage Map** for the colour-gamut + PCA-diversity popup.
4. Click tiles to **select** (purple highlight). With at least one selected, **Export Bad Tiles...** becomes active and appends them to `data/library_*/excluded.txt` (idempotent).

---

## CLI Usage

For headless rendering, scripted pipelines or batch jobs, Neural-Mosaic ships a CLI in `src/cli.py`. Both engines and all options are exposed; prerequisites (a built index and a tile/font library) are the same as the GUI.

### `render` — single image

```bash
# Smart photo mosaic at 8K, default square tiles
python -m src.cli render input/portrait.jpg --engine smart --res 8K

# Smart mosaic at 16K with hexagon tiles, soft blend, mirror disabled
python -m src.cli render input/portrait.jpg --engine smart --res 16K \
  --shape hexagon --blend 0.2 --tint 0.15 --no-mirror

# Symbol mosaic at 8K, white-on-black, restricted to CJK + Symbol fonts
python -m src.cli render input/portrait.jpg --engine typo --res 8K \
  --mode white_on_black --font-groups A_cjk C_symbols
```

Outputs default to `output/<stem>_<engine>_<res>_<timestamp>.{jpg|png}`. Override with `--output PATH`.

### `batch` — whole folder, idempotent

```bash
# Render every *.jpg in ./input/ to ./output/ at 4K
python -m src.cli batch ./input ./output --engine smart --res 4K

# Custom glob pattern
python -m src.cli batch ./input ./output --engine smart --res 8K --pattern '*.png'
```

Batch output names are **timestamp-free** — `{stem}_{engine}_{res}_{shape|mode}.ext` — so re-running the same command skips already-rendered files. Failed renders are logged and the run exits with code `1`.

### Common options

| Option | Engine | Default | Notes |
|---|---|---|---|
| `--engine {smart,typo}` | both | required | Which renderer to use |
| `--res {2K,4K,8K,16K}` | both | `8K` | Output resolution |
| `--index PATH` | both | `data/<engine>_index.pkl` | Override index location |
| `--shape SHAPE` | smart | `square` | `square` · `rectangle_3x1` · `brick_wall` · `hexagon` · `hexagon_romb` · `romb` · `triangle` · `kite` · `spectre` |
| `--scale FLOAT` | both | `1.0` | Tile/glyph size multiplier (0.5–2.0) |
| `--blend FLOAT` | smart | `0.0` | Original-over-mosaic blend, 0.0–0.3 |
| `--tint FLOAT` | smart | `0.0` | Tile tint toward sector colour, 0.0–0.4 |
| `--border` | smart | off | Add dark grout lines between tiles |
| `--no-mirror` | smart | mirror on | Disable horizontal tile mirroring |
| `--edge-aware` | smart | off | Use the 4 edge-luminance features when matching (index is always 79-dim; mutually exclusive with mirroring) |
| `--mode {black_on_white,white_on_black}` | typo | `black_on_white` | Symbol render mode |
| `--font-groups GROUP ...` | typo | all | Subset: `A_cjk` · `B_ancient` · `C_symbols` · `D_latin_clean` · `E_decorative` · `F_handwriting` · `G_uncategorized` |
| `--variation INT` | typo | `20` | Glyph density window |
| `--verbose` | both | off | Debug-level logging |

Logs go to `logs/cli.log` as well as stdout. Run `python -m src.cli --help` (or `render --help` / `batch --help`) for the full reference.

---

## Project Structure

```
Neural-Mosaic/
├── src/
│   ├── gui.py              # Entry point — CustomTkinter app (3 tabs)
│   ├── engine_smart.py     # Colour-matched photomosaic engine (LAB + cKDTree)
│   ├── engine_typo.py      # Typography / glyph mosaic engine
│   ├── spectre_tiling.py   # Aperiodic spectre monotile substitution system
│   ├── preview.py          # PreviewRenderer — 300 ms debounced background render
│   ├── cli.py              # Headless CLI: render + batch subcommands
│   ├── indexer_smart.py    # Builds data/smart_index.pkl
│   ├── indexer_typo.py     # Builds data/typo_index.pkl
│   ├── font_groups.py      # Font group definitions for the typo engine
│   ├── library_dirs.py     # Single source of truth for tile library paths
│   ├── fast_downloader.py  # Quick downloader (Picsum + LoremFlickr)
│   ├── downloader_v2.py    # Polite CC0/PD downloader (Openverse, Met, Art Institute)
│   ├── optimizer.py        # Image normalisation & cleanup
│   ├── ai_core.py          # MiDaS depth model (retained for future depth-aware features)
│   └── config.py           # Settings dataclass (reads .env)
├── assets/
│   ├── fonts/              # Bundled .ttf / .otf fonts (+ licenses/)
│   └── examples/           # Gallery images
├── data/
│   ├── library_public/tiles/
│   ├── library_private/tiles/
│   └── .thumbs/            # Thumbnail cache (runtime, not in repo)
├── tests/
├── .env.example
├── CONTRIBUTING.md
├── Makefile
└── requirements.txt
```

---

## Requirements

- Python 3.10+
- `customtkinter`, `Pillow`, `numpy`, `scipy`, `scikit-image`, `scikit-learn`, `matplotlib`, `fonttools`, `tqdm`
- PyTorch (optional — only for the dormant depth module)

Full list: `requirements.txt`.

---

## Performance

Benchmarked on: **i5-12500H · 32 GB DDR4** (the engines run on CPU; no GPU is used). Reproduce with `python -m tests.benchmark`.

<!-- BENCHMARK:START -->
| Operation | Time |
|---|---|
| Index 10,000 tiles | 31 s |
| Index 50,000 tiles | 1.6 min |
| Render 4K · square tiles | 38 s |
| Render 8K · hexagon tiles | 2.8 min |
| Render 16K · kite tiles | 21 min |
| Symbol mosaic 8K · black-on-white | 21 s |
<!-- BENCHMARK:END -->

> A single "Time" column is intentional — both engines run on CPU, so there is no separate GPU path. 16K with a non-convex shape (kite/spectre) is the heavy extreme; rectangular shapes and lower resolutions are far faster.
>
> **Memory:** peak RAM scales with output resolution. 4K/8K renders stay around ~1 GB; a 16K render holds the full canvas in memory and peaks at roughly ~10 GB (non-convex shapes are the heaviest).

---

## Print Size Guide

Maximum recommended print dimensions per resolution, at two common DPI settings (Smart engine pixel dimensions; the Symbol engine uses a comparable budget).

| Resolution | Pixels | @ 300 DPI (photo quality) | @ 150 DPI (large format) | Best for |
|---|---|---|---|---|
| **16K** | 15360 × 8640 | 130 × 73 cm | 260 × 146 cm | Billboard, large canvas, A0+ poster |
| **8K** | 7680 × 4320 | 65 × 37 cm | 130 × 73 cm | A1 poster, medium canvas |
| **4K** | 3840 × 2160 | 33 × 18 cm | 65 × 37 cm | A3 framed print |
| **2K** | 1920 × 1080 | 16 × 9 cm | 33 × 18 cm | A5 insert, digital display |

> Portrait orientations swap width and height. Symbol Mosaic supports 4K / 8K / 16K; Smart Photo Mosaic supports all four.

---

## Development History

Neural-Mosaic went through several approaches before settling on the current architecture:

- **v1–v2:** Semantic matching with OpenAI CLIP (ViT-B/32) — perceptually aware but colour-inaccurate.
- **v3–v4:** Hybrid CLIP + RGB scoring with VGG-19 structural analysis and tile transforms (mirror, rotations).
- **v5 (current):** Replaced learned embeddings with direct LAB colour matching. This removed the GPU-memory bottleneck of large neural models while producing sharper colour fidelity; the 5×5 LAB grid preserves the spatial-structure awareness that motivated the VGG approach.

Each iteration kept the anti-repetition logic and the multi-shape tile geometry — the most distinctive parts of the engine.

---

## Roadmap

- [x] Manual on-demand preview in the GUI — 512 px short edge, both tabs
- [x] Tile library browser — thumbnail grid, LAB coverage map, tile selection & exclusion export
- [x] CLI mode for batch processing — see [CLI Usage](#cli-usage)
- [x] Real (non-ASCII) script support across all seven font groups — hieroglyphs, cuneiform, math, emoji, Arabic/Bengali/Sinhala
- [ ] Export to deep-zoom (DZI) with excluded-tile support
- [ ] Plugin system for custom tile shapes

---

## Known Limitations

- 16K rendering holds the full canvas in memory; a 16K spectre render peaks around ~10 GB RAM (square/hexagon are lighter). Output is not chunked yet.
- The GUI is Windows-focused. CustomTkinter runs on Linux/macOS, but font handling and file-path assumptions target Windows.
- Tile Tint uses pixel-wise lerp in RGB space. A LAB-space variant is on the roadmap; the current RGB version produces visible, predictable results.
- The hosted Deep Zoom viewer carries a handful of 8K mosaics (kept lightweight for GitHub Pages storage limits).
- The `downloader_v2` CC0/PD filter trusts source metadata — rare false positives on user-uploaded content are reported upstream.
- The repository is ~250 MB (≈120 MB bundled font library + git history); the fonts are committed for zero-friction Symbol Mosaic setup. Initial clone takes a minute or two on a typical connection.

---

## Troubleshooting

**Q: `downloader_v2` returns 429 Too Many Requests**
A: Wait ~1 hour. The `starter` tier works without a key; for `public` / `extended` register an Openverse key (see `.env.example`). The `fast_downloader` (Picsum/LoremFlickr) needs no key.

**Q: 16K render fails or crashes**
A: Close other applications and ensure several GB of free RAM (a 16K spectre can need ~10 GB). As an alternative, render at 8K.

**Q: WARNING about an incompatible index**
A: Click **"Update / Create Index"** in the GUI to rebuild `smart_index.pkl` with the current feature schema (e.g. after upgrading from an older index version). Toggling `--edge-aware` does **not** require a rebuild — the index is always 79-dim.

**Q: Symbol Mosaic shows empty boxes, or a group looks empty**
A: Rebuild the font index after adding fonts or changing groups: **"Update Database (Scan Assets)"** or `python -m src.indexer_typo` (add `--full-scan` for the complete CJK + Hangul blocks).

**Q: Preview pane says "Select image and load index"**
A: Load both an input image and the index (sidebar for Smart, "Load Typo Index" for Symbol), then click **Generate Preview**.

---

## Contributing

Contributions, issues and feature requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

---

## Acknowledgements

- [Picsum Photos](https://picsum.photos/) & [LoremFlickr](https://loremflickr.com/) — quick default tile sources
- [Openverse](https://openverse.org/), [The Metropolitan Museum of Art](https://metmuseum.github.io/) & [Art Institute of Chicago](https://api.artic.edu/) — CC0 / public-domain artwork for the curated downloader
- [Google Noto Fonts](https://fonts.google.com/noto) — the bulk of the bundled glyph library
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — modern dark-themed GUI framework
- Smith, Myers, Kaplan & Goodman-Strauss — *A Chiral Aperiodic Monotile* ([arXiv:2305.17743](https://arxiv.org/abs/2305.17743))

---

## Author

**Piotr Łazowski** — [github.com/Piotr1686](https://github.com/Piotr1686)

---

## License

MIT — use it, fork it, build on it. See [LICENSE](LICENSE). Bundled fonts retain their own OFL 1.1 / Apache 2.0 licenses (`assets/fonts/licenses/`).
