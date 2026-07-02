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
- Obsługuje geometrie: square, rectangle_3x1, brick_wall, hexagon, hexagon_romb, triangle, romb, kites, spectre
- Geometria `kites` = deltoidalna trójheksagonalna: każdy spłaszczony heksagon dzielony na 6 latawców, każdy latawiec = osobny sektor/zdjęcie (per-tile, deterministyczne, bez RNG). Zastąpiła stary tryb `kite` (8-kite "hat" z losową orientacją) — 2026-06-30
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

[2026-06-26] **Portfolio hardening — walidacja requirements, README EN/PL, CI zielony, GitHub About** (commity ab32e7e, db427b3, cf91769, c38c2d0; na origin/main)
- `requirements.txt` ZWALIDOWANY w czystym venv (Python 3.10.19, 44 pakiety bez torch/transformers): `import src.gui` OK, render typo 4K + smart 2K przeszły → obietnica README „4 linie i działa" udowodniona empirycznie
- README dwujęzyczny: pełny `README.pl.md` (25 sekcji, parytet z EN) + przełącznik `**English** · [Polski]` w linii 3 obu plików; kotwice TOC z polskimi diakrytykami
- **CI z czerwonego na zielony**: `ci.yml` instaluje z `requirements.txt` (koniec driftu — padał `tqdm`); dodany `python -m pytest` → **152 testy** realnie w CI; pominięte `test_ai_core` (torch/MiDaS) + `test_processor` (lokalne GPU/CUDA); bump `checkout@v5`/`setup-python@v6`
- **INWARIANT CI:** install z requirements.txt (nie ręczna lista), `python -m pytest` (nie gołe `pytest` — inaczej `ModuleNotFoundError: src`), ignore test_ai_core+test_processor
- GitHub „About" (`gh repo edit`): description + homepage→live-demo + 10 topics; `opencv`→`scikit-image` (cv2 nieimportowane)

---

## Aktywne TODO (długoterminowe)

[2026-04-18] **feature/semantic-clip — CLIP semantic tile matching**
- Branch: `feature/semantic-clip`
- Cel: zamiana 3×3 LAB features w SmartEngine na CLIP embeddings (semantyczne dopasowanie)
- Status: branch UTWORZONY, ale implementacja CLIP jeszcze nie zaczęta
- Decyzja architektoniczna do podjęcia: rozszerzyć SmartEngine czy nowy SemanticEngine?

[2026-06-26] **A1 — redukcja peak-RAM renderu 16K** (architektura ZATWIERDZONA, wdrożenie od następnej sesji)
- Atrybucja peaku ~10 GB: dominuje **transient spike `cdist(chunk, cała_biblioteka)` float64** (`engine_smart.py:662-664`, ~1.8 GB ×2 z mirrorem ≈ 3.6 GB), NIE kanwa (RGBA ~531 MB). Maski spectre/kite rezydentne. `benchmark.py` nie widzi peaku (mierzy rss tylko przed/po → spike znika)
- Zakres: **Wariant 0** (wątek samplujący rss co ~50 ms — wiarygodny peak, zalicza backlog benchmark.py) → **A-tani** (float32 squared-euclidean + adaptywny chunk_size w pętli `:658-668`; 3.6 GB→~0.25 GB, ranking top-k bez zmian, NIE rusza kontraktu `_do_render→PIL`; `/sonnet` OK) → **B** (leniwe maski spectre/kite: poly+bbox w sectors_data, rasteryzacja przy kompozycie `:729`; HIGH, test regresji pikselowej)
- **ODŁOŻONE — Wariant C** (pasmowe renderowanie kanwy): łamie kontrakt `_do_render→PIL` + inwarianty `_neighbors_cache`, atakuje najmniejsze źródło; tylko gdy cel >16K

[2026-06-26] **A2 — eksport DZI z aplikacji** (architektura ZATWIERDZONA, wdrożenie od następnej sesji)
- `src/tools/make_dzi.py` JUŻ gotowy i poprawny (`Format="jpg"`) — to integracja, nie nowy silnik
- Zakres: **Wariant B** (osobny przycisk „Export Deep Zoom…" w GUI, file picker→out dir, wzorzec wątku `gui.py:run_photo:991-1006`, działa na dowolnym obrazie) + **skip-if-exists** na kafelkach piramidy (= „excluded-tile support" z Roadmapu) + **podkomenda `dzi` w `src/cli.py`**
- **ODŁOŻONE — Wariant C** („Publish to viewer", auto-update `docs/` + refaktor hardcoded `index.html` na manifest): ryzyko publicznego artefaktu GitHub Pages

[2026-06-27] **A1 + A2 WDROŻONE** (commity `5867a76`/`4f178a3`/`81a424a`/`b33b5c2`, na origin/main; CI run 28286897637 success; 173 testy lokalnie)
- **A1-0:** `PeakRAMSampler` (daemon thread 50 ms, `tests/benchmark.py`) — wiarygodny peak-RAM zamiast rss przed/po; pod indexing/render/typo + globalny peak runu
- **A1-A-tani:** `_euclid_f32(chunk, feats, feat_sq)` w `engine_smart.py` (GEMM `‖a‖²+‖b‖²−2a·b` in-place, float32) ZASTĄPIŁ `cdist` (supersedeuje notkę „cdist euclidean, chunk_size=500" z sekcji Architektura). Adaptywny `chunk_size` (macierz ≤256 MB, dzielone przez 2 z mirrorem). Per-chunk 1.8 GB→0.25 GB. **INWARIANT:** musi zwracać PRAWDZIWY euklides (`sqrt`), bo `score = dist + freq_penalty` jest addytywne — squared zepsułby balans. Parytet vs cdist: max err 4.6e-6, top-k i zwycięzca identyczne
- **A1-B:** `_LazyMask(poly, bw, bh, aa)` w `engine_smart.py` — maski kite/spectre jako wielokąt, `render()` odroczony do kompozytu (`:763`). **INWARIANT:** `render()` bit-w-bit (kite aa=1 native; spectre aa=4 supersample+LANCZOS) — pilnują golden sha256 + `TestLazyMask`. Maski grid zostają współdzielonymi PIL
- **A2:** `make_dzi(..., skip_existing=True)` + `--no-skip`; CLI podkomenda `dzi <input> <out_dir>`; przycisk GUI „Export Deep Zoom…" (`export_dzi`, wątek tła wzorem run_photo). +12 testów dzi (E2E w CI — make_dzi bez indeksu)
- **CI:** `test_processor` wrócił (importorskip("torch") + skipif(not cuda)); zdjęty `--ignore` (zostaje tylko `test_ai_core`)
- Plan i protokół: `PLAN_PRAC.md`. Pozostało (NISKI): empiryczny pomiar RAM na realnym 16K → liczby do tabeli Performance w README

[2026-06-28] **Galeria — podmiana triangle+hexagon na prawdziwe 16K (CZEKA NA USERA)**
- Audyt rozdzielczości galerii (`docs/index.html` + `docs/tiles/*.dzi`): tylko **photo/symbol/spectre = 16K**; **triangle (8192×4612) i hexagon (8192×6144) = 8K**. Etykiety w galerii są uczciwe („8K"), ale plik hexagona myląco nazwany `hexagon_jump_16K.dzi` (realnie 8K)
- **Plan uzgodniony:** USER sam wygeneruje 16K triangle+hexagon → wtedy napisze, a ja: usunę stare `showcase_triangle_*` + `hexagon_jump_16K*`, wstawię nowe DZI do `docs/tiles/`, zaktualizuję `tileSources` **i** etykiety (8K→16K, nowe wymiary/MP) w `docs/index.html`
- **Pułapki:** `Format="jpg"` w XML (nie `"jpeg"` → czarny ekran OpenSeadragon, [[project_dzi_format_bug]]); sprawdzić budżet GitHub Pages (obecnie piramidy ~165 MB)

[2026-06-28] **README hero = magnifier papugi 4×4** (commit `26c5d0a`, na origin/main)
- Pierwszy obraz w `README.md`+`README.pl.md` podmieniony: `spectre_full.jpg` → `assets/examples/spectre_hero_magnifier.jpg` (1600×900, wariant „e"). Powód: stare hero nie pokazywało kafelków nawet po powiększeniu
- Styl jak social_preview: pełna mozaika + żółty box na lewej krawędzi dzioba (przejście kolor→białe tło) + linie + inset ~4×4 kafelki + „every tile is a separate photograph". Generator: scratchpad `gen_parrot_magnifier.py` (źródło: `output/github_readme/spectre_parrot_16K.jpg`, tile pitch ~140 px w 16K). `spectre_full.jpg` ZOSTAJE w tabeli progressive-zoom (linia 103)

[2026-06-30] **Tryb `kite` → `kites` ZROBIONE** — stary `kite` (losowe 8-kite hats) zastąpiony deltoidalnym per-tile `kites` (6 latawców/hex, każdy osobnym sektorem, bez RNG, reprodukowalny bit-w-bit). Zmiana w `engine_smart.py` + nazwa wszędzie (gui/cli/make_showcase/benchmark/README EN+PL/MEMORY). 201/201 testów. ZACOMMITOWANE: `5e5d0e0`. Szczegóły: [[project_kites_mode]].

[2026-06-30] **PLAN: 10 nowych kształtów „wow" + schemat na podglądzie GUI** (7 sprintów, user zatwierdza po każdym) — **SUPERSEDED 2026-07-02 przez `PLAN_SHAPES.md` (20 kształtów, sprinty S2–S9)**, wpis niżej.
- **Schemat ułożenia w GUI** (Twój pomysł, robimy PIERWSZY): po wyborze „Tile Shape" w panelu podglądu (`lbl_preview_p`, `_fit_preview`) pojawia się schemat ułożenia; zastępowany realnym renderem po „Generate Preview". Dropdown default → **„None"** (pusto, preview zablokowany). Schematy w `assets/shape_schemes/<shape_mode>.png`.
- **Tier A** (8, czyste wielokąty — drop-in jak spectre/kites): `penrose`, `phyllotaxis`, `voronoi`, `sunburst`, `trunc_square` (4.8.8), `trunc_hex` (3.12.12), `rhombitrihex` (3.4.6.4), `pythagorean`. **Tier B** (2, maski krzywoliniowe — wymaga `_CurvedMask`): `truchet`, `truchet_hex`.
- **Sprint 2 = refaktor**: wydzielić `_build_polygon_sectors()` (dziś zduplikowane w kites+spectre) + rejestr `shape_mode→generator`, ZANIM dojdą nowe kształty. Golden SHA-256 muszą zostać zielone.
- **Reindeks NIE potrzebny** (kształty po stronie targetu; indeks 79-dim agnostyczny). **`hexagon_romb` == „tumbling blocks"** (heksagon = 3 romby przez `mask_left/right/top`). Generatory schematów (wszystkie 19, wierne geometrii silnika) gotowe w scratchpad: `gen_shape_schemes.py` + `shapes10.py`. Plan szczegółowy: ostatnia odpowiedź asystenta (7 sprintów, M1–M7).

[2026-07-02] **KSZTAŁTY: plan rozszerzony do 20 (10 Opus + 10 Fable) — kanoniczny plan = `PLAN_SHAPES.md`**
- **Sprint 1a+1b ZROBIONE:** 19 schematów PNG (`2ec504c`) + GUI: wybór kształtu pokazuje schemat w podglądzie, pusty default blokuje preview/render (`3a186b7`)
- **10 kształtów Fable ZAAKCEPTOWANE** (schematy `e6c55f4`): girih, ammann_beenker, pinwheel, voderberg (stylizowany), cairo, floret, poincare {7,3}, escher_lizard (p1), gosper, weave. Generator z działającą geometrią: `src/tools/gen_fable_shape_schemes.py` (COMMITOWANY — lekcja po utracie scratchpada Opusa). **Finalna selekcja kształtów przez usera dopiero PO wdrożeniu wszystkich 20** (mozaiki testowe)
- **Audyt wdrożenia → wymagania Sprint 2** (w PLAN_SHAPES.md): kontrakt generatorów w przestrzeni obrazu (y w dół); helper `_polygon_sector()` z bbox-strategią od kites (nie spectre); aa=4 dla nowych; rejestr `SHAPE_MODES` jako single source of truth dla GUI/CLI/tools; golden SHA-256 przed/po refaktorze
- **Pułapki geometryczne rozwiązane** (szczegóły w PLAN_SHAPES.md, nie powtarzać błędów): znak Cramera w multigrid de Bruijna; promień {7,3} to `cosh R = cot(π/p)·cot(π/q)` (NIE `cos/sin`); dedup odbić hiperbolicznych po centroidzie zaokrąglonym do 1e-3; orientacje pinwheela rosną zbyt wolno by pokazać je na schemacie (2 klasy mod 180° — to cecha, nie bug); greedy girih max ~97% pokrycia → produkcyjna decyzja w S7

[2026-07-02] **Sprint 2 W TOKU (refaktor rdzenia kształtów) — golden + szkielet gotowe, wiring NIE**
- **Golden testy** `tests/test_golden_shapes.py` (8 przypadków: square/hexagon_romb/kites/spectre × border on/off; deterministyczna syntetyczna biblioteka 32 kafli seed 12345 + gradient 384×288; SHA-256 policzone na silniku PRZED refaktorem, reprodukowalne 2×) — **8/8 zielone**. To bramka Sprint 2: muszą zostać zielone PO refaktorze.
- Do `engine_smart.py` dodane **addytywnie (jeszcze NIEUŻYWANE w `_do_render` — stare gałęzie kites/spectre wciąż aktywne, kod działa, 50/50 testów)**: helper `_polygon_sector(target, poly, render_padding, aa, edge_aware)` (bbox-strategia kites: repaste z offsetem `sb[0]-safe_box[0]`, bez clamp-min→0); rejestr `SHAPE_MODES` (dataclass `ShapeSpec{kind,generator,aa,seeded}`) + `shape_names()`; generatory modułowe `_gen_kites`/`_gen_spectre` (Y-flip WEWNĄTRZ generatora, kontrakt: poly w przestrzeni obrazu y-down).
- **Dowód równoważności kites:** przeniesienie Y-flip do generatora + shrink-do-centroidu w helperze daje IDENTYCZNY `padded_poly` (flip afiniczny komutuje z centroidem) → kites golden nie powinien się zmienić.
- ⚠ **RYZYKO do decyzji przy wznowieniu:** helper używa strategii bboxa kites (offset) zamiast spectre (clamp min→0). Dla kafli spectre przecinających GÓRNY/LEWY brzeg zmienia sub-pikselowe wyrównanie maski (`int(min_x)` vs `0.0`) → **golden spectre MOŻE paść**. Jeśli padnie: albo zregenerować golden spectre + udokumentować (poprawne edge handling wg PLAN_SHAPES.md pkt 1), albo dodać per-shape flagę strategii bboxa.

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

- **kite** — pojedynczy latawiec (1/6 spłaszczonego heksagonu): [środek, środek_kraw(k-1), wierzchołek(k), środek_kraw(k)]
- **kites** (tryb) — deltoidalne kafelkowanie per-tile: 6 latawców/heksagon, każdy osobnym sektorem (zastąpiło stary `kite`/hat)
- **density** — średnia jasność glifu typograficznego (0=biały, 1=czarny)
- **freq_penalty** — kara za ponowne użycie tego samego kafelka (domyślnie 30.0)

---

## Zewnętrzne zależności i integracje

[2026-04-18] **Fonty w assets/fonts/**
- 105+ plików .ttf, w tym IBM Plex Mono (14 wariantów), JetBrains Mono (variable), Inconsolata (variable)
- Wszystkie na dysku — nie pobieraj nic
- Indeks fontów trzeba przebudować po zmianach: `python -m src.indexer_typo`
