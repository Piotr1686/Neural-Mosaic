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
