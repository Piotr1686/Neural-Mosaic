## ═══ Sesja zarchiwizowana 2026-07-27 21:48 ═══

# last_session.md

**Sesja:** 2026-07-26 · 21:00-21:55
**Punkt odniesienia (git):** 75cbf8b @ main
**Status:** ✓ Zakończona poprawnie

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sweep blend/tint na `square` @2K — pomiar szumu w płaskim niebie.**

Konkretnie: wyrenderuj `square` @2K, `PYTHONHASHSEED=1`, scale=0.75,
grout_preset="thin", grout_level=1, edge_aware=ON, mirror=OFF, input
`input/IMG_20220727_095216.jpg` — sześć wariantów: blend ∈ {0.10, 0.20, 0.30}
× tint ∈ {0.10, 0.25}. Dla każdego policz **odchylenie L\* w płacie nieba**
(patch: `[0.03h:0.13h, 0.03w:0.30w]` po konwersji `skimage.color.rgb2lab`,
kanał 0) i porównaj z poziomem odniesienia oryginału = **1,29**. Skrypt
pomiarowy do odtworzenia: `quality.py` ze scratchpada (deltaE + sky std,
opisany w MEMORY.md → Aktywne TODO [2026-07-26] punkt ①).

Kontekst: mozaiki mają szum w niebie **6,3–9,9 vs 1,29 w oryginale (5–8×)** i
jest to jedyna wada **wspólna dla wszystkich 50 kształtów** — czyli tkwi w
dopasowaniu/blendzie, nie w geometrii. Jest to najtańsza dźwignia (zero zmian w
kodzie, metryka gotowa) i **gatuje galerię 16K**: nie ma sensu renderować 50
obrazów @16K przed ustaleniem właściwych blend/tint. Jeśli sweep nie da kolana
— następny podejrzany to `freq_penalty`.

⚠ Rekomendacja moja, **niezatwierdzona przez usera** — user wywołał /end zaraz
po jej przedstawieniu, bez wyboru punktu startowego.

---

## Co zrobiono w tej sesji

- ✓ **Selekcja finalna: rejestr 59 → 50 kształtów** (`077fec3`). Usunięte
  CAŁKOWICIE z projektu (generatory, `SHAPE_MODES`, goldeny, testy, schematy
  `assets/shape_schemes/`, wpisy w `src/tools/gen_*_schemes.py`, stare mozaiki):
  `rhombs_funnel`, `rhombs_nopole`, `rhombs_star`, `sierpinski_carpet`,
  `sierpinski_d`, `sunburst`, `sunflower_disc`, `sunflower_grande_xl`,
  `sunflower_grande_soft`.
- ✓ **−234 linie martwego kodu** — cała maszyneria log-spiralna
  (`_log_quads`/`_log_mesh`/`_bridge`/`_rosette`/`_emit_polys`/`_rh_*`) była
  wyłącznie pod `rhombs_*`; `_sierp4` osierocony po `sierpinski_d`.
- ✓ **`_sun_arc` PRZYWRÓCONY** — mimo nazwy od `sunburst` jest współdzielony
  przez `scales`/`nautilus`/`voderberg`/`truchet`; usunięcie go wywaliło
  25 testów w kształtach nietkniętych.
- ✓ **Kolejność `SHAPE_MODES` → ALFABETYCZNA**; `shape_names()` = 50 nazw.
- ✓ **Dropdown kształtów w GUI w 2 kolumnach** (25+25, bez przewijania) —
  `_spread_dropdown_columns()` w `gui.py`; CTk dropdown to `tkinter.Menu`,
  który wspiera per-wpis `columnbreak`. Zweryfikowane:
  `ammann_beenker..puzzle_classic` | `puzzle_hex..weave`.
- ✓ **`kites` — ząbkowanie krawędzi NAPRAWIONE** (`5f0e5cd`): filtr zmieniony
  z „centroid w kadrze" na „bbox przecina kadr". Pomiar: **2,349% → 0,000%**
  niepokrytego kadru (pasmo dolne 12,57% → 0). Formalny test partycji: suma
  pól przyciętych = **1 080 000,0 = dokładnie pole kadru**.
- ✓ **Zlikwidowane potrojenie przebiegu siatki kites** — jeden `_kite_lattice()`
  + modułowy `_kite_poly()`; konsumują go generator, gałąź `_do_render` i
  `_grout_cells_kites`. Goldeny `kites` zregenerowane, 4 nowe testy.
- ✓ **Sweep pokrycia po wszystkich 53 kształtach polygon** — `kites` był
  JEDYNYM z wadą (reszta 0,000%, `girih` 0,011% = znana otoczka).
- ✓ **Analiza krytyczna 50 mozaik** — 7 punktów z pomiarami (szum w niebie,
  niewidoczność kształtu przy oglądaniu całości, rozjazd ziarna, wielkie
  komórki `sierpinski`, `escher_lizard`, grout, `bloom`) + rekomendacja dla
  każdego. Wszystko w MEMORY.md → Aktywne TODO [2026-07-26].
- ✓ **MEMORY.md zaktualizowane** (`75cbf8b`) + naprawiony drift komentarza w
  `test_grout_engine.py`.
- ✓ **565 testów przechodzi**; oba commity kodu zweryfikowane jako zielone
  OSOBNO (nie tylko stan końcowy).
- ✓ **Push na origin/main** — 8 commitów.

## Co zostało (backlog sesji)

- ⚠ **`output/shapes/…_kites_….jpg` NIEAKTUALNY** — plik z 22.07 22:00,
  geometria zmieniona 26.07. Wymaga ponownego renderu @8K (świadomie odłożone).
- ⟳ **README EN+PL: tabela kształtów wymienia 9 pozycji, rejestr ma 50.**
  Było w backlogu, teraz na ścieżce krytycznej przed publikacją galerii.
- ⟳ **E8 krok 3: galeria 16K** — zablokowana do czasu rozstrzygnięcia blend/tint
  (patrz NASTĘPNY KROK).
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany już
  3× ze scratchpada. Rozważyć utrwalenie jako `src/tools/render_shapes_batch.py`.
- ⟳ Rekomendacje z analizy (kolejność wg mojej oceny): sweep blend/tint →
  usunąć `bloom` → rename `escher_lizard` → kalibracja `scale` dla 4 kształtów
  jednorodnych → A/B `sierpinski` → grout=off dla kształtów o dużym udziale tuszu.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a.

## Aktywne pliki

- `src/engine_smart.py` — rejestr 50 alfabetycznie, `_kite_lattice`/`_kite_poly`,
  usunięte generatory + log-spirale, `_sun_arc` przywrócony.
- `src/gui.py` — `_spread_dropdown_columns()`, `import tkinter`.
- `tests/test_grout_engine.py` — sekcja „kites: the frame edge", helpery
  `_shoelace`/`_clip_to_frame`, `_SIERP_GENS` = 1 wpis.
- `tests/test_golden_shapes.py` — goldeny `kites` zregenerowane, 18 wpisów usuniętych.
- `src/tools/gen_e7_schemes.py`, `gen_sunflower_schemes.py`,
  `gen_extra_shape_schemes.py` — listy SPEC przycięte.
- `MEMORY.md` — 3 nowe wpisy [2026-07-26].
- `output/shapes/` — 50 mozaik 8K (gitignored); **kites nieaktualny**.
- EFEMERYCZNE (scratchpad): `coverage_sweep.py`, `quality.py`, `grain.py`,
  `kites_cover.py`, `contact.py`, `crops2.py`, `make_thumbs.py`.

## Otwarte pytania

- **Od czego zacząć następną sesję** — przedstawiłem 6 rekomendacji z priorytetem,
  user wywołał /end bez wyboru. NASTĘPNY KROK to moja rekomendacja, nie decyzja.
- **`bloom`** — rekomenduję usunięcie (nierozróżnialny od `phyllotaxis` w mozaice:
  dE 11,47 vs 11,44); user go NIE wskazał do usunięcia, więc został.
- **`escher_lizard`** — rename czy prawdziwa sylwetka? Rekomenduję rename.
- **Kalibracja `base_s`** — przed jakąkolwiek zmianą przemierzyć średnią ważoną
  polem `Σa²/Σa`, nie medianą (mediana kłamie dla kształtów bimodalnych).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera, wciąż otwarta.

## Do MEMORY.md (przeniesiono)

- **Rozwiązane problemy** [2026-07-26]: ząbkowanie `kites` + META-LEKCJA
  „golden nie drgnął po celowej zmianie pikseli = dowód, że dotknięty kod NIE
  jest ścieżką produkcyjną" + odruch „grep nazwy kształtu przed zmianą
  geometrii" + formalny test partycji jako instrument.
- **Odrzucone podejścia** [2026-07-26]: lista 9 usuniętych kształtów (nie
  proponować ponownie) + pułapki usuwania (`_sun_arc`, log-spirale, `_sierp4`,
  `gen_e7_schemes`) + kolejność alfabetyczna + dropdown 2 kolumny.
- **Aktywne TODO** [2026-07-26]: analiza krytyczna 50 mozaik — 7 punktów z
  liczbami i rekomendacjami, w tym uwaga metodologiczna o `Σa²/Σa` vs mediana.
- **Architektura**: lista geometrii zastąpiona wskazaniem na `SHAPE_MODES`
  jako jedyne źródło prawdy (poprzednia 9-pozycyjna była nieaktualna).

## ═══ Sesja zarchiwizowana 2026-07-26 21:52 ═══

# last_session.md

**Sesja:** 2026-07-22 · 21:12-21:50
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** b91d42a @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**E8 krok 3 — selekcja finalna usera.** User wybrał tryb „oglądam sam pliki":
przegląda 59 mozaik w `output/shapes/` i wróci z listą kształtów **do
ODRZUCENIA**. Po jej otrzymaniu: odtwórz driver renderu (analogiczny do
efemerycznego `render_all_shapes.py`, ale `resolution="16K"` i TYLKO zatwierdzone
kształty) → `output/gallery_16K/`. Te same parametry co batch 8K
(scale=0.75, blend=0.10, tint=0.10, grout_preset="thin", grout_level=1,
grout_style="solid", grout_color="black", edge_aware=ON, mirror=OFF,
`PYTHONHASHSEED=1`).

Kontekst: E8 krok 2 (render 59 kształtów @8K) ZAMKNIĘTY w tej sesji — 54 OK,
5 SKIP, 0 FAIL, 59/59 plików zdrowych (22,8-36,8 MB). Selekcja to ostatnia bramka
przed galerią 16K. UWAGA do obejrzenia przy selekcji: `sierpinski_carpet`
(22,8 MB = najmniejszy, potwierdza degenerację przy dużym base_s) oraz para
`bloom`↔`phyllotaxis` (kandydat do odrzucenia — bardzo podobne).

---

## Co zrobiono w tej sesji

- ✓ **E8 krok 2 ZAMKNIĘTY: render 59 kształtów @8K** — odtworzono efemeryczny
  driver `render_all_shapes.py` (scratchpad) wg specyfikacji z last_session,
  uruchomiono w tle z `PYTHONHASHSEED=1`, log `logs/render_shapes.log`.
  Wynik: **54 OK, 5 SKIP, 0 FAIL**, 59/59 plików w `output/shapes/`.
- ✓ **Sanity rozmiarów:** wszystkie 22,8-36,8 MB (brak pustych/uszkodzonych).
  Najmniejszy `sierpinski_carpet` (22,8 MB), największe `koch_island` (36,8),
  `dragon` (35,9), `koch_snowflake` (34,9).
- ✓ **Weryfikacja fixów z poprzedniej sesji na pełnym batchu:** grout thin =
  uniform level-1 zadziałał („drawing hierarchical → uniform (level 1 = each
  tile)"); mean-fill krawędzi bez regresji.
- ✓ **Sanity startowy:** potwierdzono że przerwany batch poprzedniej sesji
  zostawił dokładnie 5 gotowych kształtów; restart poprawnie je pominął.

## Co zostało (backlog sesji)

- ⟳ **E8 krok 3:** selekcja finalna usera → galeria 16K (NASTĘPNY KROK).
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany
  już 2× ze scratchpada. Rozważyć zapisanie na stałe jako
  `src/tools/render_shapes_batch.py` (z argumentami: resolution, grout preset,
  output dir) — do decyzji usera.
- ⟳ **README EN+PL:** tabela 59 kształtów + dokumentacja
  `--grout-style`/`--grout-color`/`--grout`/`--grout-level`; panorama 4,0 GB
  osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze (batch
  używał tylko thin).

## Aktywne pliki

- `output/shapes/` — 59 mozaik 8K gotowych (gitignored).
- `logs/render_shapes.log` — pełny log batcha (gitignored).
- EFEMERYCZNE (scratchpad, do odtworzenia lub utrwalenia):
  `render_all_shapes.py`.
- (bez zmian w kodzie — HEAD niezmieniony od `b91d42a`).

## Otwarte pytania

- **`sierpinski_carpet` degeneracja** — obejrzeć w 100% zoom przy selekcji;
  jeśli kilka wielkich kwadratów → kandydat do odrzucenia lub fix base_s.
- **`bloom` vs `phyllotaxis`** — obejrzeć obok siebie; `bloom` kandydat do
  odrzucenia.
- **Rodziny wariantów** (`sunflower_*`×7, `rhomb*`, `sierpinski*`×3, `koch_*`) —
  czy trzymać wszystkie do galerii, czy przerzedzić.
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.

## Do MEMORY.md (przeniesiono)

- Nic nowego — sesja czysto wykonawcza (batch renderu), bez decyzji
  architektonicznych ani rozwiązań trudnych problemów. Empiryczne potwierdzenie
  degeneracji `sierpinski_carpet` odnotowane w Otwartych pytaniach (do
  rozstrzygnięcia przy selekcji, nie utrwalane jako trwały fakt).

## ═══ Sesja zarchiwizowana [2026-07-22 21:45] ═══

# last_session.md

**Sesja:** 2026-07-21 · wieczór (~21:00-23:12)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 0c67c71 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dokończ render 59 kształtów @8K** — pozostało 56 (5 już gotowych w
`output/shapes/`: square, rectangle_3x1, brick_wall, hexagon, hexagon_romb).

UWAGA: driver `render_all_shapes.py` był w scratchpadzie (EFEMERYCZNY, zniknął).
Odtwórz go z tych parametrów (wspólne dla wszystkich 59, wybór usera):
- input `input/IMG_20220727_095216.jpg` → `output/shapes/`
- `SmartEngine(index_path="data/smart_index.pkl")`;
  `settings["edge_aware"]=True`, `settings["allow_mirror"]=False`
- `create_mosaic(inp, out, "8K", shape, tile_scale=0.75, blend_strength=0.10,`
  `tint_strength=0.10, grout_preset="thin", grout_level=1, grout_style="solid",`
  `grout_color="black")` dla każdego `shape` z `shape_names()`
- nazwa: `IMG_20220727_095216_smart_8K_{shape}_grout-thin.jpg`, skip-if-exists
- uruchom z `PYTHONHASHSEED=1`, w tle, log do `logs/render_shapes.log`
- grout thin = **1px** (poziom 1 = uniform po fixie); ~1-3 h (sierpinski_carpet
  najdłużej)

Kontekst: to E8 krok 2 (seria mozaik testowych). Po pełnym renderze → **selekcja
finalna usera** (E8 krok 3) → galeria 16K. Sesja zeszła na naprawę 4 wad groutu/
krawędzi wykrytych na pierwszych renderach, dlatego pełny batch niedokończony.

---

## Co zrobiono w tej sesji

- ✓ **E8 krok 1: `gen_shape_montage.py`** (`99a254f`) — montaż 8×8 wszystkich 59
  schematów (`assets/shape_montage.png`, 2258×2546), kolejność = `shape_names()`,
  bramka 59/59 PNG bez braków. Deliverable do selekcji.
- ✓ **Fix 1 — ciemne pół-kafle na offsetowych krawędziach** (`0c67c71`):
  czarny padding częściowego cropu zatruwał cechę LAB → dopasowanie ciemnego
  kafla (`brick_wall` lewa krawędź). Mean-fill średnią cropu + paste w prawdziwej
  pozycji (branch grid + hexagon_romb). Goldeny `square`+`hexagon_romb` regen.
- ✓ **Fix 2/3 — grout „each tile" pokazywał struktury wyższego rzędu**:
  `_apply_grout` przy `min_level==1` rysuje teraz UNIFORM (wszystkie szwy = L1),
  nie stopniowane L1<L2<L3. Gradacja tylko przy jawnym poziomie ≥2.
- ✓ **Fix 4 + presety grubości** (A/B na realnym 8K): thin/medium/thick =
  **1/3/5 px** @ base_s=75. `PRESETS` w `src/grout.py`.
- ✓ **329 testów zielonych**; goldeny zregenerowane (4 hashe, udokumentowane).
- ✓ 3 sample 8K zweryfikowane wizualnie (square/brick/hexagon) + narzędzie
  porównawcze szerokości 1-10px (`output/grout_width_compare.png`).

## Co zostało (backlog sesji)

- ⟳ **E8 krok 2:** dokończyć render 56 pozostałych kształtów (NASTĘPNY KROK).
- ⟳ **E8 krok 3:** selekcja finalna usera → galeria 16K.
- ⟳ **README EN+PL:** tabela 59 kształtów + dokumentacja
  `--grout-style`/`--grout-color`/`--grout`/`--grout-level`; panorama 4,0 GB
  osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `src/engine_smart.py` — `_apply_grout` (uniform level-1), branch grid +
  hexagon_romb (mean-fill krawędzi).
- `src/grout.py` — `PRESETS` = 1/3/5 px.
- `tests/test_golden_shapes.py` — 4 goldeny regen (square/hexagon_romb ×2).
- `src/tools/gen_shape_montage.py` — NOWE (zacommitowane).
- `output/shapes/` — 5 mozaik gotowych; `output/grout_width_compare.png`.
- EFEMERYCZNE (scratchpad, do odtworzenia): `render_all_shapes.py`,
  `grout_width_compare.py`.

## Otwarte pytania

- **medium=3px / thick=5px NIEzweryfikowane na realnym renderze** — wybrane tylko
  na porównaniu 1-10px; thin=1px potwierdzony na 3 samplach. Batch używa tylko
  thin, więc nie blokuje.
- **Selekcja finalna kształtów** (E8) — kandydat do odrzucenia: `bloom`
  (subtelny, blisko `phyllotaxis`).
- **`sierpinski_carpet` degeneruje się** przy dużym base_s (kilka wielkich
  kwadratów) — obejrzeć w docelowej rozdzielczości.
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** Rozwiązane problemy [2026-07-21] „Trzy wady wykryte dopiero
  na realnym renderze 8K" (mean-fill krawędzi + grout level-1 uniform + presety
  1/3/5px, base_s niezależne od rez).
- **auto-memory:** `project_grout_edge_uniform.md` (NOWY).

## ═══ Sesja zarchiwizowana [2026-07-20 23:00] ═══

# last_session.md

**Sesja:** 2026-07-20 · wieczór (~22:00-23:00)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 280abf2 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**E8 krok 1: montaż zbiorczy wszystkich 59 schematów** — nowe narzędzie
`src/tools/gen_shape_montage.py`, siatka miniatur z `assets/shape_schemes/*.png`
z podpisem nazwy pod każdym, zapis do `assets/shape_montage.png`.

Konkretnie:
1. Źródło nazw = `shape_names()` z `src/engine_smart.py` (single source of truth,
   NIE `ls` po katalogu — kolejność rejestru ma się zgadzać z GUI/CLI).
2. Bramka: dla KAŻDEJ nazwy z `shape_names()` musi istnieć PNG w
   `assets/shape_schemes/`. Jeśli któregoś brakuje — wypisz listę braków i
   zregeneruj Z SILNIKA (wzorzec `gen_e6_schemes.py`/`gen_e7_schemes.py`),
   nigdy nie podstawiaj starego PNG z `assets/proposals/`.
3. ASCII-only w `print()` (terminal CP1250 — `feedback_windows_cli_ascii`).
4. Montaż jest DLA USERA do selekcji finalnej — czytelne podpisy ważniejsze niż
   gęstość; przy 59 kafelkach rozważ siatkę 8×8 lub podział na 2 plansze.

Kontekst: rejestr osiągnął **59/59** (cel puli zamknięty). E8 to ostatni etap
przed galerią 16K: montaż → seria mozaik testowych batch CLI → **selekcja
finalna usera** → galeria. Montaż idzie pierwszy, bo bez niego user nie ma na
czym wybierać.

---

## Co zrobiono w tej sesji

- ✓ **E6 `scales`** (`b407d53`, rejestr=54): rybia łuska, okręgi `r=base_s/√2` na
  siatce szachownicowej. Partycja Z KONSTRUKCJI — brzeg wyłącznie z ĆWIARTEK łuku
  pobieranych przez `center(i,j)` SĄSIADA (nie przez dodanie `r` do własnego
  środka: `c_y+r` ≠ `(j+1)*r` bit-w-bit). Pole `2r²` = wyznacznik kraty
  = niezależny cross-check. Nowy współdzielony `_join_arcs` (dedup złączeń).
  Wszystkie 7 bramek zielone za pierwszym razem.
- ✓ **E6 `nautilus`** (`e2c8a91`, rejestr=55): biegun POZA kadrem
  `(-0,55·cx, -0,30·cy)` — „dobry środek" rozwiązany konstrukcyjnie (najbliższy
  punkt kadru to zawsze róg `(0,0)` ⇒ pasmo promieni ograniczone z dołu, cap-fan
  zbędny). Odkrycie: schemat `g=1,16` przy `nsec=40` to DOKŁADNIE relacja
  `g=1+2π/nsec` ⇒ port, nie przeprojektowanie. Bramka odrębności vs `sunburst`
  (0,97 vs 0,22 półprzekątnej).
- ✓ **E6 `rosette_fractal`** (`494772b`, rejestr=56, **E6 ZAMKNIĘTY**):
  **złapany błąd schematu** — zaszyte `m=3` daje proporcję komórki podwajającą się
  co okres (63,5:1 po 8 podwojeniach; 16K to ~5). Fix: `m` wyprowadzone,
  `m = round(ln2/ln(1+2π/N))`; `m=3` wypada naturalnie przy N=24. Partycja
  FORMALNIE zweryfikowana (0 niesparowanych ×3 kadry).
- ✓ **E7 sierpiński ×3** (`280abf2`, **REJESTR=59/59, CEL OSIĄGNIĘTY**):
  `sierpinski`/`sierpinski_d`/`sierpinski_carpet`. T-junctions wbudowane
  i zamierzone ⇒ pokrycie zamiast partycji, ale proste krawędzie dają
  **min=1,000**. Przycinanie rekurencji: dywan 42 129 → 167 komórek @800×600.
- ✓ **Poprawiłem własny fałszywy docstring** (`_gen_sierpinski`): teza o wyrównaniu
  staggera S/2 słuszna, wniosek „partycja dokładna" fałszywy. Pomiar rozdzielający:
  brak staggera i S/2 = tak samo 102 szwy, S/3 i S/5 dokładają ~20.
- ✓ **540 → 594 testy**; goldeny ×12 cross-process (PYTHONHASHSEED=1); schematy
  Z SILNIKA (`gen_e6_schemes.py`, `gen_e7_schemes.py` — NOWE); surowa ścieżka CLI
  zweryfikowana dla wszystkich 6 kształtów (punkt 8 checklisty planu).

## Co zostało (backlog sesji)

- ⟳ **E8 krok 1:** montaż zbiorczy 59 (NASTĘPNY KROK).
- ⟳ **E8 krok 2:** seria mozaik testowych — batch CLI po wszystkich kształtach.
- ⟳ **E8 krok 3:** selekcja finalna usera → galeria 16K.
- ⟳ **README EN+PL:** tabela 59 kształtów + zaległa dokumentacja
  `--grout-style`/`--grout-color`/`--grout`/`--grout-level`; panorama 4,0 GB
  @324 Mpx osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan; E1–E7 ✓, została sekcja E8
  („Definicja ukończenia" mówi rejestr=56, faktycznie 59 — do korekty przy E8).
- `src/engine_smart.py` — NOWE generatory: `_gen_scales`, `_gen_nautilus`,
  `_gen_rosette_fractal`, `_gen_sierpinski`, `_gen_sierpinski_d`,
  `_gen_sierpinski_carpet`; NOWE helpery: `_join_arcs`, `_sierpinski_cells`,
  `_sierp4`, `_carpet_cells`, `_tri_outside`.
- `src/tools/gen_e6_schemes.py`, `src/tools/gen_e7_schemes.py` — NOWE.
- `tests/test_grout_engine.py` — sekcje E6/E7; `tests/test_golden_shapes.py` —
  12 nowych goldenów; `_areas_inside` = współdzielony helper pól.
- `assets/shape_schemes/` — 6 nowych PNG (z silnika).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** (E8) — kandydaci do odrzucenia
  z wcześniejszych notatek: `bloom` (subtelny).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.
- **`koch_snowflake` depth=4**: szwy sub-pikselowe (min cov 0,686) — jeśli zoom
  DZI ujawni miękkość, rozważyć depth 5 tylko dla małych kadrów.
- **Grout styles na 16K**: style testowane na previews; pierwszy render 16K
  z kintsugi/neon warto obejrzeć (capsule per segment — przy gęstych kształtach
  dużo segmentów; sierpiński/carpet są teraz najgęstsze, 34–41k komórek).
- **`sierpinski_carpet` przy dużym `base_s`**: gdy `S` przekroczy przekątną kadru,
  kształt degeneruje się do kilku wielkich kwadratów. Nie blokuje (pokrycie OK),
  ale przy selekcji warto zobaczyć go w docelowej rozdzielczości.

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** Architektura [2026-07-20] „E6 + E7 — REJESTR = 59/59";
  Rozwiązane problemy [2026-07-20] ×2 — „Stała schematu poprawna LOKALNIE,
  błędna GLOBALNIE (rosette_fractal m=3)" + „T-junctions WBUDOWANE — czwarta
  klasa w drabince instrumentów".
- **auto-memory:** `project_scheme_constant_derive.md` (NOWY);
  `project_pillow_raster_instrument.md` (ZAKTUALIZOWANY — 4. szczebel drabinki:
  proste krawędzie + wbudowane T-junctions ⇒ żądaj `min == 1.0`, nie progu).

## ═══ Sesja zarchiwizowana [2026-07-19 21:00] ═══

# last_session.md

**Sesja:** 2026-07-19 · dzień-wieczór (~21:00)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 667bcf7 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E6, krok 1: wdrożyć `scales` jako `_gen_scales` w `src/engine_smart.py`** (geometria źródłowa: `gen_scales:847` w `src/tools/gen_extra_shape_schemes.py`).

Konkretnie:
1. `scales` = rybia łuska: okręgi promienia r na siatce szachownicowej (`dx=2r, dy=r`, offset r); komórka = kopuła półkolista + 2 wklęsłe łuki zbiegające w dolny wierzchołek; przecięcia okręgów DOKŁADNIE w `(0,−r)` i `(±r,0)`. PRZENIEŚĆ geometrię wprost.
2. ⚠ **ŁUKI**: krok polygonizacji **MUSI** być `_arc_pitch(r, tol=0.35)` — NIE `seg = base_s/3` (ta pomyłka sfasetowała truchet_hex; promień łuski ~base_s, stały w px przy każdej rozdzielczości).
3. ⚠ **Instrument pokrycia wg drabinki** (MEMORY [2026-07-19]): krzywe szwy — jeśli łuki współdzielone konstrukcyjnie (ta sama polilinia z obu stron, wzorzec `_sun_arc` / puzzle) → formalny test partycji + pokrycie FLOAT ss=4 (próg 0,45; kalibracja voderberg 0,502); raster binarny 1:1 SKŁAMIE.
4. ⚠ Dedup KOLEJNYCH duplikatów wierzchołków na złączeniach łuków (parzystość scanline'a Pillow — pasy 1-2 px).
5. Domknięcie: wpis w `SHAPE_MODES` (aa=4) · goldeny ×2 border_mode w 2 procesach (jeden `PYTHONHASHSEED=1`) · schemat Z SILNIKA (nowy `gen_e6_schemes.py`, wzorzec `gen_e5_schemes.py`) · pełny `pytest`.
6. Potem `nautilus` (`gen_nautilus:688`; biegun POZA kadrem `(-1.55,-1.30)` — wzorzec „dobrego środka") i `rosette_fractal` (`:935`; sektory ×2 co `m=3` pierścienie, `g=2^(1/m)`; wspólne krawędzie próbkowane identycznie z obu stron) — domykają E6.

Kontekst: E1–E5 + rodzina puzzle ZAMKNIĘTE (rejestr=53, cel 59). Zostało 6 kształtów: E6 (`scales`/`nautilus`/`rosette_fractal`) + E7 (`sierpinski` ×3). User dał standing approval „rób pozostałe" — po E6 przejść do E7, potem E8 (docs + montaż + selekcja finalna usera).

---

## Co zrobiono w tej sesji

- ✓ **E3 domknięty**: `braid` (`def6513`, bramka izometryczna `_max_overlap` + zęby na flip parzystości) i `moire` (`3c10f0e`, ostrzeżenie „≡ square" obalone pomiarem: CV pola 0,27, 28% krawędzi osiowych). Rejestr=45.
- ✓ **Propozycje na życzenie usera**: 5 puzzli + 10 stylów groutu (`86975a5`), potem profil die-cut wg zdjęć referencyjnych (`060b1e5`). Werdykt usera: grout — WSZYSTKIE 10 + kolor; puzzle — classic/ribbon/hex (organic/penrose odrzucone), die-cut jako profil rodziny.
- ✓ **Grout: 10 stylów kreski + paleta 12 kolorów WDROŻONE** (`8945009`): `draw_grout(style=…, color=…)`, solid bit-identyczny, style per-segment do masek warstwowych, crc32 bez RNG, fallback krótkich segmentów; CLI `--grout-style`/`--grout-color` + GUI 2 menu (też preview).
- ✓ **Sprint P: rodzina puzzle** (`be64bdc`, rejestr=48): 3 kształty na wspólnej maszynerii tabów (wspólna polilinia per krawędź, crc32); bramka ribbon-vs-classic CV narożników (0 vs 0,046).
- ✓ **E4: fraktale** (`174a5a3`, rejestr=51): `dragon` (twindragon, pole DOKŁADNE), `koch_island` (żółw na intach, period=4^depth), `koch_snowflake` (2-rozmiarowa, depth STAŁE=4 — RAM-budżet).
- ✓ **E5: islamskie gwiazdy** (`667bcf7`, rejestr=53): `gereh` (16 latawców/ośmiokąt + ROMBY; **bug schematu złapany bramką**: kwadrat osiowy zamiast rombu = 11k px dziur pod konturami PNG), `rosette` (36 komórek/dwunastokąt; dziury kotwiczone analitycznie — pułapka odfiltrowanego centrum niemożliwa).
- ✓ **META-LEKCJE opłacone i zapisane** (MEMORY + auto-memory `project_pillow_raster_instrument`): (a) duplikaty kolejnych wierzchołków łamią parzystość scanline'a Pillow (pasy 1-2 px, też w aa=4); (b) drabinka instrumentów pokrycia: proste→raster 1:1 / krzywe współdzielone→partycja formalna+FLOAT / nieparujące→FLOAT; (c) formalna partycja NIE dla kształtów z legalnymi T-junctions.
- ✓ **442→540 testów**; goldeny ×20 nowych (wszystkie cross-process, PYTHONHASHSEED=1); schematy z silnika (gen_puzzle/e4/e5_schemes.py); wszystko na origin/main.

## Co zostało (backlog sesji)

- ⟳ **E6 (3 kształty):** `scales` (NASTĘPNY KROK) + `nautilus` + `rosette_fractal`.
- ⟳ **E7 (3 kształty):** `sierpinski`, `sierpinski_d`, `sierpinski_carpet` (wszystkie 3 — decyzja usera 2026-07-16).
- ⟳ **E8:** docs + montaż zbiorczy 59 + mozaiki testowe → selekcja finalna usera → galeria 16K.
- ⟳ README: dokumentacja `--grout-style`/`--grout-color` (i zaległe `--grout`/`--grout-level`); panorama 4,0 GB @324 Mpx osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan (E1–E5 ✓, sekcje E6/E7 z pułapkami — czytać przed E6).
- `src/engine_smart.py` — generatory: `_gen_braid`/`_gen_moire`/`_puzzle_*`/`_gen_dragon`/`_gen_koch_*`/`_gen_gereh`/`_gen_rosette` (NOWE); następne: `_gen_scales`/`_gen_nautilus`/`_gen_rosette_fractal`.
- `src/grout.py` — style + kolory (NOWE: `_STYLES`, `GROUT_COLORS`, `_draw_grout_styled`).
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii E6/E7 (`gen_scales:847`, `gen_nautilus:688`, `gen_rosette_fractal:935`, `gen_sierpinski:84`…).
- `tests/test_grout_engine.py` — sekcje puzzle/E4/E5 + style groutu; `tests/test_golden_shapes.py` — 20 nowych goldenów.
- `assets/proposals/` — propozycje (historia); `assets/shape_schemes/` — schematy wdrożonych (z silnika).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (E8); kandydaci do odrzucenia: `bloom` (subtelny).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.
- **koch_snowflake depth=4**: szwy sub-pikselowe (min cov 0,686) — jeśli zoom DZI ujawni miękkość szwów, rozważyć depth 5 tylko dla małych kadrów.
- **Grout styles na 16K**: style testowane na previews; pierwszy render 16K z kintsugi/neon warto obejrzeć (wydajność: capsule per segment — przy gęstych kształtach dużo segmentów).

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** [2026-07-19] Architektura: grout styles+kolory · rodzina puzzle+E4+E5 (rejestr 43→53, cel 59); Rozwiązane problemy: parzystość scanline'a Pillow + drabinka instrumentów pokrycia + bug schematu gereh.
- **auto-memory:** `project_pillow_raster_instrument.md` (NOWY — drabinka instrumentów, dedup wierzchołków).
