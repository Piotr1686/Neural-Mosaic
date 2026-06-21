# last_session.md

**Sesja:** 2026-06-21 · 20:45-23:35
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 59a0bff @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Po przebudowie GitHub Pages (~1-2 min) zweryfikować live demo na żywo (Ctrl+F5, twardy refresh): przycisk „4 — Hexagon" = skok na drodze (IMG_20220727) i „5 — Spectre" = papuga (portrait3) ładują się w 8K bez czarnego ekranu. Jeśli OK — opcjonalnie zróżnicować pozostałe: `photo_mosaic`=portrait.jpg i `triangle`=portrait2.jpg to wciąż ta sama osoba (różne sceny).**

Kontekst: w tej sesji naprawiono duplikat źródeł w viewerze (spectre i hexagon były oba papugą). Pozostałe dwie mozaiki to różne zdjęcia tej samej osoby — do decyzji, czy to wystarczająco różne. Weryfikacja deployu to jedyny krok wymagający oka użytkownika (przeglądarka cache'uje kafelki).

---

## Co zrobiono w tej sesji

- ✓ **Głęboki audyt README** — 4 tiery, ~20 znalezisk (błędy faktograficzne vs kod, sprzeczności, wizualia, marketing)
- ✓ **Opcja B — realne pisma egzotyczne w TypoEngine** (commit `1fbad26`): `indexer_typo` pełne pokrycie ~44 bloków Unicode + `--full-scan`; `engine_typo` filtr świadomy grup (`_LATIN_GROUPS`); testy zaktualizowane; reindeks → **43 829 glifów**, wszystkie 7 grup żyją; 184 testy passed; walidacja wizualna (mozaika z hieroglifów)
- ✓ **Rendery demo 16K**: spectre+grout (papuga) + tryptyk zbliżeń, macierz grup fontów, glyph-detail (CJK/hieroglify/odręczne), macierz rozmiaru; nowy `src/tools/make_matrices.py`
- ✓ **Benchmark** (`tests/benchmark.py`): format jednokolumnowy (koniec atrapy GPU/CPU) + prawdziwe liczby (16K kite 21 min itd.)
- ✓ **README przepisane** (commit `bb59a1f`): nazwa Neural-Mosaic, EN, TOC, diagram Mermaid, Tech Highlights, downloadery sprostowane (Picsum/LoremFlickr + Openverse/Met/Artic), wzór anti-rep, NUM_TILES, wymiary 16K, stopka autora; usunięto `symbol_color.jpg` + 6 zoom GIF (~47 MB)
- ✓ **Live demo (docs/, GitHub Pages)**: spectre→papuga 8K (`aa787ea`), hexagon→skok 8K (`59a0bff`); różne źródła per kształt; sprostowane kłamliwe etykiety triangle/hexagon
- ✓ Wszystkie 4 commity **wypchnięte na origin/main**; MEMORY.md zaktualizowane (3 wpisy 2026-06-21)

## Co zostało (backlog sesji)

- ⟳ Live demo: `photo`(portrait.jpg) i `triangle`(portrait2.jpg) to ta sama osoba — ewentualne dalsze zróżnicowanie
- ⟳ Opcjonalnie: wariant `white_on_black` do galerii typo w README
- ⟳ `benchmark.py`: pomiar peak-RAM niewiarygodny (psutil delta ~0.46 GB vs realne ~10 GB) — ewentualny sampling-thread
- ⟳ Niereferowane assety (`symbol_bw`, `symbol_detail`, `mosaic_portrait_spectre`, `mosaic_zoom`) — zostawione (używa ich `make_showcase`)
- ⟳ Stary backlog: `feature/semantic-clip` TODO w MEMORY nieaktualne (CLIP odrzucony); zoom-GIF spectre; UX backlog z 2026-06-04

## Aktywne pliki

- `src/indexer_typo.py`, `src/engine_typo.py`, `tests/test_typo_engine.py` (Opcja B)
- `README.md`, `tests/benchmark.py`, `src/config.py`, `src/tools/make_matrices.py` (README + benchmark)
- `docs/index.html`, `docs/tiles/spectre_parrot.*`, `docs/tiles/hexagon_jump_16K.*` (live demo)
- Mastery 16K w `output/github_readme/` (gitignored) — do reprodukcji DZI/macierzy

## Otwarte pytania

- Czy zróżnicować pozostałe źródła live-demo (triangle/photo = ta sama osoba)?
- Czy dodać wariant `white_on_black` do galerii typo w README?

## Do MEMORY.md (przeniesiono)

- „Opcja B — realne pisma egzotyczne w TypoEngine" (Rozwiązane problemy) z inwariantem: zakresy `indexer_typo` ↔ `_LATIN_GROUPS`; reindeks po zmianie; sprostowanie nieaktualnych color modes
- „README przepisane + sprostowane fakty vs kod" (downloadery Picsum/LoremFlickr vs v2; TARGET_SHORT_SIDE ignorowane; wzór anti-rep; nazwa Neural-Mosaic)
- „Live demo — różne źródła per kształt, 8K" (make_dzi --max-level 13, Format=jpg, 5 mozaik)
