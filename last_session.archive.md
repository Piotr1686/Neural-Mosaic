## ═══ Sesja zarchiwizowana [2026-06-26 22:30] ═══

# last_session.md

**Sesja:** 2026-06-26 · trwa (checkpoint 22:00)
**Status:** ⟳ W toku (checkpoint /save)
**Punkt odniesienia (git):** c38c2d0 @ main (origin zsynchronizowany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**WDROŻENIE A1 = Wariant 0 + A-tani + B** (DECYZJA usera 2026-06-26: zgoda na A i B; implementacja od NASTĘPNEJ sesji). Architektura rozpisana — patrz [[project_a1_memory_arch]]:
- **Wariant 0 (warunek wstępny):** wątek samplujący `rss` co ~50 ms wokół renderu → wiarygodny peak-RAM (zalicza też backlog B = benchmark.py). Zero ryzyka.
- **Wariant A-tani:** w `engine_smart._do_render` pętla matchingu (`:658-668`) — `chunk_size` adaptacyjny (macierz ≤256 MB) + squared-euclidean w `float32` (GEMM `‖a‖²+‖b‖²−2a·b`) zamiast `cdist` float64. Spike 3.6 GB → ~0.25 GB. Numerycznie równoważne (ten sam ranking top-k). NIE rusza kontraktu `_do_render → PIL`. De-eskalacja `/sonnet` OK.
- **Wariant B:** leniwe maski spectre/kite — trzymaj `padded_poly`+bbox w `sectors_data`, rasteryzuj przy kompozycie (`:729`) i w `_mean_fill_outside_mask`. Ścina rezydentne maski (~10 GB peak spectre). HIGH (dotyka feature-path; wymaga testu regresji pikselowej).
- **Świadomie ODŁOŻONE:** Wariant C (pasmowe renderowanie kanwy) — wysokie ryzyko (łamie kontrakt PIL + inwarianty `_neighbors_cache`), atakuje najmniejsze źródło (kanwa 0.5 GB); tylko gdy cel >16K.

**WDROŻENIE A2 = Wariant B + skip-if-exists + podkomenda CLI `dzi`** (DECYZJA usera 2026-06-26; implementacja od NASTĘPNEJ sesji, po A1 lub równolegle). Architektura: [[project_a2_dzi_export_arch]]. Skrót:
- `make_dzi.make_dzi()` JUŻ gotowy i poprawny (`Format="jpg"`) — to integracja, nie nowy silnik.
- **Wariant B:** osobny przycisk „Export Deep Zoom…" w GUI (file picker → out dir), wzorzec wątku jak `gui.py:run_photo` (`:991-1006`); działa na dowolnym istniejącym obrazie.
- **Idempotencja:** skip-if-exists na kafelkach piramidy (= „excluded-tile support" z Roadmapu).
- **Parytet CLI:** podkomenda `dzi` w `src/cli.py`.
- **ODŁOŻONE — Wariant C** („Publish to viewer", auto-update `docs/`): ryzyko publicznego artefaktu + refaktor hardcoded `index.html` na manifest; przyszły osobny temat.

---

## Co zrobiono w tej sesji (2026-06-26)

- ✓ **Walidacja `requirements.txt` w CZYSTYM venv (definitywny dowód)**: świeży venv z Python 3.10.19, `pip install -r requirements.txt` (44 pakiety, bez torch/transformers); `import src.gui` OK (bez `ModuleNotFoundError: matplotlib`); render `typo 4K` (33004 glify, `fonttools` obecny) i `smart 2K` (454857 kafelków, cKDTree) — oba przeszły. `torch=False, transformers=False` potwierdzone. Obietnica README „4 linie i działa" — udowodniona empirycznie. (SSL w gołym venv obszedłem `--trusted-host` — to lokalne certy, nie problem `requirements.txt`.)
- ✓ **Push zaległego commitu sesyjnego** `f927696` (`68819bc..f927696`).
- ✓ **README dwujęzyczny EN/PL** (commit `ab32e7e`, pushed): pełny `README.pl.md` (25 sekcji, parytet z EN), przełącznik `**English** · [Polski]` w linii 3 obu plików; kotwice TOC z polskimi diakrytykami; bloki kodu/badge/ścieżki/Mermaid bez zmian.
- ✓ **CI z czerwonego na zielony + realne testy** (commity `db427b3`, `cf91769`, `c38c2d0`, pushed):
  - install z `requirements.txt` zamiast ręcznej listy (koniec driftu — padał `tqdm`);
  - dodany `python -m pytest` → **152 testy** realnie w CI (pominięte `test_ai_core`=uśpiony MiDaS i `test_processor`=lokalne GPU/CUDA);
  - bump `checkout@v5`/`setup-python@v6` (koniec ostrzeżeń Node 20).
  - 2 czerwone runy po drodze (drift zależności; `No module named 'src'` przez gołe `pytest` zamiast `python -m pytest`) — zdiagnozowane i naprawione; finalny run **success**. Inwariant: [[project_ci_pipeline]].
- ✓ **GitHub „About" wypełnione** (`gh repo edit`): description, homepage→live-demo, 10 topics; korekta rzetelności `opencv`→`scikit-image` (cv2 nieimportowane — [[project_requirements_curated]]).

## Co zostało (backlog sesji)

- ⟳ **Wybór kierunku „co dalej"** (patrz NASTĘPNY KROK): A1 chunked-16K / A2 eksport DZI / B jakość — czeka na decyzję usera.
- ⟳ `benchmark.py`: pomiar peak-RAM niewiarygodny (psutil delta vs realne ~10 GB) — sampling-thread (pozycja B).
- ⟳ `test_processor`: twardo asertuje CUDA → zmienić na `skipif(not cuda)`, żeby był przenośny (wtedy może wrócić do CI). NISKI.
- ⟳ Drobne README↔kod: typo realnie wspiera `--res 2K` (README mówi 4K/8K/16K); workflow wymienia 2 z 6 skanowanych katalogów.
- ⟳ Live demo: zróżnicowanie źródeł (triangle/photo = ta sama osoba); więcej mozaik 8K w viewerze. NISKI.
- ⟳ Świadomie odrzucone (over-engineering solo-portfolio): CoC, SECURITY.md, CITATION.cff, Docker/cross-platform, plugin system kształtów.

## Aktywne pliki

- `.github/workflows/ci.yml` (install z requirements.txt; `python -m pytest`; ignore test_ai_core+test_processor; akcje v5/v6 — [[project_ci_pipeline]])
- `README.md` + `README.pl.md` (dwujęzyczne, przełącznik w linii 3 — parytet 25 sekcji)
- `requirements.txt` (kurowany, ZWALIDOWANY w czystym venv — [[project_requirements_curated]])
- GitHub About: description + homepage + 10 topics (ustawione przez `gh repo edit`)

## Otwarte pytania

- Czy zróżnicować pozostałe źródła live-demo (triangle/photo = ta sama osoba)? (rekomendacja: niski priorytet)
- Czy udokumentować/zablokować `--res 2K` dla typo (silnik to wspiera, README nie)?

## Do MEMORY.md (przeniesiono)

- [[project_requirements_curated]] — requirements.txt jest KUROWANY (nie pip freeze); musi mieć matplotlib + fonttools; torch/transformers opcjonalne (uśpiony ai_core); cv2 nieimportowane (2026-06-24)

## ═══ Sesja zarchiwizowana [2026-06-24 23:21] ═══

# last_session.md

**Sesja:** 2026-06-24 (checkpoint /save · sesja trwa)
**Status:** ⟳ W toku
**Punkt odniesienia (git):** 2875f99 @ main (origin zsynchronizowany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Brak twardego następnego kroku — obie otwarte kwestie z 2026-06-21 domknięte (live-demo zweryfikowane, wariant white_on_black dodany do README + pushed).** Do wyboru z backlogu poniżej; najbliższy sensowny kandydat: ewentualne zróżnicowanie źródeł live-demo `photo`(portrait.jpg) vs `triangle`(portrait2.jpg) — ta sama osoba, różne sceny. Rekomendacja: NISKI priorytet (kosmetyk; demo pokazuje zmienną „kształt kafla", nie galerię osób). Render typo 8K jest tani (~7 s).

---

## Co zrobiono w tej sesji (2026-06-24)

- ✓ **Weryfikacja live-demo (end-to-end, na żywo)**: wszystkie 5 DZI mają `Format="jpg"`, pełna piramida 0–13, wymiary zgodne z etykietami; deploy GitHub Pages odpowiada; kafelki `13/0_0.jpg` to prawidłowe JPEG-i; obejrzane motywy: **hexagon=skok/niebo, spectre=papuga/safari** (właściwe kształty, różne źródła). Zero czarnego ekranu dla świeżego użytkownika (lokalny cache → Ctrl+F5).
- ✓ **Wariant typo `white_on_black` do galerii README** (commit `2875f99`, pushed): 2 mastery 8K z `IMG_20220727` (skok), Latin monospace, black_on_white + white_on_black; reprodukowalny krok `build_mode_compare()` w `make_matrices.py` → kompozyt side-by-side `assets/examples/typo_mode_compare.jpg` (1562×644); nowa podsekcja README „Symbol Mosaic — two style modes".
- ✓ **Push porządkowy**: wypchnięto też zaległy commit sesyjny `cc9f991` z 2026-06-21; origin/main zsynchronizowany.

---

## Co zrobiono w poprzedniej sesji (2026-06-21)

- ✓ **Głęboki audyt README** — 4 tiery, ~20 znalezisk (błędy faktograficzne vs kod, sprzeczności, wizualia, marketing)
- ✓ **Opcja B — realne pisma egzotyczne w TypoEngine** (commit `1fbad26`): `indexer_typo` pełne pokrycie ~44 bloków Unicode + `--full-scan`; `engine_typo` filtr świadomy grup (`_LATIN_GROUPS`); testy zaktualizowane; reindeks → **43 829 glifów**, wszystkie 7 grup żyją; 184 testy passed; walidacja wizualna (mozaika z hieroglifów)
- ✓ **Rendery demo 16K**: spectre+grout (papuga) + tryptyk zbliżeń, macierz grup fontów, glyph-detail (CJK/hieroglify/odręczne), macierz rozmiaru; nowy `src/tools/make_matrices.py`
- ✓ **Benchmark** (`tests/benchmark.py`): format jednokolumnowy (koniec atrapy GPU/CPU) + prawdziwe liczby (16K kite 21 min itd.)
- ✓ **README przepisane** (commit `bb59a1f`): nazwa Neural-Mosaic, EN, TOC, diagram Mermaid, Tech Highlights, downloadery sprostowane (Picsum/LoremFlickr + Openverse/Met/Artic), wzór anti-rep, NUM_TILES, wymiary 16K, stopka autora; usunięto `symbol_color.jpg` + 6 zoom GIF (~47 MB)
- ✓ **Live demo (docs/, GitHub Pages)**: spectre→papuga 8K (`aa787ea`), hexagon→skok 8K (`59a0bff`); różne źródła per kształt; sprostowane kłamliwe etykiety triangle/hexagon
- ✓ Wszystkie 4 commity **wypchnięte na origin/main**; MEMORY.md zaktualizowane (3 wpisy 2026-06-21)

## Co zostało (backlog sesji)

- ✓ ~~Opcjonalnie: wariant `white_on_black` do galerii typo w README~~ — ZROBIONE 2026-06-24 (`2875f99`)
- ⟳ Live demo: `photo`(portrait.jpg) i `triangle`(portrait2.jpg) to ta sama osoba — ewentualne dalsze zróżnicowanie (NISKI priorytet)
- ⟳ `benchmark.py`: pomiar peak-RAM niewiarygodny (psutil delta ~0.46 GB vs realne ~10 GB) — ewentualny sampling-thread
- ⟳ Niereferowane assety (`symbol_bw`, `symbol_detail`, `mosaic_portrait_spectre`, `mosaic_zoom`) — zostawione (używa ich `make_showcase`)
- ⟳ Stary backlog: `feature/semantic-clip` TODO w MEMORY nieaktualne (CLIP odrzucony); zoom-GIF spectre; UX backlog z 2026-06-04

## Aktywne pliki

- `README.md`, `src/tools/make_matrices.py` (galeria typo + krok `build_mode_compare`)
- `assets/examples/typo_mode_compare.jpg` (nowy asset side-by-side, tracked)
- `src/cli.py` (render typo `--mode white_on_black --font-groups D_latin_clean`)
- `docs/index.html`, `docs/tiles/spectre_parrot.*`, `docs/tiles/hexagon_jump_16K.*` (live demo — zweryfikowane)
- Mastery w `output/github_readme/` (gitignored): `typo_mode_bow_8K.png`, `typo_mode_wob_8K.png` + 16K masters — do reprodukcji kompozytów/DZI

## Otwarte pytania

- Czy zróżnicować pozostałe źródła live-demo (triangle/photo = ta sama osoba)? (rekomendacja: niski priorytet)
- ✓ ~~Czy dodać wariant `white_on_black` do galerii typo w README?~~ — TAK, zrobione 2026-06-24

## Do MEMORY.md (przeniesiono)

- „Opcja B — realne pisma egzotyczne w TypoEngine" (Rozwiązane problemy) z inwariantem: zakresy `indexer_typo` ↔ `_LATIN_GROUPS`; reindeks po zmianie; sprostowanie nieaktualnych color modes
- „README przepisane + sprostowane fakty vs kod" (downloadery Picsum/LoremFlickr vs v2; TARGET_SHORT_SIDE ignorowane; wzór anti-rep; nazwa Neural-Mosaic)
- „Live demo — różne źródła per kształt, 8K" (make_dzi --max-level 13, Format=jpg, 5 mozaik)

## ═══ Sesja zarchiwizowana [2026-06-21 23:35] ═══

# last_session.md

**Sesja:** 2026-06-14 · 11:00-12:18
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 7bc6c07 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Przebudować `data/typo_index.pkl` (`python -m src.indexer_typo` lub przycisk „Update Database (Scan Assets)" w GUI), by aktywować fix tofu `.notdef` z tej sesji — potem wyrenderować testową mozaikę typo i potwierdzić brak kwadracików tofu.**

Kontekst: `indexer_typo` pomija teraz codepointy spoza cmap fontu (fontTools), ale istniejący pickle wciąż zawiera stare tofu — fix z Fali 2 **nie zadziała bez reindeksacji**. To jedyny krok wymagający akcji użytkownika, by zmiany z tej sesji były w pełni widoczne w runtime.

---

## Co zrobiono w tej sesji

- ✓ **Polski README** — utworzono prywatną wersję `D:\Programming_Projects\zz_INNE\README_PL.md` (poza repo, niewersjonowana)
- ✓ **Code-review całości repo** (`/code-review high`, 4 etapy: silniki, GUI, CLI/config/indeksery, pipeline/tools) — 39 findingów po weryfikacji
- ✓ **Fala 1** (`27ba89d`): crash `_nkey`+border_mode, cross-thread Tk (self.after), daemon=True na wątkach, sanity_check LAB `[:, :75]`, `src/fast_downloader.py` (alias)
- ✓ **Fala 2** (`7c62ccf`): podgląd smart syncuje mirror/edge, podgląd typo po grupach (cache), tofu `.notdef` via fontTools cmap, `used_counts` int64
- ✓ **Fala 3** (`d9aaf4d`): downloadery (cap 401, guard pustych list, HTTP 206 przy resume, atomowy zapis), indexer_smart skanuje data/tiles, batch skip niepuste, getattr-guard ścieżek
- ✓ **Fala 4** (`7bc6c07`): `src/library_dirs.py` single source of truth, helper `_mean_fill_outside_mask`, usunięty martwy `tile_size`+`render_sized`
- ✓ **182 testy passed** po każdej fali; wszystkie 4 commity **wypchnięte na origin/main**
- ✓ MEMORY.md zaktualizowane (Rozwiązane problemy + Odrzucone podejścia)

## Co zostało (backlog sesji)

- ⟳ **Reindeksacja typo** dla aktywacji fixu tofu (patrz NASTĘPNY KROK)
- ⟳ **Refaktory świadomie odłożone** (Fala 4, opisane w MEMORY.md „Odrzucone podejścia"):
  dedup handlerów preview, unifikacja 4 downloaderów, centralizacja res_map, range() indexer_typo, CACHE_PATH
- ⟳ Zoom-GIF dla spectre do README (standing backlog z 2026-06-13)
- ⟳ Stary backlog UX z 2026-06-04 (auto-preview toggle, otwarcie folderu wyniku, statusbar, codename)

## Aktywne pliki

- `src/engine_smart.py`, `src/engine_typo.py`, `src/gui.py`, `src/indexer_smart.py`, `src/indexer_typo.py` — fixy review
- `src/library_dirs.py` (NOWY), `src/fast_downloader.py` (NOWY)
- `src/downloader.py`, `src/downloader_v2.py`, `src/get_mega_pack.py`, `src/get_special_datasets.py`, `src/cli.py`, `src/config.py`, `src/optimizer.py`, `src/clean_duplicates.py`, `src/tools/sanity_check.py`
- MEMORY.md — zaktualizowane

## Otwarte pytania

- Czy zrobić którykolwiek z odłożonych refaktorów (Fala 4 backlog), czy zostawić jako dług?
- Czy `optimizer` rozszerzony na pełny zestaw bibliotek (skaluje w miejscu) jest OK przy następnym uruchomieniu?

## Do MEMORY.md (przeniesiono)

- „Code-review całości repo — 4 fale napraw" (sekcja Rozwiązane problemy) z kluczowymi inwariantami:
  `_nkey` musi zawierać border_mode; widgety Tk tylko przez self.after; tofu wymaga reindeksacji; LIBRARY_DIRS w `src/library_dirs.py`
- „Refaktory świadomie odłożone po code-review" (sekcja Odrzucone podejścia)

# last_session.archive.md

## ═══ Sesja zarchiwizowana [2026-06-14 12:18] ═══

# last_session.md

**Sesja:** 2026-06-13 · 16:00-16:30
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** c57bc39 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dodać zoom-GIF dla spectre do README przez `make_zoom_gif.py` (sekcja „Zoom animations").**

Konkretnie:
1. Przejrzyj `src/tools/make_zoom_gif.py` — jak generuje GIF-y dla pozostałych 6 kształtów
   (wejściowa mozaika, poziomy zoomu, output do `docs/` lub `assets/`).
2. Wygeneruj zoom-GIF dla spectre (użyj istniejącego showcase spectre lub renderu papugi 8K).
3. Dopisz spectre do sekcji „Zoom animations" w `README.md` (obecnie 6 kształtów).

Kontekst: kliny krawędziowe — jedyny znany defekt jakościowy — zostały naprawione w tej
sesji (commit c57bc39, wypchnięty). Z backlogu zoom-GIF spectre jest najmniejszym domkniętym
zadaniem (galeria spectre i DZI już istnieją z 2026-06-12); naturalne uzupełnienie dokumentacji.

---

## Co zrobiono w tej sesji

- ✓ **Synchronizacja repo** — wypchnięte 2 zaległe commity (`094c8f4` .gitignore +
  `5820fb6` zapis sesji); origin/main zsynchronizowany na starcie
- ✓ **Czarne kliny krawędziowe NAPRAWIONE** (commit `c57bc39`): w gałęzi STANDARD GRID
  `engine_smart.py` zmiana `range(rows)`/`range(cols)` → `range(-1, rows)`/`range(-1, cols)`.
  Fantomowy wiersz/kolumna -1 wypełnia kliny na górnej/lewej krawędzi kształtów z offsetem
- ✓ **Weryfikacja założenia:** Pillow 11.1.0 przyjmuje ujemny `dest` w `alpha_composite`
  (test empiryczny — czerwień wlała się w (0,0))
- ✓ **Harness dark% (BEFORE/AFTER)** potwierdził delty na pasach krawędziowych top+left:
  romb 88.2%→0, hexagon 69.7%→0, hexagon_romb 69.5%→0, triangle 38.6%→0, brick_wall 21.4%→0;
  square i rectangle_3x1 (bez offsetu) bez zmian = zero regresji
- ✓ **182 passed**; commit `c57bc39` wypchnięty na origin/main
- ✓ Dodano notatkę `project_grid_edge_wedges.md` do MEMORY

## Co zostało (backlog sesji)

- ⟳ Zoom-GIF dla spectre do README (patrz NASTĘPNY KROK)
- ⟳ `padding=1.02` częściowo clippowany do płótna maski — świadomie zostawione
  (naprawa = powiększenie płótna masek we wszystkich kształtach, zysk znikomy)
- ⟳ Stary backlog UX z 2026-06-04 (auto-preview toggle, otwarcie folderu wyniku,
  podgląd pełnoekranowy, zapamiętywanie ustawień, statusbar, codename w tytule)

## Aktywne pliki

- `src/engine_smart.py` — fix klinów krawędziowych w pętli STANDARD GRID (zacommitowany c57bc39)
- MEMORY.md + `project_grid_edge_wedges.md` — zaktualizowane

## Otwarte pytania

- Czy rendery usera w `output/einstein hat/` zostawić (powstały przed usunięciem kształtu)?
- Kolejność reszty backlogu po zoom-GIF: UX czy padding masek?

## Do MEMORY.md (przeniesiono)

- `project_grid_edge_wedges.md` — pętle grid od -1 wypełniają kliny krawędziowe; Pillow
  przyjmuje ujemny dest, NIE clampować ujemnych px,py (przywróciłoby kliny) (2026-06-13)

## ═══ Sesja zarchiwizowana [2026-06-13 16:30] ═══

# last_session.md

**Sesja:** 2026-06-12 · 20:45-23:05
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 094c8f4 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wyeliminować czarne kliny przy górnej/lewej krawędzi siatek w `src/engine_smart.py`
(gałąź STANDARD GRID, pętla „Scanning grid...").**

Konkretnie: pętle `for r in range(rows)` / `for c in range(cols)` zaczynają od 0, więc
kształty z offsetem nieparzystych wierszy (hexagon, hexagon_romb, romb, brick_wall) i
trójkąty nie mają wiersza/kolumny „-1" — przy górnej i lewej krawędzi zostają czarne
kliny (zmierzono na syntetyku: romb ~8.6%, hexagon ~4.8% ciemnych px; większość to
kliny krawędziowe + szwy AA). Zmienić na `range(-1, rows)` / `range(-1, cols)` i
sprawdzić, że warunki `safe`/`px > target_w` poprawnie klipują ujemne pozycje
(meta px,py mogą być ujemne — Pillow 11.1 akceptuje ujemny dest w alpha_composite,
zweryfikowane w tej sesji). Weryfikacja: harness „dark%" z tej sesji (bright tiles,
target 801×603) — wartości powinny spaść do ~poziomu szwów AA.

Kontekst: jedyny pozostały defekt jakościowy znaleziony w code-review kształtów
(2026-06-12); wszystkie pozostałe punkty review już naprawione (commit dd4e5d6).

---

## Co zrobiono w tej sesji

- ✓ **Einstein hat** — pełna implementacja (substytucja H/T/P/F z arXiv:2303.10798,
  port hatviz): `src/hat_tiling.py`, integracja engine/GUI/CLI, 12 testów, showcase,
  pyramida DZI (commity e34d55c, 9b66704, 30d01ba, 127d323)
- ✓ **Bug pokrycia hat przy 8K+** znaleziony na renderze usera i naprawiony: margines
  przycinania proporcjonalny do przekątnej węzła + poziom zapasowy substytucji (9b66704)
- ✓ **Tile Library OOM naprawiony** (eaaffa7): paginacja `_LIB_PAGE_SIZE=200` +
  `_LIB_SCAN_CAP=2000` + przycisk Load More; zweryfikowane na żywym GUI z 455 448 plikami
  (pierwsza strona ~27 s, responsywne)
- ✓ **Spectre** — chiralny monotile (arXiv:2305.17743, port spectre.js Kaplana):
  `src/spectre_tiling.py` (9 metakafli, mystic Γ, dokładne bboxy bottom-up, wspólne
  recentrowanie ramki), integracja + 13 testów + showcase + DZI (3d55a6d, 127d323)
- ✓ **Decyzja usera: einstein_hat USUNIĘTY** (fe9db96) — kształty łudząco podobne,
  spectre mocniejszy matematycznie (zero odbić); prymitywy afiniczne przeniesione
  do spectre_tiling.py; viewer Pages: spectre = przycisk 5
- ✓ **Code-review pozostałych kształtów** + wszystkie poprawki (dd4e5d6): kite
  deterministyczny (seed RNG → naprawa cache sąsiadów i potencjalnego IndexError),
  mask-mean fill cech w kite, ValueError zamiast None z `_do_render`, licznik
  nieudanych kafelków, hexagon_romb bez pustych masek, float-stepy dla hexagon/romb
  (z weryfikacją zero-regresji względem HEAD dla wszystkich 7 kształtów siatkowych)
- ✓ Testy końcowe: **182 passed**; wszystko wypchnięte na origin/main
- ✓ `.gitignore` (konsolidacja backupów) zacommitowany (094c8f4)

## Co zostało (backlog sesji)

- ⟳ Czarne kliny przy krawędziach siatek (patrz NASTĘPNY KROK)
- ⟳ `padding=1.02` częściowo clippowany do płótna maski — świadomie zostawione
  (naprawa = powiększenie płótna masek we wszystkich kształtach, zysk znikomy)
- ⟳ Zoom-GIF dla spectre do README (`make_zoom_gif.py`) — sekcja „Zoom animations"
  ma 6 kształtów, spectre by ją uzupełnił
- ⟳ Stary backlog UX z 2026-06-04 (auto-preview toggle, otwarcie folderu wyniku itd.)

## Aktywne pliki

- `src/spectre_tiling.py` — NOWY, samodzielny (prymitywy afiniczne w środku)
- `src/engine_smart.py` — gałąź spectre + poprawki review (kite/grid/matching)
- `src/gui.py` — paginacja Tile Library + spectre w liście kształtów
- `src/cli.py`, `src/tools/make_showcase.py`, `tests/test_spectre_tiling.py`
- `docs/index.html` + `docs/tiles/showcase_spectre_*` — viewer Pages (5 mozaik)
- `README.md` — sekcja spectre + galeria (papuga 8K)

## Otwarte pytania

- Czy rendery usera w `output/einstein hat/` zostawić (powstały przed usunięciem kształtu)?
- Kolejność backlogu: kliny krawędziowe → zoom-GIF spectre → UX?

## Do MEMORY.md (przeniesiono)

- `project_spectre_only_no_hat.md` — einstein_hat usunięty (2026-06-12), zostaje spectre;
  nie proponować hat ponownie + notatki techniczne substytucji (wspólne recentrowanie!)
- `project_tile_library_scale_bug.md` — zaktualizowany: bug NAPRAWIONY (paginacja 200/stronę)
