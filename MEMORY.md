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

[2026-07-08] **Dopasowanie świadome maski — plan jakości 1+2+3 WDROŻONY** (commity 3dd42d9, 0d2c5f8)
- `create_mosaic`: zapis JPEG z `subsampling=0` (4:4:4) — mozaika to tysiące ostrych granic kolorów, domyślne 4:2:0 rozmywało chrominancję na szwach/fugach
- `_mean_fill_outside_mask` rozszerzone na gałęzie grid (standardowa + hexagon_romb composite) — wcześniej tylko kites/spectre; triangle miał ~50% bboxa zanieczyszczone treścią sąsiadów
- `_mask_cell_weights` + **ważony re-scoring top-K**: wagi = pokrycie maską komórek 5×5 (BOX, ten sam kernel co cechy), normalizacja do średniej 1.0 (balans freq_penalty zachowany); maska pełna → None → square bit-w-bit; edge-dimy z wagą 1.0; `wmask` także w `_polygon_sector` (kształty S2+ dostają za darmo)
- DECYZJA ARCHITEKTONICZNA: re-scoring top-K ZAMIAST sqrt(w)-przed-GEMM — wiele masek w jednym renderze (triangle norm/flip, hexagon_romb×3, kites×6, spectre per sektor) wymagałoby kopii biblioteki per maska; GEMM/`_euclid_f32` nietknięty → inwariant A1 („prawdziwy euklides") bezpieczny
- Empiria (0013.jpg, triangle 2K): deltaE LAB do oryginału 9.27→8.46 (~9% skumulowane); czas renderu bez regresji; goldeny: 7 regen. (celowo), square/False niezmieniony przez OBIE zmiany = dowód izolacji ścieżki GEMM
- Punkt 4 planu: WDROŻONY 2026-07-09 — patrz wpis niżej (UWAGA: pierwotne założenie „re-fetch picsum po seedzie" okazało się błędne — seed dryfnął; głównym źródłem odzysku jest COCO)

[2026-07-09] **Nakładka hi-res `tiles_hires/` — punkt 4 planu jakości WDROŻONY i ZWERYFIKOWANY A/B** (commity 9e5b6cf, 3515769, 00df732, 7d8c3f9, 6bf7ac4, 6783a46; 303 testy; PLAN_HIRES.md = plan kanoniczny)
- DIAGNOZA: winowajcą miękkich kafli był `src/optimizer.py` (TARGET_SHORT_SIDE=250, nadpis in-place) — zmiażdżył całą bibliotekę 421k kafli z pełnej rozdzielczości datasetów (COCO ~640px, Food-101 512px…); archiwa źródłowe skasowane, oryginały nie istnieją lokalnie
- ARCHITEKTURA: paste-time overlay — `engine_smart.HIRES_DIR` (`data/tiles_hires/`, kluczowana nazwą pliku); `_load_hires_overlay()` buduje set nazw RAZ na render (zero stat per kafel), `_resolve_tile_path()` podmienia ścieżkę tylko przy wklejaniu; dopasowanie/indeks/GEMM NIETKNIĘTE (inwariant A1); pusta nakładka = render bit-w-bit (goldeny bez regeneracji). INWARIANT: `tiles_hires` NIGDY w LIBRARY_DIRS (indexer by zdublował, optimizer zmiażdżył) — guard + test
- PĘTLA: `create_mosaic` zapisuje `<stem>_used_tiles.json` (kafle z count>0; preview bez I/O) → `python -m src.tools.upgrade_tiles --used-json …` (router per-źródło, async fetch, zapis bajtów as-is) → następny render automatycznie ostry
- BRAMKA LAB (`verify_identity`, 5×5 CIELAB deltaE, próg 8.0): każdy pobrany plik porównywany z oryginałem 250px; złapała DRYF PICSUM — `picsum.photos/seed/{idx}` zwraca dziś INNE zdjęcia (deltaE ~49) → picsum NIEodzyskiwalny, domyślnie niepobierany (opt-in `--include-picsum`). COCO odzyskiwalny per-file (id z nazwy: `coco_train_*`→train2017, `coco_*`→unlabeled2017; kolejność prefiksów = inwariant routera)
- EMPIRIA A/B (0013.jpg, 8K, tile_scale=3.0): upgrade 313/313 COCO → re-render; przypisania identyczne; ostrość (wariancja Laplace'a) **+48.7% globalnie**, komórki do 4×; dowód `output/0013_ab_comparison.png`. Rozkład użytych kafli z realnych renderów: COCO ~69%, archiwa ~15%, stracone ~15%
- PREWENCJA (nowi userzy): `DOWNLOAD_SIZE=512` w config (odsklejone od TILE_SIZE=75 — to było źródło miękkich świeżych pobrań), optimizer 250→512 (env `OPTIMIZER_SHORT_SIDE`) + delete-corrupt tylko za flagą + guard na tiles_hires
- DECYZJA: Sprint 5 (archiwa food/places/dogs/flowers) ZAMKNIĘTY — NIE robić (8 GB pobrań za +16% przy ~15% straconych = zły ROI); wyjątek on-demand: places-only (2.3 GB → ~10%); ESRGAN odroczony — wraca TYLKO jeśli deep-zoom DZI ujawni widoczną miękkość kafli nie-COCO

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

[2026-07-10] **KSZTAŁTY: WIRING RUSZYŁ — 12 nowych kształtów WDROŻONYCH** (commity 7871951, 909ecb9, 0f625c2, b278373; 327 testów; +24 goldeny)
- **Odkrycie:** Sprint 2 był zrobiony TYLKO w połowie — rejestr `SHAPE_MODES`/`ShapeSpec`/`_polygon_sector` istniały, ale `_do_render` wciąż miał zahardkodowane `if kites/elif spectre/else grid`, a `_polygon_sector` był MARTWYM kodem.
- **Rozwiązanie:** dodana generyczna gałąź `elif SHAPE_MODES[shape_mode].kind=="polygon"` (przed grid) — iteruje generator z rejestru i składa sektory przez `_polygon_sector`. Każdy NOWY kształt polygonowy = 1 generator + 1 wpis w rejestrze + golden. **kites/spectre ZOSTAJĄ we własnych gałęziach** (zablokowane goldeny; spectre ma inną strategię bboxa — decyzja: NIE migrować, niekonieczne; ryzyko z wpisu wyżej rozwiązane przez pozostawienie). CLI `_SMART_SHAPES` + GUI `combo_shape` czytają z `shape_names()` (koniec 3 zahardkodowanych list).
- **Wdrożone (wszystkie polygon, aa=4):** sunflower ×7 (grande/xl/soft/inverse + soft/rings/disc; Vogel/Voronoi bez koloru→zero RNG; helpery `_graded_sunflower`/`_emit_cells`/`_lloyd_relax`/`_vogel_points`/`_voronoi_cells`), rhombs ×3 (nopole/funnel/star; mesh log-spiralny `_log_mesh`; **base_s steruje gęstością** przez `_solve_k` count~1/k²; inwariant samopodobności: pętla wewn. zawsze F1+F2 krawędzi→domknięcia środka niezależne od k), voronoi (jednorodny; seed z wymiarów `_shape_seed`→determinizm preview↔render; pierścień brzegowy zamrożony w Lloydzie `freeze_r`) + phyllotaxis (Vogel power=0.5).
- **Wspólne decyzje geometrii Voronoi:** (a) mapowanie afiniczne świata [-1,1]²→kadr z flipem Y — obraz Voronoi pod afinicznością to nadal partycja, więc stretch na nie-kwadracie OK; (b) liczba komórek ~pole/base_s² (tile_scale działa jak dla siatek); (c) `_SUNFLOWER_CELL_DENSITY=2.6` jeden dla całej rodziny. Golden nowego kształtu = lock pierwszego renderu (brak „before"), generowany scratch-scriptem z fixture jak `test_golden_shapes`.
- **NASTĘPNE:** PLAN_SHAPES S3+ trudniejsze (penrose/ammann_beenker multigrid, girih, poincare, truchet krzywoliniowe, voderberg, escher_lizard, weave; deterministyczne pinwheel/cairo/floret/gosper/pythagorean mają gotową geometrię w `gen_fable_shape_schemes`). User chce WSZYSTKIE kształty PRZED galerią 16K.

[2026-07-11] **KSZTAŁTY: +11 wdrożonych (rejestr=32) + pakiet poprawek UX** (commity 5f3ada0, 5e04b42, 98924bd, 9a74ff2 — wypchnięte; 325 testów; +22 goldeny cross-proces)
- **Pakiet poprawek (uwagi usera):** (1) presety groutu przemianowane na EN `thin`/`medium`/`thick` (grout.py=źródło prawdy, GUI/CLI/sufiks batch — stare pliki `_grout-sredni` nie łapią skip-if-exists); (2) `used_tiles.json` OPT-IN domyślnie OFF (`create_mosaic(save_used_tiles=False)`, checkbox GUI + `--save-used-tiles` CLI — workflow upgrade_tiles wymaga świadomego włączenia); (3) **generyczny flat grout dla kształtów polygon**: `_grout_cells` fallback — generator z SHAPE_MODES re-yielduje TE SAME poligony jako komórki `(poly,0,0)` → linie dokładnie na szwach, każdy przyszły kształt polygon dostaje grout za darmo (wizualnie: fraktalne fugi na gosperze).
- **Fable ×4 (5e04b42):** pinwheel/cairo/floret/gosper portowane z `gen_fable_shape_schemes.py` WPROST w image space (scheme renderer też y-down → zero flipu, chiralność zgodna z PNG). Helper `_lattice_mn_range` (zakresy m,n z odwrotności macierzy siatki). pinwheel: substytucja 1:2:√5, depth=round(log(L/base_s)/log√5), tilt 13°, pruning poza kadrem PODCZAS subdywizji.
- **Archimedesowe ×5 (98924bd) OD ZERA z PNG** (kod Opusa przepadł ze scratchpadem): trunc_square 4.8.8, trunc_hex 3.12.12, rhombitrihex 3.4.6.4 (ciemne trójkąty z PNG = w silniku PEŁNOPRAWNE komórki — reguła teselacji), pythagorean (⚠ PUŁAPKA: dziura to [b-s,b]×[b,b+s] wzgl. punktu siatki — pierwsza próba dała 19% dziur, ZAWSZE weryfikować rasteryzacją), sunburst (log-polar: stały nsec, g=1+2π/nsec ⇒ komórki ~kwadratowe samopodobne, twist −0.18 sektora/pierścień = spirale CCW jak schemat, czapka 7 klinów, łuki polygonizowane co ~base_s/3 — strzałka sub-px, T-junctions legalne).
- **Multigrid ×2 (9a74ff2):** wspólny `_multigrid_dual(N,zeta,gamma,...)` — Cramer VERBATIM ze zwalidowanego gen_ammann_beenker (znak = udokumentowana pułapka). **Optymalizacja okna: wierzchołek dualny ≈ (N/2)·p** (tożsamość sumy wektorów gwiazdy) → okno przecięć = kadr/(N/2)+2 ⇒ 16K w 0.2 s (~25k rombów). penrose = P3 pentagrid γ suma=1 (schemat PNG to ta sama geometria, kolorowanie gwiazd); ammann_beenker N=4 zgodny 1:1 z PNG.
- **Wzorzec skali dla teselacji mieszanych:** pole DOMINUJĄCEGO kafla ~ base_s². Lekcja testowa: NIE używać nazw realnych planowanych kształtów jako „spoza rejestru" w testach (penrose wszedł i złamał 2 testy groutu — teraz nazwy fikcyjne).
- **ZOSTAŁO z PLAN_SHAPES:** girih (sweep seedów — decyzje), poincare (model pasmowy w gen_fable), voderberg/escher_lizard/weave (geometria w gen_fable, RNG tylko kolor — najtańsze następne), truchet×2 (`_CurvedMask` — nowa maszyneria), pula extra 21-43. Po WSZYSTKICH → selekcja finalna usera → galeria 16K.

[2026-07-03] **KSZTAŁTY: +16 nowych schematów-propozycji (21-36) + TWARDA reguła „prawdziwa teselacja"** (sesja na Fable 5; NIEZACOMMITOWANE)
- **Nowy generator** `src/tools/gen_extra_shape_schemes.py` (importuje helpery z `gen_fable_shape_schemes`). Pula propozycji: 20 → **36**. Montaż `output/kite_schemes/proposals_extra_15_shapes.png`.
- **WYMÓG NADRZĘDNY usera:** każdy kształt musi być PRAWDZIWĄ teselacją brzeg-w-brzeg — kafle NIE nakładają się, pasują idealnie z każdej strony, wypełniają CAŁY prostokąt bez luk, samopowtarzalne. To unieważniło pośrednią technikę „siatka tła + motyw na wierzchu" (to było nakładanie).
- **Rozwiązanie konfliktu koło-vs-prostokąt (pomysł usera):** pierścienie KOŁOWE rozszerzane poza rogi i **przycinane** do prostokąta (`_clip_rect` = Sutherland-Hodgman) → środek okrągły, rogi ucięte, pełna teselacja. Helper `_radial_clip_cells(R, rings, pal, seed, swirl)` obsługuje rosette/mandala/nautilus/vortex/shatter. Seam-fix: offset o pół sektora co drugi pierścień.
- **ETAP B ZROBIONE (10 pewnych teselacji):** sierpinski (prawdziwy rekurencyjny, dziury=komórki, kafelkowany up+down), gereh (ośmiokąt=gwiazda-8+8 latawców — PARTYCJA, nie nakładka), koch_island (reptile, period=4^depth NIE bbox), rosette/mandala (koła przycięte), nautilus/vortex (radialne ze skrętem), shatter, moire (GEOMETRYCZNA zwichrowana siatka — pod zdjęciami ≠ square, w przeciwieństwie do wersji „kolor"), braid (basketweave płaski). Stary „sierpinski" (przesunięte trójkąty) → przemianowany `stagger_tri` (#36).
- **Fix w `gen_fable_shape_schemes.py`:** poincaré (siatka tła w rogach), voderberg (promień poza rogi + kapsel centralny).
- **ETAP A PENDING (5 trudnych aperiodycznych/reptile, oznaczone `[ETAP A]`):** bloom→Voronoi phyllotaxis+clip, hirotaka→Penrose (pentaflake nie kafelkuje), koch_snowflake→2-rozmiarowy, dragon→twindragon-reptile (teraz placeholder-wstęgi order=6), kepler_ty→teselacja 5-krotna.
- **Sprint 2 (`_do_render` refaktor) NADAL nietknięty** — ta sesja to pełny pivot na schematy. Selekcja finalna 36 kształtów do silnika PO ETAP A.

[2026-07-04] **KSZTAŁTY: rewizja wg 9 poprawek usera + 4 nowe + FIX pustki kites** (commity cedb2ce, 75bf7df; 181 testów + golden 8/8 zielone)
- **Fix silnika:** `engine_smart.py` — okno pętli `r` w gridzie kites centrowane na `-q//2` (człon shear `q/2` w `cy` przesuwał pas skanowania przy dużych |q| → czarny klin w prawym dolnym rogu). Poprawione w OBU miejscach: aktywna gałąź `_do_render` + `_gen_kites` (rejestr Sprint 2). **Golden NIE zmienione** — luka ujawniała się dopiero przy większych proporcjach niż obraz testowy 384×288. Schemat regenerowany commitowanym `src/tools/gen_kites_scheme.py`.
- **ETAP A rozwiązany w 4/5:** bloom=Voronoi phyllotaxis (r=c√i ⇒ komórki równopolowe; kolor i mod 21 = ramiona), dragon=twindragon rep-tile order 8 (2ⁿ kwadratów w bazie 1+i; brzeg: kasowanie par krawędzi + najostrzejszy skręt w lewo na pinch-wierzchołkach; siatka (1+i)ⁿ·Z[i]), koch_snowflake=teselacja 2-rozmiarowa (duże na siatce trójkątnej co 2R stykają się w 6 punktach promienia R, małe 1/√3 obrót 30° w dziurach — bilans pól DOKŁADNY), kepler_ty=pentagrid de Bruijna N=5 (kopia zwalidowanego kodu ammann_beenker, γ suma=1). Zostało TYLKO hirotaka.
- **Poincare bez tła — technika inwersji:** okno WEWNĄTRZ dysku NIE działa (hiperboliczne kafle przy środku są nieliczne i ogromne — 15 szt. przy W=0.52). Rozwiązanie: kontynuacja pattern'u POZA okrąg przez inwersję v→1/conj(v) (kafle znów rosną ku rogom) + lekki Möbius (a=0.26+0.11i) de-centruje wielki heptagon + W=1.30. Kafel zawierający 0 pomijać przy inwersji (obraz nieograniczony). `_clip_rect` przeniesiony do `gen_fable_shape_schemes` (gen_extra importuje).
- **Rodzina radialna zredukowana (user):** rosette/mandala/vortex/shatter ≈ to samo → zostaje `nautilus` z biegunem POZA kadrem (-1.55,-1.30): stały nsec + geometryczne promienie ⇒ ~kwadratowe komórki log-polar, zero osobliwości. PNG mandala/vortex/shatter usunięte.
- **Nowe kształty (linki/obrazki usera):** `rosette` reaktywowana jako 12-krotna rozeta zellij (Moulay Idriss II, Fez) = partycja 3.12.12 (dwunastokąt → 12 latawców rdzenia + 12 płatków + 12 trójkątów krawędziowych; PUŁAPKI: trójkąty międzywęzłowe osobną pętlą po WSZYSTKICH centrach — dziura może należeć do odfiltrowanego centrum; filtr BOX nie promieniowy — rogowe rozety wystają do kadru); `scales` = łuski (okręgi na siatce szachownicowej dx=2r/dy=r pokrywają płaszczyznę DOKŁADNIE — promień pokrycia=r; komórka=kopuła+2 wklęsłe łuki, przecięcia w (0,−r),(±r,0)); `pebbles` = Voronoi zmiennej gęstości (bloby gaussowskie + rejection sampling); `rosette_fractal` = aloes spiralny (log-polarny pas trójkątów, faza pierścieni ⇒ spiralne ramiona, wspólne krawędzie próbkowane identycznie).
- Pula propozycji: **39 nazw / 16 paneli w montażu extra** (4×4; plik `proposals_extra_15_shapes.png` — nazwa historyczna). Montaż Fable przeliczony (poincare).

[2026-07-04b] **KSZTAŁTY: ETAP A domknięty (penrose_p2) + pakiet „niepraktyczny środek" + warianty sierpińskiego** (commit af581e1; 181 testów zielonych; poprzedni backlog wypchnięty na origin do 9aa5416)
- **`penrose_p2` zastąpił hirotaka** (ostatni [ETAP A]; PNG hirotaka usunięty). ⚠ LEKCJA: ręczne wyprowadzanie substytucji połówek P2 (Robinson) 2× dało T-junctions — punkty podziału krawędzi muszą się zgadzać między SĄSIEDNIMI rodzicami, co wymaga idealnej spójności ról oś/zewnętrzna każdego ramienia. DZIAŁA droga pośrednia: **deflacja P3 Preshinga + relacje kafli A/B (BS=AL, BL=AL+AS)** — połówka cienkiego rombu = połówka latawca wprost, gruby dzielony w U przy |BU|=ramię (kierunek lustrzany |CU| zostawia 410 niesparowanych). Scalanie w pełne latawce/strzałki: para = rodzaj + wspólne ramię + WSPÓLNY apex (test chiralności z kolejności etykiet ODRZUCA prawdziwych bliźniaków — nie używać); cykle przy słońcach rozwiązuje matching stopień-1-najpierw. Wynik: 0 niesparowanych wewnątrz, kąty 72-72-72-144 / 36-72-36-216, latawce:strzałki ≈ φ.
- **Wzorzec „dobrego środka"** (wymóg usera dla wszystkich radialnych; wzór = bloom/phyllotaxis/sunburst): komórki nie mogą zbiegać do zera przy biegunie. `rosette_fractal`: sektory ×2 co m=3 pierścienie, g=2^(1/m) (pas podwajający = wachlarz 3 trójkątów/sektor; czapka N-gon); `voderberg`: liczba klinów ~2πr_mid/target per pierścień (T-junctions na łukach pierścieni legalne — jak rzędy sierpinskiego); `girih`: KAŻDY dekagon → 10 latawców khatam + domykanie dziur greedy przez convex hull pustych komponentów rastra (scipy label+ConvexHull, inflacja 1.10, malowane na końcu — koniec czarnych klinów przy ~95-99% pokrycia).
- **`poincare` PRZEPROJEKTOWANY** (user: totalnie niepraktyczny, usunąć okrąg): **model pasmowy** w=(2/π)log((1+z)/(1−z)) — {7,3} biegnie poziomo bez horyzontu kołowego; okno |y|≤0.80 ogranicza min komórkę do ~1/3 środkowych; heptagony (za duże: 33/kadr) dzielone na 7 latawców — środek hiperboliczny śledzony PRZEZ odbicia w BFS, środki krawędzi = próbka t=0.5 łuku (identyczna z obu stron ⇒ partycja dokładna). Wersja inwersyjna z 04a wyrzucona; BFS może ciąć na diam<0.02 (okno używa |z|≤0.9 — bez pyłu przy brzegu).
- **`sierpinski_b`/`sierpinski_c`** (wybór usera: duże dziury równo rozłożone „co dwa"): nośniki pełnego gasketu depth-3 = tylko trójkąty „góra" (siatka hex dziur) / przeplot góra-dół co rząd; nie-nośniki przez `_sierp4` = 4 pod-gaskety depth-2 (dziury capowane na S/4). **`sierpinski_carpet`** (#40, prośba usera): dywan 3×3 depth-3 na cały kadr, dziury = komórki wg poziomu (większe zdjęcia).
- Pula: **43 nazwy / 19 paneli extra** (montaż 4×5) + 10 Fable. Selekcja finalna (w tym wybór wariantu sierpińskiego) → user; potem Sprint 2 wiring.
- **Werdykty usera (koniec sesji 2026-07-04b):** `sierpinski_b` i `sierpinski_c` ODRZUCONE — chce SZACHOWNICY: duże trójkąty naprzemiennie z wypełnionymi w rzędzie, każdy kolejny rząd przesunięty o jeden. `sierpinski_carpet` — wada: najmniejsze „puste" kwadraty (1/27) mają ten sam rozmiar co wypełnione ⇒ po podmianie na zdjęcia nieodróżnialne. Czapki/wypełniacze środka w `rosette_fractal`/`voderberg`/`girih` — NIE osobny kształt: środek ma być z kafelków TEGO SAMEGO kształtu co reszta teselacji, co najwyżej delikatnie zmodyfikowanych (np. zbiegających się wierzchołkami w centrum).

[2026-07-05] **KSZTAŁTY: pakiet 3 poprawek WDROŻONY + proces adwersarialny „fraktale jako funkcjonalność" (Sprinty 1-3 z 4)** (commit kodu 49e0874 — NIE wypchnięty; 209 testów zielonych)
- **Pakiet poprawek (werdykty 04b):** `sierpinski_d` SZACHOWNICA — carrier=(t+r)%2 po pozycji SEKWENCYJNEJ t w rzędzie (licząc oba typy trójkątów), siatka BEZ staggera (⚠ to stagger ustawiał dziury z powrotem w kolumny — przyczyna porażki wariantu C); b/c usunięte (kod+PNG). `sierpinski_carpet` — depth 4 z dziurami tylko od poziomu ≥2 (tło = jednolita siatka 1/81, najmniejsza dziura 1/27 = 3× tła). Środki z kafli tego samego kształtu: `rosette_fractal` = wachlarz 12 trójkątów liść/przerwa zbiegających się w biegunie (zewn. krawędź przez edge() ⇒ szwy dokładne), `voderberg` = pierścienie od r=0 (8 wygiętych klinów w biegunie; arc_in=[] gdy rin==0), `girih` = latawce khatam zostają, kolor jedną bazą złota + vary (bez 2-tonowego koła).
- **Proces adwersarialny (4 role: Wizjoner → Inżynier+Esteta NIEZALEŻNIE → Arbiter; user werdyktuje po każdym sprincie):** 10 pomysłów → **FINALIŚCI:** `quadtree_detail` (nowy tryb kształtu), `hilbert_flow` (always-on dobór; `--flow none` = baseline bit-w-bit), `fractal_crossfade` (narzędzie, MVP=1 klatka z maską fBm), `zoom_movie` (GIF bez ffmpeg, reuse make_zoom_gif). **ODŁOŻENI:** pifs_self_collage (trzeci silnik — po fazie portfolio), lsystem_veins (pierwszy alternat, wariant recolor-LAB), dla_growth_timelapse (tani dodatek „Reveal" do dowolnego renderu).
- **KOLEJNOŚĆ WDROŻENIA (specyfikacje Inżyniera po lekturze kodu; ~11-15 dni):** hilbert_flow (2-3d, dwufazowa pętla dopasowania) → quadtree_detail (3-4d, nowy kind w SHAPE_MODES, cap głębokości, anti-repeat OFF w v1) → fractal_crossfade (2-3d, nowy src/tools/make_crossfade.py, zero zmian silnika) → zoom_movie (4-5d, nowy make_zoom_movie.py). Inwarianty każdego PR: determinizm bit-w-bit, brak regresji przy trybach OFF, jawne seedowanie każdego nowego RNG.
- **Materiały procesu** (pomysły, obie krytyki, synteza Arbitra, SWOT 10 pomysłów, specyfikacje MVP): SKONSOLIDOWANE w **PLAN_FRACTAL.md** (Sprint 4, 2026-07-05) — kanoniczny plan wdrożenia; oryginały w gitignorowanym `output/fractal_proposals/`, wizualizacje reprodukowalne przez `src/tools/gen_fractal_feature_schemes.py` (commit 883d171).

[2026-07-05b] **PLAN_FRACTAL wykonawczy + cancel render + grout + sunflower (sesja werdyktowa)** (commity cecb220, 8a28666, 7ac8139, 9f5b55f, 15100da, db6cee5, 56590d3, ea4fe49 — wypchnięte; 187 testów zielonych)
- **PLAN_FRACTAL.md sekcja „Plan wykonawczy":** 14 krótkich sprintów z checkboxami/DoD/bramkami dla Opus/Sonnet (F1a trójfazowa pętla → F1b hilbert → F2a/b quadtree → F3 crossfade → F4a/b zoom → CHECKPOINT → O1/O2/O3); kotwice w kodzie zweryfikowane (SHAPE_MODES:156 już istnieje, golden testy SHA-256 istnieją).
- **Cancel render WDROŻONY:** `cancel_event` (threading.Event) w obu silnikach, polling na granicach pętli, wyjątek `RenderCancelled` w nowym `src/render_control.py` (wspólny moduł — silniki nie importują siebie nawzajem); anulowany render NIE zapisuje pliku; przycisk „Cancel render" w obu zakładkach GUI.
- **Grout hierarchiczny (propozycje, werdykt cząstkowy):** 3 poziomy — grupowanie „po 7" to jedna pod-siatka (kwiat Gospera): `sub7` na axial (q,r) przez odwrotność M=[[2,-1],[1,3]], członkostwo dokładne (centrum+6 sąsiadów), a współrzędne grup są znów siatką axial ⇒ poziom 3 = ta sama funkcja na wynikach poziomu 2. Kwadraty: bloki 3×3/9×9; trójkąty: 3-kolorowanie wierzchołków (a mod 3) → hex z 6 trójkątów. **Werdykt: grubość linii DO WYBORU** — presety cienki/średni/gruby, przy wdrożeniu parametr GUI/CLI. Generator: `src/tools/gen_grout_proposals.py`.
- **Sunflower (fyllotaksja Vogela) — ZAMKNIĘTY na `ea4fe49`:** 7 głównych ZAAKCEPTOWANYCH — soft (Lloyd ×2), disc (2 strefy, rev4 = jedna złota paleta bez ciemnego dysku), rings (rzędy koncentryczne), grande (r=c·n^0.66, faworyt), grande_xl (n^0.75), grande_soft, grande_inverse (n^0.40). Werdykt środka rhombs (rev4, `ea4fe49`): **nopole/funnel/star ZAAKCEPTOWANE do assets**; star2/chunky odrzucone, generatory usunięte. Generator: `src/tools/gen_sunflower_schemes.py` (commity 56590d3 + ea4fe49). Szczegóły w auto-memory [[project_sunflower_grout]].
- **Lekcje techniczne rhombs (log-spirala):** (1) stała para parastychii na siatce r=c√n degeneruje w NAKŁADAJĄCE się łuski poza swoim pierścieniem dominacji — samopodobna siatka quadów wymaga r=r0·e^(kn) (każdy quad = obrócona/przeskalowana kopia sąsiada); (2) dziura wewnętrzna siatki ma ZAWSZE F1+F2 krawędzi niezależnie od N0 (samopodobieństwo) — problemu środka nie da się „zmniejszyć", trzeba go zamknąć komórkami; (3) baseline rasteryzacji: PIL wypełnia krawędzie obustronnie ⇒ DOKŁADNA partycja raportuje ~4.4% „overlaps" przy res=600 — realny problem widać dopiero znacznie powyżej (zepsuta siatka: 11%).

[2026-07-07] **Grout hierarchiczny WDROŻONY do SmartEngine** (commity 59dd0c7, ed23955, e11abde, f89f159 — wypchnięte; 209 testów zielonych; auto-memory [[project_grout_engine]])
- **Architektura:** nowy `src/grout.py` (geometria niezależna od silnika: `sub7`, `classify_edges`, `draw_grout`, `PRESETS` cienki/sredni/gruby, `scale_widths`, `stable_seed`) — wydzielony z `gen_grout_proposals.py` (usunięta duplikacja). Silnik: param `grout_preset` (None|preset) w `_do_render`/`create_mosaic`/`render_preview`; `_grout_cells_{square,hexagon,triangle,kites}` + `_apply_grout` (rysuje po blendzie jako twarda nakładka). `grout_preset=None` = BIT-W-BIT baseline (golden testy bez zmian). CLI `--grout PRESET` (batch suffix `_grout-{preset}`); GUI `CTkOptionMenu` „Hierarchical Grout".
- **Werdykty usera (2026-07-07):** grout = OSOBNY opt-in tryb (kafle się stykają, linie na wierzchu; `border_mode` shrink-gap NIETKNIĘTY, przemianowany w GUI na „uniform gap"); **4 kształty z hierarchią** (square/hexagon/triangle/kites) + reszta PŁASKA L1 (**follow-up — NIEZROBIONE**: romb/hexagon_romb/rectangle_3x1/brick_wall/spectre).
- ⚠ **LEKCJA (bug wykryty wizualnie):** hexagon grout z `th=int(base_s*1.155)` (jak composite) przy `step_y=base_s*0.866` = geometria NIESPÓJNA → przekątne sąsiednich rzędów się nie spotykają → `classify_edges` widzi same ramki (L3) → płaski grout z czarnymi przerwami. Composite to toleruje (maski nakładają się rastrowo), grout rysuje KONTURY. Fix: `th=base_s*2/√3` FLOAT ⇒ `th*0.75==step_y`. ZASADA: geometria groutu musi teselować SAMA ZE SOBĄ; <1px różnicy od composite ukryte pod grubością linii + 2% overlap.
- **Konwersja offset→axial (hexagon, dla spójnych kwiatów sub7):** `q = c - (r-(r&1))//2`, `r_ax = r` (zweryfikowane geometrycznie: span kwiatu < 2.5·base_s). Triangle/kites w silniku mają geometrię IDENTYCZNĄ z propozycją — reużyte grupowanie owner-corner/parent-hex.
- **Fix determinizmu:** `hash(str)` jest solony per-proces (PYTHONHASHSEED) → psuł seed w narzędziu; zastąpiony `zlib.crc32` (`stable_seed`).

[2026-07-08] **Grout flat-L1 DOMKNIĘTY + DZI polish + cleanup** (commity 594a01c, f9732b8, 47642a4, 3ee163c, 18e0b7c, 3fbe101, 22504ba, 7010d36 — wypchnięte; 253 testy zielone; auto-memory [[project_grout_engine]], [[project_dzi_gui_polish_todo]])
- **Flat-L1 grout — werdykt „4+flat" zrealizowany w 100%** dla 5 pozostałych kształtów. Każdy `_grout_cells_*` zwraca komórki z jednakowym `(g2,g3)=(0,0)` → szwy L1, ramka L3. `_apply_grout` rozgałęzione: `_HIERARCHICAL_GROUT=(square,triangle,hexagon,kites)` → grubości gradowane; reszta → jednolite `{1:w,2:w,3:w}` z `w=scale_widths[1]`. **DECYZJA A (user):** ramka kadru RYSOWANA (L3>0), spójnie z trybem hierarchicznym. hexagon_romb = **wariant 2** (user): 3 romby/hexagon (wewnętrzny „Y"), bo composite składa hex z 3 masek=3 zdjęć.
- ⚠ **META-LEKCJA th-vs-step:** maski NAKŁADAJĄCE się poza step (hexagon/romb) → grout musi użyć FLOAT wymiaru (int rozjeżdża szwy → brak wspólnych krawędzi, przypomnienie lekcji hexagonu z 07-07). Kształty ABUTUJĄCE dokładnie (rectangle_3x1/brick_wall) → ODWROTNIE, INTEGER step (float otwiera 1-px szczeliny). brick_wall: offset pół-cegły → T-junctions na poziomej fudze, nieszkodliwe przy flat. Test-strażnik dla obu: `len(by_level[1]) > len(by_level[3])`.
- **Sunflower schematy zunifikowane** pod prefiks `sunflower_*` (grande_{soft,inverse,xl} → sunflower_grande_*); nazwa pliku-schematu = przyszła nazwa trybu, więc rodzina grupuje się w GUI/CLI. [[project_sunflower_grout]].
- **DZI polish (dług A2 domknięty):** `make_dzi` + `progress_cb(done,total)` (kontrakt jak render, throttle ~100), pasek postępu w GUI (wzorzec pasków renderu), `tests/test_dzi.py` (4 testy). [[project_dzi_gui_polish_todo]].
- **Cleanup:** etykieta GUI/CLI „Hierarchical Grout" → „Grout" (flat dla 5 czyni „Hierarchical" nieścisłym; logika bez zmian).

[2026-07-11b] **KSZTAŁTY: rozstrzygnięcie 2 otwartych pytań (girih, truchet) — sesja konsultacyjna, ZERO zmian w kodzie**
- **TRUCHET: `_CurvedMask` NIEPOTRZEBNY — truchet ×2 to zwykłe kształty `polygon`.** Precedens rozstrzygający: **sunburst** (`_sun_arc`, `engine_smart.py:981`) polygonizuje łuk ze stałym krokiem w px tak, że strzałka cięciwy jest sub-pikselowa — przy `aa=4` w `_LazyMask` nieodróżnialne od prawdziwej krzywej. Ćwierćkole truchetu = `_sun_arc(r=base_s/2, …)` doklejone do 2 boków kwadratu. Warunki brzegowe już udowodnione w kodzie: **niewypukłość** komórek OK (spectre jest niewypukły; `ImageDraw.polygon` fill scanline), **wspólna krawędź** dokładna jeśli oba sąsiadujące poligony wołają ten sam `_sun_arc` z tymi samymi argumentami (wzorzec `edge()` z rosette_fractal). Krok polygonizacji MUSI być liczony z `base_s` (nie stały) — inaczej strzałka rośnie w 16K. **Skutek: truchet spada z „najdroższy (nowa maszyneria)" na „jeden z najtańszych"** (generator + wpis w rejestrze + golden); flat grout i `wmask` dostaje za darmo. Rewizja tylko gdyby prototyp pokazał migotanie szwu przy aa=4 (sunburst nie migocze, a ma więcej łuków/kadr).
- **GIRIH: stały zamrożony `_GIRIH_SEED`, sweep OFFLINE — NIE `_shape_seed(base_s,w,h)`.** Randomizacja w girih nie wypełnia kadru (jak chmura punktów voronoi), tylko rozstrzyga kolejność prób w greedy → jakość (pokrycie 94-99%) mocno od niej zależy. Seed per-wymiary ⇒ **preview 2K mógłby trafić dobry patch, a render 16K dziurawy** (i nikt się nie dowie do końca renderu). Stały seed = „ten sam wzór, tylko więcej go". Sweep raz, w commitowanym skrypcie `src/tools/` (drukuje pokrycie per seed), zwycięzca jako stała z komentarzem o zmierzonym pokryciu.
- ⚠ **GIRIH — PRAWDZIWA BLOKADA to `commit()`, nie seed:** `gen_fable_shape_schemes.py:626-627` robi `occ_np[:] = np.array(occ)` — PEŁNĄ kopię rastra okupacji po KAŻDYM kaflu. W schemacie nieszkodliwe (raster 572², setki kafli); w silniku przy 16K ~24k kafli × raster dziesiątek MB = setki GB memcpy ⇒ girih w ogóle nie wstanie. Fix: rysować kafel do bufora wielkości bboxa i OR-ować w `occ_np[y0:y1, x0:x1]` ⇒ O(pole kadru) zamiast O(kafle × pole kadru).
- **GIRIH — skala i dziury:** `RAD` musi ROSNĄĆ z przekątną kadru (w jednostkach girih), inaczej rozmiar komórki zależy od rozdzielczości i łamie inwariant „pole dominującego kafla ~ `base_s²`". Domykanie dziur convex-hullem JEST deterministyczne (scipy `label` + Qhull na ustalonym rastrze), ale **inflację 1.10 zejść do ~1.0**: w schemacie nakładka chowa się pod konturami (malowana ostatnia), w silniku nakładające się poligony = dwa zdjęcia walczące o piksele (późniejszy sektor zamalowuje krawędzie sąsiadów). Uszczelnienie szwu zostawić `render_padding`; bramka = rasteryzacja pokrycia, cel 0% dziur. Fallback gdyby greedy był za wolny po fixie (spodziewane 1-3 s @16K = najwolniejszy kształt, akceptowalne): girih podstawieniowy à la Lu-Steinhardt (deterministyczny, bez rastra, bez dziur) — ale to zadanie badawcze, nie zaczynać od niego.
- **Kolejność wdrożenia ustalona:** voderberg + escher_lizard + weave (kod istnieje) → truchet ×2 (właśnie potaniał) → girih (fix `commit()` + sweep offline) → poincare (najdroższy: BFS odbić, model pasmowy).

---

## Odrzucone podejścia

[2026-07-11] **`_CurvedMask` (osobna maszyneria masek krzywoliniowych) — ODRZUCONY, nie wracać**
- PLAN_SHAPES zakładał `_CurvedMask` jako warunek truchet ×2 („Tier B"). Zbędny: polygonizacja łuku z sub-pikselową strzałką + `aa=4` w `_LazyMask` daje ten sam wynik rastrowy, a sunburst udowodnił to w produkcji. Szczegóły w sekcji TODO, wpis [2026-07-11b].

[2026-07-05b] **Sunflower — odrzucone przez usera** (nie proponować ponownie):
- `sunflower_classic` (Voronoi Vogela, biegun w środku, złoto) — za blisko istniejącego `bloom`; różnica tylko paletą to za mało
- `sunflower_corner` (biegun w rogu kadru) i `sunflower_field` (2-3 głowy ściśnięte Voronoiem) — odrzucone wprost; generatory usunięte (historia w gicie, commit db6cee5)
- Środki rhombs — 3 nieudane podejścia zanim zapadł werdykt „same romby": 55 klinów z bieguna (slivery 9:1), pierścienie per-krawędź pętli (sunburst — pętla ma 55 krawędzi vs ~34 quady/obwód siatki), pierścienie skalowane pętlą (dziedziczą gwiaździsty zygzak; pętla to gwiazda ±25% promienia)

[2026-07-05] **Fraktale — 3 pomysły SKREŚLONE przez usera po procesie adwersarialnym** (nie proponować ponownie):
- `droste_infinite_zoom` (doklejane poziomy piramidy DZI poniżej natywnej rozdzielczości): make_dzi ładuje jeden raster i resizuje w dół — wymagałoby proceduralnego generatora kafli + custom TileSource w JS; oś „nieskończonego zanurzenia" przejęta przez zoom_movie
- `julia_field_mod` (pole Julii/Mandelbrota moduluje rotację/nasycenie PO doborze kafla): motyw nie przetrwa podmiany kolorów zdjęciami — czyta się jako brud renderu; wróciłby tylko jako sterowanie DOBOREM (inny pomysł)
- `fractal_dimension_match` (wymiar fraktalny box-counting jako cecha dopasowania): na kafelku 75 px fit log-log z 2-3 punktów = szum; plus reindeks ~455k kafli i trzeci duplikowany inwariant wagi obok EDGE_WEIGHT

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
