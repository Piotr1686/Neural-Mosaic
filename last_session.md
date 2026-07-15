# last_session.md

**Sesja:** 2026-07-14 · ~22:20-23:05
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** bfdc796 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wiring poincare** — ostatni kształt z PLAN_SHAPES przed pulą extra 21-43.
Model pasmowy `w = (2/π)·log((1+z)/(1−z))` — {7,3} biegnie poziomo bez horyzontu
kołowego; okno `|y| ≤ 0.80`. Heptagony (za duże: ~33/kadr) dzielone na 7 latawców;
środek hiperboliczny śledzony PRZEZ odbicia w BFS, środki krawędzi = próbka t=0.5
łuku (identyczna z obu stron ⇒ partycja dokładna). BFS może ciąć na diam<0.02.
Geometria istnieje w `src/tools/gen_fable_shape_schemes.py` (poincaré, przeprojektowany
2026-07-04b — model pasmowy, wersja inwersyjna WYRZUCONA). To NAJDROŻSZY kształt
(BFS odbić). Wzorzec wiringu: generator `_gen_poincare(engine, w, h, base_s)` +
wpis w `SHAPE_MODES` (aa=4) + golden both-borders ×2 procesy + schemat GUI
generowany z geometrii silnika (jak `gen_girih_scheme.py` / `gen_truchet_schemes.py`).

Bramki jak zawsze: render 2K na `input/0013.jpg`, pełny pytest, pokrycie kadru
(cel 0% tła — wzorzec sprawdzania w `src/tools/girih_audit.py`).

Kontekst: po poincare zostaje TYLKO pula extra 21-43, potem selekcja finalna
kształtów przez usera → galeria 16K. User chce WSZYSTKIE kształty przed selekcją.

---

## Co zrobiono w tej sesji

- ✓ **`/start`** — stan spójny z ostatnią sesją.
- ✓ **Wiring girih** (`09d447a`, rejestr SHAPE_MODES=38) — WYSZEDŁ INACZEJ NIŻ PLAN:
  - Plan zakładał port `_girih_attempt` + zamrożony `_GIRIH_SEED` po sweepie.
    **Trzy z czterech filarów algorytmu ze schematu wyleciały** (audyt pokazał, że
    nie skalują się do kadru).
  - (1) `commit()` = OR bufora bboxa (nie przepis rastra); ale PRAWDZIWE wąskie
    gardło to była pętla hulli `np.nonzero(lab==li)` po całym rastrze → `find_objects`
    (12,3 s → 0,28 s).
  - (2) Otoczka wypukła dziur DO WYRZUCENIA (nie do przeskalowania jak w planie):
    dziury to wklęsłe korytarze, hulle połykały sąsiednie kafle = 7-11% kadru 2×.
    Teraz kontur (marching squares) → dziura wchodzi jako komórka, którą naprawdę jest.
  - (3) Greedy NIE hoduje dekagonów (10 z 1610 prób) → pole heksagonów bez rozet.
    Rozety zasiane na wierzchołkach Penrose'a `d=apotema/sin(18°)` (zazębia się z
    girih dokładnie: sąsiad o krawędź rombu → mostek heksagonem; przez krótką
    przekątną cienkiego rombu 0.618·d → styk bokami = 2 apotemy).
  - (4) Wypełnianie **bowtie-first** stałe (95,3% vs 84,5% hex-first) ⇒ **ZERO RNG,
    brak seeda do zamrażania** (problem z planu zniknął).
  - Bramki: 96-99% pola = prawdziwe kafle girih, 0 dziur, nakładki ≈0; realny kadr
    <0,0015% niepokryty. 16K: 51k komórek, 2906 rozet, 10,3 s. +2 goldeny cross-proces.
- ✓ **Poziomy groutu** (`bfdc796`) — user zgłosił brak w trakcie sesji. Hierarchia
  L1/L2/L3 ISTNIAŁA, ale do wyboru była tylko grubość. `scale_widths(min_level)`
  zeruje poziomy PONIŻEJ wybranego. kites: L1=latawiec, L2=heksagon(6), L3=kwiat(7).
  PUŁAPKA kierunku: selekcja to `>= N`, nie `<= N`. GUI lista + CLI `--grout-level`.
  +2 testy (kierunek + strict shrink na realnej geometrii kites).
- ✓ **367 testów zielonych**; oba commity wypchnięte na origin (`b01198b..bfdc796`).

## Co zostało (backlog sesji)

- ⟳ **PLAN_SHAPES — ostatni kształt:** poincare (NASTĘPNY KROK) → pula extra 21-43.
  Po WSZYSTKICH → selekcja finalna usera → galeria 16K.
- ⟳ **Galeria 16K triangle+hexagon** — odłożona do wdrożenia wszystkich kształtów.
- ⟳ **PLAN_FRACTAL wykonawczy** — F1a (trójfazowa pętla, golden bit-w-bit).
- ⟳ escher_lizard: docelowa sylwetka jaszczurki = ręczne dostrojenie offsetów (estetyka).
- ⟳ (opcjonalny cleanup) migracja kites/spectre do generycznej gałęzi polygon.
- ⟳ (drobny dług) README nie dokumentuje flag `--grout` / `--grout-level` (nie regresja).

## Aktywne pliki

- `src/engine_smart.py` — `_girih_patch` + `_gen_girih` + helpery girih (rejestr 38);
  `_apply_grout`/`_do_render`/`create_mosaic`/`render_preview` przewleczony `grout_level`.
- `src/grout.py` — `scale_widths(min_level)`, stałe `LEVELS`/`DEFAULT_MIN_LEVEL`.
- `src/tools/girih_audit.py` (NOWY — zastąpił girih_seed_sweep.py), `src/tools/gen_girih_scheme.py` (NOWY).
- `src/cli.py` — `--grout-level`; `src/gui.py` — lista `_GROUT_LEVELS` + `_border_settings` zwraca 3-krotkę.
- `tests/test_golden_shapes.py` (+2 goldeny girih), `tests/test_grout.py` (+2 testy poziomów).
- `assets/shape_schemes/girih.png` — zregenerowany z geometrii silnika.
- `PLAN_SHAPES.md` — S7 zamknięty (girih ZROBIONE 2026-07-14).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (bez zmian).
- Poincare: BFS może być drogi @16K — jeśli za wolny, rozważyć cap głębokości/okna
  (analogicznie do fixu `commit()` w girih: najpierw zmierzyć, potem optymalizować).

## Do MEMORY.md (przeniesiono)

- Repo MEMORY.md: wpis **[2026-07-14]** w „Aktywne TODO" — girih (rozety na quasi-sieci,
  3 filary schematu wyleciały, zero RNG) + poziomy groutu (min_level, pułapka `>=N`).
- Auto-memory: `project_girih_lattice.md` (unieważnia plan seeda z 2026-07-11b),
  `project_grout_levels.md` (pułapka kierunku selekcji).
