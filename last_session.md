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
