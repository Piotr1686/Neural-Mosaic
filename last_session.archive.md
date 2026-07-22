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


## ═══ Sesja zarchiwizowana [2026-07-19 21:00] ═══

# last_session.md

**Sesja:** 2026-07-17 · 19:00-21:20
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** a90f33f @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E3, krok 2: wdrożyć `braid` jako `_gen_braid` w `src/engine_smart.py`** (geometria źródłowa: `gen_braid` w `src/tools/gen_extra_shape_schemes.py:783`).

Konkretnie:
1. `braid` = basketweave (naprzemienne pary prostokątów 2:1). Audyt oczyścił go jako odrębny od `brick_wall` i `weave` — PRZENIEŚĆ geometrię wprost, nie wymyślać.
2. ⚠ **UWAGA Z TEJ SESJI:** `braid` różni się od `brick_wall` **UŁOŻENIEM, nie komórką** (oba to prostokąty) — to DOKŁADNIE klasa, w której naiwna bramka `a != b` zawodzi (patrz `stagger_tri`). Bramkę odrębności zbuduj na **`_max_overlap`** z `tests/test_grout_engine.py` (niewrażliwa na translację), NIE na wzorcu `test_bloom_geometry_differs_from_phyllotaxis`. Dodaj test kontrolny na znanym duplikacie, jeśli dotyczy.
3. Wpis w `SHAPE_MODES` (aa=4, bez seeda — czysta konstrukcja). Skala wg konwencji puli: średnie pole kafla = `base_s²`.
4. Domknięcie kształtu: goldeny ×2 border_mode w 2 procesach (jeden `PYTHONHASHSEED=1`) · test pokrycia rasteryzacją ≥4 kadry (holes==0) · regeneracja schematu Z SILNIKA (wzorzec: `src/tools/gen_e3_schemes.py`) · `pytest`.
5. Potem `moire` (`:740`) domyka E3. ⚠ Dla `moire`: plan każe sprawdzić NA PRAWDZIWYM RENDERZE, czy nie degeneruje się do `square` (ostrzeżenie „≡ square" jest nieaktualne, ale zasada zostaje).

Kontekst: `PLAN_SHAPES_EXTRA.md` kanoniczny, rejestr=43, zostaje **13 kształtów** (cel 56). E1/E2/`stagger_tri` zamknięte. `braid` i `moire` to ostatnie 2 kształty E3 — oba niskiego ryzyka (przeniesienie wprost), ale `braid` wymaga bramki izometrycznej z powodu klasy „różnica w ułożeniu".

---

## Co zrobiono w tej sesji

- ✓ **`stagger_tri` WDROŻONY** (`16b8e7d`, E3, rejestr=43): przeniesienie 1:1 (wariant A, decyzja usera). **Werdykt audytu z poprzedniej sesji ODWRÓCONY pomiarem:** to `triangle` przesuwa fazę o pół podstawy co rząd (reguła flipu `(c+r)%2` JEST przesunięciem; potwierdza `_grout_cells_triangle`), a schemat trzymał fazę STAŁĄ ⇒ był odrębny od początku (pokrycie z `triangle` przy dowolnej translacji = 50%, nie 100%). Zalecony fix `s/2` odtworzyłby `triangle` w 100% = duplikat.
- ✓ **META-LEKCJA bramki:** naiwne `a != b` przepuściłoby wariant `s/2` (translacja zmienia każdą współrzędną, 0/78 vs 78/78 po wyrównaniu). Wdrożona bramka izometryczna `_max_overlap` + test kontrolny łapiący znany duplikat. Drabinka: statystyki < współrzędne < izometria.
- ✓ **Naprawiona wada dziur CAŁEJ rodziny Voronoi** (`a90f33f`): zgłoszone jako „voronoi 12,8%", pomiar pokazał wadę rodziny (do **41,6%** dla `sunflower_disc`). Fix dwuprzebiegowy w `_voronoi_cells`: odzysk komórek otoczki przez lustra względem pudełka obejmującego kadr. PUŁAPKA: wariant jednoprzebiegowy zaburza bity Qhulla → 22/22 goldenów pada; dwuprzebiegowy → 20/22 bit-w-bit. Goldeny `voronoi` ×2 zregenerowane świadomie (dowód: pixel-diff zmian tylko przy obrzeżu).
- ✓ **442 testy** (z 409 na starcie E3, z 398 na starcie sesji): +11 stagger_tri, +33 rodzina Voronoi (pokrycie 11×3) − nakładka. Schematy regenerowane Z SILNIKA (`gen_e3_schemes.py` NOWY, `gen_e2`/`gen_e3` bit-identyczne po regeneracji).
- ✓ **Oba commity wypchnięte na origin/main.** `PLAN_SHAPES_EXTRA.md` zaktualizowany (werdykt obalony, REGUŁA rozszerzona o drabinkę narzędzi).

## Co zostało (backlog sesji)

- ⟳ **E3 (2 kształty):** `braid` (NASTĘPNY KROK) + `moire`.
- ⟳ **E4-E7 (11 kształtów):** `dragon`/`koch_island`/`koch_snowflake` · `gereh`/`rosette` · `scales`/`nautilus`/`rosette_fractal` · `sierpinski` ×3.
- ⟳ **E8:** docs + montaż zbiorczy 56 + mozaiki testowe → selekcja finalna usera → galeria 16K.
- ⟳ **Hero panorama:** lokalnie (`output/hero_pano_dzi/`, gitignored), NIE opublikowana — Wariant C odłożony (ryzyko publicznego artefaktu).
- ⟳ README: panorama **4,0 GB @324 Mpx** jako liczba OSOBNA od 3,9 GB @16K; dokumentacja `--grout`/`--grout-level`.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan + audyt konstrukcji + REGUŁA z drabinką narzędzi (czytać przed E3/E4).
- `src/engine_smart.py` — `_gen_stagger_tri` (NOWY), `_voronoi_cells` (dwuprzebiegowy odzysk otoczki). E3: dodać `_gen_braid`/`_gen_moire`.
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii (`gen_braid:783`, `gen_moire:740`).
- `src/tools/gen_e3_schemes.py` — WZORZEC regeneracji schematu z silnika (E3).
- `tests/test_grout_engine.py` — `_max_overlap` (bramka izometryczna), `test_voronoi_family_covers_coarse_frames` (`_VORONOI_FAMILY` — dopisać nowego członka rodziny), pokrycie + partycja.
- `tests/test_golden_shapes.py` — goldeny (stagger_tri, voronoi zregenerowane ×2).

## Otwarte pytania

- **Publikacja hero panoramy** na GitHub Pages (Wariant C) — nietknięte, decyzja usera.
- **`bloom` — różnica realna, ale subtelna:** kandydat do odrzucenia przy selekcji finalnej (E8).
- **`braid` vs `brick_wall`:** oba prostokąty, różnica w ułożeniu — potwierdzić bramką izometryczną, że NIE duplikat (ryzyko realne, klasa `stagger_tri`).
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę. Zaakceptowane milcząco. (Fix Voronoi zamyka najgorszy przypadek dziur w tym reżimie.)
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich.

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** wpis `[2026-07-17b]` (stagger_tri + obalenie werdyktu + meta-lekcja bramki izometrycznej + naprawa rodziny Voronoi + pułapka jednoprzebiegowych luster Qhulla); skorygowano wpis `[2026-07-17]` (wada voronoi → NAPRAWIONE).
- **pamięć długoterminowa:** `project_stagger_tri_phase.md` (NOWY — werdykt odwrócony, bramka izometryczna) · `project_voronoi_hull_recovery.md` (NOWY — wada całej rodziny, dwuprzebiegowy odzysk, pułapka bitów Qhulla).

## ═══ Sesja zarchiwizowana [2026-07-17 21:20] ═══

# last_session.md

**Sesja:** 2026-07-16/17 · 22:00-00:57
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 2aaf567 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E3, krok 1: zróżnicować `stagger_tri` geometrycznie i wdrożyć jako `_gen_stagger_tri` w `src/engine_smart.py`.**

Konkretnie:
1. `gen_stagger_tri` (`src/tools/gen_extra_shape_schemes.py:239`) rysuje `(bl,br,tp)` + `(br,tp,tr)` na regularnej kracie — to **dokładnie** silnikowy tryb `triangle`; jego `on = (ci & rj) == 0` wybiera TYLKO paletę. **Nie przenosić tej geometrii 1:1** — powstałby duplikat.
2. Wdrożyć **realne przesunięcie rzędów o pół trójkąta** (decyzja usera 2026-07-17): co drugi rząd `+s/2`. T-junctions na poziomych granicach rzędów są legalne w partycji (precedens: `sierpinski`).
3. Wpis w `SHAPE_MODES` (aa=4, bez seeda — czysta konstrukcja).
4. **BRAMKA (obowiązkowa):** test porównujący WSPÓŁRZĘDNE z `triangle` musi wykazać różnicę — wzorzec gotowy: `test_bloom_geometry_differs_from_phyllotaxis` w `tests/test_grout_engine.py`. Statystyki pól NIE wystarczą (trójkąty są tej samej wielkości).
5. Potem `braid` (`:783`) i `moire` (`:740`) — oba oczyszczone audytem, przenosić wprost.
6. Domknięcie sprintu: goldeny ×2 border_mode w 2 procesach · test pokrycia rasteryzacją ≥4 kadry · regeneracja schematów Z SILNIKA (wzorzec: `src/tools/gen_e2_schemes.py`) · `pytest` · commit + push.

Kontekst: `PLAN_SHAPES_EXTRA.md` jest kanoniczny i ZATWIERDZONY; E1 (`b3e725c`) i E2 (`3990cfa`) zamknięte, rejestr=42, zostaje 14 kształtów. `stagger_tri` to jedyny element E3 wymagający decyzji projektowej — `braid` i `moire` są gotowe do przeniesienia, więc kolejność „najpierw stagger_tri" zdejmuje ryzyko z całego sprintu.

---

## Co zrobiono w tej sesji

- ✓ **Krok 5 (b++) → PLAN POINCARE UKOŃCZONY.** Drabinka 4:1 (`PeakRAMSampler` z `tests/benchmark.py`): 20 Mpx → 1,44 GB · 81 Mpx → 1,96 GB · **324 Mpx (36000×9000) → 4,02 GB / 80 422 kom. / 15,2 min**. **Model RAM `delta ≈ 1,27 GB stałe + 0,0085 GB/Mpx`, LINIOWY** (przewidział 4,03 vs 4,02). Zero członu superliniowego ⇒ tiling nie ma patologii do naprawy. Bramka 3,9 GB przekroczona o 3,1% — **decyzja usera: zaakceptować + raportować własną liczbę** (inwariant opisuje 16K, panorama to inny artefakt: 2,45× pikseli za 1,03× RAM). Eksport DZI = osobny etap: 2,37 GB / 1,9 min / 101,5 MB kafelków (szacunek 1,3 GB był o 80% za niski).
- ✓ **fix(dzi) `494333f` — REALNY BUG:** `make_dzi` gubił `Image.MAX_IMAGE_PIXELS = None`. Progi Pillow: ostrzeżenie 89,5 Mpx, **twardy błąd 179 Mpx**. 16K (133 Mpx) = warning ⇒ działało po cichu od 2026-06-27; panorama (324 Mpx) ⇒ **CLI `dzi` i przycisk GUI wywalały się `DecompressionBombError`**. META-LEKCJA: skrypt pomiarowy miał własną łatkę i MASKOWAŁ ścieżkę produkcyjną.
- ✓ **`PLAN_SHAPES_EXTRA.md` ZATWIERDZONY** (`d14b913`, odświeżony `2aaf567`): sprinty E1-E8, mapa linii, pułapki per grupa, definicja ukończenia (rejestr 56).
- ✓ **AUDYT KONSTRUKCJI puli** (`27b14a7`, decyzja usera — jednorazowo zamiast per sprint). Przyczyna systemowa: pula to SCHEMATY, gdzie różnicę niósł KOLOR. Wynik: 3 duplikaty + **6 podejrzanych OCZYSZCZONYCH** + 8 bezspornie odrębnych ⇒ realny rozmiar puli **14, nie 16**. Wynik WIĄŻĄCY — nie powtarzać per sprint.
- ✓ **`kepler_ty` USUNIĘTY** (`1e53982`): identyczne `(N, zeta, gamma)` co `penrose`. Usunięto też wpis w `SHAPES` (inaczej regeneracja przywróciłaby PNG).
- ✓ **Sprint E1 — `penrose_p2`** (`b3e725c`, rejestr=40): latawce/strzałki P2 (deflacja P3 → Robinson B→A → scalanie bliźniaków). Kontrola: latawce/strzałki **1.614 vs φ=1.618**. PUŁAPKA: scalanie porzuca niesparowane połówki, a tworzy je KAŻDA granica ⇒ sun dobrany „ledwo" dał **pasmo 42 px dziur** niewidoczne w liczbie kafli ani polach ⇒ `PRUNE_LEGS=3 > CULL_LEGS=1`.
- ✓ **Sprint E2 — `bloom` + `pebbles`** (`3990cfa`, rejestr=42): `bloom` = kąt Lucasa 99,502° (oś `power` nasycona); `pebbles` = Voronoi zmiennej gęstości (rozrzut pól 0,74-0,84 vs voronoi 0,49-0,70). Trzy pułapki zasiewania: stała suma przepełnia kadr · partia 4096 daje **stałe 425 kafli w każdej rozdzielczości** · ucięcie zagładza margines → **5,3% dziur**.
- ✓ **Korekty nieaktualnych zapisów:** „moire ≡ square" NIEAKTUALNE; `braid` = odrębny basketweave. Obie moje hipotezy „duplikatów do wycięcia" okazały się FAŁSZYWE — uratowało sprawdzenie PNG zamiast zaufania notatce.
- ✓ **398 testów** (z 377 na starcie): +10 E1, +8 E2, +1 DZI, +2 goldeny. Schematy regenerowane Z SILNIKA: `gen_penrose_p2_scheme.py`, `gen_e2_schemes.py` (oba commitowane).

## Co zostało (backlog sesji)

- ⟳ **E3:** `stagger_tri` (wymaga zróżnicowania) + `braid` + `moire` (NASTĘPNY KROK).
- ⟳ **E4-E7:** `dragon`/`koch_island`/`koch_snowflake` · `gereh`/`rosette` · `scales`/`nautilus`/`rosette_fractal` · `sierpinski` ×3. **E8:** docs + montaż 56 + selekcja finalna usera → galeria 16K.
- ⟳ **Hero panorama:** wyeksportowana lokalnie (`output/hero_pano_dzi/`, gitignored), NIE opublikowana na GitHub Pages — Wariant C wciąż odłożony (ryzyko publicznego artefaktu).
- ⟳ README: dopisać liczbę panoramy **4,0 GB @324 Mpx** jako OSOBNĄ od 3,9 GB @16K.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka; README `--grout`/`--grout-level`.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan puli + **audyt konstrukcji** (czytać przed E3).
- `src/engine_smart.py` — `_PHI`/`_LUCAS_ANGLE`, `_p3_half_deflate`, `_gen_penrose_p2`, `_gen_pebbles`, `_gen_bloom`, `angle` w `_vogel_points`/`_graded_sunflower`. E3: dodać `_gen_stagger_tri`/`_gen_braid`/`_gen_moire`.
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii (17 SHAPES; mapa linii w planie, ODŚWIEŻONA po usunięciu `gen_kepler_ty`).
- `src/tools/gen_penrose_p2_scheme.py`, `src/tools/gen_e2_schemes.py` — WZORCE regeneracji schematu z silnika.
- `tests/test_golden_shapes.py` — goldeny (penrose_p2/bloom/pebbles ×2).
- `tests/test_grout_engine.py` — pokrycie + partycja + testy odrębności geometrycznej.

## Otwarte pytania

- ⚠ **Wada w istniejącym `voronoi`: 12,8% dziur @384×288 base_s=100** (podłoga `max(16, ...)` — 16 ziaren nie pokrywa kadru). Wykryta przy E2, zgłoszona, NIE naprawiona (poza zakresem). Naprawiać osobno?
- **Publikacja hero panoramy** na GitHub Pages (Wariant C) — nietknięte, decyzja usera.
- **`bloom` — różnica realna, ale subtelna:** kąt Lucasa daje inny układ ramion, ale oba czytają się jako „słonecznikowe Voronoi". Kandydat do odrzucenia przy selekcji finalnej.
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę niż finalny render. Zaakceptowane milcząco.
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich (bez zmian).

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** wpis `[2026-07-16]` (krok 5, model RAM, decyzja o bramce, fix DZI, plan, kepler_ty, E1 + pułapka pierścienia) oraz `[2026-07-17]` (audyt konstrukcji, E2, 3 pułapki zasiewania Voronoi, meta-lekcja „statystyki nie rozstrzygną duplikatu", wada `voronoi`).
- **pamięć długoterminowa:** `project_dzi_decompression_bomb.md` (NOWY — bug + „skrypt pomiarowy ≠ produkcja") · `project_penrose_p2_pruning.md` (NOWY — niesparowane połówki przy każdej granicy; konwencja pola = base_s²) · `project_e2_voronoi_seeding.md` (NOWY — 3 pułapki zasiewania; `angle` w `_vogel_points`) · `project_poincare_bpp_plan.md` (krok 5 zamknięty) · `project_extra_15_shapes.md` (audyt wiążący, korekty).

