## ═══ Sesja zarchiwizowana [2026-07-09 23:37] ═══

# last_session.md

**Sesja:** 2026-07-08 · (Fable 5) · sesja wieczorna (2. tego dnia)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 0d2c5f8 @ main (zsynchronizowane z origin/main; oba commity sesji wypchnięte)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Punkt 4 planu jakości: nakładka hires dla biblioteki kafelków.** Dwa elementy:

1. **Resolve ścieżki w silniku** — w `src/engine_smart.py`, w pętli składania (`_do_render`, okolice `Image.open(self.paths[best_idx])` ~linia 1240): przed otwarciem sprawdź `data/tiles_hires/{Path(path).name}`; jeśli istnieje → użyj wersji hires, inaczej oryginał. Jedna mała funkcja `_resolve_tile_path(path)` + test.
2. **Skrypt `src/tools/upgrade_tiles.py`** — wejście: lista używanych kafelków (najprościej: zrzut `used_counts>0` z renderu do JSON, albo skan `paths` po ostatnich mozaikach); filtr kafelków picsum (deterministyczny seed w nazwie/URL — sprawdź format nazw plików w `data/library_public/tiles/`); pobranie `picsum.photos/seed/{idx}/512` do `data/tiles_hires/`; skip-if-exists (idempotentny jak batch CLI). Prywatne zdjęcia: generacja 512 px z oryginałów usera (katalog do ustalenia z userem); Real-ESRGAN tylko jako przyszły fallback dla loremflickr.

Kontekst: punkty 1+2+3 planu jakości WDROŻONE w tej sesji (commity 3dd42d9 + 0d2c5f8, deltaE −9%); punkt 4 to ostatni. Biblioteka ~250 px mięknie od tile_scale≈2.5 przy upscalingu. Decyzja usera: BEZ pełnego re-downloadu; rekomendacja (zaakceptowana): nakładka + selektywny re-fetch po seedzie wg used_counts. ALTERNATYWA (starszy tor, jeśli user woli): wiring `sunflower_grande` do silnika (szczegóły w archiwum sesji 2026-07-08 poranna).

---

## Co zrobiono w tej sesji

- ✓ **Analiza jakości dopasowania/kafelków** (na prośbę usera): znalezione 3 realne wady — brak mean-fill w gałęziach grid, asymetria „dopasowujemy co innego niż pokazujemy" (indeks=całe zdjęcie vs render=crop+maska), zapis JPEG 4:2:0; biblioteka zmierzona: ~250 px (dominanta 333×250, próbka 800 plików).
- ✓ **Plan jakości 4 punktów ZATWIERDZONY przez usera** i zapisany w auto-memory (`project_tile_quality_plan`).
- ✓ **Punkty 1+2 WDROŻONE** (commit 3dd42d9): `subsampling=0` dla .jpg/.jpeg (zweryfikowane sampling code 2→0) + `_mean_fill_outside_mask` w obu gałęziach grid; deltaE 9.27→9.09; 3 goldeny regen.
- ✓ **Punkt 3 WDROŻONY** (commit 0d2c5f8): `_mask_cell_weights` + ważony re-scoring top-K; DECYZJA ARCH.: re-scoring zamiast sqrt(w)-przed-GEMM (wiele masek w renderze; inwariant A1 nietknięty); deltaE 9.09→8.46 (~7%); `wmask` też w `_polygon_sector` (S2+ za darmo); 6 nowych testów (test_masked_weights.py); 7 goldenów regen., square/False bit-w-bit przez OBIE zmiany (dowód izolacji GEMM).
- ✓ **Decyzja usera pkt 4:** bez pełnego re-downloadu; zaakceptowana rekomendacja nakładki `tiles_hires/` + re-fetch po seedzie (picsum deterministyczny) wg `used_counts`; prywatne z oryginałów; ESRGAN tylko fallback loremflickr.
- ✓ **Agenci adwersarialni ponownie ODRZUCENI** dla tego typu zadań (potwierdzenie decyzji z 2026-06-27; zadanie inline > zimny kontekst subagentów).
- ✓ **231 testów zielonych** (było 225; +6). Oba commity WYPCHNIĘTE. Weryfikacja empiryczna każdej zmiany (deltaE LAB + porównania wizualne + sampling code).

## Co zostało (backlog sesji)

- ⟳ **Punkt 4 planu jakości** — nakładka tiles_hires (NASTĘPNY KROK).
- ⟳ **Wiring nowych kształtów** (sunflower×7 + rhombs×3, start: `sunflower_grande`) — tor odłożony z sesji porannej, wciąż aktualny.
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ Standing: galeria 16K triangle+hexagon (pliki usera); pasek DZI w GUI wciąż niesprawdzony w realnym `python -m src.gui`.

## Aktywne pliki

- `src/engine_smart.py` (`_mask_cell_weights`, re-scoring w pętli dopasowania, mean-fill grid, `subsampling=0` w `create_mosaic`, `wmask` w 5 miejscach)
- `tests/test_masked_weights.py` (NOWY, 6 testów), `tests/test_golden_shapes.py` (goldeny 2× regen. z komentarzem)
- `MEMORY.md` repo (wpis [2026-07-08] plan jakości + decyzja arch.)

## Otwarte pytania

- Format nazw plików kafelków picsum — czy seed da się odtworzyć z nazwy pliku? (do sprawdzenia na starcie punktu 4, determinuje kształt upgrade_tiles.py).
- Gdzie leżą oryginały prywatnych zdjęć usera (pełna rozdzielczość) do lokalnej generacji 512 px?
- Top-K=200 przy ważonym re-scoringu — czy recall wystarcza dla mocno maskowanych kształtów (kites ~50%)? Ewentualny follow-up: podbić top_k dla wmask≠None, zmierzyć.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis [2026-07-08] w sekcji Architektura — plan jakości 1+2+3 wdrożony, decyzja re-scoring vs GEMM (inwariant A1), empiria deltaE, plan punktu 4 z odrzuconym pełnym re-downloadem.
- Auto-memory: `project_tile_quality_plan` utworzone i aktualizowane na bieżąco (statusy 1+2+3 WDROŻONE + decyzja pkt 4); indeks MEMORY.md zsynchronizowany.

## ═══ Sesja zarchiwizowana [2026-07-08 23:07] ═══

# last_session.md

**Sesja:** 2026-07-08 · (Opus 4.8) · ~21:00-22:10
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 7010d36 @ main (zsynchronizowane z origin/main; wszystkie commity sesji wypchnięte)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring pierwszego kształtu sunflower do silnika: `sunflower_grande` (faworyt usera) jako shape polygon-owy.** Konkretnie w `src/engine_smart.py`:

1. Dodaj generator `_gen_sunflower_grande(engine, target_w, target_h, base_s)` yieldujący poligony komórek w image space — zaadaptuj geometrię z `src/tools/gen_sunflower_schemes.py::gen_sunflower_grande` (Voronoi na ziarnach Vogela `r=c·n^0.66`), przeskaluj z układu montażu do `target_w×target_h`, przytnij komórki brzegowe do kadru (`_clip_rect` już istnieje w narzędziach). Wzór adaptera = `_gen_spectre` (linia ~131: cienki adapter nad zewnętrzną geometrią).
2. Zarejestruj w `SHAPE_MODES` (dict ~156-169) jako `ShapeSpec("polygon", generator=_gen_sunflower_grande, aa=4)` — jeśli `_do_render` ma już gałąź polygon-sector (`_polygon_sector`), wpina się bez nowej gałęzi; jeśli nie, dodaj po wzorze spectre (~767).
3. Podłącz do `shape_names()` → GUI `combo_shape` i CLI `_SMART_SHAPES`.
4. Golden test w `tests/test_golden_shapes.py` + weryfikacja wizualna overlay (jak przy groucie: `_apply_grout` nie dotyczy — to nowy kształt, nie fuga).

Kontekst: schematy sunflower są tylko podglądowymi PNG — silnik ich NIE generuje. To otwiera duży tor „wiring nowych kształtów" (sunflower×7 + rhombs×3 → selekcja finalna z PLAN_SHAPES). `sunflower_grande` to najmniejszy pierwszy krok (jeden wariant, faworyt). ALTERNATYWA (drugi tor, gdyby user wolał): PLAN_FRACTAL F1a — trójfazowa pętla renderu z golden bit-w-bit.

---

## Co zrobiono w tej sesji

- ✓ **Grout flat-L1 DOMKNIĘTY dla 5 kształtów** — werdykt „4+flat" zrealizowany w 100%. spectre (f9732b8), romb (47642a4), rectangle_3x1+brick_wall (3ee163c), hexagon_romb wariant 2 (18e0b7c). Każdy `_grout_cells_*` → komórki z jednakowym `(g2,g3)=(0,0)`; `_apply_grout` rozgałęzione (hierarchiczne 4 → grubości gradowane; reszta → jednolite `{1:w,2:w,3:w}`).
- ✓ **DECYZJA A (user):** ramka kadru RYSOWANA dla flat (L3>0), spójnie z hierarchicznym. Zilustrowane realnym renderem PIL (scratchpad).
- ✓ **hexagon_romb = wariant 2 (user):** 3 romby/hexagon (wewnętrzny „Y"), bo composite składa hex z 3 masek=3 zdjęć.
- ✓ **META-LEKCJA th-vs-step:** maski nakładające (hexagon/romb) → FLOAT wymiar; abutujące (rectangle/brick) → INT step. Test-strażnik `L1>L3`.
- ✓ **Rename schematów sunflower** (594a01c): `grande_{soft,inverse,xl}` → `sunflower_grande_*` (unifikacja rodziny pod prefiks; nazwa pliku = przyszła nazwa trybu). Generator `gen_sunflower_schemes.py` zsynchronizowany.
- ✓ **DZI polish** (22504ba): `make_dzi` + `progress_cb(done,total)`; pasek postępu GUI (wzorzec pasków renderu); `tests/test_dzi.py` (4 testy). Domknięty dług A2.
- ✓ **Cleanup etykiet** (3fbe101, 7010d36): GUI/CLI „Hierarchical Grout" → „Grout" (flat dla 5 czyni „Hierarchical" nieścisłym); komentarze zsynchronizowane.
- ✓ **253 testy zielone** (było 209; +44). Wszystkie 8 commitów WYPCHNIĘTE na origin. Weryfikacja wizualna każdego kształtu grout.

## Co zostało (backlog sesji)

- ⟳ **Wiring nowych kształtów** (sunflower×7 + rhombs×3) do silnika → selekcja finalna z PLAN_SHAPES (NASTĘPNY KROK = pierwszy wariant `sunflower_grande`).
- ⟳ **PLAN_FRACTAL wykonawczy** — start F1a (trójfazowa pętla, golden bit-w-bit). Alternatywny tor.
- ⟳ Standing: galeria 16K triangle+hexagon (pliki usera).

## Aktywne pliki

- `src/engine_smart.py` (grout flat: `_grout_cells_flat_{spectre,romb,rect,hexagon_romb}` + `_HIERARCHICAL_GROUT` + rozgałęzienie `_apply_grout`)
- `tests/test_grout_engine.py` (+8 testów flat), `tests/test_dzi.py` (NOWY, 4 testy)
- `src/tools/make_dzi.py` (progress_cb), `src/gui.py` (pasek DZI + etykieta Grout), `src/cli.py` (help)
- `src/tools/gen_sunflower_schemes.py` (rejestr/nazwy sunflower_grande_*)
- `assets/shape_schemes/sunflower_grande_{soft,inverse,xl}.png` (rename)

## Otwarte pytania

- Który tor backlogu jako główny na następną sesję: sunflower wiring (rekomendowany, NASTĘPNY KROK) czy PLAN_FRACTAL F1a? (nierozstrzygnięte — user wybrał w tej sesji tylko DZI polish).
- Pasek postępu DZI zweryfikowany tylko przez testy make_dzi; widget CTk niesprawdzony headless — potwierdzić przy realnym `python -m src.gui`.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis [2026-07-08] — grout flat-L1 domknięty (decyzja A, hexagon_romb wariant 2, META-LEKCJA th-vs-step), rename sunflower, DZI polish, cleanup etykiet.
- Auto-memory: `project_grout_engine` zaktualizowane (flat-L1 + meta-lekcja + decyzja A); `project_dzi_gui_polish_todo` → ZROBIONE; indeks MEMORY.md zsynchronizowany.


## ═══ Sesja zarchiwizowana [2026-07-08 22:10] ═══

# last_session.md

**Sesja:** 2026-07-07 · (Opus 4.8)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** d8e03d6 @ main (zsynchronizowane z origin/main; commit stanu tej sesji dochodzi na górze)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Grout flat-L1 — zacznij od `spectre` (najprostszy).** W `src/engine_smart.py` dodaj `_grout_cells_flat_spectre(target_w, target_h, base_s)`: iteruj `generate_spectre_tiling(...)`, dla każdego `spec` emituj `(list(spec.points), 0, 0)` (jednakowy group-id ⇒ tylko L1 + ramka). Podłącz w dispatcherze `_grout_cells` (dziś `return None` dla spectre). W `_apply_grout` dla kształtów flat użyj jednej grubości na wszystkich poziomach: `level_w = {1: w, 2: w, 3: w}` (dziś `scale_widths` daje L1<L2<L3 — dla flat to niepożądane), więc rozgałęź: hierarchiczne 4 → `scale_widths(preset, base_s)`; flat → `{1:w,2:w,3:w}` gdzie `w = scale_widths(preset, base_s)[1]`. Dodaj test do `tests/test_grout_engine.py` (spectre: cells != None, wszystkie group-id równe, render z grout != baseline). Potem powtórz dla romb/hexagon_romb/rectangle_3x1/brick_wall (poligon z pętli composite; UWAGA na float-th jak w hexagonie — [[project_grout_engine]]).

Kontekst: werdykt usera „4 z hierarchią + reszta płaska L1" zrealizowany tylko w połowie — hierarchiczna czwórka (square/hexagon/triangle/kites) działa, 5 pozostałych kształtów daje dziś no-op z notą. Spectre ma już jawne poligony, więc jest najtańszym pierwszym krokiem domknięcia.

---

## Co zrobiono w tej sesji

- ✓ **Sprzątanie: przerwany /end domknięty** (c41783f): pliki stanu z 2026-07-06 były niezacommitowane i błędnie opisywały sunflower jako urwany WIP — w rzeczywistości domknięty (56590d3+ea4fe49, sunflower ZAMKNIĘTY). last_session.md → ea4fe49, poprawka wpisu w repo MEMORY.md.
- ✓ **Grout Stage 1 — src/grout.py** (59dd0c7): produkcyjny moduł geometrii (sub7, classify_edges, draw_grout, PRESETS, scale_widths, stable_seed) wydzielony z narzędzia propozycji; usunięta duplikacja; fix determinizmu seeda (crc32 zamiast solonego hash()). +11 testów.
- ✓ **Grout Stage 2 — border pass w silniku** (ed23955): param `grout_preset` (osobny opt-in tryb; border_mode nietknięty), hierarchia dla square/hexagon/triangle/kites. `grout_preset=None` = bit-w-bit baseline. LEKCJA: hexagon th musi być FLOAT `base_s*2/√3` (int rozjeżdża przekątne → brak wspólnych krawędzi; bug wykryty wizualnie). +9 testów.
- ✓ **Grout CLI** (e11abde): `--grout PRESET` obok `--border`; batch name suffix `_grout-{preset}`. +2 testy.
- ✓ **Grout GUI** (f89f159): `CTkOptionMenu` „Hierarchical Grout" w Smart tab; wpięte w podgląd on-demand i render pełny.
- ✓ **Weryfikacja wizualna** (scratchpad/grout_engine_visual.png) — 4 kształty poprawne. **209 testów zielonych** (było 187; +22). Wszystkie commity WYPCHNIĘTE na origin.

## Co zostało (backlog sesji)

- ⟳ **Grout flat-L1 dla 5 kształtów** (NASTĘPNY KROK; spectre → romb/hexagon_romb/rectangle_3x1/brick_wall).
- ⟳ **Wiring nowych kształtów** (sunflower×7 + rhombs×3) do silnika → selekcja finalna z PLAN_SHAPES.
- ⟳ **PLAN_FRACTAL wykonawczy** — start F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ Standing: galeria 16K triangle+hexagon (pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/grout.py` (NOWY — geometria groutu), `tests/test_grout.py`, `tests/test_grout_engine.py`
- `src/engine_smart.py` (border pass + `_grout_cells_*` + param grout_preset)
- `src/cli.py` (--grout), `src/gui.py` (selektor), `src/tools/gen_grout_proposals.py` (import z src.grout)

## Otwarte pytania

- Płaski grout — czy ramka kadru też ma być rysowana (dziś krawędzie ramki = L3), czy tylko krawędzie wewnętrzne? (rozstrzygnąć przy pierwszym flat — spectre).
- Nazewnictwo finalne schematów grande_* w assets (przy wiringu sunflower do silnika).

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: [2026-07-07] — grout WDROŻONY (architektura src/grout.py + border pass 4 kształtów; lekcja float-th hexagonu; offset→axial q=c-(r-(r&1))//2; fix determinizmu crc32); werdykty usera (osobny tryb, 4+flat, follow-up).
- Auto-memory: nowy `project_grout_engine` (pełna architektura + lekcje + follow-up).


## ═══ Sesja zarchiwizowana [2026-07-07 23:24] ═══

# last_session.md

**Sesja:** 2026-07-07 · (Opus 4.8)
**Status:** ⟳ W TOKU (checkpoint) — grout wdrożony do silnika + CLI + GUI; follow-up: flat-L1 dla 5 kształtów
**Punkt odniesienia (git):** f89f159 @ main (working tree czysty poza tym plikiem stanu; commity tej sesji NIE wypchnięte na origin)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Grout — flat-L1 dla pozostałych 5 kształtów** (werdykt usera: „4 z hierarchią + reszta płaska L1"; zrobiona tylko hierarchiczna czwórka):

1. Dodaj `_grout_cells_flat` dla romb / hexagon_romb / rectangle_3x1 / brick_wall / spectre → komórki (poly, g2, g3) z JEDNAKOWYM group-id (wszystkie równe) tak, by `classify_edges` dało tylko krawędzie wewnętrzne + ramkę; rysuj wszystkie jednym poziomem: `level_w={1:w,2:w,3:w}` (albo dedykowany helper flat).
2. Geometria per kształt: spectre ma już jawne poligony (`spec.points` — trywialne); romb/hexagon_romb/rectangle_3x1/brick_wall wymagają odtworzenia poligonu z pętli composite (`pos_x,pos_y,tile_w,tile_h` + kształt maski z `_get_shape_mask`). UWAGA na tę samą pułapkę co hexagon: geometria groutu musi teselować SAMA ZE SOBĄ (patrz auto-memory [[project_grout_engine]] — float th, nie int).
3. Podłącz w `_grout_cells` dispatcher (dziś zwraca None dla tych 5) i zdejmij no-op notę. Rozszerz testy w `tests/test_grout_engine.py`.
4. (Opcjonalnie) bordery na schematach w podglądzie GUI, gdy grout != Off.

Alternatywnie następny wątek z backlogu (jeśli user woli): wiring nowych kształtów sunflower/rhombs do silnika (PLAN_SHAPES), albo PLAN_FRACTAL F1a.

---

## Co zrobiono w tej sesji

- ✓ **Sprzątanie: przerwany /end domknięty** (c41783f): pliki stanu z 2026-07-06 były niezacommitowane i opisywały sunflower jako urwany WIP — w rzeczywistości domknięty commitami 56590d3+ea4fe49 (sunflower ZAMKNIĘTY). Zaktualizowano last_session.md → ea4fe49, poprawiono wpis w repo MEMORY.md.
- ✓ **Grout Stage 1 — src/grout.py** (59dd0c7): produkcyjny moduł geometrii (sub7, classify_edges, draw_grout, PRESETS, scale_widths, stable_seed) wydzielony z narzędzia propozycji; narzędzie importuje stąd (usunięta duplikacja); fix determinizmu seeda (crc32 zamiast hash() solonego per-proces). +11 testów.
- ✓ **Grout Stage 2 — border pass w silniku** (ed23955): param `grout_preset` (osobny opt-in tryb wg werdyktu; border_mode nietknięty), hierarchia dla square/hexagon/triangle/kites. `_grout_cells_*` odtwarzają geometrię kafli; grout rysowany po blendzie. `grout_preset=None` = bit-w-bit baseline. LEKCJA: hexagon th musi być FLOAT base_s*2/√3 (int rozjeżdża przekątne → brak wspólnych krawędzi; bug wykryty wizualnie). +9 testów.
- ✓ **Grout CLI** (e11abde): `--grout PRESET` obok `--border`; batch name suffix `_grout-{preset}`. +2 testy.
- ✓ **Grout GUI** (f89f159): `CTkOptionMenu` „Hierarchical Grout" Off/cienki/sredni/gruby w Smart tab; wpięte w podgląd on-demand i render pełny.
- ✓ **Weryfikacja wizualna:** montaż z geometrii silnika (scratchpad/grout_engine_visual.png) — 4 kształty poprawne. **209 testów zielonych** (było 187; +22 grout).

## Werdykty usera (2026-07-07)

- Grout = OSOBNY opt-in tryb (kafle się stykają, linie na wierzchu); `border_mode` shrink-gap zostaje niezależny (przemianowany w GUI na „uniform gap").
- 4 kształty z hierarchią (square/hexagon/triangle/kites) + reszta PŁASKA L1 (reszta = follow-up).
- Preset domyślny „średni" (i tak wybieralny).

## Co zostało (backlog)

- ⟳ **Grout flat-L1 dla 5 kształtów** (NASTĘPNY KROK).
- ⟳ **Wiring nowych kształtów** (sunflower×7 + rhombs×3) do silnika → selekcja finalna z PLAN_SHAPES.
- ⟳ **PLAN_FRACTAL wykonawczy** — start F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ **Push:** commity tej sesji (c41783f..f89f159) NIE wypchnięte na origin — do decyzji usera.
- ⟳ Standing: galeria 16K triangle+hexagon (pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/grout.py` (NOWY — geometria groutu), `tests/test_grout.py`, `tests/test_grout_engine.py`
- `src/engine_smart.py` (border pass + `_grout_cells_*` + param grout_preset)
- `src/cli.py` (--grout), `src/gui.py` (selektor), `src/tools/gen_grout_proposals.py` (import z src.grout)

## Otwarte pytania

- Płaski grout — czy ramka kadru też ma być rysowana (dziś L3), czy tylko krawędzie wewnętrzne?
- Nazewnictwo finalne schematów grande_* w assets (przy wiringu sunflower do silnika).

## Do MEMORY.md (przeniesiono)

- Auto-memory: nowy `project_grout_engine` (architektura + lekcja float-th hexagonu + konwersja offset→axial + werdykty + follow-up).
- Repo MEMORY.md: wpis o wdrożeniu groutu do dodania przy /end.

## ═══ Sesja zarchiwizowana [2026-07-06 20:54] ═══

# last_session.md

**Sesja:** 2026-07-04 · (druga sesja tego dnia, Fable 5; ~14:00-22:00)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** af581e1 @ main (commit kodu; origin/main = 9aa5416 — af581e1 NIE wypchnięty, push do decyzji)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Pakiet 3 poprawek zleconych przez usera na koniec sesji (wszystkie w `src/tools/gen_extra_shape_schemes.py` + `gen_fable_shape_schemes.py`):**

1. **`sierpinski` — nowy wariant SZACHOWNICA:** duże trójkąty (nośniki pełnego gasketu depth-3) naprzemiennie z wypełnionymi w KAŻDYM rzędzie (co drugi, niezależnie od orientacji góra/dół), a każdy kolejny rząd przesunięty o jeden — układ jak szachownica. Wersje `sierpinski_b` (tylko „góra") i `sierpinski_c` (przeplot co rząd) **ODRZUCONE** — usunąć ich PNG + wpisy SHAPES, próbować dalej. Nośnik: pozycja-w-rzędzie t (licząc oba typy trójkątów) taka, że carrier = (t + r) % 2, ale inaczej niż w c: naprzemienność MA być w obrębie rzędu co drugi trójkąt sekwencyjnie, z przesunięciem +1 na każdy rząd.
2. **`sierpinski_carpet` — wada do naprawy:** najmniejsze „puste" kwadraty (poziom 1, bok 1/27) mają IDENTYCZNY rozmiar jak wypełnione ⇒ po podmianie na kafelki zdjęciowe nieodróżnialne. Trzeba zróżnicować (np. głębsza rekurencja wypełnionych o 1 poziom, żeby najmniejsza dziura była zawsze ≥3× większa od komórki tła; albo usunąć tag dziury z poziomu 1).
3. **`rosette_fractal` / `voderberg` / `girih` — środek z kafelków TEGO SAMEGO kształtu:** czapka N-gon (rosette_fractal, voderberg) i rozeta latawców khatam różna od reszty (girih — tam akurat latawce zostają, chodzi o spójność z resztą) mają być zastąpione kafelkami tego samego kształtu co reszta teselacji, co najwyżej delikatnie zmodyfikowanymi — np. wewnętrzny pierścień trójkątów/klinów zbiegających się WIERZCHOŁKAMI w centrum (bez osobnego „koła").

Kontekst: to bezpośrednie werdykty usera po obejrzeniu montaży z 2026-07-04b. Po tych poprawkach zostaje selekcja finalna (19 paneli extra + 10 Fable) → Sprint 2 (wiring `_polygon_sector`/`SHAPE_MODES` w `_do_render`).

---

## Co zrobiono w tej sesji

- ✓ **Push zaległości** (cedb2ce+75bf7df+9aa5416 → origin/main).
- ✓ **`penrose_p2` — ostatni [ETAP A] DOMKNIĘTY** (zastąpił hirotaka, PNG usunięty): prawdziwe latawce+strzałki P2. Droga: 2 ręczne substytucje Robinsona ZAWIODŁY (T-junctions między rodzicami; 23-87% parowania) → działa **deflacja P3 Preshinga + relacje A/B kafli Robinsona (BS=AL, BL=AL+AS)**, cięcie grubego rombu w U przy |BU|=ramię (kierunek lustrzany: 410 niesparowanych, właściwy: 0), scalanie połówek matchingiem „stopień-1-najpierw" (para = rodzaj + wspólne ramię + wspólny apex; BEZ testu chiralności z etykiet). Weryfikacja numeryczna: kąty kite/dart, proporcja ≈φ, 0 niesparowanych.
- ✓ **Pakiet „niepraktyczny środek" (zlecenia usera w trakcie):** `rosette_fractal` → sektory ×2 co 3 pierścienie (g=2^(1/3), pas podwajający = wachlarz 3 trójkątów); `voderberg` → liczba klinów ~2πr/target per pierścień; `girih` → dekagony dzielone na 10 latawców khatam + domykanie dziur greedy (convex hull pustych komponentów rastra, scipy label+ConvexHull, inflacja 1.10).
- ✓ **`poincare` PRZEPROJEKTOWANY** (user: „usunąć okrąg"): model pasmowy w=(2/π)log((1+z)/(1−z)), okno |y|≤0.80, heptagony → 7 latawców (środek hiperboliczny śledzony przez odbicia; środek krawędzi = próbka t=0.5 łuku). Wersja inwersyjna wyrzucona.
- ✓ **`sierpinski_b`/`sierpinski_c`** (2 warianty równomiernych dużych dziur; helper `_sierp4` capuje dziury nie-nośników na S/4) — na koniec sesji ODRZUCONE przez usera (→ następny krok: szachownica).
- ✓ **`sierpinski_carpet` (#40)** — dywan 3×3 depth-3 na cały kadr (wada zgłoszona → następny krok).
- ✓ Regeneracja WSZYSTKICH schematów + oba montaże; **181/181 testów**; commit `af581e1`.
- ✓ MEMORY.md (repo + auto-memory) zaktualizowane o lekcję P2 i wzorzec „dobrego środka".

## Co zostało (backlog sesji)

- ⟳ **Pakiet 3 poprawek** (NASTĘPNY KROK — werdykty usera).
- ⟳ **Push af581e1** (+commit stanu) na origin/main — do decyzji usera.
- ⟳ **Selekcja finalna kształtów** (19 extra + 10 Fable) → Sprint 2 (`_do_render` wiring; ryzyko bbox spectre w MEMORY [2026-07-02]).
- ⟳ **Standing:** galeria 16K triangle+hexagon (czeka na pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/tools/gen_extra_shape_schemes.py` (penrose_p2 przez P3→A/B; rosette_fractal podwajanie; sierpinski_b/c; carpet; SHAPES=19)
- `src/tools/gen_fable_shape_schemes.py` (voderberg sektory ∝ r; girih kite-split + hole-fill; poincare model pasmowy; import scipy)
- `assets/shape_schemes/*.png` (penrose_p2/sierpinski_b/sierpinski_c/sierpinski_carpet nowe; hirotaka usunięty; girih/poincare/rosette_fractal/voderberg zmienione)

## Otwarte pytania

- Push af581e1 — nie wykonany (bez decyzji usera).
- Czy po poprawce szachownicy usunąć też PNG sierpinski_b/c z repo (ODRZUCONE) — zakładam TAK, w ramach następnego kroku.
- Girih hole-fill: hull może minimalnie zachodzić na sąsiadów (inflacja 1.10) — akceptowalne w schemacie; przy wdrożeniu do silnika wymaga dokładnej geometrii.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis [2026-07-04b] — lekcja P2 (ręczna substytucja = T-junctions; droga P3→A/B z kierunkiem cięcia i matchingiem), wzorzec „dobrego środka" radialnych, poincare pasmowy, warianty sierpińskiego + dywan, werdykty usera z końca sesji (b/c odrzucone → szachownica; carpet wada najmniejszych dziur; środki z kafelków tego samego kształtu).
- Auto-memory: `project_extra_15_shapes` rozszerzone o rewizję 04b (pełna technika P2 + pułapki).


