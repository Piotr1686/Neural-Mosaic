## ═══ Sesja zarchiwizowana [2026-07-04 21:58] ═══

# last_session.md

**Sesja:** 2026-07-04 · (sesja poprawek kształtów, Fable 5)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 75bf7df @ main (2 commity kodu: cedb2ce fix engine + 75bf7df feat shapes; NIE wypchnięte — push do decyzji)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Ostatni element ETAP A: przerobić `gen_hirotaka` w `src/tools/gen_extra_shape_schemes.py` na Penrose P2 (kites & darts) przez deflację trójkątów Robinsona** — usunąć `_bg_grid` (ostatni kształt z tłem). UWAGA: `kepler_ty` to już rhombic Penrose z pentagridu (P3-podobny), więc hirotaka musi być odróżnialny — właśnie latawce+strzałki (P2), kolorowane tak, by wyszły gwiazdy/słońca 5-krotne. Po nim: user robi selekcję finalną z 16 paneli montażu → potem Sprint 2 (wiring `_polygon_sector`/`SHAPE_MODES` w `_do_render`).

Kontekst: cała reszta rewizji kształtów jest DOMKNIĘTA (9 poprawek usera + 4 nowe kształty, wszystko zweryfikowane wizualnie i zacommitowane). Hirotaka to jedyny pozostały `[ETAP A]` placeholder.

---

## Co zrobiono w tej sesji

- ✓ **Pakiet 9 poprawek usera (/goal) — wszystkie:** bloom→Voronoi phyllotaxis (21 ramion, bez tła); dragon→twindragon rep-tile order 8 (zero nakładania); gereh→same czworokąty (gwiazda-8 z 8 rombów, r_in=0.60·apotema); kepler_ty→pentagrid de Bruijna N=5 (romby Penrose'a); koch_snowflake→teselacja 2-rozmiarowa (małe 1/√3, obrót 30°, bilans pól dokładny); sierpinski→cegiełkowy rozkład dziur (rzędy ±S/2, depth 3) + plan foto (dziury poziomów = coraz większe zdjęcia); poincare→kontynuacja inwersyjna poza okrąg + Möbius, bez tła; rodzina radialna→sam nautilus (biegun poza kadrem, mandala/vortex/shatter USUNIĘTE); **kites: FIX W SILNIKU** (okno `r` centrowane na `-q//2`, oba miejsca engine_smart.py) — golden 8/8 bez zmian hashy, 181 testów zielonych.
- ✓ **4 nowe kształty na życzenie usera (w trakcie sesji):** `rosette` = 12-krotna rozeta zellij Fez (partycja 3.12.12; 2 fixy: trójkąty dziur po WSZYSTKICH centrach + filtr BOX); `scales` = rybie łuski (pokrycie dokładne, kopuła+2 łuki); `pebbles` = Voronoi zmiennej gęstości (obrazek usera); `rosette_fractal` = aloes spiralny (log-polarny pas trójkątów ze skrętem).
- ✓ **Nowy commitowany tool** `src/tools/gen_kites_scheme.py` (generator schematu kites — stary przepadł ze scratchpadem Opusa).
- ✓ `_clip_rect` przeniesiony do `gen_fable_shape_schemes.py` (gen_extra importuje — bez cyklu importów).
- ✓ Montaż extra = 16 paneli 4×4 (`proposals_extra_15_shapes.png`, nazwa historyczna); montaż Fable przeliczony (nowy poincare, girih seedy w tle).
- ✓ Weryfikacja: **181/181 pytest + golden 8/8**; wizualna weryfikacja każdego panelu.
- ✓ Commity: `cedb2ce` fix(engine) kites + `75bf7df` feat(shapes) rewizja.

## Co zostało (backlog sesji)

- ⟳ **hirotaka → Penrose P2 deflacja** (NASTĘPNY KROK, ostatni [ETAP A]).
- ⟳ **Push** cedb2ce+75bf7df (+commit stanu) na origin/main — do decyzji usera.
- ⟳ **Selekcja finalna kształtów** przez usera (16 paneli extra + 10 Fable + 10 Opus) → które wdrażamy w silniku.
- ⟳ **Sprint 2 (`_do_render` refaktor)** — wiring `_polygon_sector` + `SHAPE_MODES` (golden gotowe, szkielet dodany addytywnie; ryzyko bbox spectre opisane w MEMORY [2026-07-02]).
- ⟳ **Standing:** galeria 16K triangle+hexagon (czeka na pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/tools/gen_extra_shape_schemes.py` (przepisany — 16 kształtów, w tym 4 nowe; hirotaka = jedyny z `_bg_grid`)
- `src/tools/gen_fable_shape_schemes.py` (M — poincare inwersja+Möbius, `_clip_rect`)
- `src/tools/gen_kites_scheme.py` (NOWY)
- `src/engine_smart.py` (M — fix okna pętli r w kites, 2 miejsca)
- `assets/shape_schemes/*.png` (16 zmienionych/nowych; mandala/vortex/shatter usunięte)

## Otwarte pytania

- Push na origin — nie wykonany (user kończył sesję limitem tokenów).
- Czy `rosette_fractal` ma trafić do puli selekcji, czy to eksperyment? (user nie doprecyzował)
- Sub-pikselowy pierścień w poincare przy |w|=1 — w realnym renderze silnik i tak będzie potrzebował min-rozmiaru kafla; zaakceptowane w schemacie jako „horyzont".

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: NOWY wpis [2026-07-04] — fix kites (-q//2, golden nietknięte), techniki: twindragon rep-tile (kasowanie krawędzi + skręt w lewo), inwersja poincare (okno w dysku NIE działa), teselacja 2-size Kocha (bilans pól), rozeta 3.12.12 (pułapki: dziury po wszystkich centrach, filtr BOX), scales (pokrycie dokładne), redukcja rodziny radialnej.
- Auto-memory: `project_extra_15_shapes` rozbudowane o pełną rewizję 2026-07-04 + zaindeksowane w MEMORY.md (wcześniej brakowało w indeksie).

## ═══ Sesja zarchiwizowana [2026-07-04 11:30] ═══

# last_session.md

**Sesja:** 2026-07-03 · (długa sesja na modelu Fable 5)
**Status:** ✓ Zakończona poprawnie (ETAP B schematów ZACOMMITOWANY `6aef038` + push)
**Punkt odniesienia (git):** 6aef038 @ main (ETAP B feat commit; po push zsynchronizowany z origin/main — dawne e9d52ce/b6429aa/8aca263 też wypchnięte)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**ETAP A: przerobić 5 pozostałych schematów na PRAWDZIWE teselacje.** Kolejność wg pewności:
1. `gen_bloom` (najpewniejsze) → `scipy.spatial.Voronoi` na ziarnach phyllotaxis (kąt złoty) rozszerzonych POZA ramkę, każdy region przez istniejący `_clip_rect(poly, R)` do `[-R,R]²`. Voronoi ziaren słonecznika = naturalna teselacja wypełniająca.
2. `gen_hirotaka` → Penrose (deflacja trójkątów Robinsona), pokolorowany na gwiazdy 5-krotne.
3. `gen_koch_snowflake` → 2-rozmiarowy kafel Kocha (duży + mniejszy towarzysz kafelkują).
4. `gen_dragon` → twindragon-**reptile** (kafle w kształcie smoka), zastąpić placeholder-wstęgi (teraz `order=6`, ~16k wielokątów przy order 9 wieszało montaż).
5. `gen_kepler_ty` → teselacja 5-krotna gap-free (aperiodyczna, najtrudniejsza).

Kontekst: user narzucił iteracyjnie TWARDĄ regułę — KAŻDY kształt musi być prawdziwą teselacją brzeg-w-brzeg (bez nakładania, bez luk, wypełnia prostokąt, samopowtarzalny). ETAP B (10 pewnych) zrobiony i zweryfikowany wizualnie; ETAP A to 5 trudnych aperiodycznych/reptile/fraktalnych, świadomie odłożonych i oznaczonych `[ETAP A]` w `SHAPES`. Wszystkie generatory szybkie (<0.02s) — jedyny problem wydajności to render dragona (dużo wielokątów).

---

## Co zrobiono w tej sesji

- ✓ **Analiza (na życzenie usera):** problemy mozaik girih/poincaré/voderberg (dziury greedy, subpikselowe kafle przy brzegu dysku, osobliwość centrum spirali); centralny kafel problematyczny (duży kafel-dominant w poincaré/girih, drzazgi w voderberg). **Czarna pustka w `kites`** — diagnoza: luka generacji siatki, człon shear `q/2` vs stały `range_r` (engine_smart.py:520) → prawy-dolny róg bez kafli. Fix (nie wdrożony): pętla `r` wokół `-q/2`.
- ✓ **Nowy generator `src/tools/gen_extra_shape_schemes.py`** — 16 schematów (21-35 + `stagger_tri` 36). Importuje helpery z `gen_fable_shape_schemes`.
- ✓ **ETAP B — 10 PRAWDZIWYCH teselacji** (wypełniają prostokąt, zero nakładania/luk): `sierpinski` (PRZEROBIONY na prawdziwy rekurencyjny z zagnieżdżonymi dziurami-komórkami, kafelkowany up+down), `gereh` (ośmiokąt=gwiazda-8+8 latawców, partycja), `koch_island` (reptile Minkowskiego, period=4^depth), `rosette`+`mandala` (koncentryczne KOŁA przycięte do prostokąta — pomysł usera), `nautilus`+`vortex` (radialne pierścienie ze skrętem, log/liniowe), `shatter` (radialne poza rogi), `moire` (GEOMETRYCZNA zwichrowana siatka — nie kolor), `braid` (basketweave, płaski przeplot bez nad/pod).
- ✓ **`stagger_tri` (#36)** — stary „sierpinski" (przesunięte warstwy trójkątów) zachowany pod nową nazwą na życzenie usera.
- ✓ **Poprawki w `gen_fable_shape_schemes.py`:** `poincaré` (siatka tła w rogach poza dyskiem), `voderberg` (promień poza rogi + kapsel centralny → wypełnia), `kepler_ty` w extra (gęstszy dekagon+10 pięciokątów — nadal ETAP A).
- ✓ **Techniki (do pamięci):** helper `_radial_clip_cells` (sektory×pierścienie, rozszerz poza rogi + clip), `_clip_rect` (Sutherland-Hodgman do prostokąta), seam-fix (offset o pół sektora co drugi pierścień).
- ✓ **Referencje usera:** czasopismomatematyka.pl (gereh=wypełnianie wielokątów liniami z krawędzi → przerobiłem na partycję; „fraktal Hirotaki" pokazany graficznie bez definicji → placeholder pentaflake/Penrose).

## Co zostało (backlog sesji)

- ✓ **COMMIT + PUSH ZROBIONE:** ETAP B `6aef038` (feat shapes) + `chore(session)` wypchnięte na origin/main.
- ⟳ **ETAP A (NASTĘPNY KROK):** 5 trudnych — bloom→Voronoi, hirotaka→Penrose, koch_snowflake→2-size, dragon→reptile, kepler_ty→teselacja 5-krotna.
- ⟳ **Montaż** `output/kite_schemes/proposals_extra_15_shapes.png` regenerowany w tle na końcu (36 shapes) — sprawdzić przy starcie.
- ⟳ **Sprint 2 (`_do_render` refaktor)** — NADAL NIETKNIĘTY (pivot na schematy); zduplikowane gałęzie kites/spectre wciąż w engine_smart.py:507/592, cli.py:26 zahardkodowany. To był oryginalny „następny krok" z poprzedniej sesji.
- ⟳ **`kites` czarna pustka** — fix zdiagnozowany (pętla r wokół -q/2), niewdrożony (dotyka golden → regeneracja hasha, po Sprint 2).
- ⟳ **Standing:** galeria 16K triangle+hexagon (czeka na pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/tools/gen_extra_shape_schemes.py` (NOWY — 16 schematów; helpery `_radial_clip_cells`/`_clip_rect`; ETAP A: bloom/hirotaka/koch_snowflake/dragon/kepler_ty)
- `src/tools/gen_fable_shape_schemes.py` (M — poincaré/voderberg/kepler naprawione)
- `assets/shape_schemes/*.png` (~16 nowych/zmienionych)
- `src/engine_smart.py` (NIETKNIĘTY — cel Sprint 2 refaktor + fix pustki kites)

## Otwarte pytania

- ⚠ **Commit teraz?** Propozycja (2 commity): (1) `feat(shapes): 15+ schematow jako prawdziwe teselacje (ETAP B) + gen_extra_shape_schemes.py` obejmujący gen_extra + assets + poincare/voderberg fix; (2) osobno stan sesji. Push (+3 niewypchnięte: e9d52ce, b6429aa, 8aca263) — do decyzji.
- Decyzja B potwierdzona przez usera: rodzina kolista→teselacja gwiaździsta/koncentryczna; niemożliwe→kafelkujące kuzyny. Trudne ETAP A mogą wyjść przybliżone (oznaczyć uczciwie).
- Selekcja finalna 36 kształtów → które wdrożyć w silniku — PO wygenerowaniu wszystkich (ETAP A).

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: NOWY wpis [2026-07-03] o ETAP B (10 teselacji), regule „prawdziwa teselacja", technikach `_radial_clip_cells`/`_clip_rect`, ETAP A pending.
- Auto-memory: [[project_extra_15_shapes]] rozbudowane (wymóg teselacji, decyzje B, moire≡square caveat, gereh/koch_island/dragon).

## ═══ Sesja zarchiwizowana [2026-07-03 23:43] ═══

# last_session.md

**Sesja:** 2026-07-02 · ~23:05-23:35
**Status:** ✓ Zakończona poprawnie (przerwana na życzenie usera przy ~94% tokenów; stan spójny, 50/50 testów)
**Punkt odniesienia (git):** e9d52ce @ main (working tree DIRTY — Sprint 2 W TOKU, niezacommitowane; e9d52ce nadal NIEwypchnięty na origin)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dokończ refaktor `_do_render` w `src/engine_smart.py` — podmień 2 gałęzie na 1 polygon.** Konkretnie: zastąp bloki `if shape_mode == "kites": ... elif shape_mode == "spectre": ...` (obecnie ~linie 504-644, kończą się tuż przed `else:` gałęzi grid) JEDNĄ gałęzią:
```python
spec = SHAPE_MODES.get(shape_mode)
if spec is not None and spec.kind == "polygon":
    print(f"Mode: {shape_mode} (polygon sectors). Borders: {border_mode}")
    polys = list(spec.generator(self, target_w, target_h, base_s))
    for i_poly, poly in enumerate(tqdm(polys, desc=f"Sampling {shape_mode} sectors")):
        sector = self._polygon_sector(target, poly, render_padding, spec.aa, edge_aware)
        if sector is None:
            continue
        m = sector["meta"]
        sector["meta"] = (i_poly,) + m[1:]   # meta[0] nieużywane gdy is_hat=False
        sectors_data.append(sector)
else:
    # ... istniejąca gałąź grid (zmień `else:` grida tak, by był fallbackiem) ...
```
Potem: (a) `pytest tests/test_golden_shapes.py` — **kites MUSI zostać identyczny**; ⚠ **spectre MOŻE paść** (helper=strategia kites/offset, nie spectre/clamp-min→0 — patrz Otwarte pytania); (b) podłącz `shape_names()` w `gui.py:389`, `cli.py:26` (`_SMART_SHAPES`), `make_showcase.py:269` (import z `engine_smart`); (c) pełny `pytest`; (d) commit.

Kontekst: helper `_polygon_sector`, rejestr `SHAPE_MODES`, generatory `_gen_kites`/`_gen_spectre` i `shape_names()` SĄ JUŻ w `engine_smart.py` (dodane addytywnie, przetestowane pośrednio), ale `_do_render` ich jeszcze NIE używa — nadal działają stare, zduplikowane gałęzie. To ostatni krok Sprint 2 przed S3.

---

## Co zrobiono w tej sesji

- ✓ **/start + sanity-check:** stan spójny; wykryto że `e9d52ce` (finalizacja poprz. sesji) NIE jest wypchnięty na origin (branch +1).
- ✓ **Golden testy Sprint 2** (`tests/test_golden_shapes.py`): 8 przypadków (square/hexagon_romb/kites/spectre × border on/off), deterministyczna syntetyczna biblioteka (32 kafle, seed 12345) + gradient 384×288, SHA-256 policzone na silniku PRZED refaktorem (skrypt scratchpad), reprodukowalne 2×. **8/8 zielone.**
- ✓ **Szkielet refaktoru w `engine_smart.py`** (addytywny, kod nadal działa): helper `_polygon_sector(target, poly, render_padding, aa, edge_aware)` (bbox-strategia kites); dataclass `ShapeSpec` + rejestr `SHAPE_MODES` + `shape_names()`; generatory modułowe `_gen_kites`/`_gen_spectre` (Y-flip przeniesiony do generatora); `from dataclasses import dataclass`.
- ✓ **Dowód równoważności kites:** Y-flip w generatorze + shrink-do-centroidu w helperze = identyczny `padded_poly` (flip afiniczny komutuje z centroidem).
- ✓ **Weryfikacja:** `pytest tests/test_golden_shapes.py tests/test_smart_engine.py` → **50/50 zielone** po dodaniu szkieletu.

## Co zostało (backlog sesji)

- ⟳ **Dokończyć Sprint 2** (NASTĘPNY KROK): podmiana gałęzi w `_do_render` + wiring GUI/CLI/showcase do `shape_names()` + golden PO + commit. Potem S3 (multigrid: penrose, ammann_beenker).
- ⟳ **DIRTY working tree:** `src/engine_smart.py` (M), `tests/test_golden_shapes.py` (??) — NIEzacommitowane (Sprint 2 niedokończony).
- ⟳ **`e9d52ce` nadal NIEwypchnięty** na origin/main (branch +1). Rozważyć push przy najbliższym commicie.
- ⟳ **Standing:** galeria 16K triangle+hexagon (czeka na pliki usera); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/engine_smart.py` (szkielet gotowy; do zrobienia: podmiana gałęzi w `_do_render` ~504-644)
- `tests/test_golden_shapes.py` (bramka golden — nie zmieniać hashy bez powodu)
- `PLAN_SHAPES.md` (kanoniczny plan S2–S9)
- `src/gui.py:389`, `src/cli.py:26`, `src/tools/make_showcase.py:269` (do podłączenia `shape_names()`)
- `src/tools/gen_fable_shape_schemes.py` (referencyjna geometria 10 kształtów Fable — dla S3+)

## Otwarte pytania

- ⚠ **Golden spectre może paść po podmianie gałęzi.** Helper używa strategii bboxa kites (repaste z offsetem, `int(min_x)` może być ujemne), a stara gałąź spectre clampowała `min` do `0.0` i pastowała w `(0,0)`. Dla kafli spectre przecinających GÓRNY/LEWY brzeg zmienia to sub-pikselowe wyrównanie maski. **Decyzja przy wznowieniu:** jeśli padnie → (a) zregenerować golden spectre + udokumentować poprawne edge handling (wg PLAN_SHAPES.md pkt 1 — kites strategia jest zamierzona), albo (b) dodać per-shape flagę strategii bboxa do `ShapeSpec`. Rekomendacja: (a) — plan świadomie unifikuje na strategii kites.
- **Girih (S7):** greedy ~97% pokrycia → dziury; decyzja z userem na starcie S7.
- **Truchet (S8):** go/no-go po prototypie 1 kafelka.

## Do MEMORY.md (przeniesiono)

- [Aktywne TODO] NOWY [2026-07-02] „Sprint 2 W TOKU — golden + szkielet gotowe, wiring NIE" (golden 8/8, `_polygon_sector`+`SHAPE_MODES`+generatory addytywnie, dowód równoważności kites, ⚠ ryzyko golden spectre).

## ═══ Sesja zarchiwizowana [2026-07-02 23:30] ═══

# last_session.md

**Sesja:** 2026-07-02 · ~20:45-23:05
**Status:** ✓ Zakończona poprawnie (model przełączony na Opus; wszystko wypchnięte)
**Punkt odniesienia (git):** 37af281 @ main (zsynchronizowany z origin/main — wszystko WYPCHNIĘTE; working tree czysty)

## ▸ NASTĘPNY KROK — Sprint 2 refaktor rdzenia kształtów wg PLAN_SHAPES.md
(1) golden SHA-256 kites+spectre+2 grid PRZED zmianami; (2) helper `_polygon_sector`; (3) rejestr `SHAPE_MODES`; (4) golden identyczne PO → commit.

## Co zrobiono (skrót)
- Sprint 1b domknięty (3a186b7); audyt kites vs spectre; 20 kształtów w kolejce (10 Opus + 10 Fable, e6c55f4); PLAN_SHAPES.md kanoniczny; push d67dd08..37af281; model→Opus 4.8; finalizacja e9d52ce.

---

## ═══ Sesja zarchiwizowana [2026-07-02 22:55] ═══

# last_session.md

**Sesja:** 2026-06-30 · 21:30-22:16
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** d67dd08 @ main (working tree DIRTY — praca `kites` niezacommitowana, 8 plików)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint 1a — uruchom generator schematów.** Plik gotowy: `scratchpad/gen_shape_schemes.py` (ścieżka pełna w sesji, lub odtworzyć z MEMORY/historii) → produkuje 19 PNG do `assets/shape_schemes/<shape_mode>.png` (10 nowych + 9 istniejących z wiernej geometrii silnika). Komenda: `KMP_DUPLICATE_LIB_OK=TRUE C:/Users/plazo/miniconda3/envs/mosaic/python.exe gen_shape_schemes.py`. Po wygenerowaniu obejrzeć kilka (spectre, kites, hexagon_romb) i przejść do Sprint 1b (GUI).

Kontekst: User chce zaimplementować wszystkie 10 nowych kształtów (plan 7 sprintów), ale NAJPIERW funkcję „schemat na podglądzie GUI". Generator był gotowy do uruchomienia — user przerwał TUŻ przed wykonaniem, żeby zamknąć sesję. `assets/shape_schemes/` jeszcze NIE istnieje.

---

## Co zrobiono w tej sesji

- ✓ **Tryb `kite` → `kites` (#1 deltoidal per-tile)** — zastąpiono losowe 8-kite „kapelusze" czystym kafelkowaniem: 6 latawców/heksagon, każdy osobnym sektorem. Bez RNG → reprodukowalność preview↔render bit-w-bit (zweryfikowane `np.array_equal`). `is_hat=False` → anty-powtórzenia globalne. Usunięto importy `random`/`defaultdict`. Netto −142/+80 linii w `engine_smart.py`.
- ✓ **Podmiana nazwy `kite`→`kites`** wszędzie: `gui.py` dropdown, `cli.py`, `make_showcase.py`, `benchmark.py`, README EN+PL (listy opcji + opisy), root `MEMORY.md` (geometria+słownik).
- ✓ **Weryfikacja:** 201/201 testów, render CLI `kites` działa (`output/kite_schemes/_render_kites_preview.png`).
- ✓ **Schematy projektowe:** 5 wariantów układu kite (`output/kite_schemes/kite_schemes.png`, `kite_134.png`); 10 propozycji nowych kształtów wow (`output/kite_schemes/proposals_10_shapes.png`).
- ✓ **Plan 7 sprintów** (M1–M7) na 10 nowych kształtów + decyzja GUI: schemat w panelu podglądu (zastępowany renderem).
- ✓ **Generatory schematów** napisane w scratchpad (`gen_shape_schemes.py`, `shapes10.py`) — NIE uruchomione.
- ✓ Pamięć: `project_kites_mode.md`, `project_10_shapes_plan.md` (+ indeks MEMORY.md).

## Co zostało (backlog sesji)

- ⟳ **COMMIT `kites` (NIEZACOMMITOWANY!):** 8 plików gotowych, treść commitu zaproponowana — czeka na akceptację (patrz Otwarte pytania).
- ⟳ **Sprint 1b (GUI):** dropdown `combo_shape` default→`None`; po wyborze ładować `assets/shape_schemes/<shape>.png` do `lbl_preview_p` przez `_fit_preview`; guard `None` w `_trigger_smart_preview` (gui.py:645) i pełnym renderze (gui.py:985); `None` → blok przycisku preview.
- ⟳ **Sprint 2:** refaktor `_build_polygon_sectors()` + rejestr `shape_mode→generator` (golden SHA-256 zielone).
- ⟳ **Sprinty 3–7:** Tier A (penrose, voronoi, phyllotaxis, trunc_square, trunc_hex, rhombitrihex, sunburst, pythagorean) → Tier B (truchet, truchet_hex, `_CurvedMask`) → docs.
- ⟳ **Standing:** galeria 16K triangle+hexagon (czeka na pliki usera); Krok 6 portfolio (audyt README); test_dzi + pasek postępu DZI ([[project_dzi_gui_polish_todo]]).

## Aktywne pliki

- `src/engine_smart.py` (kites; cel Sprint 2 refaktor), `src/gui.py` (cel Sprint 1b)
- `assets/shape_schemes/` (DO UTWORZENIA — Sprint 1a)
- scratchpad: `gen_shape_schemes.py`, `shapes10.py`, `kite_schemes.py`, `kite_134.py`
- `output/kite_schemes/*` (montaże podglądowe)

## Otwarte pytania

- ⚠ **Czy commitować `kites`?** Working tree dirty (8 plików), zweryfikowane. Proponowany commit: `feat(engine): replace random-hat 'kite' with deterministic per-tile 'kites'`. NIE zrobiony — przerwano przed /end. Do decyzji na starcie następnej sesji.
- Nazwy kanoniczne nowych `shape_mode` (ustalone): penrose, truchet, truchet_hex, phyllotaxis, sunburst, voronoi, trunc_square, trunc_hex, rhombitrihex, pythagorean.

## Do MEMORY.md (przeniesiono)

- [Aktywne TODO] NOWY [2026-06-30] „Tryb kite→kites ZROBIONE (NIEZACOMMITOWANE)" + „PLAN: 10 nowych kształtów wow + schemat na podglądzie GUI (7 sprintów)".
- [.claude] `project_kites_mode.md`, `project_10_shapes_plan.md`.

