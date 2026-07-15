# last_session.md

**Sesja:** 2026-07-15 · ~21:00-22:25
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 5390546 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Krok 5 planu (b++): pomiar peak-RAM panoramy 4:1 → decyzja o hero DZI.**
To OSTATNI krok planu poincare. Kolejność (measure-before-promise, inwariant A1):

1. Zlokalizuj `PeakRAMSampler` (`grep -n "PeakRAMSampler" src/engine_smart.py`)
   i sposób jego użycia w renderze 16K (wzorzec z A1, commit z 2026-06-27).
2. Zbuduj target 4:1 (np. ~36000×9000 px lub proporcjonalnie mniejszy do
   ekstrapolacji) — poincare jest NIEokresowy wzdłuż pasma, więc panoramy nie
   da się skleić z kopii, trzeba render całości.
3. Uruchom `_do_render(target, "poincare", ...)` owinięty w `PeakRAMSampler`;
   zmierz peak. Szacunek: ~58k komórek `_LazyMask` @36000×9000.
4. BRAMKA: peak ≤ inwariant A1 (**3.9 GB @16K**)? → eksport `make_dzi` jako
   hero panorama (przycisk „Export Deep Zoom" / CLI `dzi` już istnieją).
   Jeśli przekracza budżet → NIE obiecuj hero; rozważyć streaming/tiling renderu
   PRZED eksportem.

Kontekst: kroki 1-4 (b++) WDROŻONE i wypchnięte (da891fc, f26c3aa, 40174bd,
5390546; rejestr=39; 377 testów). Poincare jest kompletny jako kształt (geometria
+ subdywizja + grout hierarchiczny + goldeny + schemat + formalny test partycji).
Krok 5 to jedyny pozostały element i dotyczy WYDAJNOŚCI/prezentacji, nie
poprawności — stąd twarda bramka pomiaru przed obietnicą.

---

## Co zrobiono w tej sesji

- ✓ **Krok 3 (b++) — grout hierarchiczny poincare (40174bd, push):**
  `_grout_cells_poincare` re-yielduje `_poincare_cells` jako
  `(poly, g2=(hi,k), g3=hi)` (L1=subkomórka quad / L2=latawiec khatam /
  L3=heptagon). Gałąź dedykowana w `_grout_cells` PRZED generycznym fallthrough
  polygon; `poincare` dopisane do `_HIERARCHICAL_GROUT` i `GROUT_HIERARCHICAL`.
  +3 testy (`test_grout_engine.py`): hierarchia g2/g3, wszystkie 3 poziomy
  zapełnione (anti-collapse), dispatcher hierarchiczny≠flat. Bramka wizualna 2K
  `0013.jpg` L1/L2/L3 — near-black monotonicznie **609k → 483k → 295k**;
  L3 pokazuje kwiaty heptagonów z dystorsją hiperboliczną.
- ✓ **Routing Fable (fd5f641, push):** `MODEL_ROUTING.md` — trzeci alias
  **MID = `claude-fable-5`** jako tryb SUGEROWANY dla zadań generatywno-
  dywergencyjnych (brainstorm kształtów, „daj N pomysłów", copy portfolio).
  Nowa sekcja 🟪 macierzy; reguła nadrzędna/protokół/lista komend rozszerzone
  o MID; doprecyzowana granica HIGH (trade-offy, jedna odpowiedź) vs MID
  (dywergencja) i przejście MID→HIGH gdy pomysł staje się implementacją.
  Brak komendy `/fable` — przełączenie przez `/model fable`.
- ✓ **Krok 4 (b++) — goldeny + schemat + test partycji (5390546, push):**
  (a) goldeny `(poincare,False/True)` zablokowane, hashe zweryfikowane bit-w-bit
  w DWÓCH procesach (overlay hi-res = no-op, bo `tile_NNN.png` ≠ `coco_*.jpg`);
  (b) `src/tools/gen_poincare_scheme.py` + regenerowany `poincare.png` z
  `_poincare_cells` (model pasmowy) — zastąpił mylący dysk z `gen_fable`
  (pułapka „schemat ≠ silnik" jak w girih); kolor per heptagon (kąt złoty HSV)
  + odcień per latawiec; (c) formalny test partycji parametryzowany ×5 kadrów
  (jednorodne grupowanie → niesparowany szew z oboma końcami wewnątrz = T-junction;
  **zero** wszędzie). Pełny pytest **377/377**.
- ✓ **Tryb pracy:** ustalono uczenie usera przez inżynierię wsteczną NA BIEŻĄCO
  (komentarz przy każdej czynności, nie wykład po fakcie) — po sprostowaniu usera.

## Co zostało (backlog sesji)

- ⟳ **Krok 5 (b++):** peak-RAM panoramy 4:1 → hero DZI (NASTĘPNY KROK).
- ⟳ Po poincare: pula extra 21-43 → selekcja finalna usera → galeria 16K.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka;
  README `--grout`/`--grout-level`.
- ⟳ Tasks w harness: #5 (pending) odpowiada krokowi 5; #3/#4 zamknięte.

## Aktywne pliki

- `src/engine_smart.py` — blok POINCARE (`_poincare_*` + `_gen_poincare` +
  `_grout_cells_poincare` + wpisy hierarchiczne). Krok 5: pomiar przez
  `PeakRAMSampler` (bez zmian w geometrii — tylko instrumentacja/render).
- `tests/test_golden_shapes.py` — goldeny poincare ×2.
- `tests/test_grout_engine.py` — testy groutu poincare + test partycji ×5.
- `src/tools/gen_poincare_scheme.py` — generator schematu (regeneracja PNG).
- `MODEL_ROUTING.md` — routing z MID (Fable).

## Otwarte pytania

- **Peak-RAM panoramy 4:1** (krok 5): ~58k komórek `_LazyMask` @36000×9000 —
  zmierzyć PRZED obietnicą hero (inwariant A1 3.9 GB @16K). To główna niewiadoma.
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę niż
  finalny render. Zaakceptowane milcząco; jeśli user zauważy — nd z rozdzielczości
  docelowej.
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich (bez zmian).

## Do MEMORY.md (przeniesiono)

- `feedback_teach_while_working.md` (NOWY) — user uczy się przez inżynierię
  wsteczną NA BIEŻĄCO (komentuj przy każdej czynności co+dlaczego); doprecyzowane
  po sprostowaniu (nie wykład po fakcie).
- `project_poincare_bpp_plan.md` — status zaktualizowany na **kroki 1-4 WDROŻONE**
  (+ commity 40174bd/5390546, 377 testów); został tylko krok 5.
- Routing Fable NIE dostał osobnego wpisu — jest self-documenting w
  `MODEL_ROUTING.md` (ładowanym co sesję przez CLAUDE.md).
