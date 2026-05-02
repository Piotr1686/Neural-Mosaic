# Changelog

All notable changes to Neural-Mosaic are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [5.0.0] — 2026-04 — Initial public release

### Added

- 5×5 feature grid (75-dim LAB descriptors) replacing the earlier 3×3 (27-dim) grid
- Color Blend post-processing (0–30%) — blends source photo over mosaic for softer transitions
- Tile Tint post-processing (0–40%) — pixel-wise lerp shifts tile colours toward target sector mean
- Multi-source tile downloader (Openverse + Met Museum + Art Institute + NASA + Cleveland + Wikimedia) with polite rate-limiting and per-source delays
- Perceptual-hash deduplication (`imagehash.phash`, Hamming < 5) to avoid near-duplicate tiles
- Quality filter (blur detection + uniform-colour rejection replacing old `img.resize(1,1)` heuristic)
- Sanity check tool (`src/tools/sanity_check.py`)
- Deep Zoom viewer on GitHub Pages (OpenSeadragon, keyboard: `1`/`2` switch, `H` reset, `F` fullscreen)
- Architecture diagram (`docs/ARCHITECTURE.md` with Mermaid)
- Showcase mosaics at 16K (photo: square, triangle, hexagon) and 8K (symbol)
- `make_showcase.py` helper — renders + crops detail and preview images from a 16K output
- `make_dzi.py` + `make_all_tiles.py` — Deep Zoom Image pyramid builder for GitHub Pages viewer

### Added — Symbol Mosaic

- Thematic font grouping: 7 groups (CJK, Ancient, Symbols, Latin Clean/Mono, Decorative, Handwriting, Other) covering 120 fonts
- New `color_on_black` mode with HLS lightness boost
- HLS clamping for `color_on_white` — ensures dark colours remain readable on white background
- Palette size control (8 / 16 / 32 / Full) for colour quantisation
- Variation control (5 / 20 / 50) — glyph selection randomness
- `--full-cjk` flag for the indexer (complete CJK Unified Ideographs block)
- Scrollable tab layout — RENDER button always pinned and visible regardless of window height
- Full IBM Plex Mono family (14 weights + italics) for fine ink-density matching

### Changed

- Hard blocks rendering when index schema mismatches (was: WARNING, continued anyway)
- Library tile count now aggregates all `LIBRARY_DIRS` (public + private)
- Colour saturation enhancement reduced from 2.5× → 1.3× (previous value was overly aggressive)
- `gui.py` now calls `load_dotenv()` directly — config settings are applied even without importing `config.py` first

### Removed

- Flickr integration (API key now requires a paid account)
- Library of Congress fetcher (was never implemented)
- CLIP / VGG-based semantic matching (replaced by direct 5×5 LAB colour matching for better colour fidelity and lower VRAM usage)
