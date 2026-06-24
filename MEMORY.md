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

[2026-06-21] **Opcja B — realne pisma egzotyczne w TypoEngine** (commit 1fbad26; 184 testy passed)
- Problem: grupy B_ancient/C_symbols/G_uncategorized były praktycznie martwe — dwa niezsynchronizowane filtry (wąskie zakresy w `indexer_typo` + twardy filtr ASCII+CJK w `engine_typo`) wyrzucały ich glify; indexer renderował też strzałki/math/box/runy, które engine i tak kasował (marnotrawstwo)
- `indexer_typo`: `FULL_BLOCKS` (~44 bloki Unicode: hieroglify, klinopis, Linear A/B, Phoenician, runy, math, music, emoji, arabski/bengalski/syngaleski) + `LARGE_BLOCKS` (CJK/Hangul stride-sample), flaga `--full-scan`; tofu-guard cmap bez zmian
- `engine_typo`: filtr świadomy grup — `_LATIN_GROUPS={D_latin_clean,E_decorative,F_handwriting}` zachowują wyselekcjonowany podzbiór ASCII; reszta grup ufa indekserowi (char_ok=True)
- **INWARIANT:** zakresy `indexer_typo.FULL_BLOCKS/LARGE_BLOCKS` ↔ `engine_typo._LATIN_GROUPS` muszą być spójne z `font_groups.py`; po zmianie zakresów ZAWSZE reindeks (`python -m src.indexer_typo`)
- Reindeks → 43 829 glifów; wszystkie 7 grup żyją (B_ancient 9685, C_symbols 4289, G 3715)
- SPROSTOWANIE: linie 26–27 wyżej (color_on_white/black) są NIEAKTUALNE — TypoEngine ma tylko black_on_white/white_on_black (tryby koloru usunięte 2026-05-04)

[2026-06-21] **README przepisane + sprostowane fakty vs kod** (commit bb59a1f)
- Domyślny downloader `fast_downloader`→`downloader.FastDownloader` = **Picsum + LoremFlickr** (NIE Chicago/Openverse); `downloader_v2`=`PoliteDownloader` = Openverse/Met/Art Institute z tierami starter/public/extended (+klucz Openverse z .env)
- `TARGET_SHORT_SIDE` jest IGNOROWANE przez smart engine (rozdzielczość steruje res_map: smart 16K=15360×8640, typo 16K=16000); `NUM_TILES` = cel downloadera, NIE cap indexera/engine
- anti-repetition (faktyczny wzór): `score = dist + used_count² × freq_penalty × 0.001` (kwadratowo, freq_penalty=30.0); sąsiedztwo promieniowe (query_ball_tree r=1.5×spacing), nie „4 sąsiadów"
- Nazwa kanoniczna: **Neural-Mosaic** (nie NeuroMosaic/NeuroMosaik); benchmark.py: jedna kolumna Time (silnik CPU-only); RAM 16K ~10 GB (obserwowane, nie z psutil delta)
- Nowy `src/tools/make_matrices.py` (composite'y README); usunięto symbol_color.jpg + 6 zoom GIF

[2026-06-21] **Live demo (docs/, GitHub Pages main/docs) — różne źródła per kształt, czyste 8K** (commity aa787ea, 59a0bff)
- DZI przez `make_dzi --max-level 13` (cap 8192 px); Format="jpg" w .dzi (zgodny z plikami — inaczej czarny ekran)
- Było: spectre i hexagon oba z papugi (portrait3) → duplikat. Teraz: spectre=papuga, hexagon=skok (IMG_20220727); triangle=portrait2, photo=portrait
- viewer ma 5 mozaik (README wcześniej błędnie mówił „tylko 2"); poprawione kłamliwe etykiety triangle/hexagon (mówiły 16K, są 8K)

[2026-06-24] **requirements.txt łamał quick start + sprostowania README vs kod** (debata adwersarialna Krytyk vs Obrońca; commit 68819bc; na origin/main)
- `requirements.txt` był surowym `pip freeze`: brakowało **matplotlib** (import top-level w `gui.py:29-30` → GUI w ogóle NIE wstawało po `pip install -r requirements.txt`) i **fonttools** (`indexer_typo`); jednocześnie wymuszał torch/transformers (kilka GB) wbrew deklaracji „PyTorch optional"
- Fix: kurowana lista realnie importowanych zależności (zweryfikowane `grep -rhoE "(import|from) \w+" src/`); torch/torchvision/transformers → OPCJONALNY zakomentowany blok (uśpiony ai_core); cv2/opencv NIE jest importowane mimo wzmianki w CLAUDE.md/stacku
- **INWARIANT:** NIE regenerować `requirements.txt` przez `pip freeze` — edytować ręcznie; matplotlib + fonttools muszą zostać
- README sprostowania faktów: indeks Smart jest **ZAWSZE 79-dim** (`indexer_smart` bezwarunkowo zapisuje feature_dim=79, schema „5x5_edge"); `--edge-aware` przełącza tylko UŻYCIE 4 cech krawędziowych w matchingu, NIE buduje innego indeksu (usunięto błędne „requires an index built with --edge-aware" + radę o przebudowie przy toggle) — to też prostuje nieaktualne linie 12/20 wyżej (75-dim/„5x5"); ujednolicono „6 vs 7 grup fontów"; rozmiar repo ~100→~250 MB; dodano kolumnę kodów CLI (`A_cjk`…`G_uncategorized`) w tabeli grup fontów

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
