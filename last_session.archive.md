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

## ═══ Sesja zarchiwizowana [2026-07-15 12:20] ═══

# last_session.md

**Sesja:** 2026-07-15 · w toku (checkpoint /save)
**Status:** ⏳ W toku — sesja dotąd czysto planistyczna (kod nietknięty)
**Punkt odniesienia (git):** 8a3fb73 @ main (zsynchronizowane z origin/main; working tree czysty)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring poincare wg planu (b++)** — ZATWIERDZONY 2026-07-15 po adwersarialnej
drugiej opinii agenta `architect`. UNIEWAŻNIA poprzedni opis kroku w punktach:
BFS NIE jest drogi @16K (obawa z ery modelu dyskowego), `diam<0.02` do USUNIĘCIA
(nie zachowania), subdywizja OBOWIĄZKOWA (bez niej latawiec ~4000 px @16K z kafla
~kilkuset px = miękkie w DZI). Szczegóły decyzji: MEMORY.md wpis [2026-07-15].

**Krok 1 (0.5 d) — port BFS do silnika:** `_gen_poincare(engine, w, h, base_s)`.
BFS ZOSTAJE w dysku (odbicia = inwersje w okręgach, tanie; NIE reimplementować
w paśmie). Do PASMA przenosi się TYLKO test akceptacji/prune:
`|band_y| ≤ W+margin ∧ |band_x| ≤ x_max+margin`. Cutoff `diam<0.02` WYLATUJE
(przy x=3.2 zabija prawdziwe kafle: z≈0.987, dysk-⌀≈0.0155). `depth≤14` zostaje
(do x=3.2 wystarcza 4-6 pierścieni). Dedup `round(,4)` bezpieczny (do |z|<0.99997).

**Kolejne kroki (b++):**
2. Subdywizja HIPERBOLICZNO-BIEGUNOWA latawców do ~base_s (2-2.5 d) — NIE euklidesowy
   quad-split (anizotropia cos(πy/2)→3:1 przy |y|=0.8; band-map konforemna ⇒ podział
   w metryce hiperbolicznej = izotropia za darmo). ANTY-T-JUNCTION: liczba podziałów
   krawędzi geodezyjnej = GLOBALNA funkcja krawędzi (obie komórki czytają tę samą).
3. `_grout_cells_poincare` (g2=latawiec, g3=heptagon) + wpisy `_HIERARCHICAL_GROUT`
   (~l. 2440) i `GROUT_HIERARCHICAL` (~l. 52) — generyczny fallthrough polygon daje
   TYLKO płaski grout (1 d). Bez L4/„kwiata" — {7,3} nie ma supergrupy (7 nieparzyste).
4. Golden ×2 procesy + schemat PNG z geometrii silnika + SHAPE_MODES (rejestr→39)
   + TEST PARTYCJI: zero krawędzi `len(adj)==1` we WNĘTRZU kadru po `classify_edges`
   (detektor T-junction; wada widoczna dopiero w zoomie DZI — jak historyczna
   pikseloza groutu) (1.5 d).
5. Hero portfolio: panorama 4:1 (np. 36000×9000) → DZI. NAJPIERW zmierzyć peak-RAM
   (80-150k `_LazyMask` vs inwariant A1 3.9 GB @16K). UWAGA: {7,3} NIE jest okresowe
   wzdłuż osi pasma — panoramy NIE da się skleić z kopii; pełny BFS wymagany.

Geometria źródłowa: `gen_fable_shape_schemes.py:302-419`. Szacunek całości ~5-5.5 d.
Liczby (skorygowane przez architekta): heptagon ~0.74 j. pasma (~8300 px @16K square),
panorama 80-150k komórek, generacja 20-45 s (2-4× girih).

Bramki: render 2K na `input/0013.jpg`, pełny pytest, pokrycie kadru 0% tła
(wzorzec `src/tools/girih_audit.py`) + NOWA bramka: audyt pokrycia na aspekcie
panoramicznym (tryby awarii poincare są aspect-driven — jedyny taki kształt).

Kontekst: po poincare zostaje TYLKO pula extra 21-43, potem selekcja finalna
kształtów przez usera → galeria 16K. User chce WSZYSTKIE kształty przed selekcją.

---

## Co zrobiono w tej sesji

- ✓ **`/start`** — stan spójny (HEAD `8a3fb73` = chore-commit z `/end` 14.07;
  working tree czysty).
- ✓ **Analiza planu poincare przed wiringiem** (zero zmian w kodzie):
  - Obawa „BFS najdroższy @16K" OBALONA — dotyczyła modelu DYSKOWEGO (wyrzuconego
    2026-07-04b); w modelu pasmowym koszt zależy od ASPEKTU kadru, nie pikseli.
  - Wykryte prawdziwe ryzyka: stała liczba komórek (~230-310 latawców/kadr
    niezależnie od rozdzielczości) ⇒ latawiec ~4000 px @16K z kafla ~kilkuset px;
    cutoffy w współrzędnych dysku łamią się na szerokich kadrach.
  - Rekomendacja (b+): subdywizja do base_s + grout 3-poziomowy + hero-panorama DZI.
- ✓ **Druga opinia agenta `architect`** (na prośbę usera; mandat adwersarialny).
  Werdykt: kierunek słuszny, 3 korekty → plan **(b++)**. Nowe znaleziska:
  T-junctions przy adaptacyjnym quad-splicie (⇒ per-edge-consistent sampling),
  skinny cells 3:1 (⇒ subdywizja hiperboliczno-biegunowa — konforemność band-map),
  grout hierarchiczny wymaga dedykowanego `_grout_cells_poincare` (fallthrough =
  płaski), {7,3} NIEokresowe wzdłuż pasma (panoramy nie da się skleić z kopii),
  koszt realny ~5-5.5 d (nie 2-3). Skorygowane moje błędy: dedup `round(,4)`
  bezpieczny; heptagon ~0.74 j. (nie 0.79); komórki panoramy 80-150k (nie 50-80k).
- ✓ **User ZATWIERDZIŁ (b++)** — plan wpisany jako NASTĘPNY KROK + MEMORY.md
  [2026-07-15] + auto-memory `project_poincare_bpp_plan.md`.

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES — poincare wg (b++):** kroki 1-5 z NASTĘPNEGO KROKU (~5-5.5 d,
  wieloseryjne) → potem pula extra 21-43. Po WSZYSTKICH → selekcja finalna usera
  → galeria 16K.
- ⟳ **Galeria 16K triangle+hexagon** — odłożona do wdrożenia wszystkich kształtów.
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ escher_lizard: docelowa sylwetka jaszczurki = ręczne dostrojenie offsetów (estetyka).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon.
- ⟳ (drobny dług) README nie dokumentuje flag `--grout` / `--grout-level` (nie regresja).

## Aktywne pliki

- (sesja 2026-07-15 dotąd planistyczna — kod nietknięty; poniżej zestaw roboczy kroku 1)
- `src/engine_smart.py` — cel portu: nowy `_gen_poincare` (~l. 1665, obok `_gen_girih`),
  wpis `SHAPE_MODES` (~l. 1698); później `_grout_cells_poincare` (~l. 2308),
  `_HIERARCHICAL_GROUT` (l. 2440), `GROUT_HIERARCHICAL` (l. 52), gałąź
  `_polygon_grout_cells` (l. 2222).
- `src/tools/gen_fable_shape_schemes.py:302-419` — geometria źródłowa do portu
  (`_geo_circle`/`_reflect`/`_edge_arc`/`gen_poincare`).
- `src/grout.py` — BEZ zmian (konsumuje g2/g3).
- `tests/test_golden_shapes.py` — dojdą goldeny poincare + NOWY test partycji
  (zero `len(adj)==1` we wnętrzu kadru).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (bez zmian).
- **Peak-RAM panoramy 4:1** (80-150k `_LazyMask` vs inwariant A1 3.9 GB @16K) —
  zmierzyć w kroku 5, PRZED obietnicą hero-panoramy 36000×9000.
- (rozstrzygnięte 2026-07-15: „BFS drogi @16K" — obalone, patrz MEMORY [2026-07-15])

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis **[2026-07-15]** w „Aktywne TODO" — plan poincare (b++)
  zatwierdzony (BFS w dysku + prune w paśmie, diam-cutoff wylatuje, subdywizja
  hiperboliczno-biegunowa, anty-T-junction, grout dedykowany, panorama nieokresowa).
- Auto-memory: `project_poincare_bpp_plan.md` (unieważnia „BFS drogi @16K"
  z last_session 2026-07-14).
- (poprzednia sesja 2026-07-14: `project_girih_lattice.md`, `project_grout_levels.md`)

# last_session.md

**Sesja:** 2026-07-13 · ~11:30-12:30
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** e8e0b74 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring girih** — port `_girih_attempt` (`src/tools/gen_fable_shape_schemes.py:585`) do `engine_smart.py` jako `_gen_girih`, z rozstrzygnięciami z MEMORY [2026-07-11b]:
1. **Fix `commit()`** (gen_fable:625-627): zamiast pełnej kopii rastra okupacji po każdym kaflu (`occ_np[:] = np.array(occ)` — setki GB memcpy przy 16K) rysować kafel do bufora wielkości bboxa i OR-ować w `occ_np[y0:y1, x0:x1]` ⇒ O(pole kadru).
2. **`RAD` rosnący z przekątną kadru** (w jednostkach girih) — inwariant „pole dominującego kafla ~ base_s²".
3. **Inflacja convex-hulla dziur 1.10 → ~1.0** (w silniku nakładka = dwa zdjęcia walczące o piksele; uszczelnienie szwu zostawić `render_padding`).
4. **Stały `_GIRIH_SEED` + sweep offline**: commitowany skrypt w `src/tools/` drukujący pokrycie per seed; zwycięzca jako stała z komentarzem o zmierzonym pokryciu (NIE `_shape_seed` per-wymiary — preview 2K mógłby trafić dobry patch, a 16K dziurawy).
5. Bramki jak zawsze: rasteryzacja pokrycia (cel 0% dziur; scratch `check_coverage.py` — wzorzec w archiwum czatu), goldeny both-borders ×2 procesy, render 2K na `input/0013.jpg`, pełny pytest. Spodziewany czas girih @16K po fixie: 1-3 s (najwolniejszy kształt, akceptowalne). Fallback (tylko gdyby za wolno): girih podstawieniowy Lu-Steinhardt — zadanie badawcze, nie zaczynać od niego.

Kontekst: to przedostatnia pozycja PLAN_SHAPES przed pulą extra (kolejność ustalona 2026-07-11: → poincare → extra 21-43). Tier B (truchet/weave) ZAMKNIĘTY w tej sesji. User chce WSZYSTKIE kształty przed selekcją finalną i galerią 16K.

---

## Co zrobiono w tej sesji

- ✓ **`/start`** — stan spójny; wypchnięty zaległy commit sesyjny `9eae032`.
- ✓ **Wiring voderberg + escher_lizard + weave** (`5e27d0c`): voderberg z 2 korektami skali (wygięcie i grubość pierścienia zależne od promienia), escher 1:1, **weave przebudowany na prawdziwą partycję** (widoczne kawałki wstęg + komórki-węzły; schemat PNG zregenerowany z geometrii silnika). Pokrycie: 0-0.01% dziur.
- ✓ **Wiring truchet + truchet_hex** (`ee00c92`, Tier B zamknięty bez `_CurvedMask`): komórki = regiony wycięte łukami; nowy helper `_arc_pitch(r,tol)` (pułapka: krok `base_s/3` fasetował łuki o promieniu ~base_s/2); orientacja z hasha indeksu (zero RNG, wzór stały między rozdzielczościami); schematy GUI zregenerowane z silnika (`src/tools/gen_truchet_schemes.py`).
- ✓ **FIX pikselozy groutu** (`e8e0b74`, zgłoszenie usera): `draw_grout` = AA kapsuły ss=4 przez maskę L, downscale BOX (nie LANCZOS — ringing); 16K = 4 s; `grout_preset=None` bit-w-bit. Diagnoza: aliasowane `ImageDraw.line` + tool propozycji rysujący na SS=2 (wada niewidoczna przy akceptacji).
- ✓ Rejestr `SHAPE_MODES`: 32 → **37**; +10 goldenów cross-proces; **363 testy zielone**; PLAN_SHAPES.md zaktualizowany (S6/S7-połowa/S8 zrobione).
- ✓ Rendery testowe 2K: `output/new3_{voderberg,escher_lizard,weave,truchet,truchet_hex}.jpg`; zoom groutu: `output/grout_aa_zoom.png`.

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES — ostatnie kształty:** girih (NASTĘPNY KROK) → poincare (model pasmowy, BFS odbić — najdroższy) → pula extra 21-43. Po WSZYSTKICH → selekcja finalna usera.
- ⟳ **Galeria 16K triangle+hexagon** — odłożona do wdrożenia wszystkich kształtów.
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ escher_lizard: docelowa sylwetka jaszczurki = ręczne dostrojenie offsetów polilinii (zadanie estetyczne z userem, geometria bez zmian).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon.

## Aktywne pliki

- `src/engine_smart.py` — +5 generatorów (`_gen_voderberg`, `_gen_escher`, `_gen_weave`, `_gen_truchet`, `_gen_truchet_hex`), helpery `_arc_pitch`/`_truchet_flip`, rejestr 37; `_apply_grout` woła nowe `draw_grout(img,…)`.
- `src/grout.py` — `draw_grout` przepisany (AA kapsuły ss=4, maska L, BOX).
- `src/tools/gen_fable_shape_schemes.py` (`gen_weave` = partycja), `src/tools/gen_truchet_schemes.py` (NOWY), `src/tools/gen_grout_proposals.py` (caller).
- `tests/test_golden_shapes.py` (+10 goldenów), `tests/test_grout.py` (nowa sygnatura).
- `assets/shape_schemes/{weave,truchet,truchet_hex}.png` — zregenerowane z geometrii silnika.
- `PLAN_SHAPES.md` — S8 zamknięty, wpisy weave/truchet zaktualizowane.

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (bez zmian).
- Girih: fallback podstawieniowy (Lu-Steinhardt) TYLKO jeśli greedy po fixie `commit()` przekroczy kilka sekund przy 16K.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis **[2026-07-13]** w „Aktywne TODO" — 5 kształtów (korekty skali voderberga, weave-partycja, pułapka `_arc_pitch`, truchet bez RNG) + fix groutu (BOX nie LANCZOS, lekcja „tool propozycji musi rasteryzować jak silnik").
- Auto-memory: `project_grout_aa_fix.md` (diagnoza + fix pikselozy groutu).

==============================================================================

