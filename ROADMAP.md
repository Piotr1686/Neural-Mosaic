# ROADMAP — Neural-Mosaic

Plan ustalony 2026-05-11. Aktualizacja po każdym ukończonym sprincie.

## Bieżący focus

- Dopracowanie SmartEngine (5×5 LAB + cKDTree) — w toku, kontynuacja po roadmap items lub równolegle.

## Kolejność realizacji

1. **CLI mode** (priorytet 1, fundament) — łatwe, otwiera batch rendering i regresję
2. **Tile library browser** (priorytet 2) — wizualna inspekcja `data/library_*`, integracja z indekserem
3. **Real-time preview** (priorytet 3) — duży UX win, ale wymaga refactoru silników
4. ~~SVG export~~ — odrzucone: koszt/wartość, przeglądarka się dławi przy 50k+ tagów

---

## 1) CLI mode — sprinty

Cel: `python -m src.cli render input.jpg --engine smart --res 8K --output out.jpg`
bez uruchamiania customtkinter. Batch: folder → folder.

- [x] **Sprint 1.1** — Szkielet `src/cli.py`: argparse, podstawowa walidacja (engine, res, paths), logowanie do `logs/cli.log`. Smoke test: `--help` działa, błędy ścieżek raportowane czytelnie.
- [x] **Sprint 1.2** — Smart engine path: `--engine smart --index data/smart_index.pkl`. Pełna parytetowość z GUI: tile_size, target_short_side, scale, mirror.
- [x] **Sprint 1.3** — Typo engine path: `--engine typo --mode {black_on_white,white_on_black} --font ...`. Parytet z GUI.
- [x] **Sprint 1.4** — Batch mode: `cli batch <input_dir> <output_dir> --engine ... [--pattern *.jpg]`. Skip already-rendered (idempotentność).
- [x] **Sprint 1.5** — README sekcja "CLI usage" + smoke testy w `tests/test_cli.py` (1 obraz, niska rozdzielczość).

## 2) Tile library browser — sprinty (TBD po CLI)

Cel: GUI tab lub osobne narzędzie do przeglądu kafelków z `data/library_*` —
thumbnaile, filtry (kolor, edge-density), statystyki pokrycia LAB.

- [x] **Sprint 2.1** — Decyzja: nowy tab w `gui.py` vs osobny `python -m src.tools.library_browser`. Mock UI / wireframe.
- [ ] **Sprint 2.2** — Loader: thumbnail grid (lazy, np. 200x200 cache w `data/.thumbs/`).
- [x] **Sprint 2.3** — Filtry: dominantny kolor LAB, edge-density (z indeksu), nazwa pliku.
- [ ] **Sprint 2.4** — Heatmapa pokrycia LAB (2D PCA / hex bins) — ile mamy "różnorodności" w bibliotece.
- [ ] **Sprint 2.5** — Akcje: usuń/oznacz kafelek, eksport listy "bad tiles" do `data/library_*/excluded.txt`.

## 3) Real-time preview — sprinty (TBD po Tile browser)

Cel: live podgląd ~1K przy zmianie suwaków (tile_size, scale, mode), bez ponawiania
pełnego 16K renderu.

- [ ] **Sprint 3.1** — Refactor `engine_smart.process()` → wydzielić `process_to_target_size(target_w, target_h)`. Bez zmiany API publicznego.
- [ ] **Sprint 3.2** — Analogiczny refactor `engine_typo`.
- [ ] **Sprint 3.3** — Preview pipeline: downsample input do 512px short edge, render do ~1024px, debounce 300ms.
- [ ] **Sprint 3.4** — GUI: preview pane w obu tabach, throttling, anulowanie poprzedniego zadania.
- [ ] **Sprint 3.5** — Cache: cKDTree query wynikowy keyed by (tile_size, target_size) — invalidate przy zmianie indeksu.

---

## Zasady pracy

- Po każdym sprincie: pokaż diff, zapytaj "kontynuować?" zanim wejdziesz w kolejny.
- `/save` w trakcie dłuższego item, `/end` na koniec sesji.
- Jeśli sprint okazuje się większy niż zaplanowano — rozbij na pod-sprinty, nie idź na ślepo.
- Na startcie każdego głównego itemu (CLI / Tile browser / Preview): zapytaj "Gotowy zaczynać X?" zanim ruszysz.
