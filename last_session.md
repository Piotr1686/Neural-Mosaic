# last_session.md

**Sesja:** 2026-06-26 · 21:00-22:30
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** c38c2d0 @ main (origin zsynchronizowany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Zacznij wdrożenie A1 od Wariantu 0 (warunek wstępny dla A+B):** dodaj wiarygodny pomiar peak-RAM przez wątek samplujący `psutil.Process().memory_info().rss` co ~50 ms wokół renderu w `tests/benchmark.py` (zastępując obecny niewiarygodny `_rss_mb() - ram0` z linii 108/133, który mierzy tylko przed/po i gubi transient spike). To daje liczbę bazową „przed" dla Wariantu A-tani i równocześnie zalicza backlog „benchmark.py peak-RAM".

Kontekst: A1 i A2 mają zatwierdzoną architekturę (decyzja usera 2026-06-26), implementacja miała ruszyć od TEJ następnej sesji. Wariant 0 jest warunkiem wstępnym — bez wiarygodnego pomiaru nie udowodnimy efektu A-tani (cdist float64 3.6 GB → float32 ~0.25 GB). Pełna architektura: [[project_a1_memory_arch]], [[project_a2_dzi_export_arch]].

---

## Co zrobiono w tej sesji (2026-06-26)

- ✓ **Walidacja `requirements.txt` w CZYSTYM venv (definitywny dowód)**: świeży venv Python 3.10.19, `pip install -r requirements.txt` (44 pakiety, bez torch/transformers); `import src.gui` OK (bez `ModuleNotFoundError: matplotlib`); render `typo 4K` (33004 glify, `fonttools`) i `smart 2K` (454857 kafelków, cKDTree) przeszły; `torch=False, transformers=False`. Obietnica README „4 linie i działa" udowodniona empirycznie. (SSL w gołym venv → `--trusted-host`; lokalne certy, nie problem requirements.)
- ✓ **Push zaległego commitu sesyjnego** `f927696`.
- ✓ **README dwujęzyczny EN/PL** (commit `ab32e7e`): pełny `README.pl.md` (25 sekcji, parytet z EN), przełącznik `**English** · [Polski]` w linii 3 obu plików; kotwice TOC z polskimi diakrytykami.
- ✓ **CI z czerwonego na zielony + realne testy** (`db427b3`, `cf91769`, `c38c2d0`): install z `requirements.txt` (koniec driftu — padał `tqdm`); `python -m pytest` → **152 testy** w CI (pominięte test_ai_core/test_processor = torch/GPU); bump `checkout@v5`/`setup-python@v6`. Inwariant: [[project_ci_pipeline]].
- ✓ **GitHub „About"** (`gh repo edit`): description, homepage→live-demo, 10 topics; korekta `opencv`→`scikit-image` (cv2 nieimportowane).
- ✓ **/architect A1** (peak-RAM 16K) — atrybucja peaku (spike cdist float64 ~3.6 GB, nie kanwa); zatwierdzony zakres **0 + A-tani + B**, C odłożony. → [[project_a1_memory_arch]]
- ✓ **/architect A2** (eksport DZI) — `make_dzi.py` już gotowy; zatwierdzony **Wariant B (osobny przycisk) + skip-if-exists + podkomenda CLI `dzi`**, C (publikacja do viewera) odłożony. → [[project_a2_dzi_export_arch]]

## Co zostało (backlog sesji)

- ⟳ **Wdrożenie A1** = Wariant 0 → A-tani (`engine_smart._do_render:658-668`; de-eskalacja `/sonnet` OK) → B (leniwe maski spectre/kite `:729`, `:303`; HIGH, test regresji pikselowej). C ODŁOŻONY.
- ⟳ **Wdrożenie A2** = Wariant B (przycisk „Export Deep Zoom…", wzorzec `gui.py:run_photo:991-1006`) + skip-if-exists + `dzi` w `src/cli.py`. C ODŁOŻONY.
- ⟳ `test_processor`: twardo asertuje CUDA → `skipif(not cuda)`, by wrócił do CI. NISKI.
- ⟳ Drobne README↔kod: typo wspiera `--res 2K` (README mówi 4K/8K/16K); workflow wymienia 2 z 6 katalogów.
- ⟳ Live demo: zróżnicowanie źródeł (triangle/photo = ta sama osoba); więcej mozaik 8K. NISKI.
- ⟳ Świadomie odrzucone (over-engineering solo-portfolio): CoC, SECURITY.md, CITATION.cff, Docker/cross-platform, plugin system kształtów, Wariant C w A1 i A2.

## Aktywne pliki

- `tests/benchmark.py` (NASTĘPNY KROK: sampling-thread peak-RAM; obecny pomiar `:108`/`:133` niewiarygodny)
- `src/engine_smart.py` (A1: pętla matchingu `:658-668` float32; maski spectre/kite `:303`,`:729`)
- `src/gui.py` (A2: przycisk Export DZI, wzorzec `:991-1006`), `src/cli.py` (A2: podkomenda `dzi`), `src/tools/make_dzi.py` (gotowy, reuse)
- `.github/workflows/ci.yml`, `README.md` + `README.pl.md`, `requirements.txt` (zwalidowany) — wszystko pushed

## Otwarte pytania

- Czy A2 wdrażać po A1, czy równolegle? (architektury niezależne — można równolegle)
- Czy udokumentować/zablokować `--res 2K` dla typo (silnik wspiera, README nie)?
- Czy zróżnicować pozostałe źródła live-demo? (rekomendacja: niski priorytet)

## Do MEMORY.md (przeniesiono w tej sesji)

- [[project_ci_pipeline]] — inwarianty CI (install z requirements.txt, `python -m pytest`, ignore test_ai_core+test_processor); 152 testy (2026-06-26)
- [[project_a1_memory_arch]] — A1 peak-RAM: zatwierdzone 0+A-tani+B; peak = spike cdist float64, nie kanwa; C odłożony (2026-06-26)
- [[project_a2_dzi_export_arch]] — A2 eksport DZI: Wariant B + skip-if-exists + CLI `dzi`; make_dzi.py gotowy; C odłożony (2026-06-26)
- [[project_requirements_curated]] — zaktualizowany: ZWALIDOWANY w czystym venv (2026-06-26)
