# MEMORY.md — Długoterminowa pamięć projektu Neural-Mosaic

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].

---

## Architektura

[2026-04-18, zaktualizowano 2026-04-18] **SmartEngine — dopasowanie kolorowe (LAB 5×5)**
- Silnik w `src/engine_smart.py` używa 75-wymiarowego wektora cech (siatka 5×5 w przestrzeni CIELAB)
- Indeks buduje `src/indexer_smart.py` → `data/smart_index.pkl`; schema_version="5x5", feature_dim=75
- Dopasowanie przez `cKDTree` + `cdist` (euclidean), chunk_size=500, top-50 kandydatów
- Spatial anti-repetition: `cKDTree` po współrzędnych kafelka, search_radius = 1.5×base_s
- Obsługuje geometrie: square, rectangle_3x1, brick_wall, hexagon, hexagon_romb, triangle, romb, kite
- Kite geometry = 8-kite "hat" z płaskiej siatki heksagonalnej (axial coords q, r, k)
- LIBRARY_DIRS: data/library_starter/tiles, library_public, library_extended, library_private
- Blokada renderowania przy niezgodnym indeksie (hard block jeśli dim≠75 lub schema≠"5x5")
- Post-processing: Color Blend (0–30%, Image.blend) + Tile Tint (0–40%, RGB mean shift)
- WAŻNE: po zmianie 3×3→5×5 istniejący smart_index.pkl jest niekompatybilny — wymaga przebudowy!

[2026-04-18] **TypoEngine — font/symbol mosaic**
- Silnik w `src/engine_typo.py`, indeks w `data/typo_index.pkl`
- Glify renderowane PIL, dopasowanie po density (jasność)
- Grupowanie fontów: `src/font_groups.py` — 7 grup (A_cjk, B_ancient, C_symbols, D_latin_clean, E_decorative, F_handwriting, G_uncategorized)
- Tryby: black_on_white, white_on_black, color_on_white, color_on_black
- color_on_white: HLS clamping l≤0.45, s≥0.4; color_on_black: l≥0.55, s≥0.5
- Posteryzacja przez PIL quantize(MEDIANCUT) — palette_size 8/16/32/None
- Parametr variation (domyślnie 20): niższy = ostrzejszy, wyższy = organiczny

---

## Rozwiązane problemy

[2026-04-18] **color_on_white dawał prześwietlone/neonowe kolory**
- Fix 1: HLS clamping zamiast bezpośredniego RGB (colorsys.rgb_to_hls → clamp → hls_to_rgb)
- Fix 2: Saturation w _preprocess_image obniżona z 2.5 → 1.3
- Fix 3: Posteryzacja quantize(MEDIANCUT, palette_size=16) przed renderem

[2026-06-14] **Code-review całości repo — 4 fale napraw** (commity 27ba89d, 7c62ccf, d9aaf4d, 7bc6c07; 182 testy passed; na origin/main)
- Fala 1: crash `_nkey` — klucz cache sąsiadów w `engine_smart._do_render` MUSI zawierać `border_mode` (render_padding 0.94 vs 1.02 zmienia liczbę sektorów kite/spectre → IndexError przy toggle borderów); cross-thread Tk w gui (widgety z wątków zawsze przez `self.after(0,…)`); `daemon=True` na wszystkich wątkach roboczych; `sanity_check` LAB slice `[:, :75]` (indeks zawsze 79-dim); dodano `src/fast_downloader.py` (alias udokumentowanej komendy `python -m src.fast_downloader`)
- Fala 2: podgląd smart synchronizuje allow_mirror/edge_aware z checkboxów; podgląd typo używa silnika filtrowanego po grupach (cache `_typo_engine_for_groups`); `indexer_typo` pomija codepointy spoza cmap fontu (fontTools) → koniec tofu `.notdef` — **WYMAGA przebudowy `typo_index.pkl`**; `used_counts` int64 (overflow `**2`)
- Fala 3: downloadery — cap powtarzanych 401, guard pustych list data/imageinfo, sprawdzenie HTTP 206 przy resume (anty-korupcja), atomowy temp+rename; `indexer_smart` skanuje też `data/tiles`; batch skip tylko niepuste pliki; getattr-guard ścieżek w GUI
- Fala 4: `src/library_dirs.py` = single source of truth dla LIBRARY_DIRS (6 katalogów; indexer/clean_duplicates/optimizer/sanity_check importują — koniec driftu list); helper `_mean_fill_outside_mask` (dedup kite/spectre); usunięty martwy `settings["tile_size"]` i `render_sized` z obu silników
- UWAGA: `optimizer`/`clean_duplicates` pokrywają teraz pełny zestaw bibliotek; `optimizer` skaluje w miejscu

---

## Aktywne TODO (długoterminowe)

[2026-04-18] **feature/semantic-clip — CLIP semantic tile matching**
- Branch: `feature/semantic-clip`
- Cel: zamiana 3×3 LAB features w SmartEngine na CLIP embeddings (semantyczne dopasowanie)
- Status: branch UTWORZONY, ale implementacja CLIP jeszcze nie zaczęta
- Decyzja architektoniczna do podjęcia: rozszerzyć SmartEngine czy nowy SemanticEngine?

---

## Odrzucone podejścia

[2026-06-14] **Refaktory świadomie odłożone po code-review (Fala 4)** — niski zysk / wysokie ryzyko / nieweryfikowalne headless:
- Dedup ~8 handlerów preview smart/typo w `gui.py` (GUI bez testów)
- Unifikacja 4 downloaderów (downloader, downloader_v2, get_mega_pack, get_special_datasets) pod wspólny interfejs
- Centralizacja `res_map`/listy rozdzielczości (zbiór 2K/4K/8K/16K stabilny, drift teoretyczny, przeciąga przez nieotestowane GUI)
- `range()` w `indexer_typo` gubi ostatni codepoint bloków — NIE ruszać: częściowo zamierzone subsety, a CJK już poprawnie półotwarte
- Usunięcie `CACHE_PATH` z `config.py` — ma testy (test_config), nieszkodliwe

---

## Słownik projektu

- **hat** — 8-kite cluster użyty jako jedna jednostka tiling (kite geometry)
- **kite** — pojedynczy romb z siatki heksagonalnej (q, r, k)
- **density** — średnia jasność glifu typograficznego (0=biały, 1=czarny)
- **freq_penalty** — kara za ponowne użycie tego samego kafelka (domyślnie 30.0)

---

## Zewnętrzne zależności i integracje

[2026-04-18] **Fonty w assets/fonts/**
- 105+ plików .ttf, w tym IBM Plex Mono (14 wariantów), JetBrains Mono (variable), Inconsolata (variable)
- Wszystkie na dysku — nie pobieraj nic
- Indeks fontów trzeba przebudować po zmianach: `python -m src.indexer_typo`
