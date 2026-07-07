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

