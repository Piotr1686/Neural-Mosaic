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

## ═══ Sesja zarchiwizowana [2026-06-30 22:16] ═══

# last_session.md

**Sesja:** 2026-06-28 · 22:05-22:30
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 26c5d0a @ main (origin ZSYNCHRONIZOWANY — `26c5d0a` wypchnięty, branch == origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Podmiana triangle + hexagon w galerii na prawdziwe 16K — CZEKA NA PLIKI OD USERA.** User sam wygeneruje 16K triangle+hexagon i napisze, że gotowe. Wtedy: (1) wstaw nowe `.dzi` + foldery `*_files/` do `docs/tiles/`, (2) usuń stare `showcase_triangle_20260502_101900*` i `hexagon_jump_16K*`, (3) zaktualizuj `tileSources` **oraz** etykiety w `docs/index.html` (8K→16K, nowe wymiary/MP, przyciski btn4/btn5). Pułapki: `Format="jpg"` w XML (nie `"jpeg"` → czarny ekran OpenSeadragon, [[project_dzi_format_bug]]); sprawdź budżet GitHub Pages (piramidy obecnie ~165 MB).

Kontekst: galeria miała „3×16K + 2×8K"; user chce 5×16K. Akcja jest zablokowana do momentu, aż user dostarczy pliki — jeśli na /start ich jeszcze nie ma, w międzyczasie zrób **Krok 6 portfolio** (audyt twierdzeń README, patrz backlog).

---

## Co zrobiono w tej sesji

- ✓ **README hero podmienione na magnifier papugi 4×4** (commit `26c5d0a`, na origin/main): stare `spectre_full.jpg` nie pokazywało kafelków nawet po zoomie → nowy `assets/examples/spectre_hero_magnifier.jpg` (1600×900, wariant „e" z 5 propozycji). Styl jak social_preview: żółty box na lewej krawędzi dzioba (przejście kolor→białe tło), linie łączące, inset ~4×4 kafelki, podpis „every tile is a separate photograph". Podmieniono w `README.md`+`README.pl.md` (linia 17); `spectre_full.jpg` ZOSTAJE w tabeli progressive-zoom (linia 103).
- ✓ **Audyt rozdzielczości galerii:** potwierdzono że tylko **photo/symbol/spectre = 16K**; **triangle (8192×4612) i hexagon (8192×6144) = 8K**. Etykiety w `docs/index.html` są uczciwe („8K"); plik hexagona myląco nazwany `hexagon_jump_16K.dzi` (realnie 8K) — kosmetyka, niewidoczna dla zwiedzających.
- ✓ Commit `26c5d0a` wypchnięty na origin; branch == origin/main.

## Co zostało (backlog sesji)

- ⟳ **Galeria 5×16K (NASTĘPNY KROK):** swap triangle+hexagon na 16K — czeka na pliki od usera.
- ⟳ **Krok 6 portfolio (standing):** adwersarialny audyt twierdzeń README.md/README.pl.md (każda liczba/feature/flaga/ścieżka pokryta kodem) → poprawki jednym commitem `docs(readme): fix unverified claims`. Nieaktualny w tej sesji, nadal otwarty.
- ⟳ **Krok 5 portfolio:** PyInstaller `.exe` (model-free) — wysiłek wysoki, ROI średni; osobny projekt.
- ⟳ **TODO odłożony:** pasek postępu „Export Deep Zoom" + `test_dzi` ([[project_dzi_gui_polish_todo]]).
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1/A2), ML/CLIP, Docker/plugin.

## Aktywne pliki

- `docs/index.html`, `docs/tiles/{showcase_triangle_*,hexagon_jump_16K}*` (cel swapu 16K)
- `README.md` + `README.pl.md` (hero zmienione; cel Kroku 6)
- `assets/examples/spectre_hero_magnifier.jpg` (nowe hero)
- Generator (scratchpad, nie w repo): `gen_parrot_magnifier.py` (źródło: `output/github_readme/spectre_parrot_16K.jpg`, tile pitch ~140 px w 16K)

## Otwarte pytania

- Galeria: czy 5×16K zmieści się w budżecie GitHub Pages (obecnie ~165 MB piramid + 2×16K dojdzie ~70-100 MB)? Sprawdzić przy swapie.
- Przy swapie: zmienić też mylącą nazwę `hexagon_jump_16K.dzi` na coś bez „16K" w starej wersji / nadać sensowny slug nowym plikom.

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [Aktywne TODO] NOWY wpis [2026-06-28] „Galeria — podmiana triangle+hexagon na 16K (CZEKA NA USERA)" — audyt rozdzielczości + plan swapu + pułapki.
- [Aktywne TODO] NOWY wpis [2026-06-28] „README hero = magnifier papugi 4×4" (commit `26c5d0a`) — co, dlaczego, generator, że `spectre_full.jpg` zostaje w tabeli zoom.

## ═══ Sesja zarchiwizowana [2026-06-28 22:28] ═══

# last_session.md

**Sesja:** 2026-06-28 · 10:30-13:04
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** ebc790b @ main (origin ZSYNCHRONIZOWANY — wszystkie 4 commity wypchnięte, branch == origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Krok 6 z `PLAN_PORTFOLIO.md` — adwersarialny audyt twierdzeń README (przed publikacją).** Jeden przebieg (`/code-audit` lub subagent `Explore`): „znajdź każdą liczbę / feature / flagę / ścieżkę w README.md **i** README.pl.md, której nie potwierdza kod". Cel: wyłapać przechwalstwo, martwe linki, nieaktualne flagi, rozjazd EN↔PL. Po audycie: lista znalezisk → poprawki w obu README jednym commitem `docs(readme): fix unverified claims`.

Kontekst: Kroki 1–4 portfolio domknięte i wypchnięte; przed pochwaleniem się projektem (LinkedIn/HN) warto, by każde twierdzenie w README było pokryte kodem. Niski wysiłek, higiena. Krok 5 (PyInstaller `.exe`) świadomie odłożony jako większy, osobny projekt o średnim ROI ([[project_portfolio_phase]]).

---

## Co zrobiono w tej sesji

- ✓ **Krok 1 — galeria live 16K** (`ad5d6c8`): zweryfikowano 3 mozaiki 16K (foto/spectre/typo); zmierzono realny DZI (foto 35.5 + spectre 49.5 + typo 79.7 = **~165 MB/3**, obalony szacunek 150–300 MB/szt.); podmieniono stare sloty 8K w `docs/tiles` na 16K (slug `spectre_parrot`→`spectre_mosaic`); przebudowano `docs/index.html` (3×16K + 2×8K, uczciwe etykiety MP); link hero w README EN+PL.
- ✓ **Krok 2 — social preview** (`6d5a8ea`): wygenerowano 5 konceptów → wybrany magnifier b (~30 tiles, kolorowy obszar kapelusza); `assets/examples/social_preview.png` 256-color PNG **0.55 MB** (<1 MB); user wgrał w repo Settings.
- ✓ **Krok 3 — Performance Engineering** (`170636c`): case study A1 w README EN+PL (PeakRAMSampler → atrybucja float64 cdist → `_euclid_f32` + `_LazyMask` pod inwariantami → 16K ~10→3.9 GB, ~21→5.9 min); odświeżono 3 nieaktualne noty (roadmap DZI [x], viewer 3×16K, rozmiar repo).
- ✓ **Krok 4 — post o monokafelku** (`ebc790b`): `docs/posts/aperiodic-monotile-mosaic{,.pl}.md` EN+PL + assety z `generate_spectre_tiling()` (grid kolorowany wg orientacji, GIF 36-klatkowy reveal, sylwetka 14-boku); linki z sekcji Spectre obu README.
- ✓ **Wszystkie 4 commity wypchnięte**; branch == origin/main.

## Co zostało (backlog sesji)

- ⟳ **Krok 6 (NASTĘPNY KROK):** adwersarialny audyt twierdzeń README.
- ⟳ **Krok 5:** zero-friction install (PyInstaller `.exe`, model-free) — wysiłek wysoki, ROI średni; odłożony jako osobny projekt.
- ⟳ **TODO odłożony:** pasek postępu dla przycisku „Export Deep Zoom" + dołożyć `test_dzi` ([[project_dzi_gui_polish_todo]]) — przy przebiegu czyszczącym GUI.
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1/A2), ML/CLIP, Docker/plugin.

## Aktywne pliki

- `README.md` + `README.pl.md` (cel audytu Kroku 6)
- `docs/index.html`, `docs/tiles/{photo,symbol,spectre}_mosaic*` (galeria 16K)
- `docs/posts/aperiodic-monotile-mosaic{,.pl}.md` + `docs/posts/img/*` (post monotile)
- `assets/examples/social_preview.png` (social preview, wgrany w Settings)
- Generatory (scratchpad, nie w repo): `gen_social.py`, `gen_magnifier.py`, `gen_final.py`, `gen_monotile.py`

## Otwarte pytania

- Krok 4: czy przepuścić prozę posta przez Claude.ai (web) pod konkretną platformę (HN/dev.to/LinkedIn) — plan zakładał narrację na web; draft w CC gotowy do publikacji jak jest.
- Krok 5 vs odłożenie: czy w ogóle robimy `.exe`, czy zostaje przy „clone + run".

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [[project_portfolio_phase]] — dodano postęp: Kroki 1–4 WDROŻONE (commity ad5d6c8 / 6d5a8ea / 170636c / ebc790b), realny pomiar DZI 165 MB/3, parametry faktycznie użyte, status kroków 5–6.
- [[project_dzi_gui_polish_todo]] — NOWY: odłożony pasek postępu „Export Deep Zoom" + brakujący `test_dzi`.

