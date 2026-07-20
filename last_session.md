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
