## ═══ Sesja zarchiwizowana [2026-06-28 13:04] ═══

# last_session.md

**Sesja:** 2026-06-27 · 22:00-22:10
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** fae2ef5 @ main (origin ZSYNCHRONIZOWANY — push wykonany na starcie sesji, branch == origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Weryfikacja dostarczonych mozaik 16K + osadzenie w viewerze GitHub Pages (Krok 1 — live zoomable gallery hero).** User generuje sam 2 mozaiki 16K (foto + typo) wg ustalonych parametrów i przynosi do weryfikacji. Zadanie: sprawdzić jakość/rozpoznawalność makro + gęstość zoomu, zmierzyć realny rozmiar DZI (zastąpić szacunek 150–300 MB/szt. faktem), wyeksportować przez `make_dzi` / przycisk GUI „Export Deep Zoom", osadzić w `docs/` (OpenSeadragon na Pages) i dodać na górze README EN+PL wielki link „🔍 Open the live zoomable gallery".

Kontekst: faza portfolio = prezentacja, nie kod ([[project_portfolio_phase]]). Ustalono parametry „pod wow" (poniżej). Dopiero po pomiarze realnego DZI decyzja czy dokładamy 3. mozaikę (spectre/monotile).

---

## Co zrobiono w tej sesji

- ✓ **Push origin** — wypchnięto 2 zaległe commity `e6766b5..fae2ef5` (plan portfolio `c9f6101` + zapis sesji `fae2ef5`); branch == origin/main, CI zielony.
- ✓ **Ustalono budżet galerii** — Pages repo ~1 GB miękki limit; 16K DZI ~150–300 MB/szt. (mozaiki słabo kompresują JPEG przez gęste krawędzie). Plan: start od **2 mozaik**, zmierz, ew. dołóż spectre (~sufit 0.9 GB).
- ✓ **Ustalono parametry „pod wow"** (z realnych pokręteł GUI) — Foto: 16K, tile_scale 0.5, shape kite/hexagon_romb, blend 0%, tint 0%, border off. Typo: 16K, white_on_black, variation 5, 2–3 grupy fontów, scale 0.5–0.75. Mechanizm: iluzja dwóch skal.
- ✓ **MEMORY zaktualizowane** — [[project_portfolio_phase]] dostał blok „Ustalenia Krok 1 — galeria" z budżetem i parametrami; status = user generuje, przyniesie do weryfikacji.

## Co zostało (backlog sesji)

- ⟳ **Krok 1 (w toku):** weryfikacja mozaik → eksport DZI → osadzenie w `docs/` viewer → link hero w README EN+PL.
- ⟳ **PLAN_PORTFOLIO.md kroki 2–6:** GitHub social preview (1280×640) · sekcja Performance Engineering · post „aperiodic monotile mosaic" · zero-friction install (PyInstaller) · adwersarialny audyt twierdzeń README.
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1/A2), ML/CLIP, Docker/plugin. test_dzi (follow-up z A2).

## Aktywne pliki

- `PLAN_PORTFOLIO.md` (plan fazy), `README.md` + `README.pl.md` (dojdzie link hero)
- Do Kroku 1: `src/tools/make_dzi.py`, `src/gui.py` (przycisk „Export Deep Zoom"), `docs/` (OpenSeadragon viewer), `assets/examples/` (16K + `mosaic_zoom.gif`)

## Otwarte pytania

- Ile finalnie mozaik w galerii (2 vs +spectre) — rozstrzygnie pomiar realnego DZI.
- Social preview: kompozycja w CC czy layout na Claude.ai (web)?
- Dobór konkretnych obrazów-celów (wysoki kontrast, rozpoznawalny temat) — po stronie usera.

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [[project_portfolio_phase]] — dodano blok „Ustalenia Krok 1 — galeria (2026-06-27)": budżet Pages, parametry wow foto/typo, status „user generuje → weryfikacja w kolejnej sesji".

## ═══ Sesja zarchiwizowana [2026-06-27 22:10] ═══

# last_session.md

**Sesja:** 2026-06-27 · 20:30-21:40
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** c9f6101 @ main (UWAGA: branch ahead of origin o 1 commit — `c9f6101` plan portfolio niewypchnięty; README `e6766b5` już na origin)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Krok 1 z `PLAN_PORTFOLIO.md` — Live zoomable gallery jako HERO README.** Wygeneruj 1–2 prawdziwe mozaiki **16K** → DZI (gotowy `make_dzi` / przycisk GUI „Export Deep Zoom"), wrzuć do hostowanego viewera OpenSeadragon na GitHub Pages (dziś tylko „a handful of 8K", README l. 560), i dodaj na samej górze README (EN+PL) wielki link „🔍 Open the live zoomable gallery". Reuse `assets/examples/mosaic_zoom.gif`.

Kontekst: po domknięciu A1+A2 faza skupia się na PREZENTACJI/WIDOCZNOŚCI, nie kodzie ([[project_portfolio_phase]]). Krok 1 ma najwyższy ROI — infrastruktura DZI+Pages już istnieje i jest najbardziej niedoeksploatowana; daje efekt „wow" bez instalacji u odbiorcy. Krok 2 (GitHub social preview) łączy się naturalnie z tą samą pracą wizualną.

---

## Co zrobiono w tej sesji

- ✓ **Pomiar empiryczny peak-RAM 16K** — pełny `python -m tests.benchmark` (i5-12500H/16 wątków, CPU-only, indeks 454857). Peak RAM całego runu **3.90 GB** (vs ~10 GB analitycznie); per-op RAM+: 4K 1344 MB, 8K 1619 MB, 16K/kite 3212 MB, typo 255 MB. Bonus: render 3–5× szybszy (16K 21→5.9 min) — GEMM float32 wyparł cdist. Log: `logs/benchmark_16k_20260627.log`.
- ✓ **README EN+PL zaktualizowane** (`e6766b5`, wypchnięte) — tabela Performance (nowe czasy), nota Memory (~4 GB + „z ~10 GB"), Known Limitations, FAQ. Zweryfikowano brak zbłąkanego „~10 GB" (zostały tylko celowe „przed/po").
- ✓ **Push origin** — `4f01318..e6766b5`; objął też zaległy commit sesyjny `6c0ee46`. Origin był zsynchronizowany do tego momentu.
- ✓ **MEMORY zaktualizowane** — [[project_a1_memory_arch]] (pomiar 16K potwierdzony) + nowy wpis [[project_portfolio_phase]].
- ✓ **Prompt dla DriftScope** — gotowy do skopiowania prompt na dwujęzyczne README (EN źródłowe + PL), wzorzec przełącznika języka + zasady (badge CI tylko gdy workflow; polskie kotwice z diakrytykami). Tylko dostarczony userowi, nic w repo.
- ✓ **`PLAN_PORTFOLIO.md`** (`c9f6101`) — plan fazy portfolio, 6 zadań po ROI; decyzja: adwersarialni agenci ODRZUCENI dla appki desktop CPU-only.

## Co zostało (backlog sesji)

- ⟳ **PLAN_PORTFOLIO.md kroki 2–6:** GitHub social preview (1280×640) · sekcja Performance Engineering · post „aperiodic monotile mosaic" · zero-friction install (PyInstaller) · adwersarialny audyt twierdzeń README przed publikacją.
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1 pasmowa kanwa / A2 publish-to-viewer), kolejne ML/CLIP, Docker/plugin system. test_dzi (follow-up z A2).

## Aktywne pliki

- `PLAN_PORTFOLIO.md` (nowy plan — krok 1 do startu), `PLAN_PRAC.md` (A1+A2 — wszystko ✓)
- `README.md` + `README.pl.md` (Performance/Memory zaktualizowane)
- `tests/benchmark.py` (`PeakRAMSampler` — użyty do pomiaru), `logs/benchmark_16k_20260627.log`
- Do kroku 1: `src/tools/make_dzi.py`, `src/gui.py` (przycisk DZI), `docs/` (GitHub Pages viewer), `assets/examples/` (16K + zoom assety)

## Otwarte pytania

- Krok 1: ile mozaik 16K do galerii i jakie źródła? (limit storage GitHub Pages — README l. 560 wspomina o „lightweight").
- Social preview: kompozycja w CC czy layout na Claude.ai (web)?
- `c9f6101` (plan) niewypchnięty — wypchnąć na starcie kolejnej sesji czy zostawić.

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [[project_a1_memory_arch]] — dodano blok „POMIAR EMPIRYCZNY 16K POTWIERDZONY 2026-06-27" (peak 3.9 GB vs ~10 GB, README `e6766b5`); domyka jedyną otwartą pozycję A1.
- [[project_portfolio_phase]] — NOWY: faza portfolio, wow = prezentacja nie kod, adwersarialni agenci odrzuceni, lewary ROI, link do `PLAN_PORTFOLIO.md`.

## ═══ Sesja zarchiwizowana [2026-06-27 21:40] ═══

# last_session.md

**Sesja:** 2026-06-27 · 10:30-12:20
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 4f01318 @ main (origin zsynchronizowany — wszystko wypchnięte, CI zielony)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Brak twardego następnego kroku — plan A1+A2 i cały housekleeping domknięte i wypchnięte (CI run `28286897637` = success).** Do wyboru z backlogu poniżej; rekomendowany kandydat: **empiryczny pomiar zysku RAM na realnym renderze 16K** nowym `PeakRAMSampler` (`tests/benchmark.py`) — uruchom `python -m tests.benchmark` (pełny, ~30 min) lub punktowo `_do_render` spectre/kite 16K z `data/smart_index.pkl`, by udokumentować realny peak „przed/po" A-tani+B i wstawić liczby do tabeli Performance w README. To jedyne, co zostało z A1, a obecne liczby w README (~10 GB) są sprzed optymalizacji.

Kontekst: A1 (0+A-tani+B) i A2 (DZI) wdrożone i zweryfikowane (golden sha256, 173 testy), ale zysk RAM udowodniony jest tylko analitycznie/syntetycznie — brakuje pomiaru na produkcyjnym 16K. Pełna architektura: [[project_a1_memory_arch]], plan: `PLAN_PRAC.md`.

---

## Co zrobiono w tej sesji (2026-06-27)

- ✓ **PLAN_PRAC.md** — plan A1+A2 wg ryzyka (0→A-tani→A2→B + housekeeping), protokół „commit + pytanie po kroku".
- ✓ **A1-Wariant 0** (`5867a76`): `PeakRAMSampler` (daemon thread 50 ms) w `tests/benchmark.py`; pod indexing/render/typo + globalny peak runu. Smoke-test: łapie spike 200 MB gubiony przez stary pomiar.
- ✓ **A1-A-tani** (`4f178a3`): `_euclid_f32` (GEMM float32 in-place) zamiast `cdist`; adaptacyjny `chunk_size` ≤256 MB. Per-chunk 1.8 GB→0.25 GB (3.6→0.5 z mirrorem). Parytet vs cdist: max err 4.6e-6, top-k i zwycięzca po freq_penalty identyczne.
- ✓ **A2 eksport DZI** (`b33b5c2`): `make_dzi` skip_existing + `--no-skip`; CLI podkomenda `dzi`; przycisk GUI „Export Deep Zoom…" (wątek tła wzorem run_photo). E2E skip-if-exists potwierdzony.
- ✓ **A1-B leniwe maski** (`81a424a`): `_LazyMask` (wielokąt zamiast rezydentnego L-obrazu, rasteryzacja odroczona do kompozytu). Golden sha256 (kite+spectre × border) BIT-W-BIT identyczne; +5 testów regresji.
- ✓ **README EN+PL** (`85edada`): `--res 2K` dla typo (res_map ma 2K:2500); workflow/struktura → `library_*` + legacy `tiles/` z odnośnikiem do `src/library_dirs.py`.
- ✓ **Testy `dzi`** (`b300410`): +12 testów (parser, walidacja, pełne E2E w CI — make_dzi bez indeksu; idempotencja + `--no-skip`).
- ✓ **test_processor wrócił do CI** (`4f01318`): `importorskip("torch")` + `skipif(not cuda)`; zdjęty `--ignore` w ci.yml. CI bez torcha → moduł skip (udowodnione symulacją), dev → 4 zielone.
- ✓ **Push 8 commitów** (`c38c2d0..4f01318`) → origin/main; **CI run `28286897637` = success**.
- ✓ **MEMORY**: [[project_a1_memory_arch]] + [[project_a2_dzi_export_arch]] → WDROŻONE 2026-06-27; [[project_ci_pipeline]] → ignore tylko test_ai_core, wzorzec importorskip+skipif.
- ✓ **173 testy zielone** lokalnie (z GPU); 169 + test_processor self-skip w CI.

## Co zostało (backlog sesji)

- ⟳ **Empiryczny pomiar RAM 16K** (patrz NASTĘPNY KROK) — jedyne otwarte z A1; zaktualizować liczby Performance w README. NISKI.
- ⟳ Live demo: zróżnicowanie źródeł (triangle/photo = ta sama osoba); więcej mozaik 8K. NISKI.
- ⟳ Świadomie ODŁOŻONE: Wariant C w A1 (pasmowa kanwa) i A2 (publish-to-viewer); CoC/SECURITY.md/CITATION.cff/Docker/plugin system kształtów.

## Aktywne pliki

- `PLAN_PRAC.md` (plan 4/4 + housekeeping — wszystko ✓ poza pomiarem RAM)
- `tests/benchmark.py` (`PeakRAMSampler` — gotowy do pomiaru 16K), `src/engine_smart.py` (`_euclid_f32`, `_LazyMask`)
- `src/cli.py` / `src/gui.py` / `src/tools/make_dzi.py` (eksport DZI), `tests/test_cli.py` (+12 dzi), `tests/test_smart_engine.py` (+5 regresji)
- `tests/test_processor.py` + `.github/workflows/ci.yml` (test_processor w CI), `README.md` + `README.pl.md`

## Otwarte pytania

- Czy uruchomić pełny `python -m tests.benchmark` (~30 min) dla liczb 16K, czy punktowy pomiar tylko spectre/kite 16K?
- Czy po pomiarze zaktualizować sekcję „Memory" w README (obecne ~10 GB jest sprzed A-tani+B)?

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [[project_a1_memory_arch]] — WDROŻONE 2026-06-27: PeakRAMSampler + _euclid_f32 (inwariant: prawdziwy euklides) + _LazyMask (inwariant: render bit-w-bit)
- [[project_a2_dzi_export_arch]] — WDROŻONE 2026-06-27: make_dzi skip_existing + CLI `dzi` + przycisk GUI
- [[project_ci_pipeline]] — ignore TYLKO test_ai_core; test_processor wrócił przez importorskip+skipif; 173 testy lokalnie

## ═══ Sesja zarchiwizowana [2026-06-27 12:15] ═══

# last_session.md

**Sesja:** 2026-06-27 · checkpoint (sesja trwa)
**Status:** ⟳ W toku — A1+A2 wdrożone, housekeeping przed nami
**Punkt odniesienia (git):** 81a424a @ main (UWAGA: branch ahead of origin — niewypchnięte commity sesyjne + 4 nowe)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**A1+A2 WDROŻONE I ZACOMMITOWANE (4/4 kroki, golden sha256 + 157 testów zielonych).** Pozostało housekeeping z PLAN_PRAC.md:

1. **README ↔ kod (1 commit)**: dodać `--res 2K` dla typo do tabeli (silnik wspiera, zwalidowane); workflow wymienia 2 z 6 katalogów → uzupełnić. Decyzja: dokumentować, NIE blokować 2K.
2. **Test `dzi` w `test_cli.py`** (luka pokrycia z kroku A2 — świadomie pominięta na prośbę usera; parser + idempotencja skip-if-exists).
3. **`test_processor`**: twarda asercja CUDA → `skipif(not cuda)`, by wrócił do CI. NISKI.
4. Opcjonalnie: empiryczny pomiar zysku RAM nowym `PeakRAMSampler` na realnym 16K.
5. **Push** niewypchniętych commitów (branch ahead of origin).

Pełna architektura/inwarianty: [[project_a1_memory_arch]], [[project_a2_dzi_export_arch]], plan: `PLAN_PRAC.md`.

---

## Co zrobiono w tej sesji (2026-06-27)

- ✓ **PLAN_PRAC.md** — zapisany plan A1+A2 wg ryzyka (0→A-tani→A2→B), protokół „commit + pytanie po kroku".
- ✓ **A1-Wariant 0** (commit `5867a76`): `PeakRAMSampler` (daemon thread 50 ms) w `tests/benchmark.py`; podpięty pod indexing/render/typo + globalny peak runu. Smoke-test: łapie transient spike 200 MB, który stary pomiar gubił.
- ✓ **A1-A-tani** (commit `4f178a3`): `_euclid_f32` (GEMM float32 in-place) zastąpił `cdist`; adaptacyjny `chunk_size` ≤256 MB. Per-chunk 1.8 GB → 0.25 GB (3.6 → 0.5 GB z mirrorem). Parytet vs cdist: max err 4.6e-6, top-k i zwycięzca po freq_penalty identyczne.
- ✓ **A2 eksport DZI** (commit `b33b5c2`): `make_dzi` skip_existing + `--no-skip`; CLI podkomenda `dzi`; przycisk GUI „Export Deep Zoom…" (wątek tła wzorem run_photo). E2E: skip-if-exists potwierdzony.
- ✓ **A1-B leniwe maski** (commit `81a424a`): `_LazyMask` (wielokąt zamiast rezydentnego L-obrazu, rasteryzacja odroczona do kompozytu). Golden sha256 (kite+spectre × border) BIT-W-BIT identyczne przed/po. +5 testów regresji.
- ✓ **MEMORY zaktualizowane**: [[project_a1_memory_arch]] i [[project_a2_dzi_export_arch]] oznaczone WDROŻONE 2026-06-27 z inwariantami.
- ✓ **157 testów zielonych** (152 + 5 nowych regresji).

(Sesja kontynuowana po checkpoincie: README EN+PL, testy dzi, test_processor→CI, push 8 commitów — szczegóły w finalnym last_session.md sesji.)

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

_(starsze sesje usunięte — archiwum trzyma maks. 5 ostatnich)_

