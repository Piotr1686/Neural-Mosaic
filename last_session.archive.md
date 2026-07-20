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

## ═══ Sesja zarchiwizowana [2026-07-17 00:57] ═══

# last_session.md

**Sesja:** 2026-07-16/17 · ~22:00-00:15 (TRWA — checkpoint /save 00:15)
**Status:** ⟳ w toku
**Punkt odniesienia (git):** b3e725c @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E2 z `PLAN_SHAPES_EXTRA.md`: `bloom` + `pebbles`** (oba reużywają
`_gen_voronoi` — najtańsza pozostała grupa; E1 zamknięty).

Wzorzec wdrożenia jednego kształtu (ustalony, trzymać się go):
1. Przenieś geometrię z `gen_extra_shape_schemes.py` (`gen_bloom:~805`,
   `gen_pebbles:~887` — numery po usunięciu gen_kepler_ty, zweryfikuj grepem).
   **Przenoś, nie wymyślaj.**
2. **NAJPIERW porównaj KONSTRUKCJĘ z tym, co silnik już ma** — `kepler_ty`
   wypadł, bo miał identyczne `(N, zeta, gamma)` co `penrose`. `bloom` =
   Voronoi ziaren phyllotaxis; sprawdź, czy nie jest tym samym co wdrożony
   `phyllotaxis` (RYZYKO DUPLIKATU — zbadać PRZED kodowaniem).
3. Wpis w `SHAPE_MODES` (aa=4, `seeded=True` — RNG tylko przez
   `np.random.default_rng(f(base_s, target_w, target_h))`, nigdy globalny).
4. Kalibracja: **średnie pole komórki ≈ base_s²** (kontrola: penrose 3536,
   cairo 3600 przy base_s=60). Próg min-area `(base_s/4)²`.
5. Testy: goldeny ×2 border_mode (weryfikuj w 2 procesach), **test pokrycia
   rasteryzacją** (ten złapał dziury w E1 — liczba kafli i pola były OK!),
   test partycji przez `classify_edges`.
6. Regeneracja schematu PNG **Z SILNIKA** (wzorzec: `gen_penrose_p2_scheme.py`).
7. `pytest` zielony + commit + push.

Kontekst: plan puli extra ZATWIERDZONY (`d14b913`), E1 zamknięty (`b3e725c`,
rejestr=40, 388 testów). Zostaje 16 kształtów: E2 bloom/pebbles · E3 braid/
moire/stagger_tri · E4 dragon/koch_island/koch_snowflake · E5 gereh/rosette ·
E6 scales/nautilus/rosette_fractal · E7 sierpinski ×3 (wszystkie 3 warianty —
decyzja usera) · E8 docs+montaż+selekcja finalna → galeria 16K.

---

## Co zrobiono w tej sesji

- ✓ **Krok 5 (b++) — peak-RAM panoramy 4:1 → PLAN POINCARE UKOŃCZONY.**
  Drabinka 4:1 (`_do_render` w `PeakRAMSampler` z `tests/benchmark.py` — NIE
  w engine_smart, jak sugerował zapis; tryby jak `bench_render`; delta ponad
  baseline 0,55 GB z indeksem): 20 Mpx → 1,44 GB / 5 667 kom. · 81 Mpx →
  1,96 GB / 21 628 kom. · **324 Mpx (36000×9000) → 4,02 GB / 80 422 kom. /
  15,2 min**. **Model RAM: `delta ≈ 1,27 GB stałe + 0,0085 GB/Mpx`, LINIOWY**
  (przewidział 4,03 vs 4,02 zmierzone). Człon stały = `_euclid_f32` nad
  biblioteką 454k, niezależny od kadru; zero członu superliniowego ⇒ tiling
  nie ma patologii do naprawy. Bramka 3,9 GB przekroczona o 3,1% —
  **decyzja usera: zaakceptować + raportować własną liczbę** (inwariant 3,9 GB
  opisuje ścieżkę 16K, nie panoramę: 2,45× pikseli za 1,03× RAM; poincare @16K
  wg modelu ≈2,4 GB). Eksport DZI = osobny etap: **2,37 GB / 1,9 min / 101,5 MB
  kafelków** (szacunek 1,3 GB był o 80% za niski). Artefakty w `output/`
  (gitignored). Szacunek „58k komórek" z 2026-07-15 był o 40% za niski (80k).
- ✓ **fix(dzi) `494333f` (push) — REALNY BUG:** `make_dzi` gubił
  `Image.MAX_IMAGE_PIXELS = None`, które mają siostrzane narzędzia. Progi
  Pillow: ostrzeżenie 89,5 Mpx, **twardy błąd 179 Mpx**. 16K (133 Mpx) =
  tylko warning ⇒ eksport działał po cichu od 2026-06-27; panorama (324 Mpx)
  przekracza próg błędu ⇒ **CLI `dzi` i przycisk GUI wywalały się
  `DecompressionBombError`**. Wykryte, bo skrypt pomiarowy miał własną łatkę
  i MASKOWAŁ ścieżkę produkcyjną. +test inwariantu.
- ✓ **`PLAN_SHAPES_EXTRA.md` ZATWIERDZONY (`d14b913`, push):** plan puli extra,
  sprinty E1-E8 grupowane po maszynerii, mapa linii w `gen_extra_shape_schemes.py`,
  pułapki per grupa. Weryfikacja kodem: rejestr 39 vs 57 PNG ⇒ 18 brakujących,
  0 sierot. Decyzja usera: sierpiński = **wszystkie 3 warianty**.
- ✓ **`kepler_ty` USUNIĘTY (`1e53982`, push; pula 18→17):** identyczne
  `(N, zeta, gamma)` co wdrożony `penrose` ⇒ **ta sama teselacja**; różniła
  tylko paleta, a kolor pod zdjęciami znika (tryb awarii „moire ≡ square").
  Usunięte: funkcja, wpis w `SHAPES` (inaczej regeneracja przywróciłaby PNG),
  PNG, wzmianki. **Reguła: porównuj KONSTRUKCJĘ, nie nazwę.**
- ✓ **Sprint E1 — `penrose_p2` (`b3e725c`, push; rejestr=40, 388 testów):**
  latawce/strzałki P2 przez deflację P3 → konwersję Robinsona B→A → scalanie
  bliźniaków. Kontrola: latawce/strzałki = **1.614 vs φ=1.618**. Adaptacja
  schemat→silnik: głębokość z `base_s` (sun pokrywa kadr, ceil), przycinanie
  PO KAŻDEJ deflacji (dzieci w rodzicu ⇒ bezpieczne; ~3,6× taniej @16K), noga
  = `base_s*sqrt(2)` bo średnie pole = `leg²/2`, a konwencja to `base_s²`.
  **PUŁAPKA:** scalanie porzuca niesparowane połówki, a tworzy je KAŻDA granica
  (rant suna + pudełko przycinania) → sun dobrany „ledwo" (zapas 3 px) dał
  **pasmo 42 px dziur**, NIEwidoczne w liczbie kafli ani w polach. Stąd
  `PRUNE_LEGS=3 > CULL_LEGS=1`. Schemat zregenerowany Z SILNIKA
  (`gen_penrose_p2_scheme.py`). +10 testów.
- ✓ **Korekta nieaktualnej pamięci:** ostrzeżenie „moire ≡ square" NIEAKTUALNE
  (rewizja 2026-07-04 dała prawdziwe moiré geometryczne — zweryfikowane na PNG);
  `braid` = odrębny basketweave, NIE duplikat `weave`. Obie moje hipotezy
  „duplikatów do wycięcia" okazały się fałszywe — uratowało sprawdzenie.

## Co zostało (backlog sesji)

- ⟳ **Sprint E2:** `bloom` + `pebbles` (NASTĘPNY KROK). ⚠ Zbadać RYZYKO
  DUPLIKATU `bloom` vs wdrożony `phyllotaxis` PRZED kodowaniem.
- ⟳ E3-E7: 14 kolejnych kształtów; E8 = docs + montaż 56 + selekcja finalna
  usera → galeria 16K.
- ⟳ **Hero panorama:** wyeksportowana lokalnie (`output/hero_pano_dzi/`),
  ale NIE opublikowana na GitHub Pages — to Wariant C, wciąż odłożony
  (ryzyko publicznego artefaktu). Decyzja usera potrzebna, gdy wróci temat.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka;
  README `--grout`/`--grout-level`; README: dopisać liczbę panoramy 4,0 GB
  jako OSOBNĄ od 3,9 GB @16K.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan puli extra (E1 zamknięty).
- `src/engine_smart.py` — `_PHI`, `_p3_half_deflate`, `_gen_penrose_p2`
  + wpis w `SHAPE_MODES`. E2: dodać `_gen_bloom`/`_gen_pebbles` przy
  `_gen_voronoi:628`.
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii puli (17 SHAPES).
- `src/tools/gen_penrose_p2_scheme.py` — WZORZEC regeneracji schematu z silnika.
- `tests/test_golden_shapes.py` — goldeny (penrose_p2 ×2).
- `tests/test_grout_engine.py` — pokrycie penrose_p2 ×5 + partycja ×3.
- `src/tools/make_dzi.py` — po fixie MAX_IMAGE_PIXELS.

## Otwarte pytania

- **`bloom` vs `phyllotaxis`** — oba to Voronoi ziaren phyllotaxis. Realne
  ryzyko powtórki `kepler_ty`. Zbadać konstrukcję PRZED wdrożeniem E2.
- **Publikacja hero panoramy** na GitHub Pages (Wariant C) — nietknięte.
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę niż
  finalny render. Zaakceptowane milcząco.
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich (bez zmian).

## Do MEMORY.md (przeniesiono)

- `project_dzi_decompression_bomb.md` (NOWY) — bug + META-LEKCJA „skrypt
  pomiarowy ≠ produkcja: weryfikuj surową ścieżkę CLI/GUI".
- `project_penrose_p2_pruning.md` (NOWY) — pułapka niesparowanych połówek przy
  KAŻDEJ granicy; konwencja średniego pola = base_s²; kontrola „nakładek".
- `project_poincare_bpp_plan.md` — krok 5 zamknięty, model RAM, decyzja o bramce.
- `project_extra_15_shapes.md` — stan zweryfikowany kodem, wskaźnik na
  PLAN_SHAPES_EXTRA.md, korekta moire/braid/sierpinski_b-c.

## ═══ Sesja zarchiwizowana [2026-07-15 22:25] ═══

# last_session.md

**Sesja:** 2026-07-15 · ~11:15-12:20
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** f26c3aa @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Krok 3 planu (b++): `_grout_cells_poincare`** w `src/engine_smart.py`:

1. Nowa metoda obok `_grout_cells_kites` (~l. 2390+): re-yield
   `_poincare_cells(w, h, base_s)` jako `(poly, g2=hi*7+k, g3=hi)` —
   `_poincare_cells` JUŻ zwraca `(poly, hept_idx, kite_idx)`, więc to
   ~10 linii. L1=subkomórka, L2=latawiec, L3=heptagon (kwiat 7 siatek).
2. Wpis `"poincare"` do `_HIERARCHICAL_GROUT` (~l. 2550) i `GROUT_HIERARCHICAL`
   (~l. 53) — bez tego generyczny fallthrough polygon daje TYLKO płaski grout.
   Sprawdzić, że gałąź dedykowana odpala PRZED generycznym fallthrough
   w `_grout_cells` (wzorzec kites).
3. +2 testy w `tests/test_grout_engine.py`: (a) hierarchia — 7 komórek
   z tym samym g2 na latawiec... UWAGA: g2 grupuje SUBKOMÓRKI latawca
   (nd² sztuk), a 7 latawców dzieli g3; wzorzec asercji z
   `test_kites_cells` dostosować; (b) poziomy `--grout-level` na realnej
   geometrii poincare (pułapka kierunku: selekcja `>= N`).
4. Bramka: render 2K `0013.jpg` `--grout thin --grout-level 1/2/3` —
   L3 ma pokazać kwiaty heptagonów, L2 latawce; pełny pytest.

Kontekst: kroki 1-2 (b++) WDROŻONE i wypchnięte (da891fc, f26c3aa) — BFS w dysku
+ prune w paśmie + subdywizja hiperboliczna quad-mesh do ~base_s; partycja
zweryfikowana (0 niesparowanych segmentów wewnętrznych na 5 kadrach). Grout
hierarchiczny to ostatni element wizualny przed goldenami (krok 4) — bez niego
struktura hiperboliczna jest na renderze subtelna.

---

## Co zrobiono w tej sesji

- ✓ **Analiza planu + druga opinia `architect`** (adwersarialna, na prośbę usera)
  → plan **(b++)** ZATWIERDZONY: subdywizja do base_s + grout 3-poziomowy +
  hero-panorama DZI; szczegóły MEMORY.md [2026-07-15]. Tasks #1-5 założone.
- ✓ **Krok 1 (da891fc): port BFS poincare do silnika** — rejestr SHAPE_MODES=39.
  BFS odbić w DYSKU, akceptacja/prune w PAŚMIE; `diam<0.02` usunięty; depth-cap
  z okna (4:3→13, 4:1→19). **Bug złapany audytem:** margines y prune 0.25
  przekraczał horyzont pasma (0.8+0.25=1.05>1) → prune po y martwy → BFS gonił
  pył do zdegenerowanych krawędzi (sqrt domain error). Fix: `m_y=min(m,(1-W)/2)`
  + guard `r2<=0` w `_poincare_geo_circle`.
- ✓ **Krok 2 (f26c3aa): subdywizja hiperboliczna** — `_poincare_hyp_frac`
  (Möbius) + `_poincare_cells`: siatka quad transfinita per latawiec, `nd`
  per heptagon. DWIE zmiany vs szkic architekta: (1) quad-mesh zamiast
  biegunowej (biegunowa = szpic 4.5:1 przy C); (2) anty-T-junction
  KONSTRUKCYJNY — podziały łuków snapowane do globalnej siatki próbek,
  komórki emitują wszystkie próbki jako wierzchołki → segmenty pasują przy
  różnych nd sąsiadów; maszyneria „conforming subdivision" (2-2.5 d wyceny)
  okazała się zbędna.
- ✓ **Bramki:** audyt pokrycia ss=4 × 6 kadrów (w tym 4:1 panorama) — max
  szczelina 1 subpx, zero dziur geometrycznych; smoke-test partycji
  `classify_edges` × 5 kadrów — 0 niesparowanych segmentów wewnętrznych;
  2× pełny pytest **367/367**; 2 rendery 2K `0013.jpg` (przed/po subdywizji:
  201 → 1378 komórek); t_gen ≤ 0.11 s, BFS 2-25 ms.
- ✓ Oba commity wypchnięte na origin (`da891fc`, `f26c3aa`).

## Co zostało (backlog sesji)

- ⟳ **Krok 3 (b++):** `_grout_cells_poincare` (NASTĘPNY KROK).
- ⟳ **Krok 4 (b++):** goldeny ×2 procesy + schemat PNG z geometrii silnika
  (`gen_poincare_scheme.py` wzorem girih) + formalny test partycji w pytest
  (zero `len(adj)==1` we wnętrzu; smoke-test w scratchpadzie sesji był zielony).
- ⟳ **Krok 5 (b++):** pomiar peak-RAM panoramy 4:1 → hero DZI (dopiero po pomiarze).
- ⟳ Po poincare: pula extra 21-43 → selekcja finalna usera → galeria 16K.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka; README --grout/--grout-level.
- ⟳ Tasks w harness: #3/#4/#5 (pending) odpowiadają krokom 3/4/5.

## Aktywne pliki

- `src/engine_smart.py` — blok POINCARE po `_gen_girih`: `_POINCARE_W/_MARGIN`,
  `_poincare_band/_geo_circle/_reflect/_edge_arc/_heptagons/_hyp_frac/_cells`
  + `_gen_poincare` + wpis SHAPE_MODES (39). Krok 3 doda `_grout_cells_poincare`
  + wpisy `_HIERARCHICAL_GROUT`/`GROUT_HIERARCHICAL`.
- Scratchpad sesji (poza repo): `audit_poincare.py` (audyt pokrycia ss=4,
  6 kadrów), `smoke_partition.py` (detektor T-junctions) — do kroku 4 warto
  przenieść logikę partycji do pytest.
- `output/0013_smart_2K_poincare.jpg` — render weryfikacyjny (nadpisywany).

## Otwarte pytania

- **Peak-RAM panoramy 4:1** (krok 5): ~58k komórek @36000×9000 — zmierzyć
  PRZED obietnicą hero (inwariant A1 3.9 GB @16K).
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę niż
  finalny render (analogia: seeded voronoi). Zaakceptowane milcząco — jeśli
  user zauważy, rozważyć nd z rozdzielczości docelowej.
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich (bez zmian).

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis **[2026-07-15b]** — kroki 1-2 wdrożone: bug marginesu
  ponad horyzontem, quad-mesh zamiast biegunowej, snapping = anty-T-junction
  konstrukcyjny, wyniki bramek, `_poincare_cells` zwraca grupy dla kroku 3.
- (z /save w tej sesji) wpis **[2026-07-15]** — plan (b++) + auto-memory
  `project_poincare_bpp_plan.md`.

---

