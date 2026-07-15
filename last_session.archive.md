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

## ═══ Sesja zarchiwizowana [2026-07-13 12:30] ═══

# last_session.md

**Sesja:** 2026-07-11 · ~22:30-23:00 · (Opus 4.8) — sesja konsultacyjna, ZERO zmian w kodzie
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 3c5bde5 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring voderberg + escher_lizard + weave** — trzy ostatnie kształty z gotową geometrią w `src/tools/gen_fable_shape_schemes.py` (`gen_voderberg`:425, `gen_escher`:495, `gen_weave`:534; RNG tylko do kolorów paneli, geometria deterministyczna). Wzorzec identyczny jak Fable ×4 z 5e04b42:
1. Port geometrii do `engine_smart.py` jako `_gen_<shape>(engine, w, h, base_s)` w image space (scheme renderer był y-down → bez flipu); skala: pole DOMINUJĄCEGO kafla ~ base_s².
2. Wpis `ShapeSpec("polygon", _gen_<shape>, aa=4)` w `SHAPE_MODES` (dziś 32 wpisy).
3. Rasteryzacja pokrycia (scratch `check_coverage.py` — wzorzec w archiwum czatu; cel 0% dziur, sub-px na łukach OK) + side-by-side z PNG schematu.
4. Goldeny both-borders ×2 procesy (scratch `gen_goldens.py`) → hashe do `GOLDEN` w `tests/test_golden_shapes.py`.
5. Montaż na `input/0013.jpg` (CLI render 2K) + pełny pytest.

UWAGA voderberg: środek przeprojektowany werdyktem 2026-07-05 (pierścienie od r=0, 8 wygiętych klinów w biegunie, `arc_in=[]` gdy `rin==0`) — portować wersję z gen_fable (już poprawioną), nie wymyślać od nowa. escher_lizard: krawędzie `_wavy` to poliliniowe poligony — przechodzą przez `_polygon_sector` bez nowej maszynerii.

Kontekst: to najtańsza z pozostałych pozycji PLAN_SHAPES (kod geometrii istnieje i jest wizualnie zwalidowany). Kolejność dalsza USTALONA w tej sesji: → **truchet ×2** (potaniał: bez `_CurvedMask`) → **girih** (fix `commit()` + sweep offline) → **poincare** (najdroższy: BFS odbić, model pasmowy) → pula extra 21-43. User chce WSZYSTKIE kształty przed galerią 16K i selekcją finalną.

---

## Co zrobiono w tej sesji

- ✓ **`/start`** — sanity-check: stan spójny, drzewo czyste, rejestr `SHAPE_MODES` = 32 potwierdzony empirycznie, `gen_voderberg`/`gen_escher`/`gen_weave` istnieją w gen_fable.
- ✓ **Wypchnięty zaległy commit sesyjny** `3c5bde5` (`9a74ff2..3c5bde5`) — `main` == `origin/main`.
- ✓ **ROZSTRZYGNIĘTE 2 z 3 otwartych pytań** (analiza kodu, nie spekulacja — decyzje w MEMORY.md wpis [2026-07-11b]):
  - **truchet: `_CurvedMask` ODRZUCONY** — precedens `_sun_arc`/sunburst (`engine_smart.py:981`) dowodzi, że polygonizacja łuku z sub-px strzałką + `aa=4` w `_LazyMask` = to samo co prawdziwa krzywa. Niewypukłość OK (spectre), wspólna krawędź dokładna przy identycznym wywołaniu `_sun_arc` z obu stron. Truchet spada z „najdroższy" na „jeden z najtańszych".
  - **girih: stały `_GIRIH_SEED` + sweep offline** (NIE `_shape_seed` per-wymiary — dałby dobry patch w preview 2K i dziurawy w 16K). Znaleziona PRAWDZIWA blokada: `commit()` w gen_fable:626-627 kopiuje CAŁY raster po każdym kaflu (setki GB memcpy przy 16K) → fix bbox-OR. Plus: `RAD` rosnący z kadrem (inwariant base_s²), inflacja hulla 1.10 → ~1.0.
- ✓ **Standing „GUI niesprawdzone wizualnie"** — user uznał za OK, zdjęte z listy pytań.
- ✓ MEMORY.md: wpis [2026-07-11b] w TODO + `_CurvedMask` w „Odrzucone podejścia".

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES — ostatnie kształty** (NASTĘPNY KROK = voderberg/escher_lizard/weave): potem truchet ×2, girih, poincare, pula extra 21-43. Po WSZYSTKICH → selekcja finalna usera.
- ⟳ **Galeria 16K triangle+hexagon** — odłożona do wdrożenia wszystkich kształtów (decyzja 2026-07-10).
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon.
- ⟳ Stare pliki batch `_grout-sredni` w output/ nie łapią skip-if-exists po rename presetów (kosmetyka).

## Aktywne pliki

- Żadnych zmian w kodzie w tej sesji. Pliki CZYTANE (kontekst dla następnego kroku):
  - `src/engine_smart.py` (`_sun_arc`:981, `_LazyMask`:74, `_polygon_sector`:1474, `_shape_seed`:614, `SHAPE_MODES`:1050, `_grout_cells`:1541)
  - `src/tools/gen_fable_shape_schemes.py` (`_girih_attempt`:585 z blokadą `commit()`:625-627, `gen_girih`:729; `gen_voderberg`:425, `gen_escher`:495, `gen_weave`:534)
- Zmienione: `MEMORY.md`, `last_session.md`, `last_session.archive.md` (pliki stanu).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (jedyne pozostałe otwarte pytanie; girih i truchet ROZSTRZYGNIĘTE w tej sesji).
- Girih: rewizja na wariant podstawieniowy (Lu-Steinhardt) TYLKO jeśli greedy po fixie `commit()` przekroczy kilka sekund przy 16K — zadanie badawcze, nie zaczynać od niego.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis **[2026-07-11b]** w „Aktywne TODO" — rozstrzygnięcie girih (stały seed, blokada `commit()`, RAD z kadru, inflacja hulla) + truchet (`_CurvedMask` zbędny, precedens `_sun_arc`) + ustalona kolejność wdrożenia pozostałych kształtów.
- Repo MEMORY.md: wpis **[2026-07-11]** w „Odrzucone podejścia" — `_CurvedMask` odrzucony, nie wracać.

## ═══ Sesja zarchiwizowana [2026-07-11 22:59] ═══

# last_session.md

**Sesja:** 2026-07-11 · ~10:30-12:30 · (Opus 4.8 + Fable 5)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 9a74ff2 @ main (zsynchronizowane z origin/main; wszystkie 4 commity sesji wypchnięte)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring voderberg + escher_lizard + weave** — trzy ostatnie kształty z gotową geometrią w `src/tools/gen_fable_shape_schemes.py` (`gen_voderberg`:425, `gen_escher`:495, `gen_weave`:534; RNG tylko do kolorów paneli, geometria deterministyczna). Wzorzec identyczny jak dzisiejsze Fable ×4:
1. Port geometrii do `engine_smart.py` jako `_gen_<shape>(engine, w, h, base_s)` w image space (scheme renderer był y-down → bez flipu); skala: pole DOMINUJĄCEGO kafla ~ base_s².
2. Wpis `ShapeSpec("polygon", _gen_<shape>, aa=4)` w `SHAPE_MODES`.
3. Rasteryzacja pokrycia (scratch `check_coverage.py` — wzorzec w archiwum czatu; cel 0% dziur, sub-px na łukach OK) + side-by-side z PNG schematu.
4. Goldeny both-borders ×2 procesy (scratch `gen_goldens.py`) → hashe do `GOLDEN` w `tests/test_golden_shapes.py`.
5. Montaż na `input/0013.jpg` (CLI render 2K) + pełny pytest.

UWAGA voderberg: środek przeprojektowany werdyktem 2026-07-05 (pierścienie od r=0, 8 wygiętych klinów w biegunie, arc_in=[] gdy rin==0) — portować wersję z gen_fable (już poprawioną), nie wymyślać od nowa. escher_lizard: krawędzie `_wavy` to poliliniowe poligony — przechodzą przez `_polygon_sector` bez nowej maszynerii.

Kontekst: po dzisiejszych 11 kształtach z PLAN_SHAPES zostają: ta trójka (najtańsza — kod istnieje), girih (sweep seedów → potrzebne decyzje: zamrożenie seeda per wymiary?), poincare (model pasmowy, BFS odbić — złożony), truchet×2 (wymaga nowej maszynerii `_CurvedMask`), pula extra 21-43. User chce WSZYSTKIE kształty przed galerią 16K i selekcją finalną.

---

## Co zrobiono w tej sesji

- ✓ **Pakiet poprawek po uwagach usera** (5f3ada0): presety groutu EN `thin`/`medium`/`thick` wszędzie (grout.py/GUI/CLI/sufiks batch); `used_tiles.json` opt-in domyślnie OFF (param `save_used_tiles`, checkbox GUI, flaga `--save-used-tiles`); **generyczny flat grout dla WSZYSTKICH kształtów polygon** (`_grout_cells` fallback re-yieldujący poligony generatora → linie na szwach; naprawia „grout nie działa na nowych kształtach").
- ✓ **Fable ×4 wdrożone** (5e04b42): pinwheel (substytucja Conway-Radin, pruning w subdywizji), cairo, floret, gosper (162-gon depth-3). Helper `_lattice_mn_range`. Pokrycie ≤0.025%, chiralność zgodna z PNG (scheme renderer y-down).
- ✓ **Archimedesowe ×5 OD ZERA z PNG schematów** (98924bd; kod Opusa przepadł): trunc_square, trunc_hex, rhombitrihex (ciemne trójkąty PNG = pełnoprawne komórki), pythagorean (pułapka dziury [b-s,b]×[b,b+s] — złapana rasteryzacją, było 19% dziur), sunburst (log-polar, twist −0.18, czapka 7 klinów, łuki polygonizowane).
- ✓ **Multigrid ×2 wdrożone** (9a74ff2): `_multigrid_dual` (Cramer verbatim ze zwalidowanego kodu; okno przecięć = kadr/(N/2) → 16K w 0.2 s); penrose P3 (pentagrid γ suma=1) + ammann_beenker (N=4, zgodny 1:1 z PNG).
- ✓ **Bilans: +11 kształtów dziś, rejestr SHAPE_MODES = 32; 325 testów zielonych (+22 goldeny cross-proces).** Każdy kształt: rasteryzacja pokrycia + side-by-side ze schematem + montaż na 0013.jpg.
- ✓ Fix 2 testów groutu (penrose jako „spoza rejestru" wszedł do rejestru → nazwy fikcyjne).
- ✓ MEMORY.md repo (wpis [2026-07-11]) + auto-memory (`project_grout_engine`, `project_tile_quality_plan`, `project_10_shapes_plan`) zaktualizowane na bieżąco.
- ✓ Wyjaśnienie zagadki liczby testów: „327" poprzedniej sesji liczyło z `test_ai_core` (28); konwencja CI = ignore test_ai_core.

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES — ostatnie kształty** (NASTĘPNY KROK = voderberg/escher_lizard/weave): potem girih (decyzje seedów), poincare (pasmowy), truchet×2 (`_CurvedMask`), pula extra 21-43. Po WSZYSTKICH → selekcja finalna usera.
- ⟳ **Galeria 16K triangle+hexagon** — odłożona do wdrożenia wszystkich kształtów (decyzja 2026-07-10).
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon.
- ⟳ Standing: GUI niesprawdzone wizualnie w realnym `python -m src.gui` (pasek DZI, dropdown Tile Borders z EN presetami, nowy checkbox used-tiles, 11 nowych kształtów w dropdownie ze schematami).
- ⟳ Stare pliki batch `_grout-sredni` w output/ nie łapią skip-if-exists po rename presetów (kosmetyka).

## Aktywne pliki

- `src/engine_smart.py` (sekcja generatorów: `_lattice_mn_range`/`_pin_sub`/`_gen_pinwheel`/`_gen_cairo`/`_gen_floret`/`_gosper_edge`/`_gen_gosper` + `_multigrid_dual`/`_gen_penrose`/`_gen_ammann_beenker` + `_gen_trunc_square`/`_gen_trunc_hex`/`_gen_rhombitrihex`/`_gen_pythagorean`/`_sun_arc`/`_gen_sunburst`; `_grout_cells` generyczny fallback polygon; `create_mosaic(save_used_tiles=False)`; rejestr `SHAPE_MODES` = 32)
- `src/grout.py` (PRESETS thin/medium/thick), `src/cli.py` (`--save-used-tiles`, `_GROUT_PRESETS` EN), `src/gui.py` (dropdown Tile Borders EN, checkbox used-tiles)
- `tests/test_golden_shapes.py` (GOLDEN = 54 hashe), `tests/test_grout_engine.py` (+3 testy generycznego groutu), `tests/test_used_tiles.py` (opt-in), `tests/test_grout.py`, `tests/test_cli.py`
- Scratch (wzorce, w scratchpadzie sesji): `check_coverage.py`, `gen_goldens.py`

## Otwarte pytania

- girih w silniku: jak zamrozić sweep seedów (per wymiary jak `_shape_seed`? stały seed?) i czy domykanie dziur convex-hullem jest deterministyczne — decyzja przy wiringu.
- truchet: go/no-go po prototypie 1 kafelka `_CurvedMask` (per PLAN_SHAPES).
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis [2026-07-11] — pakiet poprawek UX (grout EN, used_tiles opt-in, generyczny grout polygon), 11 kształtów z lekcjami (pułapka pythagorean, optymalizacja okna multigridu (N/2)·p, wzorzec „pole dominującego kafla ~ base_s²", lekcja testowa o nazwach fikcyjnych).
- Auto-memory: `project_grout_engine` (presety EN + generyczna gałąź), `project_tile_quality_plan` (used_tiles opt-in), `project_10_shapes_plan` (Fable ×4, archimedesowe ×5, stan „zostało") + indeks MEMORY.md.

## ═══ Sesja zarchiwizowana [2026-07-11 12:24] ═══

# last_session.md

**Sesja:** 2026-07-10 · 21:00-22:31 · (Opus 4.8, częściowo Fable 5)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** b278373 @ main (5 commitów sesji NIE wypchnięte na origin — ahead 5; push do decyzji usera)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**PLAN_SHAPES S3+ — wiring kolejnych kształtów, zacznij od najtańszych „deterministycznych Fable".** Konkretnie: `pinwheel`, `cairo`, `floret`, `gosper`, `pythagorean` mają już zweryfikowaną wizualnie geometrię w `src/tools/gen_fable_shape_schemes.py` (`gen_pinwheel`, `gen_cairo`, `gen_floret`, `gen_gosper`, `gen_pythagorean` — czyste konstrukcje deterministyczne, bez RNG). Dla każdego:
1. Przenieś geometrię z generatora Fable do `engine_smart.py` jako `_gen_<shape>(engine, target_w, target_h, base_s)` yieldujący poligony w przestrzeni obrazu (y w dół); użyj `_emit_polys` (jawne partycje) albo mapowania afinicznego jak w rodzinie sunflower. base_s ma sterować gęstością/skalą.
2. Wpis w `SHAPE_MODES` (`ShapeSpec("polygon", _gen_<shape>, aa=4)`).
3. Golden (both borders) przez scratch-script z fixture jak `tests/test_golden_shapes.py` → dodaj 2 hashe do `GOLDEN`.
4. Weryfikacja: pokrycie (0% dziur), montaż na `input/0013.jpg`.

**NIE ruszaj gałęzi kites/spectre** w `_do_render` (zablokowane goldeny). Nowe kształty wpinają się w generyczną gałąź `elif ...kind=="polygon"`.

Kontekst: generyczny dispatch polygon jest już aktywny (wzorzec ustalony na 12 kształtach tej sesji). Zostają trudniejsze kształty z PLAN_SHAPES — deterministyczne Fable to najtańszy kolejny krok przed geometrią ryzykowną (penrose multigrid, girih, poincare, truchet). User chce WSZYSTKIE kształty wdrożone przed galerią 16K.

---

## Co zrobiono w tej sesji

- ✓ **Push zaległego commitu `/end`** z poprzedniej sesji (915adfd → origin/main).
- ✓ **GUI polish** (509136f): Output Resolution Smart domyślnie 8K; **Black Borders + Grout scalone w jeden dropdown „Tile Borders"** (Off | Gap (uniform) | Grout: cienki/sredni/gruby; `_border_settings()` mapuje na (border_mode, grout_preset), wzajemnie wykluczające się — koniec mylącej kombinatoryki); Edge-Aware przeniesiony pod Allow Mirroring (mutex razem); Color Blend +40% (wyrównanie z Tile Tint).
- ✓ **ODKRYCIE: Sprint 2 refaktor był w połowie** — `SHAPE_MODES`/`ShapeSpec`/`_polygon_sector` istniały, ale `_do_render` miał zahardkodowane gałęzie, a `_polygon_sector` był MARTWYM kodem.
- ✓ **Generyczny dispatch polygon** (7871951): gałąź `elif kind=="polygon"` aktywuje `_polygon_sector`; nowy kształt = generator + wpis w rejestrze. CLI/GUI czytają z `shape_names()` (koniec 3 zahardkodowanych list).
- ✓ **12 nowych kształtów WDROŻONYCH** (wszystkie polygon aa=4, +24 goldeny cross-proces):
  - **sunflower ×7** (7871951+909ecb9): grande/grande_xl/grande_soft/grande_inverse + soft/rings/disc. Vogel/Voronoi bez koloru → zero RNG. Helpery `_graded_sunflower`/`_emit_cells`/`_lloyd_relax`/`_vogel_points`/`_voronoi_cells`/`_poly_centroid`.
  - **rhombs ×3** (0f625c2): nopole/funnel/star. Mesh log-spiralny `_log_mesh`/`_log_quads` + `_bridge`/`_rosette`/`_circle_pts`/`_align_rot`/`_group_loop` + `_emit_polys`. **DECYZJA USERA: tile_scale steruje gęstością** → `_solve_k` (count~1/k²); inwariant samopodobności (pętla F1+F2) → domknięcia środka niezależne od k.
  - **voronoi + phyllotaxis** (b278373): voronoi jednorodny (seed z wymiarów `_shape_seed` → determinizm; pierścień brzegowy zamrożony w Lloydzie `freeze_r`, 0.05% dziur); phyllotaxis = Vogel power=0.5.
- ✓ **Decyzje geometrii Voronoi:** mapowanie afiniczne [-1,1]²→kadr z flipem Y (partycja przeżywa stretch), liczba komórek ~pole/base_s², `_SUNFLOWER_CELL_DENSITY=2.6`.
- ✓ **327 testów zielonych** (było 305; +12 nowych goldenów: sunflower rodzina + rhombs + voronoi/phyllotaxis; grande golden bit-identyczny przez refaktor). Każdy kształt zweryfikowany wizualnie na `0013.jpg` (montaże w scratchpad). Rejestr `SHAPE_MODES` = 21 kształtów.
- ✓ MEMORY.md repo (wpis [2026-07-10]) + auto-memory (`project_10_shapes_plan`) zaktualizowane.

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES S3+ pozostałe kształty** (NASTĘPNY KROK = deterministyczne Fable): penrose/ammann_beenker (multigrid de Bruijna), pinwheel/gosper/cairo/floret/pythagorean, poincare, girih, truchet/truchet_hex (maski krzywoliniowe `_CurvedMask` — nowa maszyneria), sunburst/voderberg, trunc_square/trunc_hex/rhombitrihex, escher_lizard, weave. Po WSZYSTKICH → selekcja finalna usera.
- ⟳ **Galeria 16K triangle+hexagon** z workflow hires — ODŁOŻONA przez usera do czasu wdrożenia WSZYSTKICH kształtów (decyzja 2026-07-10).
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon (kites bit-identyczny, spectre wymaga regen golden — niekonieczne).
- ⟳ Standing: pasek DZI w GUI wciąż niesprawdzony w realnym `python -m src.gui`; GUI polish tej sesji też niesprawdzony wizualnie w realnym GUI.
- ⟳ **Push:** 5 commitów sesji (509136f..b278373) niewypchnięte na origin.

## Aktywne pliki

- `src/engine_smart.py` (generyczny dispatch polygon w `_do_render`; sekcja geometrii: `_vogel_points`/`_clip_square`/`_voronoi_cells`/`_poly_centroid`/`_lloyd_relax`/`_emit_cells`/`_emit_polys`/`_graded_sunflower` + 7 generatorów sunflower; `_log_mesh`/`_log_quads`/`_bridge`/`_rosette`/`_circle_pts`/`_align_rot`/`_group_loop`/`_solve_k`/`_rh_mesh_k` + 3 generatory rhombs; `_shape_seed`/`_gen_voronoi`/`_gen_phyllotaxis`; rejestr `SHAPE_MODES` 21 wpisów)
- `src/cli.py` (`_SMART_SHAPES` = `shape_names()`), `src/gui.py` (Tile Borders dropdown + `_border_settings`; combo_shape z `shape_names()`; 8K default; blend 40%)
- `tests/test_golden_shapes.py` (24 nowe hashe: 14 sunflower + 6 rhombs + 4 voronoi/phyllotaxis)
- `MEMORY.md` repo (wpis [2026-07-10])

## Otwarte pytania

- Kolejność wdrażania pozostałych PLAN_SHAPES — sugerowana: najpierw deterministyczne Fable (tanie), potem multigrid (penrose/AB), na końcu ryzykowne (girih/poincare/truchet — decyzja go/no-go po prototypie per PLAN_SHAPES).
- Czy migrować kites/spectre do generycznej gałęzi (dedup) — obecnie NIE, bit-repro ważniejszy.
- Push 5 commitów na origin — do decyzji.

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis [2026-07-10] w Architekturze — pełny opis wiringu (odkrycie połowicznego Sprint 2, generyczny dispatch, 12 kształtów z podziałem na rodziny, decyzje geometrii Voronoi/rhombs base_s-scaling, następne kroki).
- Auto-memory: `project_10_shapes_plan` zaktualizowane (12 kształtów wdrożonych, wzorzec dodania kształtu, base_s-scaling rhombs, następne S3+); indeks MEMORY.md zsynchronizowany.

