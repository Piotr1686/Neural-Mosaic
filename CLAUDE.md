# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neural-Mosaic is a standalone Python AI app that generates photomosaics up to 16K resolution. The GUI offers two modes: **Smart Photo Mosaic** (color-based, LAB color space) and **Symbol Mosaic** (typography/font-based).

## Environment & Setup

- **Python 3.10 via conda** — always use the conda environment
- **GPU:** RTX 3050 Laptop, 4GB VRAM
- **RAM:** 32GB DDR4

```bash
# Run the GUI (customtkinter) — sole entry point
python -m src.gui

# Build tile dataset (async downloader)
python -m src.fast_downloader

# Run tests
pytest tests/

# Run a single test
pytest tests/test_processor.py::test_cuda_availability
```

## Architecture

**Entry point:** `src/gui.py` — customtkinter GUI with two tabs:
- **Smart Photo Mosaic** — uses `SmartEngine`, requires `data/smart_index.pkl`
- **Symbol Mosaic (Typo)** — uses `TypoEngine`, requires `data/typo_index.pkl`

**Engines:**
- `src/engine_smart.py` — color photo mosaic; matches tiles via 3x3 LAB grid features + `cKDTree`; loads from `data/smart_index.pkl`
- `src/engine_typo.py` — font/symbol mosaic; renders glyphs as tiles; loads from `data/typo_index.pkl`
- `src/ai_core.py` — Singleton for MiDaS DPT_Hybrid (depth estimation), lazy-loaded

**Indexers** (must be run before first use, or via GUI buttons):
```bash
python -m src.indexer_smart   # produces data/smart_index.pkl  (3x3 LAB features)
python -m src.indexer_typo    # produces data/typo_index.pkl   (font glyph analysis)
```

**Data flow:**
- `Config` (`src/config.py`) — `@dataclass` instance `settings`, reads from `.env`. Key fields: `TILE_SIZE=75`, `TARGET_SHORT_SIDE=18000`, `USE_CUDA=True`
- Tile library: `data/library_public/tiles/` (public domain art) or `data/library_private/tiles/`
- Fonts: `assets/fonts/`

## Conventions

- **Always write full files** — never use `# rest unchanged` or partial edits
- `pathlib.Path` everywhere — no raw string paths
- `logging.getLogger(__name__)` in all modules; `logging.basicConfig` only in entry points
- `os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"` must be set before torch imports in entry points
